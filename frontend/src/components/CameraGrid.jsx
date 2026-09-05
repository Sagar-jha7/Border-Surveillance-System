import React from 'react';
import { Smartphone, Video, Shield, Plus, Trash2, Radio, Server, Camera, ExternalLink } from 'lucide-react';

export default function CameraGrid({
  cameras,
  cameraFrames,
  mobileStreamUrl,
  onOpenAddCamera,
  onRemoveCamera,
  onQuickStartWebcam,
}) {
  // Empty State: All dummy cameras removed
  if (!cameras || cameras.length === 0) {
    return (
      <div className="h-full flex flex-col items-center justify-center border-2 border-dashed border-slate-800 rounded-2xl p-6 text-center bg-slate-950/40 backdrop-blur-sm">
        <div className="max-w-xl w-full bg-slate-900/90 border border-slate-700/80 p-8 rounded-2xl shadow-2xl flex flex-col items-center">
          {/* Radar icon badge */}
          <div className="relative mb-5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-500 opacity-30"></span>
            <div className="relative bg-blue-600/20 border border-blue-500 p-4 rounded-2xl text-blue-400">
              <Shield className="w-10 h-10" />
            </div>
          </div>

          <h3 className="text-xl font-bold text-slate-100 tracking-wide mb-1">
            IBVAP Tactical Surveillance Grid
          </h3>
          <p className="text-xs text-slate-400 mb-6 leading-relaxed max-w-md">
            No dummy cameras loaded. Ingest live IP-based CCTV infrastructure, USB border cameras, or mobile patrol units without requiring dedicated FRS or ANPR hardware.
          </p>

          {/* 3 Quick Action Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 w-full mb-6">
            {/* 1. Start Local Webcam */}
            <button
              onClick={onQuickStartWebcam}
              className="bg-slate-950 hover:bg-slate-800 border border-slate-700 hover:border-blue-500/80 p-4 rounded-xl flex flex-col items-center gap-2 text-center transition group shadow-lg"
            >
              <div className="p-2.5 rounded-lg bg-blue-600/20 text-blue-400 group-hover:scale-110 transition">
                <Camera className="w-5 h-5" />
              </div>
              <span className="text-xs font-bold text-slate-200">Start Local Webcam</span>
              <span className="text-[10px] text-slate-500 leading-tight">Instant 1-click test with device index 0</span>
            </button>

            {/* 2. Add IP CCTV */}
            <button
              onClick={onOpenAddCamera}
              className="bg-slate-950 hover:bg-slate-800 border border-slate-700 hover:border-blue-500/80 p-4 rounded-xl flex flex-col items-center gap-2 text-center transition group shadow-lg"
            >
              <div className="p-2.5 rounded-lg bg-emerald-600/20 text-emerald-400 group-hover:scale-110 transition">
                <Server className="w-5 h-5" />
              </div>
              <span className="text-xs font-bold text-slate-200">Add IP Camera (RTSP)</span>
              <span className="text-[10px] text-slate-500 leading-tight">Connect RTSP or HTTP CCTV feed</span>
            </button>

            {/* 3. Mobile Phone */}
            <a
              href={mobileStreamUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="bg-slate-950 hover:bg-slate-800 border border-slate-700 hover:border-cyan-500/80 p-4 rounded-xl flex flex-col items-center gap-2 text-center transition group shadow-lg"
            >
              <div className="p-2.5 rounded-lg bg-cyan-600/20 text-cyan-400 group-hover:scale-110 transition">
                <Smartphone className="w-5 h-5" />
              </div>
              <span className="text-xs font-bold text-slate-200">Mobile Patrol Phone</span>
              <span className="text-[10px] text-slate-500 leading-tight">Stream live camera from phone browser</span>
            </a>
          </div>

          {/* Direct Mobile URL Bar */}
          <div className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-left">
            <div className="flex items-center justify-between gap-2 text-[11px] text-slate-400 mb-1">
              <span className="font-semibold text-slate-300 flex items-center gap-1.5">
                <Smartphone className="w-3.5 h-3.5 text-cyan-400" />
                Mobile Patrol Streamer URL:
              </span>
              <span className="font-mono text-cyan-400">Zero Hardware Needed</span>
            </div>
            <div className="font-mono text-xs text-cyan-300 break-all select-all">
              {mobileStreamUrl}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Active Cameras Grid
  return (
    <div className="flex flex-col gap-3 h-full">
      {/* Mobile Stream Quick Access Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg px-3.5 py-2 flex flex-wrap items-center justify-between text-xs text-slate-300 gap-2 shrink-0">
        <div className="flex items-center gap-2">
          <Smartphone className="w-4 h-4 text-cyan-400 shrink-0" />
          <span className="font-semibold text-slate-200">Mobile Patrol Ingestion:</span>
          <a
            href={mobileStreamUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-cyan-300 font-mono hover:underline truncate max-w-md"
          >
            {mobileStreamUrl}
          </a>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={onOpenAddCamera}
            className="bg-blue-600 hover:bg-blue-500 text-white px-2.5 py-1 rounded text-xs font-bold flex items-center gap-1 transition"
          >
            <Plus className="w-3.5 h-3.5" /> Add Camera
          </button>
        </div>
      </div>

      {/* Grid of active cameras */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-3 flex-1 overflow-y-auto pb-4">
        {cameras.map((cam) => {
          const frameSrc = cameraFrames[cam.camera_id];
          const isPhone = cam.type === 'ws_phone' || cam.camera_id?.startsWith('phone_');
          const isWebcam = cam.type === 'webcam';
          const isIP = cam.type === 'ip_camera' || cam.type === 'rtsp';

          let typeBadge = 'Fixed CCTV';
          if (isPhone) typeBadge = 'Mobile Patrol';
          else if (isWebcam) typeBadge = 'USB Webcam';
          else if (isIP) typeBadge = 'IP Camera (RTSP)';

          return (
            <div
              key={cam.camera_id}
              className="bg-slate-900 border border-slate-700/80 rounded-xl overflow-hidden flex flex-col shadow-2xl relative"
            >
              {/* Camera Header Bar */}
              <div className="bg-slate-950 px-4 py-2 border-b border-slate-800 flex items-center justify-between text-xs select-none">
                <div className="flex items-center gap-2.5 min-w-0">
                  <span className="relative flex h-2 w-2 shrink-0">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                  </span>
                  <span className="font-mono font-bold text-blue-400 tracking-wider truncate">
                    {cam.camera_id}
                  </span>
                  <span className="text-slate-400 font-medium truncate">{cam.location}</span>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <span className={`text-[10px] border font-mono px-2 py-0.5 rounded font-semibold uppercase ${
                    isPhone
                      ? 'bg-cyan-950 text-cyan-300 border-cyan-800/60'
                      : isWebcam
                      ? 'bg-purple-950 text-purple-300 border-purple-800/60'
                      : 'bg-blue-950 text-blue-300 border-blue-800/60'
                  }`}>
                    {typeBadge}
                  </span>

                  <button
                    onClick={() => onRemoveCamera && onRemoveCamera(cam.camera_id)}
                    className="text-slate-500 hover:text-rose-400 p-1 rounded hover:bg-slate-800 transition"
                    title="Remove Camera"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              {/* Video Feed Area */}
              <div className="flex-1 bg-black relative flex items-center justify-center min-h-[340px] overflow-hidden">
                {frameSrc ? (
                  <img
                    src={frameSrc}
                    alt={`Feed for ${cam.camera_id}`}
                    className="w-full h-full object-contain"
                  />
                ) : (
                  <div className="text-center p-8 text-slate-500 flex flex-col items-center">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mb-3"></div>
                    <p className="text-xs font-mono text-slate-400">Connecting to {cam.camera_id} video stream...</p>
                    <p className="text-[11px] text-slate-600 mt-1">Acquiring video packets & initializing AI inference</p>
                  </div>
                )}

                {/* HUD Sector Watermark */}
                <div className="absolute top-3 left-3 pointer-events-none flex flex-col gap-1">
                  <div className="bg-black/75 backdrop-blur-sm text-slate-200 text-[10px] font-mono px-2 py-0.5 rounded border border-white/10 flex items-center gap-1.5">
                    <Shield className="w-3 h-3 text-blue-400" />
                    <span>SECTOR: {cam.location}</span>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
