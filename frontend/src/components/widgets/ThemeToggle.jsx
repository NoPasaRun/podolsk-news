import React from 'react'

export default function ThemeToggle({ theme, setTheme }) {
  return (
    <button
      onClick={() => {
        const newTheme = theme === 'light' ? 'dark' : 'light';
        setTheme(newTheme)
        localStorage.setItem('theme', newTheme)
        document.documentElement.classList.toggle('dark', newTheme === 'dark')
      }}
      className="px-3 py-1 rounded-lg border dark:border-gray-600 dark:bg-gray-700 whitespace-nowrap"
      title="Переключить тему"
    >
      {theme === 'dark' ? '🌙 Тёмная' : '☀️ Светлая'}
    </button>
  )
}