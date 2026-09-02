"""
backend/alerts/section_coordinator.py
--------------------------------------
Centralized 6-Section Intelligence Coordinator with Anti-Spam Debouncing & Border-Grade Reliability.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

import cv2
import numpy as np

from backend.ingestion.frame_model import Detection, Frame, SOURCE_TIER1, SOURCE_TIER2, SOURCE_TIER3
from backend.alerts.schema import Alert, AlertPriority, SectionType, SECTION_TITLES, BoundingBox
from backend.reid.matcher import CrossCameraReIDMatcher

logger = logging.getLogger("SectionCoordinator")


class SectionCoordinator:
    """
    Categorizes all pipeline detections into the 6 tactical sections with intelligent debouncing.
    """

    def __init__(self, camera_id: str, location: str, reid_matcher: Optional[CrossCameraReIDMatcher] = None):
        self.camera_id = camera_id
        self.location = location
        self.reid_matcher = reid_matcher or CrossCameraReIDMatcher()

        # Appearance gallery for Section 4
        self._appearance_gallery: Dict[int, dict] = {}
        # Multi-sector tracking points for Section 5
        self._recent_incursion_points: List[Tuple[float, float, float]] = []

        # Anti-spam cooldown tracking (key -> last_alert_time)
        self._alert_cooldowns: Dict[str, float] = {}

    def _should_emit(self, key: str, cooldown_seconds: float = 3.5) -> bool:
        now = time.time()
        last_time = self._alert_cooldowns.get(key, 0.0)
        if (now - last_time) >= cooldown_seconds:
            self._alert_cooldowns[key] = now
            return True
        return False

    def _extract_appearance_vector(self, frame_img: np.ndarray, bbox: Tuple[float, float, float, float]) -> Optional[np.ndarray]:
        x1, y1, x2, y2 = [int(v) for v in bbox]
        h, w = frame_img.shape[:2]
        crop = frame_img[max(0, y1):min(h, y2), max(0, x1):min(w, x2)]
        if crop.size < 200:
            return None
        hist = cv2.calcHist([crop], [0, 1, 2], None, [6, 6, 6], [0, 256, 0, 256, 0, 256])
        return cv2.normalize(hist, hist).flatten()

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        na, nb = np.linalg.norm(a), np.linalg.norm(b)
        if na == 0 or nb == 0:
            return 0.0
        return float(np.dot(a, b) / (na * nb))

    def process(
        self,
        frame: Frame,
        t1_dets: List[Detection],
        t3_dets: List[Detection],
        tracked_dets: List[Detection],
        boundary_line: Optional[Tuple[Tuple[int, int], Tuple[int, int]]] = None,
    ) -> List[Alert]:
        alerts: List[Alert] = []
        now_ts = datetime.utcnow()
        now_sec = time.time()
        h, w = frame.img.shape[:2]
        mid_y = boundary_line[0][1] if boundary_line else h // 2

        # ------------------------------------------------------------------
        # SECTION 1: Standard Reconnaissance (Person / Vehicle / Animal)
        # ------------------------------------------------------------------
        for det in tracked_dets:
            if det.category in ["Person", "Vehicle", "Animal", "Car", "Truck", "Bicycle", "Dog", "Bird"]:
                is_crossing = abs(det.cy - mid_y) < (h * 0.09)
                tid = det.track_id or 0

                # Separate cooldowns for regular presence vs. critical crossing
                if is_crossing:
                    if self._should_emit(f"s1_cross_{tid}", cooldown_seconds=4.0):
                        alerts.append(
                            Alert(
                                timestamp=now_ts,
                                section=1,
                                section_title=SECTION_TITLES[1],
                                camera_id=self.camera_id,
                                location=self.location,
                                category=det.category,
                                priority=AlertPriority.RED,
                                description=f"CRITICAL BREACH: {det.category} #{tid} crossed virtual border boundary!",
                                bboxes=[BoundingBox(x1=det.bbox[0], y1=det.bbox[1], x2=det.bbox[2], y2=det.bbox[3])],
                                track_ids=[tid],
                                global_id=det.global_id,
                                is_crossing=True,
                            )
                        )
                else:
                    if self._should_emit(f"s1_det_{tid}", cooldown_seconds=3.0):
                        alerts.append(
                            Alert(
                                timestamp=now_ts,
                                section=1,
                                section_title=SECTION_TITLES[1],
                                camera_id=self.camera_id,
                                location=self.location,
                                category=det.category,
                                priority=AlertPriority.BLUE,
                                description=f"Target Verified: {det.category} #{tid} active in surveillance sector",
                                bboxes=[BoundingBox(x1=det.bbox[0], y1=det.bbox[1], x2=det.bbox[2], y2=det.bbox[3])],
                                track_ids=[tid],
                                global_id=det.global_id,
                                is_crossing=False,
                            )
                        )

        # ------------------------------------------------------------------
        # SECTION 2: Aerial & Small Object Interception (Drone & Small Objects)
        # ------------------------------------------------------------------
        for det in tracked_dets:
            is_aerial = det.cy < (h * 0.40)
            is_small = det.area < 2500
            tid = det.track_id or 0
            if det.category == "Drone" or (is_aerial and is_small and det.category not in ["Person", "Vehicle"]):
                if self._should_emit(f"s2_drone_{tid}", cooldown_seconds=3.5):
                    alerts.append(
                        Alert(
                            timestamp=now_ts,
                            section=2,
                            section_title=SECTION_TITLES[2],
                            camera_id=self.camera_id,
                            location=self.location,
                            category="Drone",
                            priority=AlertPriority.RED if det.cy > (h * 0.25) else AlertPriority.AMBER,
                            description=f"Airspace Threat: Drone / Small Aerial Object intercepted at Y:{int(det.cy)}px",
                            bboxes=[BoundingBox(x1=det.bbox[0], y1=det.bbox[1], x2=det.bbox[2], y2=det.bbox[3])],
                            track_ids=[tid],
                            global_id=det.global_id,
                        )
                    )

        # ------------------------------------------------------------------
        # SECTION 3: Mass Infiltration & Crowd Grouping (Large Numbers)
        # ------------------------------------------------------------------
        active_entities = [d for d in tracked_dets if d.track_id is not None]
        clusters: List[List[Detection]] = []
        assigned = [False] * len(active_entities)

        for i, d1 in enumerate(active_entities):
            if assigned[i]:
                continue
            cluster = [d1]
            assigned[i] = True
            for j, d2 in enumerate(active_entities):
                if assigned[j] or i == j:
                    continue
                dist = np.hypot(d1.cx - d2.cx, d1.cy - d2.cy)
                if dist < 120.0:
                    cluster.append(d2)
                    assigned[j] = True
            if len(cluster) >= 2:
                clusters.append(cluster)

        for cl in clusters:
            n = len(cl)
            tids = [d.track_id for d in cl if d.track_id is not None]
            group_key = f"s3_group_{'_'.join(str(t) for t in sorted(tids))}"
            if self._should_emit(group_key, cooldown_seconds=3.5):
                is_crossing = any(abs(d.cy - mid_y) < (h * 0.09) for d in cl)
                alerts.append(
                    Alert(
                        timestamp=now_ts,
                        section=3,
                        section_title=SECTION_TITLES[3],
                        camera_id=self.camera_id,
                        location=self.location,
                        category="Group",
                        priority=AlertPriority.RED if is_crossing else AlertPriority.AMBER,
                        description=f"Mass Incursion: Formation of {n} entities detected moving together (Tracks: #{', #'.join(str(t) for t in tids)})",
                        bboxes=[BoundingBox(x1=d.bbox[0], y1=d.bbox[1], x2=d.bbox[2], y2=d.bbox[3]) for d in cl],
                        track_ids=tids,
                        group_size=n,
                        is_crossing=is_crossing,
                    )
                )

        # ------------------------------------------------------------------
        # SECTION 4: Visual Identity & Cross-Frame Re-ID Matcher
        # ------------------------------------------------------------------
        for det in tracked_dets:
            if det.track_id is not None:
                tid = det.track_id
                emb = self._extract_appearance_vector(frame.img, det.bbox)
                if emb is not None:
                    best_match_id = None
                    best_sim = 0.0

                    for hist_id, entry in self._appearance_gallery.items():
                        if hist_id == tid:
                            continue
                        sim = self._cosine_similarity(emb, entry["embedding"])
                        if sim > best_sim:
                            best_sim = sim
                            best_match_id = hist_id

                    if best_match_id is not None and best_sim > 0.74:
                        if self._should_emit(f"s4_reid_{tid}_{best_match_id}", cooldown_seconds=4.5):
                            match_pct = int(best_sim * 100)
                            alerts.append(
                                Alert(
                                    timestamp=now_ts,
                                    section=4,
                                    section_title=SECTION_TITLES[4],
                                    camera_id=self.camera_id,
                                    location=self.location,
                                    category="ReID-Match",
                                    priority=AlertPriority.AMBER,
                                    description=f"Visual Identity Match: Track #{tid} confirmed identical to Target #{best_match_id} ({match_pct}% signature confidence)",
                                    bboxes=[BoundingBox(x1=det.bbox[0], y1=det.bbox[1], x2=det.bbox[2], y2=det.bbox[3])],
                                    track_ids=[tid, best_match_id],
                                    similarity_score=round(best_sim, 2),
                                )
                            )

                    self._appearance_gallery[tid] = {
                        "embedding": emb,
                        "category": det.category,
                        "timestamp": now_sec,
                    }

        # ------------------------------------------------------------------
        # SECTION 5: Multi-Sector Simultaneous Incursions (Dispersed Points)
        # ------------------------------------------------------------------
        current_points = [(d.cx, d.cy, now_sec) for d in tracked_dets if d.track_id is not None]
        self._recent_incursion_points = [p for p in self._recent_incursion_points if (now_sec - p[2]) < 4.0]
        self._recent_incursion_points.extend(current_points)

        total_simultaneous_points = len(self._recent_incursion_points)
        if total_simultaneous_points >= 3:
            if self._should_emit("s5_multipoint", cooldown_seconds=4.0):
                alerts.append(
                    Alert(
                        timestamp=now_ts,
                        section=5,
                        section_title=SECTION_TITLES[5],
                        camera_id=self.camera_id,
                        location=self.location,
                        category="Multi-Sector",
                        priority=AlertPriority.RED if total_simultaneous_points >= 5 else AlertPriority.AMBER,
                        description=f"Multi-Point Activity: {total_simultaneous_points} simultaneous incursion coordinates active across sector grid",
                        incursion_points_count=total_simultaneous_points,
                        bboxes=[BoundingBox(x1=d.bbox[0], y1=d.bbox[1], x2=d.bbox[2], y2=d.bbox[3]) for d in tracked_dets],
                    )
                )

        # ------------------------------------------------------------------
        # SECTION 6: Verified Unidentified Objects
        # ------------------------------------------------------------------
        known_boxes = [d.bbox for d in tracked_dets if d.category in ["Person", "Vehicle", "Animal", "Drone"]]

        for m_det in t3_dets:
            overlaps_known = False
            for kb in known_boxes:
                if (m_det.bbox[0] < kb[2] and m_det.bbox[2] > kb[0] and
                    m_det.bbox[1] < kb[3] and m_det.bbox[3] > kb[1]):
                    overlaps_known = True
                    break

            if not overlaps_known:
                # Tier-3 is already temporally gated; keep alerts reserved for clear unidentified objects.
                if m_det.confidence >= 0.48 and m_det.area >= 900:
                    motion_key = f"s6_motion_{int(m_det.cx / 60)}_{int(m_det.cy / 60)}"
                    if self._should_emit(motion_key, cooldown_seconds=10.0):
                        alerts.append(
                            Alert(
                                timestamp=now_ts,
                                section=6,
                                section_title=SECTION_TITLES[6],
                                camera_id=self.camera_id,
                                location=self.location,
                                category="Unidentified",
                                priority=AlertPriority.GRAY,
                                description=f"Verified Unidentified Object: persistent object-like movement at ({int(m_det.cx)}, {int(m_det.cy)})",
                                bboxes=[BoundingBox(x1=m_det.bbox[0], y1=m_det.bbox[1], x2=m_det.bbox[2], y2=m_det.bbox[3])],
                                unidentified_confidence=m_det.confidence,
                            )
                        )

        # Cleanup expired cooldown keys
        if len(self._alert_cooldowns) > 200:
            self._alert_cooldowns = {k: v for k, v in self._alert_cooldowns.items() if (now_sec - v) < 20.0}

        return alerts
