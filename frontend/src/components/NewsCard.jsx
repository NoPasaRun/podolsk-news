// src/components/NewsCard.jsx
import { useMemo, useEffect, useRef } from 'react';

export default function NewsCard({
  item,              // { cluster_id, article, other_articles, is_bookmarked, is_read }
  isOpen,
  onToggleMore,
  onToggleBookmark,  // (clusterId, nextValue) => Promise<void>
  onToggleRead,      // (clusterId, nextValue) => Promise<void>
  onCopyLink,
}) {
  const main = item.article;
  const others = item.other_articles;
  const isBookmarked = !!item.bookmarked;
  const isRead = !!item.read;

    // >>> NEW: наблюдаем появление карточки на экране
  const rootRef = useRef(null);

  useEffect(() => {
    if (!rootRef.current) return;
    if (isRead) return; // уже прочитано — не отслеживаем

    const el = rootRef.current;
    const observer = new IntersectionObserver(
      (entries) => {
        const e = entries[0];
        if (e && e.isIntersecting && e.intersectionRatio >= 0.6) {
          // оптимистично подсветим как прочитанное
          onToggleRead(item.cluster_id, true).catch(() => {});
          observer.disconnect();
        }
      },
      {
        root: null,          // viewport
        rootMargin: '0px',
        threshold: [0, 0.25, 0.5, 0.6, 0.75, 1],
      }
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, [item.cluster_id, onToggleRead]);

  const published = useMemo(() => {
    if (!main.published_at) return '';
    try {
      const d = new Date(main.published_at);
      return d.toLocaleString();
    } catch { return main.published_at; }
  }, [main.published_at]);

  return (
      <div ref={rootRef} className="border rounded-2xl p-4 bg-white dark:bg-neutral-900 shadow-sm">
        <div className="mb-2">
          <a href={main.url} target="_blank" rel="noreferrer"
             className="text-lg font-semibold hover:underline">
            {main.title}
          </a>
        </div>
        {main.summary && (
            <p className="text-sm text-neutral-600 dark:text-neutral-400 line-clamp-3">
              {main.summary}
            </p>
        )}
        <div className="mt-2 text-xs text-neutral-500">
          {main.source_domain} • {published}
        </div>

        {/* Кнопки действий */}
          <div className="mt-3 flex flex-wrap items-center gap-2">
              <button className="px-3 py-1 rounded-lg bg-neutral-100 dark:bg-neutral-800 text-sm hover:bg-neutral-200"
                      onClick={() => onCopyLink(main.url)}>
                  🔗 Копировать
              </button>

              <button
                  className={`px-3 py-1 rounded-lg text-sm ${isBookmarked ? 'bg-yellow-200 dark:bg-yellow-700' : 'bg-neutral-100 dark:bg-neutral-800 hover:bg-neutral-200'}`}
                  onClick={() => onToggleBookmark(item.cluster_id, !isBookmarked)}
                  title={isBookmarked ? 'Убрать из избранного' : 'Добавить в избранное'}>
                  {isBookmarked ? '⭐ В избранном' : '☆ В избранное'}
              </button>

              <button
                  className={`px-3 py-1 rounded-lg text-sm ${isRead
                      ? 'bg-green-200 dark:bg-green-700'
                      : 'bg-neutral-100 dark:bg-neutral-800 hover:bg-neutral-200'}`}
                  onClick={() => onToggleRead(item.cluster_id, !isRead)}
                  title={isRead ? 'Отметить как непрочитанный' : 'Отметить как прочитанный'}>
                  {isRead ? '✓ Прочитано' : '✓ Прочитать'}
              </button>

              {item.other_articles?.length > 0 && (
                  <button
                      className="px-3 py-1 rounded-lg bg-neutral-100 dark:bg-neutral-800 text-sm hover:bg-neutral-200"
                      onClick={onToggleMore}>
                      {isOpen ? '▴ Свернуть источники' : `▾ Ещё источники (${item.other_articles.length})`}
                  </button>
              )}
          </div>

          {/* Выпадающий список других источников */}
          {isOpen && others.length > 0 && (
              <ul className="mt-3 space-y-2 border-t pt-3">
                  {others.map((it) => (
                      <li key={it.id} className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                              <a href={it.url} target="_blank" rel="noreferrer"
                                 className="text-sm hover:underline break-all">
                                  {it.title || it.url}
                              </a>
                              <div className="text-xs text-neutral-500">
                                  {it.source_domain}
                              </div>
                          </div>
                          <button
                              className="px-2 py-1 rounded bg-neutral-100 dark:bg-neutral-800 text-xs hover:bg-neutral-200 shrink-0"
                        onClick={() => onCopyLink(it.url)}
                        title="Скопировать ссылку"
                    >
                      🔗
                    </button>
                  </li>
              ))}
            </ul>
        )}
      </div>
  );
}
