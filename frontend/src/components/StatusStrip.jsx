import React from 'react';
import { Shield, Smartphone, AlertTriangle, Clock, SearchCheck } from 'lucide-react';

export default function StatusStrip({ status, connected }) {
  const formattedTime = status.last_update
    ? new Date(status.last_update).toLocaleTimeString()
    : '--:--:--';

  return (
    <header className="bg-slate-950 border-b border-slate-800 px-4 py-2.5 flex items-center justify-between shadow-lg select-none">
      {/* Brand & Zone */}
      <div className="flex items-center gap-3">
        <div className="bg-blue-600/20 border border-blue-500/40 p-2 rounded-lg text-blue-400">
          <Shield className="w-5 h-5" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="font-bold tracking-wider text-slate-100 text-sm">
              BORDER SURVEILLANCE SYSTEM
            </span>
            <span className="text-[10px] bg-blue-900/60 text-blue-300 font-mono px-1.5 py-0.5 rounded border border-blue-700/50 font-bold">
              SIH26187
            </span>
            <span className="text-[10px] bg-emerald-950 text-emerald-300 font-mono px-1.5 py-0.5 rounded border border-emerald-700/50 font-semibold">
              6-TIER INTEL ACTIVE
            </span>
          </div>
          <p className="text-xs text-slate-400 font-medium">{status.zone_name}</p>
        </div>
      </div>

      {/* Metrics Strip */}
      <div className="flex items-center gap-5 text-xs">
        {/* Backend Link Status */}
        <div className="flex items-center gap-2">
          <span className="relative flex h-2.5 w-2.5">
            {connected ? (
              <>
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
              </>
            ) : (
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-rose-500"></span>
            )}
          </span>
          <span className={connected ? 'text-emerald-400 font-semibold font-mono' : 'text-rose-400 font-semibold font-mono'}>
            {connected ? 'TACTICAL LINK LIVE' : 'DISCONNECTED'}
          </span>
        </div>

        {/* Mobile Nodes Metric */}
        <div className="flex items-center gap-1.5 text-slate-300 bg-slate-900 px-2.5 py-1 rounded-md border border-slate-800">
          <Smartphone className="w-3.5 h-3.5 text-cyan-400" />
          <span>Mobile Units:</span>
          <span className="font-bold text-cyan-300 font-mono">
            {status.cameras_online}
          </span>
        </div>

        {/* Total Active Alerts */}
        <div className="flex items-center gap-1.5 text-slate-300 bg-slate-900 px-2.5 py-1 rounded-md border border-slate-800">
          <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
          <span>Alerts:</span>
          <span className="font-bold text-amber-300 font-mono">{status.active_alerts}</span>
        </div>

        {/* Unidentified object verification status */}
        <div className="flex items-center gap-1.5 text-slate-300 bg-slate-900 px-2.5 py-1 rounded-md border border-slate-800 hidden lg:flex">
          <SearchCheck className="w-3.5 h-3.5 text-emerald-400" />
          <span>Unidentified:</span>
          <span className="font-bold text-emerald-300 font-mono">VERIFIED ONLY</span>
        </div>

        {/* Last Sync Time */}
        <div className="flex items-center gap-1.5 text-slate-400 hidden md:flex font-mono text-[11px]">
          <Clock className="w-3.5 h-3.5 text-slate-500" />
          <span>Sync: {formattedTime}</span>
        </div>
      </div>
    </header>
  );
}
