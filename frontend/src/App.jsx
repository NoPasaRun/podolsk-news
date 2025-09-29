import React, { useEffect, useState } from 'react'
import NewsList from './components/NewsList'
import NewsFilters from './components/NewsFilters'
import AuthPopup from './auth/AuthPopup'
import ThemeToggle from './components/ThemeToggle'
import {useAuth} from "./auth/AuthProvider.jsx";
import './index.css'
import SourceModal from "./components/SourceModal.jsx";

export default function App() {
  const [news, setNews] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [source, setSource] = useState(false)

  const [search, setSearch] = useState('')
  const [sort, setSort] = useState('newest')

  const { api, openLogin, closeLogin, showLogin, isAuthed, logout  } = useAuth();
  const [theme, setTheme] = useState('light')

  // загрузка новостей
  useEffect(() => {
    api.get("/news/all")
      .then(r => r.json().then(data => setNews(data?.items)) )
      .catch((e) => { setError(e?.message || 'Ошибка'); console.error(e) })
      .finally(() => { setLoading(false) })
  }, [])

  // тема (persist)
  useEffect(() => {
    const saved = localStorage.getItem('theme') || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
    setTheme(saved)
    document.documentElement.classList.toggle('dark', saved === 'dark')
  }, [])

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900 text-gray-900 dark:text-gray-100">
      <header className="flex justify-between items-center px-6 py-4 shadow bg-white dark:bg-gray-800">
        <h1 className="text-2xl font-bold">📰 Новости</h1>
        <div className="flex items-center gap-3">
          <ThemeToggle theme={theme} setTheme={setTheme}/>
          {
            !isAuthed ? (
                <button className="btn-secondary" onClick={openLogin}>Войти</button>
            ) : <button className="btn-secondary" onClick={logout}>Выйти</button>
          }
          <button className="btn-primary" onClick={() => setSource(true)}>Источники</button>
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
        {!loading && !error && <NewsList items={news} />}
      </main>
      <SourceModal open={source} onClose={()=>setSource(false)} />
      {showLogin && <AuthPopup onClose={closeLogin} />}
    </div>
  )
}