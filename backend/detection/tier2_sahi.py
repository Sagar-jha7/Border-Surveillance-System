"""
backend/detection/tier2_sahi.py
---------------------------------
Tier-2 Detection: YOLOv8 + SAHI (Slicing Aided Hyper Inference).

Designed to catch small or aerial objects (drones, small vehicles, birds
at distance) that are missed by standard full-frame inference.

All detections from this tier are labelled category="Drone" by default.
(In a future fine-tuning phase, the category can be refined to "UAV",
"Paraglider", etc. — the COCO_TO_CATEGORY override in merger.py handles this.)

Phase: 3
"""

from __future__ import annotations

import logging
import os
from typing import List, Optional

from backend.ingestion.frame_model import Detection, Frame, SOURCE_TIER2
from backend.config.settings import settings

logger = logging.getLogger(__name__)


class Tier2SAHIDetector:
    """
    SAHI slicing detector for small/aerial objects.

    Instantiate once; call detect(frame) per frame.
    """

    def __init__(self, model_path: str = "yolov8n.pt", device: str | None = None):
        try:
            from sahi import AutoDetectionModel
            from sahi.predict import get_sliced_prediction
        except ImportError as exc:
            raise ImportError("sahi is not installed. Run: pip install sahi") from exc

        self._get_sliced_prediction = get_sliced_prediction
        self._device = device or os.environ.get("YOLO_DEVICE", "cpu")

        logger.info("[Tier2] Loading SAHI model '%s' on '%s'", model_path, self._device)
        self._detection_model = AutoDetectionModel.from_pretrained(
            model_type="yolov8",
            model_path=model_path,
            confidence_threshold=settings.detection.day_confidence,
            device=self._device,
        )
        logger.info("[Tier2] SAHI model ready.")

    def detect(self, frame: Frame, confidence: float | None = None) -> List[Detection]:
        """Run SAHI sliced inference on the frame. Returns Detection list."""
        from PIL import Image as PILImage
        import cv2

        cfg = settings.detection
        conf = confidence or (
            cfg.night_confidence
            if frame.compute_brightness() < cfg.night_brightness_threshold
            else cfg.day_confidence
        )

        # SAHI expects RGB PIL image
        rgb = cv2.cvtColor(frame.img, cv2.COLOR_BGR2RGB)
        pil_img = PILImage.fromarray(rgb)

        try:
            result = self._get_sliced_prediction(
                image=pil_img,
                detection_model=self._detection_model,
                slice_height=cfg.tier2_slice_height,
                slice_width=cfg.tier2_slice_width,
                overlap_height_ratio=cfg.tier2_overlap_ratio,
                overlap_width_ratio=cfg.tier2_overlap_ratio,
                postprocess_type="NMS",
                verbose=0,
            )
        except Exception as exc:
            logger.error("[Tier2][%s] SAHI inference error: %s", frame.camera_id, exc)
            return []

        detections: List[Detection] = []
        for obj in result.object_prediction_list:
            if obj.score.value < conf:
                continue
            bb = obj.bbox
            detections.append(
                Detection(
                    category="Drone",
                    confidence=float(obj.score.value),
                    bbox=(bb.minx, bb.miny, bb.maxx, bb.maxy),
                    source_tier=SOURCE_TIER2,
                    camera_id=frame.camera_id,
                    location=frame.location,
                    timestamp=frame.timestamp,
                )
            )
        return detections
