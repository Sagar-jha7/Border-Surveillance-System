"""
backend/detection/tier3_motion.py
-----------------------------------
Tier-3 Detection: Verified Unidentified Object Interceptor with Wind & Noise Filtering.

Filters out:
  - Wind-blown grass/trees and camera sensor compression noise.
  - Single-frame lighting fluctuations or pixel jitter.

Only emits genuine moving objects (crawling infiltrators, camouflaged entities,
drones, creeping objects) that exhibit coherent temporal persistence across frames.
"""

from __future__ import annotations

import logging
import time
from typing import List, Tuple

import cv2
import numpy as np

from backend.ingestion.frame_model import Detection, Frame, SOURCE_TIER3
from backend.config.settings import settings

logger = logging.getLogger(__name__)


class MotionTrackCandidate:
    def __init__(
        self,
        cx: float,
        cy: float,
        bbox: Tuple[float, float, float, float],
        area: float,
        object_score: float,
    ):
        self.cx = cx
        self.cy = cy
        self.first_cx = cx
        self.first_cy = cy
        self.bbox = bbox
        self.area = area
        self.first_seen = time.time()
        self.hits = 1
        self.last_seen = time.time()
        self.scores = [object_score]
        self.areas = [area]

    def update(self, cx: float, cy: float, bbox: Tuple[float, float, float, float], area: float, object_score: float) -> None:
        self.cx = cx
        self.cy = cy
        self.bbox = bbox
        self.area = area
        self.hits += 1
        self.last_seen = time.time()
        self.scores = (self.scores + [object_score])[-12:]
        self.areas = (self.areas + [area])[-12:]

    @property
    def age_seconds(self) -> float:
        return self.last_seen - self.first_seen

    @property
    def displacement(self) -> float:
        return float(np.hypot(self.cx - self.first_cx, self.cy - self.first_cy))

    @property
    def average_score(self) -> float:
        return float(np.mean(self.scores)) if self.scores else 0.0

    @property
    def area_stability(self) -> float:
        if len(self.areas) < 4:
            return 0.0
        mean_area = float(np.mean(self.areas))
        if mean_area <= 0:
            return 0.0
        return 1.0 - min(1.0, float(np.std(self.areas)) / mean_area)


class Tier3MotionDetector:
    """
    Temporal Persistence Motion Filter:
    - Adaptive background subtractor with high shadow suppression.
    - Morphological noise suppression.
    - Multi-frame temporal persistence gate (rejects isolated wind/noise spikes).
    """

    def __init__(self, camera_id: str):
        self.camera_id = camera_id
        self._subtractor = cv2.createBackgroundSubtractorMOG2(
            history=400,
            varThreshold=24,
            detectShadows=True,
        )
        self._kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        self._candidates: List[MotionTrackCandidate] = []
        logger.info("[Tier3][%s] Border-grade motion filter initialised.", camera_id)

    def detect(self, frame: Frame) -> List[Detection]:
        min_area = float(max(settings.detection.tier3_min_contour_area, 900))
        now = time.time()
        frame_h, frame_w = frame.img.shape[:2]
        frame_area = float(frame_h * frame_w)

        # Bilateral / Gaussian blur to cancel sensor grain and wind jitter
        gray = cv2.cvtColor(frame.img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (9, 9), 0)

        # Foreground mask
        fg_mask = self._subtractor.apply(blurred)
        _, fg_mask = cv2.threshold(fg_mask, 200, 255, cv2.THRESH_BINARY)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, self._kernel)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, self._kernel)

        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        foreground_ratio = float(cv2.countNonZero(fg_mask)) / max(1.0, frame_area)
        if foreground_ratio > 0.16:
            logger.debug("[Tier3][%s] suppressing global motion: %.2f%% foreground", self.camera_id, foreground_ratio * 100)
            self._candidates = []
            return []

        current_blobs: List[Tuple[float, float, Tuple[float, float, float, float], float, float]] = []
        significant_contours = 0

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < min_area:
                continue
            significant_contours += 1

            x, y, w, h = cv2.boundingRect(cnt)
            bbox_area = float(w * h)
            if w < 20 or h < 20:
                continue
            if bbox_area > frame_area * 0.28:
                continue

            # Aspect ratio check: avoid extreme horizontal/vertical noise streaks
            aspect_ratio = float(w) / max(1.0, float(h))
            if aspect_ratio > 5.0 or aspect_ratio < 0.20:
                continue

            extent = area / max(1.0, bbox_area)
            if extent < 0.24:
                continue

            hull = cv2.convexHull(cnt)
            hull_area = cv2.contourArea(hull)
            solidity = area / max(1.0, hull_area)
            if solidity < 0.42:
                continue

            perimeter = cv2.arcLength(cnt, True)
            compactness = (4.0 * np.pi * area) / max(1.0, perimeter * perimeter)
            if compactness < 0.035:
                continue

            cx = x + w / 2.0
            cy = y + h / 2.0
            bbox = (float(x), float(y), float(x + w), float(y + h))
            object_score = min(1.0, (extent * 0.40) + (solidity * 0.40) + (compactness * 0.20))
            current_blobs.append((cx, cy, bbox, area, object_score))

        if significant_contours > 18 and len(current_blobs) > 6:
            logger.debug("[Tier3][%s] suppressing noisy scene: %d significant contours", self.camera_id, significant_contours)
            return []

        # Temporal Association & Persistence Check
        updated_candidates: List[MotionTrackCandidate] = []
        confirmed_detections: List[Detection] = []

        for cx, cy, bbox, area, object_score in current_blobs:
            matched = False
            for cand in self._candidates:
                dist = np.hypot(cx - cand.cx, cy - cand.cy)
                match_radius = max(42.0, min(90.0, np.sqrt(area) * 1.15))
                if dist < match_radius:  # Moving in nearby neighborhood
                    cand.update(cx, cy, bbox, area, object_score)
                    matched = True
                    updated_candidates.append(cand)

                    # Border-grade unidentified gate: persistent, coherent, object-like motion only.
                    enough_history = cand.hits >= 8 and cand.age_seconds >= 0.35
                    stable_shape = cand.area_stability >= 0.45
                    object_like = cand.average_score >= 0.34
                    has_motion = cand.displacement >= 6.0 or cand.hits >= 12
                    if enough_history and stable_shape and object_like and has_motion:
                        persistence_score = min(1.0, cand.hits / 16.0)
                        size_score = min(1.0, area / 6500.0)
                        intensity = min(1.0, (cand.average_score * 0.45) + (persistence_score * 0.35) + (size_score * 0.20))
                        confirmed_detections.append(
                            Detection(
                                category="Unidentified",
                                confidence=round(intensity, 2),
                                bbox=bbox,
                                source_tier=SOURCE_TIER3,
                                camera_id=frame.camera_id,
                                location=frame.location,
                                timestamp=frame.timestamp,
                            )
                        )
                    break

            if not matched:
                updated_candidates.append(MotionTrackCandidate(cx, cy, bbox, area, object_score))

        # Retain active candidates briefly; short gaps happen on weak phone streams.
        self._candidates = [c for c in updated_candidates if (now - c.last_seen) < 1.2]

        return confirmed_detections
