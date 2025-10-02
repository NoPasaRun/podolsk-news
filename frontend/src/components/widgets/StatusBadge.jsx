export default function StatusBadge({ status, error }) {
  const s = String(status || '').toLowerCase();
  if (s === 'validating') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-orange-100 text-orange-800 text-xs">
        <svg className="w-3.5 h-3.5 animate-spin" viewBox="0 0 24 24" fill="none">
          <path d="M12 3a9 9 0 1 1-6.364 2.636" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
        </svg>
        Проверка
      </span>
    );
  }
  if (s === 'error') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-red-100 text-red-800 text-xs" title={error || ''}>
        <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none">
          <path d="M12 9v4m0 4h.01M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
        Ошибка
      </span>
    );
  }
  // ready / verified / default -> зелёный
  return (
    <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-green-100 text-green-800 text-xs">
      <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none">
        <path d="M20 6 9 17l-5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
      Подтверждён
    </span>
  );
}
