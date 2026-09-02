import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * Custom hook to handle real-time communications with the Border Surveillance backend.
 */
export function useSystemWebSocket() {
  const [connected, setConnected] = useState(false);
  const [cameraList, setCameraList] = useState([]);
  const [cameraFrames, setCameraFrames] = useState({});
  const [alerts, setAlerts] = useState([]);
  const [status, setStatus] = useState({
    total_cameras: 0,
    cameras_online: 0,
    active_tracks: 0,
    active_alerts: 0,
    last_update: new Date().toISOString(),
    zone_name: 'Border Sector North (Alpha-7)',
  });

  const alertWsRef = useRef(null);
  const frameWsRefs = useRef({});

  // 1. Fetch camera registry
  const refreshCameras = useCallback(async () => {
    try {
      const res = await fetch('/cameras');
      if (res.ok) {
        const data = await res.json();
        const cams = data.cameras || [];
        setCameraList(cams);
        setStatus((prev) => ({
          ...prev,
          total_cameras: cams.length,
          cameras_online: cams.filter((c) => c.enabled !== false).length,
          last_update: new Date().toISOString(),
        }));
      }
    } catch (err) {
      console.warn('Backend not yet reachable on /cameras, retrying...', err);
    }
  }, []);

  useEffect(() => {
    refreshCameras();
    const interval = setInterval(refreshCameras, 2500);
    return () => clearInterval(interval);
  }, [refreshCameras]);

  // 2. Connect Alert WebSocket
  useEffect(() => {
    let reconnectTimer = null;
    const connectAlerts = () => {
      const isHttps = window.location.protocol === 'https:';
      const protocol = isHttps ? 'wss:' : 'ws:';
      const host = window.location.host;
      const wsUrl = `${protocol}//${host}/ws/alerts`;

      const ws = new WebSocket(wsUrl);
      alertWsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        console.log('[Alert WS] Connected');
        refreshCameras();
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === 'alert' && msg.payload) {
            const payload = msg.payload;
            if (payload.alert_id === 'SYS_CAM_UPDATE') {
              refreshCameras();
              return;
            }
            setAlerts((prev) => [payload, ...prev].slice(0, 50));
            setStatus((prev) => ({
              ...prev,
              active_alerts: prev.active_alerts + 1,
              last_update: new Date().toISOString(),
            }));
          } else if (msg.type === 'status' && msg.payload) {
            setStatus((prev) => ({ ...prev, ...msg.payload }));
          }
        } catch (e) {
          console.error('[Alert WS] Failed to parse message:', e);
        }
      };

      ws.onclose = () => {
        setConnected(false);
        console.log('[Alert WS] Closed, reconnecting in 2s...');
        reconnectTimer = setTimeout(connectAlerts, 2000);
      };

      ws.onerror = (err) => {
        console.warn('[Alert WS] Error:', err);
        ws.close();
      };
    };

    connectAlerts();

    return () => {
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (alertWsRef.current) alertWsRef.current.close();
    };
  }, [refreshCameras]);

  // 3. Connect Frame WebSockets for each camera
  useEffect(() => {
    const activeWsMap = frameWsRefs.current;
    const isHttps = window.location.protocol === 'https:';
    const protocol = isHttps ? 'wss:' : 'ws:';
    const host = window.location.host;

    cameraList.forEach((cam) => {
      const cid = cam.camera_id;
      if (!activeWsMap[cid] || activeWsMap[cid].readyState === WebSocket.CLOSED) {
        const wsUrl = `${protocol}//${host}/ws/frames/${cid}`;
        const ws = new WebSocket(wsUrl);
        activeWsMap[cid] = ws;

        ws.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data);
            if (msg.type === 'frame' && msg.data) {
              setCameraFrames((prev) => ({
                ...prev,
                [cid]: `data:image/jpeg;base64,${msg.data}`,
              }));
            }
          } catch (e) {
            console.error(`[Frame WS ${cid}] Parse error:`, e);
          }
        };

        ws.onerror = () => {};
        ws.onclose = () => {
          delete activeWsMap[cid];
        };
      }
    });

    // Cleanup disconnected cameras
    Object.keys(activeWsMap).forEach((cid) => {
      if (!cameraList.some((c) => c.camera_id === cid)) {
        try {
          activeWsMap[cid].close();
        } catch (e) {}
        delete activeWsMap[cid];
        setCameraFrames((prev) => {
          const next = { ...prev };
          delete next[cid];
          return next;
        });
      }
    });
  }, [cameraList]);

  return {
    connected,
    status,
    alerts,
    cameraFrames,
    cameraList,
    refreshCameras,
  };
}
