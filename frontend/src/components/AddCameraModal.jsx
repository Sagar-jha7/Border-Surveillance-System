import React, { useState } from 'react';
import { Video, X, Plus, Radio, Server, Shield, AlertTriangle } from 'lucide-react';

// Force absolute API base URL (guards against empty strings or missing protocol prefixes)
const getApiBaseUrl = () => {
  const rawApiUrl = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL;
  if (
    rawApiUrl &&
    typeof rawApiUrl === 'string' &&
    rawApiUrl.trim().startsWith('http')
  ) {
    return rawApiUrl.trim().replace(/\/+$/, '');
  }
  return 'https://border-surveillance-api.onrender.com';
};

const API_BASE_URL = getApiBaseUrl();

export default function AddCameraModal({ isOpen, onClose, onCameraAdded }) {
  const [cameraId, setCameraId] = useState('');
  const [location, setLocation] = useState('');
  const [sourceType, setSourceType] = useState('http'); // Default to HTTP feed for cloud deployments
  const [sourceVal, setSourceVal] = useState(`${API_BASE_URL}/phone_stream.html`);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  if (!isOpen) return null;

  const handleSourceTypeChange = (type) => {
    setSourceType(type);
    if (type === 'webcam') {
      setSourceVal('0');
    } else if (type === 'rtsp') {
      setSourceVal('rtsp://192.168.1.100:554/stream1');
    } else if (type === 'http') {
      setSourceVal(`${API_BASE_URL}/phone_stream.html`);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    // Guard: Warn if user tries to use device index 0 on cloud hosting
    if (sourceType === 'webcam' && (sourceVal === '0' || sourceVal === '1')) {
      if (window.location.hostname.includes('onrender.com')) {
        setError(
          'Local USB devices (index 0/1) cannot be accessed directly by the cloud server. Please use the HTTP / MJPEG Feed or Mobile Stream URL.'
        );
        return;
      }
    }

    setLoading(true);

    const cleanId = (
      cameraId.trim() || `cam_${Date.now().toString().slice(-4)}`
    )
      .replace(/\s+/g, '_')
      .toLowerCase();
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
      const res = await fetch(`${API_BASE_URL}/api/cameras`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const contentType = res.headers.get('content-type');
      if (res.ok && contentType && contentType.includes('application/json')) {
        onCameraAdded && onCameraAdded();
        onClose();
      } else if (!res.ok) {
        let errorMsg = `Server error (${res.status})`;
        if (contentType && contentType.includes('application/json')) {
          const data = await res.json();
          errorMsg = data.detail || errorMsg;
        }
        throw new Error(errorMsg);
      } else {
        throw new Error('Backend returned non-JSON response.');
      }
    } catch (err) {
      setError(
        err.message === 'Failed to fetch'
          ? `Unable to reach API server at ${API_BASE_URL}. Verify backend status.`
          : err.message
      );
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
              <p className="text-[11px] text-slate-400">
                Connect IP CCTV, RTSP feed, or mobile web stream
              </p>
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
            <div className="bg-rose-950/60 border border-rose-700 p-3 rounded-lg text-xs text-rose-300 flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400 mt-0.5" />
              <span>{error}</span>
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
                onClick={() => handleSourceTypeChange('http')}
                className={`p-2.5 rounded-lg border text-left flex flex-col gap-1 transition ${
                  sourceType === 'http'
                    ? 'bg-blue-950/60 border-blue-500 text-blue-300'
                    : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'
                }`}
              >
                <span className="font-bold flex items-center gap-1.5">
                  <Video className="w-3.5 h-3.5" /> Mobile / Web Stream
                </span>
                <span className="text-[10px] text-slate-500">
                  HTTP / WebSocket Feed
                </span>
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
                <span className="text-[10px] text-slate-500">
                  Standard RTSP URL
                </span>
              </button>

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
                  <Radio className="w-3.5 h-3.5" /> Local Hardware
                </span>
                <span className="text-[10px] text-slate-500">
                  Local USB Index
                </span>
              </button>
            </div>
          </div>

          {/* Source Value Input */}
          <div>
            <label className="text-xs font-semibold text-slate-300 block mb-1">
              {sourceType === 'webcam'
                ? 'Webcam Device Index (Local Server Only):'
                : 'Live Stream Network URL:'}
            </label>
            <input
              type="text"
              value={sourceVal}
              onChange={(e) => setSourceVal(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs font-mono text-cyan-300 focus:outline-none focus:border-blue-500"
              required
            />
          </div>

          {/* Quick Preset Helper */}
          {sourceType === 'http' && (
            <div className="flex items-center gap-2 text-[11px]">
              <span className="text-slate-400">Quick Fill:</span>
              <button
                type="button"
                onClick={() =>
                  setSourceVal(`${API_BASE_URL}/phone_stream.html`)
                }
                className="text-blue-400 hover:underline"
              >
                Render Mobile Feed
              </button>
            </div>
          )}

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
