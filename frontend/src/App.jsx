import React, { useEffect, useState, useMemo } from 'react'
import { fetchNews } from './api'
import NewsList from './components/NewsList'
import NewsFilters from './components/NewsFilters'
import AuthPopup from './components/AuthPopup'
import ThemeToggle from './components/ThemeToggle'

export default function App() {
  const [news, setNews] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const [search, setSearch] = useState('')
  const [sort, setSort] = useState('newest')
  const [showAuth, setShowAuth] = useState(true)
  const [theme, setTheme] = useState('light')

  // загрузка новостей
  useEffect(() => {
    let alive = true
    fetchNews()
      .then((data) => { if (alive) setNews(Array.isArray(data) ? data : (data.items || [])) })
      .catch((e) => { if (alive) setError(e?.message || 'Ошибка'); console.error(e) })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [])

  // тема (persist)
  useEffect(() => {
    const saved = localStorage.getItem('theme') || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
    setTheme(saved)
    document.documentElement.classList.toggle('dark', saved === 'dark')
  }, [])

  useEffect(() => {
    localStorage.setItem('theme', theme)
    document.documentElement.classList.toggle('dark', theme === 'dark')
  }, [theme])

  const filtered = useMemo(() => {
    const bySearch = (n) => {
      const q = search.trim().toLowerCase()
      if (!q) return true
      return (
        n.title?.toLowerCase().includes(q) ||
        n.description?.toLowerCase().includes(q) ||
        n.author?.toLowerCase().includes(q)
      )
    }
    const arr = (news || []).filter(bySearch)
    if (sort === 'newest') arr.sort((a,b) => new Date(b.created_at) - new Date(a.created_at))
    if (sort === 'oldest') arr.sort((a,b) => new Date(a.created_at) - new Date(b.created_at))
    if (sort === 'author') arr.sort((a,b) => (a.author || '').localeCompare(b.author || ''))
    return arr
  }, [news, search, sort])

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900 text-gray-900 dark:text-gray-100">
      <header className="flex justify-between items-center px-6 py-4 shadow bg-white dark:bg-gray-800">
        <h1 className="text-2xl font-bold">📰 Новости</h1>
        <div className="flex items-center gap-3">
          <ThemeToggle theme={theme} setTheme={setTheme} />
          <button className="btn-secondary" onClick={() => setShowAuth(true)}>Войти</button>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-6">
        <NewsFilters search={search} setSearch={setSearch} sort={sort} setSort={setSort} />

        {loading && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="card animate-pulse h-32">
                <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mb-3" />
                <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-full mb-2" />
                <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-5/6" />
                <div className="mt-4 h-3 bg-gray-200 dark:bg-gray-700 rounded w-1/2" />
              </div>
            ))}
          </div>
        )}
        {error && <div className="text-center text-red-500 mb-4">Ошибка: {error}</div>}
        {!loading && !error && <NewsList news={filtered} />}
      </main>

      {showAuth && <AuthPopup onClose={() => setShowAuth(false)} />}
    </div>
  )
}