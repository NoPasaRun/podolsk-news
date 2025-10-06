import { useEffect, useRef, useCallback } from "react";
import { useTelemetry } from "./TelemetryProvider";

/**
 * @param meta { cluster_id:number, article_id:number, source_id:number, position?:number }
 */
export function useNewsCard(meta) {
  const { observeCard, onCardClick, onOutbound } = useTelemetry();
  const ref = useRef(null);

  useEffect(() => observeCard(ref.current, meta), [observeCard, meta]);

  const handleCardClick = useCallback(() => onCardClick(meta), [onCardClick, meta]);
  const handleLinkClick = useCallback((e) => {
    // не мешаем навигации, просто сообщаем
    const href = e.currentTarget?.href || "";
    onOutbound(meta, href);
  }, [onOutbound, meta]);

  return { ref, handleCardClick, handleLinkClick };
}
