import React from 'react';

export default function NewsFilters({ search, setSearch, sort, setSort }) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center gap-3 mb-6">
      <input
        type="text"
        placeholder="Поиск по заголовку, описанию, автору…"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="input flex-1"
      />
      <div className="flex items-center gap-2">
        <label className="text-sm text-gray-500 dark:text-gray-400">Сортировка:</label>
        <select
          value={sort}
          onChange={(e) => setSort(e.target.value)}
          className="input sm:w-56"
        >
          <option value="newest">Сначала новые</option>
          <option value="oldest">Сначала старые</option>
          <option value="author">По автору (A→Z)</option>
        </select>
      </div>
    </div>
  );
}
