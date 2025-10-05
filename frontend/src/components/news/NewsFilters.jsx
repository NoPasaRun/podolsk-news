import { useEffect, useMemo, useState } from "react";
import MultiSelect from "@/components/ui/MultiSelect";
import Switch from "@/components/ui/Switch";
import DateTimeInput from "@/components/ui/DateTimeInput";


export default function NewsFilters({ api, state, set, onReset }) {
  const { topicIds, language, q, since, until, orderInCluster, sort } = state;

  // опции тем
  const [topics, setTopics] = useState([]);
  const topicOptions = useMemo(
    () => topics.map((t) => ({ id: t.id, label: t.title })),
    [topics]
  );

  // загрузка тем
  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const res = await api.get("/news/topics/all");
        const data = await res.json().catch(() => ({}));
        if (!alive) return;
        setTopics(data?.items || data || []);
      } catch {
        if (!alive) return;
        setTopics([]);
      }
    })();
    return () => { alive = false; };
  }, [api]);

  // свитчи
  const orderAsc = orderInCluster === "date_asc";
  const sortByWeight = sort === "weight";

  return (
    <div className="rounded-2xl border p-3 md:p-4 bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 mb-4">
      <div className="grid gap-3 lg:grid-cols-5 md:grid-cols-3">
        {/* Поиск */}
        <div className="flex flex-col gap-1">
          <label className="text-xs opacity-70">Поиск</label>
          <input
            className="input"
            placeholder="ключевые слова…"
            value={q || ""}
            onChange={(e) => set.setQ(e.target.value)}
          />
        </div>

        {/* Темы */}
        <div className="flex flex-col gap-1">
          <label className="text-xs opacity-70">Темы</label>
          <MultiSelect
            options={topicOptions}
            value={topicIds || []}
            onChange={(ids) => set.setTopicIds(ids.map(Number))}
            placeholder="Темы"
            className=""
            size="sm"
            maxVisibleChips={2}
          />
        </div>

        {/* Язык */}
        <div className="flex flex-col gap-1">
          <label className="text-xs opacity-70">Язык</label>
          <select
            className="input"
            value={language || ""}
            onChange={(e) => set.setLanguage(e.target.value || null)}
          >
            <option value="">Любой</option>
            <option value="russian">Русский</option>
            <option value="english">English</option>
            <option value="german">Deutsch</option>
            <option value="spanish">Espanol</option>
          </select>
        </div>

        {/* С даты */}
        <div className="flex flex-col gap-1">
          <label className="text-xs opacity-70">С даты</label>
          <DateTimeInput value={since || ""} onChange={(iso) => set.setSince(iso)} />
        </div>

        {/* По дату */}
        <div className="flex flex-col gap-1">
          <label className="text-xs opacity-70">По дату</label>
          <DateTimeInput value={until || ""} onChange={(iso) => set.setUntil(iso)} />
        </div>
      </div>

      {/* Свитчи и сброс */}
      <div className="mt-3 grid gap-3 md:grid-cols-3">
        <div className="flex items-center gap-4">
          <span className="text-xs opacity-70 min-w-36">Порядок в кластере:</span>
          <Switch
            checked={orderAsc}
            onChange={(v) => set.setOrderInCluster(v ? "date_asc" : "date_desc")}
            label={orderAsc ? "старые → новые" : "новые → старые"}
            hint="Сортировка статей внутри кластера"
          />
        </div>

        <div className="flex items-center gap-4">
          <span className="text-xs opacity-70 min-w-36">Сортировка кластеров:</span>
          <Switch
            checked={sortByWeight}
            onChange={(v) => set.setSort(v ? "weight" : "recent")}
            label={sortByWeight ? "по весу" : "по времени"}
            hint="Основная сортировка ленты"
          />
        </div>

        <div className="flex items-center gap-2 justify-end">
          <button
            type="button"
            className="px-3 py-2 rounded-xl bg-neutral-100 dark:bg-neutral-700 text-sm"
            onClick={onReset}
          >
            Сбросить
          </button>
        </div>
      </div>
    </div>
  );
}
