"""
backend/tracking/tracker.py
-----------------------------
Within-camera object tracker using supervision's ByteTrack wrapper.

Assigns and maintains persistent local track_id values for each detected
entity within one camera's stream.  One Tracker instance per camera.

Phase: 2
"""

from __future__ import annotations

import logging
from typing import List

import numpy as np

from backend.ingestion.frame_model import Detection
from backend.config.settings import settings

logger = logging.getLogger(__name__)


class WithinCameraTracker:
    """
    Wraps supervision's ByteTrack to track detections within one camera stream.

    Parameters
    ----------
    camera_id   : Used in log messages.
    """

    def __init__(self, camera_id: str):
        self.camera_id = camera_id
        try:
            import supervision as sv
            self._tracker = sv.ByteTrack(
                lost_track_buffer=settings.tracking.max_lost_frames,
                minimum_matching_threshold=0.8,
                minimum_consecutive_frames=settings.tracking.min_hits,
            )
        except ImportError as exc:
            raise ImportError(
                "supervision is not installed. Run: pip install supervision"
            ) from exc
        logger.info("[Tracker][%s] ByteTrack tracker initialised.", camera_id)

    def update(self, detections: List[Detection], frame_shape: tuple) -> List[Detection]:
        """
        Update tracker with the current frame's detections.

        Returns the same Detection list with track_id fields populated.
        Detections that the tracker drops (low-confidence spurious boxes)
        are returned with track_id=None.
        """
        import supervision as sv

        if not detections:
            # Feed empty frame to ByteTrack so it can age out lost tracks
            empty = sv.Detections.empty()
            self._tracker.update_with_detections(empty)
            return detections

        # Build supervision Detections object
        boxes = np.array([list(d.bbox) for d in detections], dtype=np.float32)
        confs = np.array([d.confidence for d in detections], dtype=np.float32)
        class_ids = np.zeros(len(detections), dtype=int)   # all same class for now

        sv_dets = sv.Detections(
            xyxy=boxes,
            confidence=confs,
            class_id=class_ids,
        )

        tracked = self._tracker.update_with_detections(sv_dets)

        # Map tracker IDs back to Detection objects by box position
        # ByteTrack returns results in the same order as input when all match
        id_map: dict[int, int] = {}   # detection_index → tracker_id
        if tracked.tracker_id is not None:
            for i, tid in enumerate(tracked.tracker_id):
                if i < len(detections):
                    id_map[i] = int(tid)

        for i, det in enumerate(detections):
            det.track_id = id_map.get(i, None)

        return detections
