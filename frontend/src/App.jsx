import { useState, useEffect } from 'react'
import StatusStrip from './components/StatusStrip'
import CameraGrid from './components/CameraGrid'
import AlertFeed from './components/AlertFeed'
import { useSystemWebSocket } from './hooks/useSystemWebSocket'

/**
 * Root application component.
 *
 * Layout (Phase 2 target):
 * ┌─────────────────── Status Strip ──────────────────────┐
 * │  Alert Dashboard       │  Live Camera Grid            │
 * │                        │                              │
 * └────────────────────────┴──────────────────────────────┘
 *
 * Phase 1: Shows connecting state and a "waiting for backend" placeholder.
 */
export default function App() {
  const { connected, status, alerts, cameraFrames, cameraList } = useSystemWebSocket()
  const [mobileStreamUrl, setMobileStreamUrl] = useState(() => {
    const host = window.location.hostname || 'localhost'
    return `https://${host}:8443/phone_stream.html`
  })

  useEffect(() => {
    let cancelled = false

    async function loadMobileStreamInfo() {
      try {
        const res = await fetch('/mobile-stream-info')
        if (!res.ok) return
        const info = await res.json()
        if (!cancelled && info.https_url) {
          setMobileStreamUrl(info.https_url)
        }
      } catch (err) {
        console.warn('Mobile stream info unavailable, using browser host fallback.', err)
      }
    }

    loadMobileStreamInfo()
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div className="flex flex-col h-screen overflow-hidden">
      {/* Top status strip */}
      <StatusStrip status={status} connected={connected} />

      <div className="flex flex-1 overflow-hidden">
        {/* Left sidebar: full-height alert dashboard */}
        <div className="w-[28rem] flex-shrink-0 flex flex-col border-r border-slate-700 overflow-hidden">
          <AlertFeed alerts={alerts} />
        </div>

        {/* Main area: camera grid */}
        <div className="flex-1 overflow-auto p-2">
          <CameraGrid cameras={cameraList} cameraFrames={cameraFrames} mobileStreamUrl={mobileStreamUrl} />
        </div>
      </div>
    </div>
  )
}
