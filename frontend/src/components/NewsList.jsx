// src/components/NewsList.jsx
import { useMemo, useState, useCallback, useEffect } from 'react';
import { useAuth } from '../auth/AuthProvider.jsx';
import NewsCard from './NewsCard';

export default function NewsList({ items: initialItems }) {
  // items: [{ cluster_id, article, other_articles }, ...]
  const {api} = useAuth();
  const newsApi = useMemo(() => ({
    async bookmarkCluster(clusterId, value) {
      return await api.post(`/news/${clusterId}/bookmark`, { value });
    },
    async markClusterRead(clusterId, value) {
      return await api.post(`/news/${clusterId}/read`, { value });
    },
  }), [api]);

  // открытые кластеры (для выпадающих списков)
  // локальная копия ленты, чтобы можно было менять is_bookmarked
  const [items, setItems] = useState(initialItems || []);
  // если приходят новые пропсы извне — можно синхронизировать:
  // useEffect(()=> setItems(initialItems||[]), [initialItems]);

  const [open, setOpen] = useState(() => new Set());
  const toggle = useCallback((cid) => {
    setOpen(prev => {
      const next = new Set(prev);
      next.has(cid) ? next.delete(cid) : next.add(cid);
      return next;
    });
  }, []);

  const copyLink = useCallback(async (url) => {
    try {
      if (navigator.clipboard?.writeText) await navigator.clipboard.writeText(url);
      else {
        const ta = document.createElement('textarea');
        ta.value = url; document.body.appendChild(ta);
        ta.select(); document.execCommand('copy'); document.body.removeChild(ta);
      }
      // eslint-disable-next-line no-alert
      alert('Ссылка скопирована');
    } catch { alert('Не удалось скопировать'); }
  }, []);

  const toggleBookmark = useCallback(async (clusterId, nextValue) => {
    setItems(prev => prev.map(it => it.cluster_id === clusterId ? { ...it, bookmarked: nextValue } : it));
    try {
      await newsApi.bookmarkCluster(clusterId, nextValue);
    } catch {
      setItems(prev => prev.map(it => it.cluster_id === clusterId ? { ...it, bookmarked: !nextValue } : it));
      alert('Не удалось изменить избранное');
    }
  }, [newsApi]);

  const toggleRead = useCallback(async (clusterId, nextValue) => {
    setItems(prev => prev.map(it => it.cluster_id === clusterId ? { ...it, read: nextValue } : it));
    try {
      await newsApi.markClusterRead(clusterId, nextValue);
    } catch {
      setItems(prev => prev.map(it => it.cluster_id === clusterId ? { ...it, read: !nextValue } : it));
      alert('Не удалось изменить статус прочтения');
    }
  }, [newsApi]);

  if (!items || items.length === 0) {
    return <div className="text-neutral-500">Новостей нет</div>;
  }

  return (
    <div className="grid gap-3 md:gap-4">
      {items.map((it) => (
        <NewsCard
          key={it.cluster_id}
          item={it}
          isOpen={open.has(it.cluster_id)}
          onToggleMore={() => toggle(it.cluster_id)}
          onCopyLink={copyLink}
          onToggleBookmark={toggleBookmark}
          onToggleRead={toggleRead}
        />
      ))}
    </div>
  );
}
