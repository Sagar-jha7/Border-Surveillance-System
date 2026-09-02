"""
backend/ingestion/video_source.py
-----------------------------------
Camera source adapters. Each adapter is a generator that yields Frame objects.
All adapters share the same interface:
    frames() -> Iterator[Frame]
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional

import cv2
import numpy as np

from backend.ingestion.frame_model import Frame
from backend.config.settings import settings

logger = logging.getLogger(__name__)


class BaseVideoSource(ABC):
    def __init__(self, camera_id: str, location: str, target_fps: int = 15):
        self.camera_id = camera_id
        self.location = location
        self.target_fps = target_fps
        self._frame_idx: int = 0

    @abstractmethod
    def frames(self) -> Iterator[Frame]:
        ...

    def _make_frame(self, img: np.ndarray) -> Frame:
        frame = Frame(
            camera_id=self.camera_id,
            location=self.location,
            timestamp=datetime.utcnow(),
            img=img,
            frame_idx=self._frame_idx,
        )
        self._frame_idx += 1
        return frame

    def __iter__(self) -> Iterator[Frame]:
        return self.frames()


class VideoFileSource(BaseVideoSource):
    def __init__(
        self,
        camera_id: str,
        location: str,
        source_path: str | Path,
        loop: bool = True,
        target_fps: int | None = None,
        resize_to: Optional[tuple[int, int]] = None,
    ):
        super().__init__(
            camera_id=camera_id,
            location=location,
            target_fps=target_fps or settings.pipeline.target_fps,
        )
        self.source_path = Path(source_path)
        self.loop = loop
        self.resize_to = resize_to or (
            settings.pipeline.frame_width,
            settings.pipeline.frame_height,
        )

        if not self.source_path.exists():
            raise FileNotFoundError(
                f"[VideoFileSource] Video file not found: {self.source_path}\n"
                f"Tip: place a sample clip at demo_assets/sample.mp4 or pass "
                f"--source 0 to use your webcam."
            )

    def frames(self) -> Iterator[Frame]:
        run = True
        while run:
            cap = cv2.VideoCapture(str(self.source_path))
            if not cap.isOpened():
                logger.error("[%s] Cannot open video file: %s", self.camera_id, self.source_path)
                return

            native_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
            skip_ratio = max(1, round(native_fps / self.target_fps))
            raw_frame_idx = 0

            logger.info(
                "[%s] Opened '%s' — native %.1f fps (target %d fps)",
                self.camera_id, self.source_path.name, native_fps, self.target_fps,
            )

            while True:
                ok, img = cap.read()
                if not ok:
                    break

                raw_frame_idx += 1
                if raw_frame_idx % skip_ratio != 0:
                    continue

                if img.shape[1] != self.resize_to[0] or img.shape[0] != self.resize_to[1]:
                    img = cv2.resize(img, self.resize_to, interpolation=cv2.INTER_LINEAR)

                yield self._make_frame(img)

            cap.release()
            if not self.loop:
                run = False


class WebcamSource(BaseVideoSource):
    def __init__(
        self,
        camera_id: str,
        location: str,
        device_index: int = 0,
        target_fps: int | None = None,
        resize_to: Optional[tuple[int, int]] = None,
    ):
        super().__init__(
            camera_id=camera_id,
            location=location,
            target_fps=target_fps or settings.pipeline.target_fps,
        )
        self.device_index = device_index
        self.resize_to = resize_to or (
            settings.pipeline.frame_width,
            settings.pipeline.frame_height,
        )

    def frames(self) -> Iterator[Frame]:
        cap = cv2.VideoCapture(self.device_index)
        if not cap.isOpened():
            logger.error("[%s] Cannot open webcam at index %d", self.camera_id, self.device_index)
            return

        cap.set(cv2.CAP_PROP_FPS, self.target_fps)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resize_to[0])
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resize_to[1])

        logger.info("[%s] Opened webcam index %d", self.camera_id, self.device_index)

        try:
            while True:
                ok, img = cap.read()
                if not ok:
                    time.sleep(0.05)
                    continue

                if img.shape[1] != self.resize_to[0] or img.shape[0] != self.resize_to[1]:
                    img = cv2.resize(img, self.resize_to, interpolation=cv2.INTER_LINEAR)

                yield self._make_frame(img)
        finally:
            cap.release()
            logger.info("[%s] Webcam released", self.camera_id)


def source_from_config(camera_cfg: dict) -> BaseVideoSource:
    cid = camera_cfg["camera_id"]
    loc = camera_cfg.get("location", cid)
    src = camera_cfg["source"]
    kind = camera_cfg.get("type", "file")

    if kind == "file":
        return VideoFileSource(
            camera_id=cid,
            location=loc,
            source_path=src,
            loop=camera_cfg.get("loop", True),
        )
    elif kind == "webcam":
        return WebcamSource(
            camera_id=cid,
            location=loc,
            device_index=int(src),
        )
    else:
        raise ValueError(
            f"[source_from_config] Unknown source type '{kind}' for camera '{cid}'."
        )
