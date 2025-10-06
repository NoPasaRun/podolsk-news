import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef } from "react";
import {useAuth} from "@/hooks/auth/AuthProvider.jsx";

const TelemetryCtx = createContext(null);

// простая генерация session_id
const sessionId = crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2)}`;

export function TelemetryProvider({ children, endpoint = "/api/telemetry/events" }) {
  const itemsRef = useRef(new Map()); // el -> { meta, visibleSince, totalMs, impressionSent, timer }
  const queueRef = useRef([]);        // массив событий для батча
  const flushTimer = useRef(null);

  const {api} = useAuth();

  const pushEvent = useCallback(async (evt) => {
    queueRef.current.push({
      session_id: sessionId,
      ts: Date.now(),
      ...evt,
    });
    // автофлаш: по 20 событий или каждые 5 секунд
    if (queueRef.current.length >= 20) {
      await flush("size");
    } else if (!flushTimer.current) {
      flushTimer.current = setTimeout(() => flush("timer"), 5000);
    }
  }, []);

  const sendImmediately = useCallback(async (events) => {
    const payload = JSON.stringify({ events });
    // максимально надёжная доставка при уходе со страницы
    if (navigator.sendBeacon) {
      const blob = new Blob([payload], { type: "application/json" });
      return navigator.sendBeacon(endpoint, blob);
    }
    // fallback: fetch keepalive
    try {
      await api.post(endpoint, payload)
      return true;
    } catch {
      return false;
    }
  }, [endpoint]);

  const flush = useCallback(async (_reason = "") => {
    if (flushTimer.current) { clearTimeout(flushTimer.current); flushTimer.current = null; }
    if (queueRef.current.length === 0) return;
    const batch = queueRef.current.splice(0, queueRef.current.length);
    await sendImmediately(batch);
  }, [sendImmediately]);

  // IntersectionObserver для измерения видимости
  const io = useMemo(() => new IntersectionObserver((entries) => {
    for (const e of entries) {
      const rec = itemsRef.current.get(e.target);
      if (!rec) continue;
      const now = performance.now();
      if (e.isIntersecting && e.intersectionRatio >= 0.5) {
        // стал видим >=50%
        if (!rec.visibleSince) {
          rec.visibleSince = now;
          // отложенно шлём impression (по умолчанию через 800ms видимости)
          if (!rec.impressionSent) {
            rec.timer = setTimeout(() => {
              rec.impressionSent = true;
              pushEvent({
                type: "impression",
                cluster_id: rec.meta.cluster_id,
                article_id: rec.meta.article_id,
                source_id: rec.meta.source_id,
                position: rec.meta.position,
              }).then(r => r);
            }, 800);
          }
        }
      } else {
        // ушёл из видимости — накапливаем dwell
        if (rec.visibleSince) {
          rec.totalMs += now - rec.visibleSince;
          rec.visibleSince = 0;
          if (rec.timer) { clearTimeout(rec.timer); rec.timer = null; }
        }
      }
    }
  }, { threshold: [0, 0.5, 1] }), []);

  // публичные методы
  const observeCard = useCallback((el, meta) => {
    if (!el) return () => {};
    const rec = { meta, visibleSince: 0, totalMs: 0, impressionSent: false, timer: null };
    itemsRef.current.set(el, rec);
    io.observe(el);
    return () => {
      // финализируем dwell
      const r = itemsRef.current.get(el);
      if (r) {
        if (r.visibleSince) {
          r.totalMs += performance.now() - r.visibleSince;
          r.visibleSince = 0;
        }
        // репортим dwell >= 1000ms
        if (r.totalMs >= 1000) {
          pushEvent({
            type: "dwell",
            cluster_id: r.meta.cluster_id,
            article_id: r.meta.article_id,
            source_id: r.meta.source_id,
            dwell_ms: Math.round(r.totalMs),
            position: r.meta.position,
          }).then(r => r);
        }
        if (r.timer) clearTimeout(r.timer);
        itemsRef.current.delete(el);
        io.unobserve(el);
      }
    };
  }, [io, pushEvent]);

  const onCardClick = useCallback((meta) => {
    pushEvent({
      type: "click",
      cluster_id: meta.cluster_id,
      article_id: meta.article_id,
      source_id: meta.source_id,
      position: meta.position
    }).then(r => r);
  }, [pushEvent]);

  const onOutbound = useCallback((meta, href) => {
    pushEvent({
      type: "outbound",
      cluster_id: meta.cluster_id,
      article_id: meta.article_id,
      source_id: meta.source_id,
      url: href,
      position: meta.position,
    }).then(r => r);
    // сразу послать, т.к. возможен уход со страницы
    const batch = queueRef.current.splice(0, queueRef.current.length);
    batch.push({
      session_id: sessionId,
      ts: Date.now(),
      type: "outbound",
      cluster_id: meta.cluster_id,
      article_id: meta.article_id,
      source_id: meta.source_id,
      url: href,
      position: meta.position,
    });
    sendImmediately(batch).then(r => r);
  }, [pushEvent, sendImmediately]);

  // flush при закрытии вкладки / переходе
  useEffect(() => {
    const handler = () => flush("pagehide");
    window.addEventListener("pagehide", handler);
    window.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "hidden") flush("hidden").then(r => r);
    });
    return () => {
      window.removeEventListener("pagehide", handler);
    };
  }, [flush]);

  const telemetryApi = useMemo(() => ({ observeCard, onCardClick, onOutbound }), [observeCard, onCardClick, onOutbound]);
  return <TelemetryCtx.Provider value={telemetryApi}>{children}</TelemetryCtx.Provider>;
}

export function useTelemetry() {
  const ctx = useContext(TelemetryCtx);
  if (!ctx) throw new Error("useTelemetry must be used within TelemetryProvider");
  return ctx;
}
