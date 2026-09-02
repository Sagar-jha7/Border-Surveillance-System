import React from 'react';
import { Smartphone, Video, Shield, QrCode, Radio, Zap } from 'lucide-react';

export default function CameraGrid({ cameras, cameraFrames, mobileStreamUrl }) {
  if (!cameras || cameras.length === 0) {
    return (
      <div className="h-full flex flex-col items-center justify-center border-2 border-dashed border-slate-700/80 rounded-xl p-8 text-center bg-slate-900/40 backdrop-blur-sm">
        <div className="max-w-md bg-slate-900 border border-slate-700 p-8 rounded-2xl shadow-2xl flex flex-col items-center">
          <div className="relative mb-5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-40"></span>
            <div className="relative bg-blue-600/20 border border-blue-500 p-4 rounded-full text-blue-400">
              <Smartphone className="w-10 h-10" />
            </div>
          </div>

          <h3 className="text-lg font-bold text-slate-100 tracking-wide mb-1">
            Awaiting Mobile Camera Feed
          </h3>
          <p className="text-xs text-slate-400 mb-6 leading-relaxed">
            Connect your phone as a mobile surveillance node. Open the secure streamer on your phone browser:
          </p>

          <div className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 mb-5 font-mono text-xs text-cyan-300 break-all select-all flex items-center justify-between">
            <span>{mobileStreamUrl}</span>
          </div>

          <div className="flex flex-col gap-2 w-full text-left text-xs text-slate-400 bg-slate-800/60 p-3.5 rounded-lg border border-slate-700/60">
            <div className="flex items-center gap-2 text-slate-300 font-semibold">
              <Zap className="w-4 h-4 text-amber-400" />
              <span>Quick Mobile Connect:</span>
            </div>
            <ol className="list-decimal list-inside space-y-1 text-[11px] text-slate-400 mt-1">
              <li>Open Chrome/Safari on your phone on this Wi-Fi.</li>
              <li>Type <span className="text-cyan-300 font-mono">{mobileStreamUrl}</span></li>
              <li>Tap <strong>Start Camera Stream</strong>.</li>
            </ol>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-3 h-full">
      {cameras.map((cam) => {
        const frameSrc = cameraFrames[cam.camera_id];
        const isOnline = cam.enabled !== false;

        return (
          <div
            key={cam.camera_id}
            className="bg-slate-900 border border-slate-700/80 rounded-xl overflow-hidden flex flex-col shadow-2xl relative"
          >
            {/* Camera Header Bar */}
            <div className="bg-slate-950 px-4 py-2 border-b border-slate-800 flex items-center justify-between text-xs select-none">
              <div className="flex items-center gap-2.5">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                </span>
                <span className="font-mono font-bold text-blue-400 tracking-wider">
                  {cam.camera_id}
                </span>
                <span className="text-slate-400 font-medium">{cam.location}</span>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-[10px] bg-cyan-950 text-cyan-300 border border-cyan-800/60 font-mono px-2 py-0.5 rounded font-semibold uppercase">
                  Mobile Unit
                </span>
                <span className="text-[10px] bg-emerald-950 text-emerald-300 border border-emerald-800/60 font-mono px-2 py-0.5 rounded font-semibold flex items-center gap-1">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                  SURVEILLANCE LIVE
                </span>
              </div>
            </div>

            {/* Video Feed Area */}
            <div className="flex-1 bg-black relative flex items-center justify-center min-h-[320px] overflow-hidden">
              {frameSrc ? (
                <img
                  src={frameSrc}
                  alt={`Feed for ${cam.camera_id}`}
                  className="w-full h-full object-contain"
                />
              ) : (
                <div className="text-center p-8 text-slate-500">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-3"></div>
                  <p className="text-xs font-mono">Receiving video packets from phone...</p>
                </div>
              )}

              {/* Watermark */}
              <div className="absolute top-3 left-3 pointer-events-none flex flex-col gap-1">
                <div className="bg-black/70 backdrop-blur-sm text-slate-200 text-[11px] font-mono px-2 py-1 rounded border border-white/10 flex items-center gap-1.5">
                  <Shield className="w-3.5 h-3.5 text-blue-400" />
                  <span>ZONE: {cam.location}</span>
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
