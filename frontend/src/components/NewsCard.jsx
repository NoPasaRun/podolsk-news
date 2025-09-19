import React from 'react';

export default function NewsCard({ item }) {
  const date = item.created_at ? new Date(item.created_at).toLocaleString() : '';
  return (
    <article className="group card hover:shadow-lg transition-shadow h-full flex flex-col">
      <header className="mb-2">
        <h3 className="text-lg font-semibold line-clamp-2 group-hover:underline">
          {item.link ? (
            <a href={item.link} target="_blank" rel="noreferrer" className="text-blue-600 dark:text-blue-400">
              {item.title}
            </a>
          ) : item.title}
        </h3>
      </header>

      <p className="text-sm text-gray-700 dark:text-gray-300 line-clamp-3 flex-1">
        {item.description}
      </p>

      <footer className="mt-3 flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
        <span className="truncate">✍ {item.author || 'Неизвестный автор'}</span>
        <time className="whitespace-nowrap">{date}</time>
      </footer>
    </article>
  );
}
