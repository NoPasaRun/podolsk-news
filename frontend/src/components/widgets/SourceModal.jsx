// src/components/SourceModal.jsx
import { useEffect, useMemo, useState, useCallback, useRef } from 'react';
import { useAuth } from "@/hooks/auth/AuthProvider";
import { useSourceVerifySocket } from '@/lib/useSourceVerifySocket';
import StatusBadge from "./StatusBadge";
import Alert from "./Alert";

// dnd-kit
import { DndContext, closestCenter, PointerSensor, KeyboardSensor,
useSensor, useSensors } from "@dnd-kit/core";
import {
  SortableContext, verticalListSortingStrategy, useSortable, arrayMove
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { restrictToVerticalAxis, restrictToParentElement } from "@dnd-kit/modifiers";

export default function SourceModal({ open, onClose }) {
  const { api } = useAuth();
  const sourcesApi = useMemo(() => ({
    async listMySources() { return await (await api.get('/source/my')).json(); },
    async listAllSources() { return await (await api.get('/source/all')).json(); },
    async addExistingSource(sourceId) { return await (await api.post(`/source/${sourceId}`)).json(); },
    async removeExistingSource(sourceId) { return await (await api.delete(`/source/${sourceId}`)).json(); },
    async createSource(payload) { return await (await api.post('/source/create', payload)).json(); }, // {domain, kind}
    async updateUserSource(userSourceId, patch) { return await (await api.patch(`/source/update/${userSourceId}`, patch)).json(); },
  }), [api]);

  const [tab, setTab] = useState('mine'); // 'mine' | 'catalog' | 'custom'
  const [mine, setMine] = useState([]);   // [{ id, rank, source:{ status, domain, kind }, ... }]
  const [allSources, setAllSources] = useState([]);
  const [loading, setLoading] = useState(false);

  const [form, setForm] = useState({ domain: '', kind: '' });
  const [saving, setSaving] = useState(false);
  const [openError, setOpenError] = useState(false);
  const [savingOrder, setSavingOrder] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [mineRes, allRes] = await Promise.all([
        sourcesApi.listMySources(),
        sourcesApi.listAllSources(),
      ]);
      setMine([...(mineRes || [])]);
      setAllSources([...(allRes || [])]);
    } finally {
      setLoading(false);
    }
  }, [sourcesApi]);

  useEffect(() => { if (open) refresh(); }, [open, refresh]);

  // WS обновления статусов
  useSourceVerifySocket((payload) => {
    // payload: {source_id, status, error?}
    setMine(prev => prev.map(us => {
      if (us.source_id === payload.source_id) {
        const patch = (payload.status === 'ok')
          ? { source: { ...us.source, status: 'active' }, last_error: null }
          : { source: { ...us.source, status: 'error' }, last_error: payload.error || 'Unknown error' };
        return { ...us, ...patch };
      }
      return us;
    }));
  });

  const notSubscribed = useMemo(() => {
    const mineIds = new Set(mine.map(m => m.source_id));
    return allSources.filter(s => !mineIds.has(s.id));
  }, [mine, allSources]);

  const connectExisting = async (sourceId) => { await sourcesApi.addExistingSource(sourceId); await refresh(); };
  const removeExisting = async (sourceId) => { await sourcesApi.removeExistingSource(sourceId); await refresh(); };

  const createNew = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const res = await sourcesApi.createSource({ domain: form.domain, kind: form.kind });
      if (!res?.id) throw new DOMException("Client Error");
      await refresh();
    } catch {
      setOpenError(true);
      setSaving(false);
      return;
    }
    setSaving(false);
    setTab('mine');
  };

  const updateUserSource = async (userSourceId, patch) => {
    await sourcesApi.updateUserSource(userSourceId, patch);
    await refresh();
  };

  // ======== DND only for ACTIVE sources ========
  const isActive = (us) => (us?.source?.status === 'active');
  const sortByRankDesc = (a, b) => (Number(b.rank ?? 0) - Number(a.rank ?? 0)) || (Number(b.id) - Number(a.id));

  const activeList = useMemo(() => mine.filter(isActive).slice().sort(sortByRankDesc), [mine]);
  const inactiveList = useMemo(() => mine.filter(us => !isActive(us)).slice().sort(sortByRankDesc), [mine]);

  const isMobile = typeof window !== "undefined" && window.matchMedia("(pointer:coarse)").matches;
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: isMobile ? { delay: 180, tolerance: 8 } : { distance: 6 } }),
    useSensor(KeyboardSensor)
  );

  // Коммит порядка на сервер после drop
  const saveOrder = useCallback(async (newActiveOrder) => {
    // Собираем итоговый список: активные (в новом порядке) + неактивные (как были)
    const combined = [...newActiveOrder, ...inactiveList];
    const total = combined.length;

    // Проставляем ранги сверху вниз (включая неактивные — чтобы они гарантированно ушли вниз)
    const withRanks = combined.map((it, idx) => ({ ...it, rank: total - idx }));

    // Патчим только изменившиеся
    const changed = withRanks.filter(it => it.rank !== (mine.find(m => m.id === it.id)?.rank));
    if (changed.length === 0) return;

    setSavingOrder(true);
    try {
      await Promise.all(changed.map(it => sourcesApi.updateUserSource(it.id, { rank: it.rank })));
      // Локально покажем новый порядок (без ожидания сети)
      setMine(withRanks);
      await refresh();
    } finally {
      setSavingOrder(false);
    }
  }, [inactiveList, mine, sourcesApi, refresh]);

  const onDragEnd = (e) => {
    const { active, over } = e;
    if (!over || active.id === over.id) return;

    const ids = activeList.map(x => String(x.id));
    const oldIndex = ids.indexOf(String(active.id));
    const newIndex = ids.indexOf(String(over.id));
    if (oldIndex < 0 || newIndex < 0) return;

    const newActiveOrder = arrayMove(activeList, oldIndex, newIndex);
    // мгновенно отрисуем локально
    const total = newActiveOrder.length + inactiveList.length;
    const previewCombined = [...newActiveOrder, ...inactiveList].map((it, idx) => ({ ...it, rank: total - idx }));
    setMine(previewCombined);

    // и сохраним на бэке
    saveOrder(newActiveOrder);
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="w-full max-w-4xl bg-white dark:bg-neutral-900 rounded-2xl shadow-xl p-4 md:p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold">Источники</h2>
          <button className="px-3 py-1 rounded-lg bg-neutral-100 dark:bg-neutral-800" onClick={onClose}>Закрыть</button>
        </div>

        <div className="flex gap-2 mb-4">
          {['mine','catalog','custom'].map(k => (
            <button
              key={k}
              className={`px-3 py-1 rounded-lg ${tab===k?'bg-blue-600 text-white':'bg-neutral-100 dark:bg-neutral-800'}`}
              onClick={()=>setTab(k)}
            >
              {k==='mine'?'Мои':k==='catalog'?'Подключить существующий':'Добавить свой'}
            </button>
          ))}
        </div>

        {tab==='mine' && (
          <div className="space-y-4">
            {loading && <div>Загрузка…</div>}
            {!loading && mine.length===0 && <div className="text-neutral-500">Пока нет подключенных источников</div>}

            {!loading && mine.length>0 && (
              <>
                {/* ACTIVE block (draggable) */}
                <section>
                  <div className="text-xs uppercase tracking-wide text-neutral-500 mb-2">Активные</div>
                  <div className="rounded-2xl border border-neutral-200 dark:border-neutral-800 overflow-hidden">
                    <DndContext
                      sensors={sensors}
                      collisionDetection={closestCenter}
                      onDragEnd={onDragEnd}
                      modifiers={[restrictToVerticalAxis, restrictToParentElement]}
                    >
                      <SortableContext
                        items={activeList.map(m => String(m.id))}
                        strategy={verticalListSortingStrategy}
                      >
                        <ul className="divide-y divide-neutral-200 dark:divide-neutral-800">
                          {activeList.map((us, idx) => (
                            <SortableRow key={us.id} us={us} rank={(activeList.length + inactiveList.length) - idx} />
                          ))}
                        </ul>
                      </SortableContext>
                    </DndContext>
                  </div>
                </section>

                {/* INACTIVE block (not draggable, always at bottom) */}
                {inactiveList.length > 0 && (
                  <section>
                    <div className="text-xs uppercase tracking-wide text-neutral-500 mt-4 mb-2">Неактивные</div>
                    <ul className="rounded-2xl border border-neutral-200 dark:border-neutral-800 overflow-hidden divide-y divide-neutral-200 dark:divide-neutral-800">
                      {inactiveList.map((us, idx) => {
                        const rank = (activeList.length + inactiveList.length) - (activeList.length + idx); // снизу
                        return (
                          <InactiveRow key={us.id} us={us} rank={rank} />
                        );
                      })}
                    </ul>
                  </section>
                )}

                {savingOrder && <div className="text-xs text-neutral-500">Сохраняем порядок…</div>}
              </>
            )}
          </div>
        )}

        {tab==='catalog' && (
          <div className="space-y-3">
            {loading && <div>Загрузка…</div>}
            {!loading && notSubscribed.length===0 && <div className="text-neutral-500">Нет доступных неподключенных источников</div>}
            {!loading && notSubscribed.map(s => (
              <div key={s.id} className="border rounded-xl p-3 flex items-center justify-between gap-3">
                <div>
                  <div className="font-medium">{s.kind}</div>
                  <div className="text-sm text-neutral-500 break-all">{s.domain}</div>
                </div>
                { s.connected ? (
                    <button className="btn-primary bg-red-400 hover:bg-red-600" onClick={() => removeExisting(s.id)}>Отключить</button>
                ) : (
                    <button className="btn-primary" onClick={() => connectExisting(s.id)}>Подключить</button>
                )}
              </div>
            ))}
          </div>
        )}

        {tab==='custom' && (
          <form onSubmit={createNew} className="space-y-3">
            <div className="grid md:grid-cols-2 gap-3">
              <div>
                <label className="block text-sm mb-1">Домен</label>
                <input
                  className="input w-full"
                  required
                  placeholder="example.com"
                  value={form.domain || ""}
                  onChange={e => setForm(f => ({...f, domain: e.target.value}))}
                />
              </div>
              <div>
                <label className="block text-sm mb-1">Тип источника</label>
                <select
                  className="input w-full"
                  required
                  value={form.kind || ""}
                  onChange={e => setForm(f => ({...f, kind: e.target.value}))}
                >
                  <option value="">Выберите тип…</option>
                  <option value="rss">RSS</option>
                  <option value="telegram">TG</option>
                  <option value="json">API</option>
                </select>
              </div>
            </div>

            <div className="text-sm text-neutral-500">
              После отправки источник пройдёт автоматическую проверку качества. Статус обновится здесь в реальном времени.
            </div>
            <div className="flex gap-2">
              <button className="btn-primary" disabled={saving}>
                {saving ? 'Добавляем…' : 'Добавить'}
              </button>
              <button
                type="button"
                className="px-3 py-2 rounded-lg bg-neutral-100 dark:bg-neutral-800"
                onClick={() => setTab('mine')}
              >
                К моим
              </button>
            </div>
          </form>
        )}
      </div>

      <Alert
        open={openError}
        onClose={() => {setOpenError(false)}}
        title={"Ошибка сохранения"}
        description={"Такой источник уже существует"}
        variant={"warning"}
      />
    </div>
  );
}

