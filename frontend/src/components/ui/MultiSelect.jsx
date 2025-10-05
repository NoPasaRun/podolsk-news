import { useEffect, useMemo, useRef, useState } from 'react';


export default function MultiSelect({
  options,
  value,
  onChange,
  placeholder = 'Выберите…',
  searchPlaceholder = 'Поиск…',
  emptyText = 'Ничего не найдено',
  className = '',
  disabled = false,
  maxHeight = 260,
  showSelectAll = true,
  maxVisibleChips = 2,
  size = 'md',
}) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState('');
  const rootRef = useRef(null);
  const triggerRef = useRef(null);
  const listRef = useRef(null);
  const [focusIdx, setFocusIdx] = useState(-1);

  const strIds = useMemo(() => (value || []).map(String), [value]);
  const map = useMemo(() => new Map(options.map(o => [String(o.id), o])), [options]);
  const selected = useMemo(() => strIds.map(v => map.get(v)).filter(Boolean), [strIds, map]);

  const filtered = useMemo(() => {
    const s = q.trim().toLowerCase();
    if (!s) return options;
    return options.filter(o => o.label.toLowerCase().includes(s));
  }, [options, q]);

  // click outside
  useEffect(() => {
    const onDoc = (e) => {
      if (!rootRef.current?.contains(e.target)) setOpen(false);
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, []);

  // focus list when opened
  useEffect(() => {
    if (open) setTimeout(() => listRef.current?.focus(), 0);
  }, [open]);

  const toggleId = (id) => {
    if (!onChange) return;
    const sid = String(id);
    const set = new Set(strIds);
    if (set.has(sid)) set.delete(sid); else set.add(sid);
    onChange(Array.from(set));
  };

  const allSelected = !!value?.length && value.length === options.length;
  const selectAll = () => onChange?.(options.map(o => String(o.id)));
  const clearAll  = () => onChange?.([]);

  // keyboard on trigger & list
  const onKeyDown = (e) => {
    if (!open && (e.key === 'ArrowDown' || e.key === 'Enter' || e.key === ' ')) {
      e.preventDefault(); setOpen(true); return;
    }
    if (!open) return;
    if (e.key === 'Escape') { setOpen(false); triggerRef.current?.focus(); }
    if (e.key === 'ArrowDown') { e.preventDefault(); setFocusIdx(i => Math.min(i + 1, filtered.length - 1)); }
    if (e.key === 'ArrowUp')   { e.preventDefault(); setFocusIdx(i => Math.max(i - 1, 0)); }
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      const opt = filtered[focusIdx];
      if (opt) toggleId(opt.id);
    }
  };

  const sizeCls = size === 'sm'
    ? 'min-h-9 px-3 py-1.5 text-sm'
    : 'min-h-10 px-3 py-2';

  return (
    <div ref={rootRef} className={`relative ${className}`}>
      {/* Trigger (div, не button — чтобы крестики не сворачивали меню) */}
      <div
        ref={triggerRef}
        role="button"
        tabIndex={0}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-disabled={disabled}
        onKeyDown={onKeyDown}
        onClick={() => !disabled && setOpen(o => !o)}
        className={[
          'w-full rounded-2xl border bg-white dark:bg-neutral-900',
          'border-neutral-200 dark:border-neutral-700 hover:border-neutral-300',
          'focus:outline-none focus:ring-2 focus:ring-blue-500',
          'flex items-center gap-1.5 flex-wrap cursor-pointer',
          disabled ? 'opacity-60 pointer-events-none' : '',
          sizeCls,
        ].join(' ')}
      >
        {selected.length === 0 && (
          <span className="text-neutral-400">{placeholder}</span>
        )}
        {selected.slice(0, maxVisibleChips).map(s => (
            <span
                key={s.id}
                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs
                       bg-neutral-100/70 dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200"
            >
            {s.label}
              <span
                  role="button"
                  aria-label="Удалить"
                  className="flex items-center justify-center cursor-pointer select-none
                             text-neutral-500 hover:text-neutral-900 dark:hover:text-white
                             hover:bg-neutral-200/70 dark:hover:bg-neutral-700/70
                             rounded-full ml-1 min-w-[18px] min-h-[18px]"
                                  onMouseDown={(e) => e.preventDefault()}
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    toggleId(s.id);
                                  }}>×</span>
          </span>
        ))}
        {selected.length > maxVisibleChips && (
            <span className="px-2 py-0.5 rounded-full text-xs bg-neutral-100/70 dark:bg-neutral-800">
            +{selected.length - maxVisibleChips}
          </span>
        )}
        <span className="ml-auto text-neutral-400">{open ? '▴' : '▾'}</span>
      </div>

      {/* Dropdown */}
      {open && (
          <div
              className="absolute z-50 mt-2 w-full rounded-2xl border bg-white dark:bg-neutral-900
                     border-neutral-200 dark:border-neutral-700 shadow-xl"
          onKeyDown={onKeyDown}
        >
          {/* Controls */}
          <div className="p-2 border-b border-neutral-200 dark:border-neutral-800 flex items-center gap-2">
            <input
              className="input w-full text-sm"
              placeholder={searchPlaceholder}
              value={q}
              onChange={e => { setQ(e.target.value); setFocusIdx(0); }}
            />
            {showSelectAll && (
              <button
                type="button"
                className="px-2 py-1 rounded-xl text-xs bg-neutral-100 dark:bg-neutral-800"
                onClick={allSelected ? clearAll : selectAll}
              >
                {allSelected ? 'Очистить' : 'Все'}
              </button>
            )}
          </div>

          {/* List */}
          <ul
            ref={listRef}
            tabIndex={0}
            role="listbox"
            aria-multiselectable="true"
            className="py-1 overflow-auto"
            style={{ maxHeight }}
          >
            {filtered.length === 0 && (
              <li className="px-3 py-2 text-sm text-neutral-500">{emptyText}</li>
            )}
            {filtered.map((o, idx) => {
              const active = strIds.includes(String(o.id));
              const focused = idx === focusIdx;
              return (
                <li key={o.id}>
                  <button
                    type="button"
                    role="option"
                    aria-selected={active}
                    className={[
                      'w-full px-3 py-2 text-left flex items-center gap-2',
                      focused ? 'bg-neutral-100 dark:bg-neutral-800'
                              : 'hover:bg-neutral-100 dark:hover:bg-neutral-800'
                    ].join(' ')}
                    onMouseEnter={() => setFocusIdx(idx)}
                    onClick={() => toggleId(o.id)}
                  >
                    <span
                      className={[
                        'w-4 h-4 rounded border flex items-center justify-center text-[11px]',
                        active ? 'bg-blue-600 border-blue-600 text-white'
                               : 'border-neutral-300 dark:border-neutral-700'
                      ].join(' ')}
                    >
                      {active ? '✓' : ''}
                    </span>
                    <span className="truncate text-sm">{o.label}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}
