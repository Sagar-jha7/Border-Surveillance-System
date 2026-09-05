import React, { useState } from 'react';
import { Video, X, Plus, Radio, Server, Shield, CheckCircle2 } from 'lucide-react';

export default function AddCameraModal({ isOpen, onClose, onCameraAdded }) {
  const [cameraId, setCameraId] = useState('');
  const [location, setLocation] = useState('');
  const [sourceType, setSourceType] = useState('webcam'); // 'webcam', 'rtsp', 'http', 'file'
  const [sourceVal, setSourceVal] = useState('0');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  if (!isOpen) return null;

  const handleSourceTypeChange = (type) => {
    setSourceType(type);
    if (type === 'webcam') setSourceVal('0');
    else if (type === 'rtsp') setSourceVal('rtsp://192.168.1.100:554/stream1');
    else if (type === 'http') setSourceVal('http://192.168.1.100:8080/video');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const cleanId = (cameraId.trim() || `cam_${Date.now().toString().slice(-4)}`).replace(/\s+/g, '_').toLowerCase();
    const cleanLoc = location.trim() || `Border Post (${cleanId})`;

    let typeStr = 'webcam';
    if (sourceType === 'rtsp' || sourceType === 'http') typeStr = 'ip_camera';

    const payload = {
      camera_id: cleanId,
      location: cleanLoc,
      source: sourceVal.trim(),
      type: typeStr,
      enabled: true,
    };

    try {
      const res = await fetch('/api/cameras', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to add camera feed');
      }

      onCameraAdded && onCameraAdded();
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="bg-slate-950 px-5 py-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="bg-blue-600/20 border border-blue-500 p-2 rounded-lg text-blue-400">
              <Video className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wider">
                Ingest New Surveillance Camera
              </h3>
              <p className="text-[11px] text-slate-400">Connect IP CCTV, local USB webcam, or RTSP border stream</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-5 flex flex-col gap-4">
          {error && (
            <div className="bg-rose-950/60 border border-rose-700 p-3 rounded-lg text-xs text-rose-300">
              ⚠️ {error}
            </div>
          )}

          {/* Camera ID */}
          <div>
            <label className="text-xs font-semibold text-slate-300 block mb-1">
              Camera ID / Codename:
            </label>
            <input
              type="text"
              placeholder="e.g., bop_north_01, checkpost_alpha"
              value={cameraId}
              onChange={(e) => setCameraId(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs font-mono text-cyan-300 focus:outline-none focus:border-blue-500"
            />
          </div>

          {/* Location */}
          <div>
            <label className="text-xs font-semibold text-slate-300 block mb-1">
              Border Location / Sector:
            </label>
            <input
              type="text"
              placeholder="e.g., Border Out Post Alpha - Sector 7"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-blue-500"
            />
          </div>

          {/* Source Type Selector */}
          <div>
            <label className="text-xs font-semibold text-slate-300 block mb-1.5">
              Stream Source Type:
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs">
              <button
                type="button"
                onClick={() => handleSourceTypeChange('webcam')}
                className={`p-2.5 rounded-lg border text-left flex flex-col gap-1 transition ${
                  sourceType === 'webcam'
                    ? 'bg-blue-950/60 border-blue-500 text-blue-300'
                    : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'
                }`}
              >
                <span className="font-bold flex items-center gap-1.5">
                  <Radio className="w-3.5 h-3.5" /> Local USB / Webcam
                </span>
                <span className="text-[10px] text-slate-500">Device index (0, 1)</span>
              </button>

              <button
                type="button"
                onClick={() => handleSourceTypeChange('rtsp')}
                className={`p-2.5 rounded-lg border text-left flex flex-col gap-1 transition ${
                  sourceType === 'rtsp'
                    ? 'bg-blue-950/60 border-blue-500 text-blue-300'
                    : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'
                }`}
              >
                <span className="font-bold flex items-center gap-1.5">
                  <Server className="w-3.5 h-3.5" /> IP Camera (RTSP)
                </span>
                <span className="text-[10px] text-slate-500">Standard RTSP stream</span>
              </button>

              <button
                type="button"
                onClick={() => handleSourceTypeChange('http')}
                className={`p-2.5 rounded-lg border text-left flex flex-col gap-1 transition ${
                  sourceType === 'http'
                    ? 'bg-blue-950/60 border-blue-500 text-blue-300'
                    : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'
                }`}
              >
                <span className="font-bold flex items-center gap-1.5">
                  <Video className="w-3.5 h-3.5" /> HTTP / MJPEG Feed
                </span>
                <span className="text-[10px] text-slate-500">IP Webcam URL</span>
              </button>
            </div>
          </div>

          {/* Source Value Input */}
          <div>
            <label className="text-xs font-semibold text-slate-300 block mb-1">
              {sourceType === 'webcam' ? 'Webcam Device Index (e.g., 0 for default PC camera):' : 'Live Stream Network URL:'}
            </label>
            <input
              type="text"
              value={sourceVal}
              onChange={(e) => setSourceVal(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs font-mono text-cyan-300 focus:outline-none focus:border-blue-500"
              required
            />
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-slate-800">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-5 py-2 text-xs font-bold bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition flex items-center gap-1.5 shadow-lg shadow-blue-600/30 disabled:opacity-50"
            >
              {loading ? (
                <>Connecting...</>
              ) : (
                <>
                  <Plus className="w-4 h-4" /> Start Ingestion
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