// ===== Rows =====

function SortableRow({ us, rank }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: String(us.id) });

  const style = { transform: CSS.Transform.toString(transform), transition };

  return (
    <li ref={setNodeRef} style={style} className={`bg-white dark:bg-neutral-900 ${isDragging ? "relative z-10" : ""}`}>
      <div className="border-0 px-3 py-3 flex items-center gap-3">
        {/* handle */}
        <button
          {...attributes} {...listeners}
          className="w-10 h-10 rounded-md flex items-center justify-center
                     cursor-grab active:cursor-grabbing hover:bg-neutral-100 dark:hover:bg-neutral-800"
          style={{ touchAction: 'none' }}
          aria-label="Переместить"
          title="Перетащи, чтобы изменить порядок"
        >
          {/* простая ручка без икон-библиотек */}
          <span className="text-lg leading-none">⋮⋮</span>
        </button>

        <span className="w-9 h-9 rounded-lg bg-neutral-100 dark:bg-neutral-800 flex items-center justify-center text-sm font-semibold">
          {rank}
        </span>

        <div className="min-w-0 flex-1">
          <div className="text-sm sm:text-base font-medium truncate">{us?.source?.domain || '—'}</div>
          <div className="text-xs text-neutral-500">{us?.source?.kind} • <StatusBadge status={us?.source?.status} error={us?.last_error} /></div>
        </div>
      </div>
    </li>
  );
}

function InactiveRow({ us, rank }) {
  return (
    <li className="bg-white dark:bg-neutral-900 opacity-60">
      <div className="px-3 py-3 flex items-center gap-3">
        {/* пустая ручка (disabled) */}
        <div className="w-10 h-10 rounded-md flex items-center justify-center border border-transparent">
          <span className="text-lg leading-none text-neutral-300">⋮⋮</span>
        </div>

        <span className="w-9 h-9 rounded-lg bg-neutral-100 dark:bg-neutral-800 flex items-center justify-center text-sm font-semibold">
          {rank}
        </span>

        <div className="min-w-0 flex-1">
          <div className="text-sm sm:text-base font-medium truncate">{us?.source?.domain || '—'}</div>
          <div className="text-xs text-neutral-500">{us?.source?.kind} • <StatusBadge status={us?.source?.status} error={us?.last_error} /></div>
        </div>
      </div>
    </li>
  );
}
