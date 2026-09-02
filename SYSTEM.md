# Border Surveillance System — SYSTEM.md

AI-based intelligent video analytics platform for border surveillance.
Built for Smart India Hackathon problem SIH26187 (Ministry of Home Affairs).

---

## Capabilities

| Capability | Status |
|---|---|
| Tier-1: Person / Vehicle / Animal detection (YOLOv8 COCO) | ✅ Phase 1 |
| Day/night auto-switching with CLAHE preprocessing | ✅ Phase 4 |
| Within-camera persistent tracking (ByteTrack) | ✅ Phase 2 |
| Tier-2: Drone / small aerial object detection (SAHI) | ✅ Phase 3 |
| Tier-3: Motion catch-all (MOG2 + contour) → Unidentified | ✅ Phase 3 |
| Virtual boundary line crossing alerts | ✅ Phase 3 |
| Face + body embedding extraction | ✅ Phase 5 |
| Cross-camera topology-based re-identification | ✅ Phase 5 |
| Event grouping (spatial cluster → "Group of N") | ✅ Phase 6 |
| FastAPI + WebSocket backend | ✅ Phase 2 |
| React live dashboard | ✅ Phase 2+ |
| Android IP Webcam ingestion | ✅ Phase 7 |
| iOS / cross-platform browser WebSocket ingestion | ✅ Phase 7 |

## Architecture

See `docs/SETUP.md` for setup instructions.

```
Ingestion → Detection (T1+T2+T3) → Tracking → Embedding → Re-ID → Alerts → Dashboard
```

Each stage is a separate Python module connected through `asyncio.Queue` pipelines.

## What is NOT implemented (by design)

See `docs/SETUP.md` Roadmap section for full details:
- Full geometric multi-camera frame stitching
- Thermal / radar sensor fusion
- Guaranteed detection in zero-visibility or fully camouflaged scenarios
