"""
backend/api/app.py
--------------------
FastAPI application — REST endpoints + WebSocket streaming + 6-Section Intelligence Coordinator.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import cv2
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from backend.config.settings import settings
from backend.config.network import get_lan_ip
from backend.engine import SurveillanceEngine
from backend.ingestion.frame_model import Frame, Detection
from backend.detection.night_switch import NightSwitcher
from backend.detection.tier3_motion import Tier3MotionDetector
from backend.detection.merger import merge_detections
from backend.tracking.tracker import WithinCameraTracker
from backend.alerts.section_coordinator import SectionCoordinator
from backend.alerts.schema import Alert, AlertPriority, AlertCategory, SectionType
from backend.detection.visualizer import draw_detections, encode_jpeg

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Connection manager
# ---------------------------------------------------------------------------

class ConnectionManager:
    """
    Manages active WebSocket connections for frame streaming and alerts.
    """

    def __init__(self):
        self.frame_subscribers: Dict[str, Set[WebSocket]] = {}
        self.alert_subscribers: Set[WebSocket] = set()

    async def connect_frames(self, ws: WebSocket, camera_id: str) -> None:
        await ws.accept()
        self.frame_subscribers.setdefault(camera_id, set()).add(ws)
        logger.info("[WS] Frame subscriber connected for camera '%s'", camera_id)

    async def connect_alerts(self, ws: WebSocket) -> None:
        await ws.accept()
        self.alert_subscribers.add(ws)
        logger.info("[WS] Alert subscriber connected")

    def disconnect_frames(self, ws: WebSocket, camera_id: str) -> None:
        subs = self.frame_subscribers.get(camera_id, set())
        subs.discard(ws)

    def disconnect_alerts(self, ws: WebSocket) -> None:
        self.alert_subscribers.discard(ws)

    async def broadcast_frame(self, camera_id: str, jpeg_bytes: bytes) -> None:
        """Send a JPEG frame as base64 to all subscribers for this camera."""
        b64 = base64.b64encode(jpeg_bytes).decode("utf-8")
        msg = json.dumps({
            "type": "frame",
            "camera_id": camera_id,
            "data": b64,
        })
        dead: Set[WebSocket] = set()
        for ws in list(self.frame_subscribers.get(camera_id, set())):
            try:
                await ws.send_text(msg)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.frame_subscribers.get(camera_id, set()).discard(ws)

    async def broadcast_alert(self, alert_dict: dict) -> None:
        """Send an alert payload to all alert subscribers."""
        msg = json.dumps({"type": "alert", "payload": alert_dict})
        dead: Set[WebSocket] = set()
        for ws in list(self.alert_subscribers):
            try:
                await ws.send_text(msg)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.alert_subscribers.discard(ws)


manager = ConnectionManager()
engine: Optional[SurveillanceEngine] = None
active_phone_cameras: Dict[str, dict] = {}

# ---------------------------------------------------------------------------
# App factory & lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    global engine
    logger.info("Border Surveillance API starting up...")
    engine = SurveillanceEngine(
        broadcast_frame_cb=manager.broadcast_frame,
        broadcast_alert_cb=manager.broadcast_alert,
    )
    await engine.start()
    yield
    logger.info("Border Surveillance API shutting down...")
    if engine:
        await engine.stop()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Border Surveillance System",
        description="AI-based intelligent video analytics platform (SIH26187)",
        version="0.3.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"
    phone_html_path = Path(__file__).parent.parent.parent / "frontend" / "public" / "phone_stream.html"

    # ------------------------------------------------------------------
    # REST endpoints
    # ------------------------------------------------------------------

    @app.get("/health")
    async def health():
        total_cams = (len(engine.workers) if engine else 0) + len(active_phone_cameras)
        return {
            "status": "ok",
            "active_cameras": total_cams,
            "engine_running": engine is not None,
            "connected_phones": list(active_phone_cameras.keys()),
        }

    @app.get("/mobile-stream-info")
    async def mobile_stream_info():
        host = get_lan_ip()
        return {
            "host": host,
            "https_url": f"https://{host}:8443/phone_stream.html",
            "http_url": f"http://{host}:8000/phone_stream.html",
            "websocket_path": "/ws/phone/{client_id}",
        }

    @app.get("/cameras")
    async def list_cameras():
        registry_path = Path(__file__).parent.parent / "config" / "camera_registry.json"
        cameras = []
        try:
            with open(registry_path, "r") as f:
                data = json.load(f)
                cameras = data.get("cameras", [])
        except FileNotFoundError:
            cameras = []

        # Merge live connected mobile units
        for phone_cam in active_phone_cameras.values():
            if not any(c["camera_id"] == phone_cam["camera_id"] for c in cameras):
                cameras.append(phone_cam)

        return {"cameras": cameras}

    # ------------------------------------------------------------------
    # WebSocket: frame streaming
    # ------------------------------------------------------------------

    @app.websocket("/ws/frames/{camera_id}")
    async def ws_frames(websocket: WebSocket, camera_id: str):
        await manager.connect_frames(websocket, camera_id)
        try:
            while True:
                await asyncio.sleep(30)
        except (WebSocketDisconnect, asyncio.CancelledError):
            manager.disconnect_frames(websocket, camera_id)
            logger.info("[WS] Frame subscriber disconnected for camera '%s'", camera_id)

    # ------------------------------------------------------------------
    # WebSocket: alert streaming
    # ------------------------------------------------------------------

    @app.websocket("/ws/alerts")
    async def ws_alerts(websocket: WebSocket):
        await manager.connect_alerts(websocket)
        try:
            while True:
                await asyncio.sleep(30)
        except (WebSocketDisconnect, asyncio.CancelledError):
            manager.disconnect_alerts(websocket)
            logger.info("[WS] Alert subscriber disconnected")

    # ------------------------------------------------------------------
    # Phase 7: Ultra-Smooth Phone Stream Ingestion with 6-Section Intel
    # ------------------------------------------------------------------

    @app.websocket("/ws/phone/{client_id}")
    async def ws_phone(websocket: WebSocket, client_id: str):
        await websocket.accept()
        camera_id = f"phone_{client_id}"
        location = f"Mobile Patrol Unit ({client_id})"
        logger.info("[Phone] Mobile camera connected: %s", camera_id)

        active_phone_cameras[camera_id] = {
            "camera_id": camera_id,
            "location": location,
            "type": "ws_phone",
            "enabled": True,
        }

        # Broadcast camera list update to all alert subscribers
        await manager.broadcast_alert({
            "alert_id": "SYS_CAM_UPDATE",
            "timestamp": datetime.utcnow().isoformat(),
            "section": 1,
            "section_title": "System Status",
            "camera_id": camera_id,
            "location": location,
            "category": "System",
            "priority": "AMBER",
            "description": f"Mobile patrol unit {camera_id} connected and active.",
            "group_size": 1,
            "is_crossing": False,
        })

        phone_tracker = WithinCameraTracker(camera_id)
        night_switcher = NightSwitcher(camera_id)
        motion_detector = Tier3MotionDetector(camera_id)
        section_coordinator = SectionCoordinator(camera_id, location, reid_matcher=engine.reid_matcher if engine else None)

        frame_queue: asyncio.Queue[str] = asyncio.Queue(maxsize=1)
        running = True

        def sync_process_frame(b64_str: str) -> Tuple[Optional[bytes], List[Alert]]:
            try:
                raw_bytes = base64.b64decode(b64_str)
                np_arr = np.frombuffer(raw_bytes, np.uint8)
                img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                if img is None:
                    return None, []

                h, w = img.shape[:2]
                boundary_line = ((0, h // 2), (w, h // 2))

                frame_obj = Frame(
                    camera_id=camera_id,
                    location=location,
                    timestamp=datetime.utcnow(),
                    img=img,
                )

                # 1. Night/Day Auto-Switch
                proc_frame, is_night, avg_lum = night_switcher.process(frame_obj)

                # 2. Tier 1: YOLOv8 Detection
                conf = settings.detection.night_confidence if is_night else settings.detection.day_confidence
                t1_dets = engine.detector_t1.detect(proc_frame, confidence=conf) if engine else []

                # 3. Tier 3: Verified unidentified object motion
                t3_dets = motion_detector.detect(proc_frame)

                # 4. Merge Tiers
                merged_dets = merge_detections(t1_dets, [], t3_dets)

                # 5. Tracking
                tracked_dets = phone_tracker.update(merged_dets, proc_frame.shape)

                # 6. Check virtual boundary crossings
                crossing_ids = set()
                mid_y = h // 2
                for d in tracked_dets:
                    if d.track_id is not None and abs(d.cy - mid_y) < (h * 0.09):
                        crossing_ids.add(d.track_id)

                # 7. Multi-Section Intelligence Analysis (Sections 1-6)
                alerts = section_coordinator.process(
                    proc_frame,
                    t1_dets,
                    t3_dets,
                    tracked_dets,
                    boundary_line=boundary_line,
                )

                # 8. Visualization
                annotated = draw_detections(
                    proc_frame,
                    tracked_dets,
                    boundary_line=boundary_line,
                    crossing_ids=crossing_ids,
                )

                mode_badge = f"NIGHT (CLAHE) - Lum: {avg_lum:.0f}" if is_night else f"DAY - Lum: {avg_lum:.0f}"
                cv2.putText(
                    annotated,
                    f"LIVE PATROL | {mode_badge} | {len(tracked_dets)} Tracks",
                    (8, 45),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.45,
                    (0, 255, 255) if is_night else (100, 255, 100),
                    1,
                    cv2.LINE_AA,
                )

                jpeg_bytes = encode_jpeg(annotated, quality=55)
                return jpeg_bytes, alerts
            except Exception as e:
                logger.error("[Phone Frame Error] %s", e)
                return None, []

        async def worker_loop():
            while running:
                try:
                    b64_str = await frame_queue.get()
                    jpeg, alerts = await asyncio.to_thread(sync_process_frame, b64_str)
                    if jpeg:
                        await manager.broadcast_frame(camera_id, jpeg)
                    for alert in alerts:
                        await manager.broadcast_alert(alert.model_dump(mode="json"))
                except asyncio.CancelledError:
                    break
                except Exception as exc:
                    logger.debug("[Worker Exception] %s", exc)

        worker_task = asyncio.create_task(worker_loop())

        try:
            while True:
                data = await websocket.receive_text()
                # Single-slot queue: replace older unconsumed frame to maintain 0 lag
                if frame_queue.full():
                    try:
                        frame_queue.get_nowait()
                    except Exception:
                        pass
                try:
                    frame_queue.put_nowait(data)
                except asyncio.QueueFull:
                    pass

        except (WebSocketDisconnect, asyncio.CancelledError):
            logger.info("[Phone] Mobile camera disconnected: %s", camera_id)
        finally:
            running = False
            worker_task.cancel()
            active_phone_cameras.pop(camera_id, None)

    # ------------------------------------------------------------------
    # Phase 7: Serve phone capture HTML page
    # ------------------------------------------------------------------

    @app.get("/phone_stream.html", response_class=HTMLResponse)
    async def phone_stream_page():
        if phone_html_path.exists():
            return HTMLResponse(phone_html_path.read_text(encoding="utf-8"))
        return HTMLResponse("<h1>phone_stream.html not found</h1>")

    # ------------------------------------------------------------------
    # Serve React Dashboard (dist)
    # ------------------------------------------------------------------

    if frontend_dist.exists():
        app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")

        @app.get("/")
        async def serve_root():
            return FileResponse(frontend_dist / "index.html")

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            target = frontend_dist / full_path
            if target.is_file():
                return FileResponse(target)
            index_file = frontend_dist / "index.html"
            if index_file.exists():
                return FileResponse(index_file)
            return {"status": "ok"}
    else:
        @app.get("/")
        async def root():
            return {
                "service": "Border Surveillance System",
                "version": "0.3.0",
                "status": "online",
            }

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.api.app:app", host="0.0.0.0", port=8000, reload=True)
