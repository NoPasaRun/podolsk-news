import React from 'react';
import NewsCard from './NewsCard';

export default function NewsList({ news }) {
  if (!news || news.length === 0) {
    return <div className="text-center text-gray-500">Новостей пока нет</div>;
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
      {news.map((n, idx) => (
        <NewsCard key={idx} item={n} />
      ))}
    </div>
  );
}
