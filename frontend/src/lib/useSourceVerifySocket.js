// src/lib/useSourceVerifySocket.js
import { useEffect, useRef } from 'react';
import { useAuth } from '@/hooks/auth/AuthProvider';
import {BASE} from "./config.js"


export function useSourceVerifySocket(onMessage) {
  const { tokens } = useAuth();
  const wsRef = useRef(null);

  useEffect(() => {
    if (!tokens?.access) return;

    const wsBase = BASE.replace(/^http/, 'ws'); // http->ws, https->wss
    const url = `${wsBase}/source/ws/verify?token=${encodeURIComponent(tokens.access)}`;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        if (data?.type === 'source_verification') {
          onMessage?.(data.payload);
        }
      } catch {}
    };
    ws.onerror = () => {/* optional: toast */}
    ws.onclose = () => { wsRef.current = null; }

    return () => { ws.close(); };
  }, [tokens?.access, onMessage]);
}
