"""
backend/detection/visualizer.py
--------------------------------
Draw detection bounding boxes on a frame for preview windows and
streaming to the dashboard.

Used by:
  - Phase 1: OpenCV preview window in pipeline.py
  - Phase 2+: Encode annotated frame as JPEG and push over WebSocket

Color scheme (BGR):
  Person       → green   (0, 255, 0)
  Vehicle      → blue    (255, 100, 0)
  Animal       → yellow  (0, 220, 220)
  Drone        → red     (0, 0, 255)
  Unidentified → white   (200, 200, 200)
  Other        → magenta (255, 0, 255)
  Crossing!    → bright orange  (0, 165, 255)  [Phase 3+]
"""

from __future__ import annotations

from typing import List, Optional, Tuple

import cv2
import numpy as np

from backend.ingestion.frame_model import Detection, Frame

# ---------------------------------------------------------------------------
# Colour palette (BGR)
# ---------------------------------------------------------------------------

CATEGORY_COLORS: dict[str, Tuple[int, int, int]] = {
    "Person":        (0, 220, 0),
    "Vehicle":       (230, 80, 0),
    "Animal":        (0, 200, 200),
    "Drone":         (0, 0, 255),
    "Unidentified":  (180, 180, 180),
}
DEFAULT_COLOR: Tuple[int, int, int] = (255, 0, 255)   # magenta for unknown labels
CROSSING_COLOR: Tuple[int, int, int] = (0, 165, 255)  # orange for boundary crossing

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def draw_detections(
    frame: Frame,
    detections: List[Detection],
    boundary_line: Optional[Tuple[Tuple[int, int], Tuple[int, int]]] = None,
    crossing_ids: Optional[set] = None,
    show_tier: bool = False,
) -> np.ndarray:
    """
    Draw bounding boxes and labels onto a copy of frame.img.

    Parameters
    ----------
    frame           : Source frame (not modified in place).
    detections      : List of Detection objects to draw.
    boundary_line   : Optional ((x1,y1),(x2,y2)) line drawn as a red line.
    crossing_ids    : Set of track_ids currently crossing the line (drawn orange).
    show_tier       : If True, append the source tier to the label.

    Returns
    -------
    Annotated BGR numpy array (same shape as frame.img).
    """
    img = frame.img.copy()
    crossing_ids = crossing_ids or set()

    for det in detections:
        if det.suppressed:
            continue

        x1, y1, x2, y2 = (int(v) for v in det.bbox)

        is_crossing = det.track_id is not None and det.track_id in crossing_ids
        color = CROSSING_COLOR if is_crossing else CATEGORY_COLORS.get(det.category, DEFAULT_COLOR)

        # Bounding box
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)

        # Label text
        label_parts = [det.category]
        if det.track_id is not None:
            label_parts.append(f"#{det.track_id}")
        label_parts.append(f"{det.confidence:.2f}")
        if show_tier:
            label_parts.append(f"[{det.source_tier}]")
        label = " ".join(label_parts)

        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
        # Background rect for legibility
        cv2.rectangle(img, (x1, y1 - th - 6), (x1 + tw + 4, y1), color, -1)
        cv2.putText(
            img, label,
            (x1 + 2, y1 - 4),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )

    # Boundary line overlay
    if boundary_line is not None:
        pt1, pt2 = boundary_line
        cv2.line(img, pt1, pt2, (0, 0, 255), 2, cv2.LINE_AA)
        cv2.putText(
            img, "BOUNDARY",
            (pt1[0], pt1[1] - 8),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1, cv2.LINE_AA,
        )

    # HUD: camera ID + location top-right
    hud_text = f"{frame.camera_id} | {frame.location}"
    cv2.putText(
        img, hud_text,
        (8, 22),
        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA,
    )

    # Detection count bottom-left
    count_text = f"Detections: {sum(1 for d in detections if not d.suppressed)}"
    cv2.putText(
        img, count_text,
        (8, img.shape[0] - 10),
        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1, cv2.LINE_AA,
    )

    return img


def encode_jpeg(img: np.ndarray, quality: int = 75) -> bytes:
    """Encode a BGR numpy array as JPEG bytes for WebSocket streaming."""
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise RuntimeError("JPEG encoding failed")
    return buf.tobytes()
