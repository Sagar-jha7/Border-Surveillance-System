import { useState, useEffect, useCallback, useRef } from "react";
import StatusStrip from "./components/StatusStrip";
import CameraGrid from "./components/CameraGrid";
import AlertFeed from "./components/AlertFeed";
import AddCameraModal from "./components/AddCameraModal";
import EventLogModal from "./components/EventLogModal";
import WatchlistModal from "./components/WatchlistModal";
import { useSystemWebSocket } from "./hooks/useSystemWebSocket";
import { useAlarmBeep } from "./hooks/useAlarmBeep";

/**
 * IBVAP Root Dashboard Component.
 * Intelligent Border Video Analytics Platform (SIH26187 / BSF / MHA).
 *
 * v2 Additions:
 *  - Beep alarm hook (RED/AMBER/BLUE distinct tones)
 *  - System Start / Stop master toggle
 *  - Full System Reset (clears all cameras, alerts, logs)
 *  - Threat indicator dots in StatusStrip
 */
export default function App() {
  const { beep, toggleMute } = useAlarmBeep();
  const [muted, setMuted] = useState(false);

  // Latest non-system alert priority for the threat dot indicator
  const [latestAlertPriority, setLatestAlertPriority] = useState(null);
  const latestPriorityTimerRef = useRef(null);

  const handleNewAlert = useCallback((alert) => {
    const p = alert.priority;
    if (p === "RED" || p === "AMBER" || p === "BLUE") {
      beep(p);
      setLatestAlertPriority(p);
      // Clear the dot highlight after a few seconds so it resets when quiet
      if (latestPriorityTimerRef.current) clearTimeout(latestPriorityTimerRef.current);
      latestPriorityTimerRef.current = setTimeout(() => setLatestAlertPriority(null), 4000);
    }
  }, [beep]);

  const {
    connected,
    status,
    alerts,
    setAlerts,
    cameraFrames,
    cameraList,
    refreshCameras,
    systemRunning,
    setSystemRunning,
  } = useSystemWebSocket({ onNewAlert: handleNewAlert });

  const [mobileStreamUrl, setMobileStreamUrl] = useState(() => {
    const host = window.location.hostname || "localhost";
    return `https://${host}:8443/phone_stream.html`;
  });

  const [isAddCameraOpen, setIsAddCameraOpen] = useState(false);
  const [isEventLogOpen, setIsEventLogOpen] = useState(false);
  const [isWatchlistOpen, setIsWatchlistOpen] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function loadMobileStreamInfo() {
      try {
        const res = await fetch("/mobile-stream-info");
        if (!res.ok) return;
        const info = await res.json();
        if (!cancelled && info.https_url) setMobileStreamUrl(info.https_url);
      } catch (err) {
        console.warn("Mobile stream info unavailable, using browser host fallback.", err);
      }
    }
    loadMobileStreamInfo();
    return () => { cancelled = true; };
  }, []);

  // ── System Controls ──────────────────────────────────────────────────

  const handleSystemStop = async () => {
    try {
      const res = await fetch("/api/system/stop", { method: "POST" });
      if (res.ok) setSystemRunning(false);
    } catch (err) { console.error("System stop failed:", err); }
  };

  const handleSystemStart = async () => {
    try {
      const res = await fetch("/api/system/start", { method: "POST" });
      if (res.ok) { setSystemRunning(true); refreshCameras(); }
    } catch (err) { console.error("System start failed:", err); }
  };

  const handleSystemReset = async () => {
    try {
      const res = await fetch("/api/system/reset", { method: "POST" });
      if (res.ok) {
        setAlerts([]);
        setSystemRunning(true);
        refreshCameras();
      }
    } catch (err) { console.error("System reset failed:", err); }
  };

  const handleToggleMute = () => {
    const nowMuted = toggleMute();
    setMuted(nowMuted);
  };

  // ── Camera Controls ──────────────────────────────────────────────────

  const handleQuickStartWebcam = async () => {
    try {
      const res = await fetch("/api/cameras", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          camera_id: "webcam_local_01",
          location: "Command Post (Integrated USB Webcam)",
          type: "webcam",
          source: "0",
          enabled: true,
        }),
      });
      if (res.ok) refreshCameras();
    } catch (err) { console.error("Failed to quick-start webcam:", err); }
  };

  const handleRemoveCamera = async (cameraId) => {
    if (window.confirm(`Remove camera '${cameraId}'?`)) {
      try {
        const res = await fetch(`/api/cameras/${cameraId}`, { method: "DELETE" });
        if (res.ok) refreshCameras();
      } catch (err) { console.error("Failed to remove camera:", err); }
    }
  };

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-slate-950 text-slate-100 select-none">
      {/* Top status strip */}
      <StatusStrip
        status={status}
        connected={connected}
        systemRunning={systemRunning}
        latestAlertPriority={latestAlertPriority}
        muted={muted}
        onToggleMute={handleToggleMute}
        onOpenAddCamera={() => setIsAddCameraOpen(true)}
        onOpenEventLog={() => setIsEventLogOpen(true)}
        onOpenWatchlist={() => setIsWatchlistOpen(true)}
        onSystemStart={handleSystemStart}
        onSystemStop={handleSystemStop}
        onSystemReset={handleSystemReset}
      />

      <div className="flex flex-1 overflow-hidden">
        {/* Left sidebar: tactical alert feed */}
        <div className="w-[28rem] flex-shrink-0 flex flex-col border-r border-slate-800 overflow-hidden shadow-xl z-10">
          <AlertFeed alerts={alerts} />
        </div>

        {/* Main area: camera grid */}
        <div className="flex-1 overflow-auto p-3 bg-slate-950/60">
          <CameraGrid
            cameras={cameraList}
            cameraFrames={cameraFrames}
            mobileStreamUrl={mobileStreamUrl}
            onOpenAddCamera={() => setIsAddCameraOpen(true)}
            onRemoveCamera={handleRemoveCamera}
            onQuickStartWebcam={handleQuickStartWebcam}
          />
        </div>
      </div>

      {/* Modals */}
      <AddCameraModal
        isOpen={isAddCameraOpen}
        onClose={() => setIsAddCameraOpen(false)}
        onCameraAdded={refreshCameras}
      />
      <EventLogModal
        isOpen={isEventLogOpen}
        onClose={() => setIsEventLogOpen(false)}
      />
      <WatchlistModal
        isOpen={isWatchlistOpen}
        onClose={() => setIsWatchlistOpen(false)}
      />
    </div>
  );
}
