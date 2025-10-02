// components/NewsFilters.jsx
import React, {useEffect, useMemo, useState} from "react";

export default function NewsFilters({ api, state, set, onReset }) {
  const { topicIds, language, q, since, until, orderInCluster, sort } = state;
  const { setTopicIds, setLanguage, setQ, setSince, setUntil, setOrderInCluster, setSort } = set;

  const [topics, setTopics] = useState([]);
  const [loadingTopics, setLoadingTopics] = useState(false);

  // грузим темы
  useEffect(() => {
    let cancelled = false;
    setLoadingTopics(true);
    api.get("/news/topics/all")
      .then(r => r.json())
      .then(data => {
        if (cancelled) return;
        // допускаем разные поля названия: title/name/label
        const items = data?.items || data || [];
        const normalized = items.map(t => ({
          id: t.id ?? t.topic_id ?? t.value,
          title: t.title ?? t.name ?? t.label ?? `Тема #${t.id}`,
        })).filter(t => t.id != null);
        setTopics(normalized);
      })
      .catch(() => setTopics([]))
      .finally(() => setLoadingTopics(false));
    return () => { cancelled = true; };
  }, [api]);

  // helper: мультиселект -> number[]
  const handleTopicsChange = (e) => {
    const options = Array.from(e.target.selectedOptions);
    const ids = options.map(o => Number(o.value)).filter(n => !Number.isNaN(n));
    setTopicIds(ids);
  };

  // для отображения выбранных
  const selectedSet = useMemo(() => new Set(topicIds || []), [topicIds]);

  // свитч «порядок в кластере»
  const toggleOrder = () => {
    setOrderInCluster(orderInCluster === "date_desc" ? "date_asc" : "date_desc");
  };

  return (
    <div className="card mb-4 p-4 flex flex-col gap-4">
      {/* Поиск + Язык */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div className="flex flex-col gap-1">
          <label className="text-sm opacity-80">Поиск по новостям</label>
          <input
            className="input"
            placeholder="Введите минимум 2 символа"
            value={q}
            onChange={e => setQ(e.target.value)}
          />
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-sm opacity-80">Язык</label>
          <select
            className="input"
            value={language || ""}
            onChange={(e) => setLanguage(e.target.value || null)}
          >
            <option value="">Любой</option>
            <option value="ru">Русский</option>
            <option value="en">English</option>
          </select>
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-sm opacity-80">Темы</label>
          <select
            multiple
            className="input min-h-12"
            value={topicIds?.map(String) || []}
            onChange={handleTopicsChange}
          >
            {loadingTopics && <option disabled>Загрузка…</option>}
            {!loadingTopics && topics.length === 0 && <option disabled>Нет тем</option>}
            {!loadingTopics && topics.map(t => (
              <option key={t.id} value={t.id}>
                {selectedSet.has(t.id) ? "✓ " : ""}{t.title}
              </option>
            ))}
          </select>
          <p className="text-xs opacity-70">Удерживайте Ctrl/Cmd для выбора нескольких тем</p>
        </div>
      </div>

      {/* Сортировки */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div className="flex flex-col gap-1">
          <label className="text-sm opacity-80">Сортировка кластеров</label>
          <select
            className="input"
            value={sort}
            onChange={(e)=> setSort(e.target.value)}
            title='sort: "recent" | "weight"'
          >
            <option value="recent">По дате (недавние)</option>
            <option value="weight">По весу (важные)</option>
          </select>
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-sm opacity-80">Порядок внутри кластера</label>
          {/* свитч */}
          <button
            type="button"
            onClick={toggleOrder}
            className={`inline-flex items-center justify-between w-full rounded-lg border px-3 py-2
              ${orderInCluster === "date_desc" ? "bg-gray-200 dark:bg-gray-700" : "bg-white dark:bg-gray-800"}
            `}
            title='order_in_cluster: "date_desc" | "date_asc"'
          >
            <span className="text-sm">
              {orderInCluster === "date_desc" ? "Сначала новые" : "Сначала старые"}
            </span>
            <span
              className={`ml-3 inline-block w-10 h-6 rounded-full relative transition-colors
                ${orderInCluster === "date_desc" ? "bg-green-500" : "bg-gray-400"}
              `}
            >
              <span
                className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform
                  ${orderInCluster === "date_desc" ? "" : "-translate-x-full"}
                `}
              />
            </span>
          </button>
        </div>

        <div className="flex items-end">
          <button className="btn-secondary w-full" onClick={onReset}>Сбросить фильтры</button>
        </div>
      </div>

      {/* Период */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div className="flex flex-col gap-1">
          <label className="text-sm opacity-80">Период: с</label>
          <input
            className="input"
            type="datetime-local"
            value={since}
            onChange={e => setSince(e.target.value)}
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-sm opacity-80">Период: по</label>
          <input
            className="input"
            type="datetime-local"
            value={until}
            onChange={e => setUntil(e.target.value)}
          />
        </div>
        <div className="flex items-end">
          {/* пусто, чтобы сетка была ровная */}
        </div>
      </div>
    </div>
  );
}
