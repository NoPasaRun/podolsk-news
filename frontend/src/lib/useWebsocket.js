import { useCallback, useEffect, useRef } from "react";
import {useAuth} from "@/hooks/auth/AuthProvider.jsx";


export function useWebsocket({ wsPath = "/ws/", onMessage }) {
  const socketsRef = useRef(new Map()); // key -> WebSocket
  const { api } = useAuth();

  const makeUrl = useCallback(() => {
    const isHttps = typeof window !== "undefined" && window.location.protocol === "https:";
    const proto = isHttps ? "wss" : "ws";
    const host = typeof window !== "undefined" ? window.location.host : "localhost";
    if (/^wss?:\/\//i.test(wsPath)) return wsPath; // уже полный URL
    return `${proto}://${host}${wsPath}`;
  }, [wsPath]);

  const closeForKey = useCallback((key) => {
    const ws = socketsRef.current.get(key);
    if (!ws) return;
    try { ws.onopen = ws.onclose = ws.onmessage = ws.onerror = null; } catch {}
    try { ws.close(); } catch {}
    socketsRef.current.delete(key);
  }, []);

  /**
   * verify(sourceId)
   * - если сокет открыт — просто шлём {source_id}
   * - если сокета нет/закрыт — открываем и шлём при onopen
   * - соединение не закрываем
   */
  const verify = useCallback((sourceId) => {
    const key = String(sourceId);
    const existing = socketsRef.current.get(key);
    const payload = JSON.stringify({ source_id: sourceId });

    const sendSafe = (ws) => {
      try { ws.send(payload); } catch {}
    };

    if (existing && existing.readyState === WebSocket.OPEN) {
      sendSafe(existing);
      return;
    }

    if (existing && existing.readyState === WebSocket.CONNECTING) {
      // дождёмся открытия и отправим
      const prevOnOpen = existing.onopen;
      existing.onopen = (ev) => {
        prevOnOpen && prevOnOpen(ev);
        sendSafe(existing);
      };
      return;
    }

    // создаём новое соединение
    closeForKey(key);

    const url = makeUrl();
    const protocols = ["bearer", api.tokens.access];

    const ws = new WebSocket(url, protocols);
    socketsRef.current.set(key, ws);

    ws.onopen = () => sendSafe(ws);

    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        onMessage && onMessage(data);
      } catch {}
    };

    ws.onerror = () => {};
    ws.onclose  = () => {
      // не переоткрываем автоматически — откроем при следующем verify()
    };
  }, [makeUrl, closeForKey, onMessage]);

  useEffect(() => {
    return () => {
      for (const [key] of socketsRef.current) closeForKey(key);
    };
  }, [closeForKey]);

  return { verify };
}
