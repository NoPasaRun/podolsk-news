// src/components/SourceModal.jsx
import { useEffect, useMemo, useState, useCallback } from 'react';
import {useAuth} from "@/hooks/auth/AuthProvider";
import { useSourceVerifySocket } from '@/lib/useSourceVerifySocket';
import StatusBadge from "./StatusBadge";
import Alert from "./Alert";

export default function SourceModal({ open, onClose }) {
  const {api} = useAuth();
  const sourcesApi = useMemo(() => ({
      async listMySources() { return await (await api.get('/source/my')).json(); },
      async listAllSources() { return await (await api.get('/source/all')).json(); },
      async addExistingSource(sourceId) { return await (await api.post(`/source/${sourceId}`)).json(); },
      async removeExistingSource(sourceId) { return await (await api.delete(`/source/${sourceId}`)).json(); },
      async createSource(payload) { return await (await api.post('/source/create', payload)).json(); }, // {name, url}
      async updateUserSource(userSourceId, patch) { return await (await api.patch(`/source/update/${userSourceId}`, patch)).json(); },
  }) , [api]);

  const [tab, setTab] = useState('mine'); // 'mine' | 'catalog' | 'custom'
  const [mine, setMine] = useState([]);       // [{user_source_id, source_id, name, url, status, last_error, cache_ttl_sec, priority}]
  const [allSources, setAllSources] = useState([]); // [{id, name, url, ...}]
  const [loading, setLoading] = useState(false);

  const [form, setForm] = useState({ domain: '', kind: '' });
  const [saving, setSaving] = useState(false);
  const [openError, setOpenError] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [mineRes, allRes] = await Promise.all([
        sourcesApi.listMySources(),
        sourcesApi.listAllSources(),
      ]);

      setMine(_ => [...(mineRes || [])]); // под твой формат
      setAllSources(_ => [...(allRes || [])]);
    } finally {
      setLoading(false);
    }
  }, [sourcesApi]);

  useEffect(() => { if (open) refresh().then(r => r); }, [open, refresh]);

  // Реактивные обновления из WS
  useSourceVerifySocket((payload) => {
    // payload: {source_id, status, error?, articles?}
    setMine(prev => prev.map(us => {
      if (us.source_id === payload.source_id) {
        const patch = (payload.status === 'ok')
          ? { status: 'ready', last_error: null }
          : { status: 'error', last_error: payload.error || 'Unknown error' };
        return { ...us, ...patch };
      }
      return us;
    }));
  });

  const notSubscribed = useMemo(() => {
    const mineIds = new Set(mine.map(m => m.source_id));
    return allSources.filter(s => !mineIds.has(s.id));
  }, [mine, allSources]);

  const connectExisting = async (sourceId) => {
    await sourcesApi.addExistingSource(sourceId); // бэк может сам ставить status='verifying' если требует валидации
    await refresh();
  };

  const removeExisting = async (sourceId) => {
    await sourcesApi.removeExistingSource(sourceId); // бэк может сам ставить status='verifying' если требует валидации
    await refresh();
  };

  const createNew = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const res = await sourcesApi.createSource({ domain: form.domain, kind: form.kind });
      if (!res?.id) {
        throw new DOMException("Client Error")
      }
      await refresh();
    } catch (e) {
      setOpenError(true)
      setSaving(false)
      return null
    }
    setSaving(false)
    setTab('mine')
  };

  const updateUserSource = async (userSourceId, patch) => {
    await sourcesApi.updateUserSource(userSourceId, patch); // {cache_ttl_sec, priority}
    await refresh();
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
          <div className="space-y-3">
            {loading && <div>Загрузка…</div>}
            {!loading && mine.length===0 && <div className="text-neutral-500">Пока нет подключенных источников</div>}
            {!loading && mine.map(us => (
              <div key={us.id}
                   className="border rounded-xl p-3 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <StatusBadge status={us?.source.status} error={us.last_error} />
                  </div>
                  <div className="mt-1 text-xs text-neutral-600 flex items-center gap-3">
                    <span className="inline-flex items-center gap-1">
                      <span className="opacity-70">Домен:</span> <span className="font-medium">{us?.source.domain || '—'}</span>
                    </span>
                    <span className="inline-flex items-center gap-1">
                      <span className="opacity-70">Тип:</span> <span className="font-medium">{us?.source.kind}</span>
                    </span>
                  </div>
                  {us.last_error && us?.source.status === 'error' && (
                    <div className="mt-1 text-xs text-red-600">Причина: {us.last_error}</div>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  <label className="text-sm">TTL (сек):</label>
                  <input
                    type="number"
                    className="input w-28"
                    defaultValue={us.poll_interval_sec}
                    onBlur={(e)=>updateUserSource(us.id, { poll_interval_sec: Number(e.target.value||0) })}
                  />
                  <label className="text-sm">Приоритет:</label>
                  <input
                    type="number"
                    className="input w-20"
                    defaultValue={us.rank}
                    onBlur={(e)=>updateUserSource(us.id, { rank: Number(e.target.value||0) })}
                  />
                </div>
              </div>
              )
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
                После отправки источник пройдёт автоматическую проверку качества. Статус обновится здесь в реальном
                времени.
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
