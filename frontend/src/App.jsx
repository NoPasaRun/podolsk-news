import React, { useEffect, useState, useCallback } from 'react'
import NewsList from './components/news/NewsList'
import NewsFilters from './components/news/NewsFilters'
import AuthPopup from './hooks/auth/AuthPopup'
import ThemeToggle from './components/widgets/ThemeToggle'
import {useAuth} from "./hooks/auth/AuthProvider";
import './index.css'
import SourceModal from "./components/widgets/SourceModal";
import Alert from "./components/widgets/Alert";
import { useFilters } from "./hooks/news/useFilters";
import { TelemetryProvider } from "./telemetry/TelemetryProvider";
import DotBouncer from "@/components/widgets/DotBouncer.jsx";

export default function App() {
  const [news, setNews] = useState([])
  const [loading, setLoading] = useState(true)
  const [isErrorOpen, setErrorOpen] = useState(false)
  const [source, setSource] = useState(false)

  const [theme, setTheme] = useState('light')
  const [isBottom, setIsBottom] = useState(false)
  const [cursor, setCursor] = useState(null)

  // наш фильтр-хук
  const { api, openLogin, closeLogin, showLogin, isAuthed, logout, onUnauthorized  } = useAuth();
  const { filters, state: filterState, set: filterSet, reset: resetFilters } = useFilters();

  // helper: собрать URL для fetch
  const buildUrl = useCallback((base, filtersStr, extraParamsObj) => {
    const url = new URL(base + (filtersStr || ""), window.location.origin);
    if (extraParamsObj) {
      Object.entries(extraParamsObj).forEach(([k, v]) => {
        if (v !== null && v !== undefined && v !== "") url.searchParams.set(k, v);
      });
    }
    // Вернём только path+search (без хоста), т.к. api.get ждёт относительный путь
    return url.pathname + "?" + url.searchParams.toString();
  }, []);

  // первичная загрузка + реакция на смену фильтров
  useEffect(() => {
    setLoading(true);
    setErrorOpen(false);
    setNews([]);
    setCursor(null);
    const url = buildUrl("/news/all", filters);
    api.get(url)
      .then(r => r.json().then(data => {
        setNews(data?.items || []);
        setCursor(data?.next_cursor || null);
      }))
      .catch(() => setErrorOpen(true))
      .finally(() => setLoading(false));
  }, [api, filters, buildUrl]);

  // тема (persist)
  useEffect(() => {
    const saved = localStorage.getItem('theme') || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
    setTheme(saved)
    document.documentElement.classList.toggle('dark', saved === 'dark')
  }, [])

  const handleScroll = () => {
    const { scrollTop, clientHeight, scrollHeight } = document.documentElement;
    if (scrollTop + clientHeight >= scrollHeight) {
      setIsBottom(true);
    } else {
      setIsBottom(false);
    }
  };

  // бесконечная прокрутка (берёт те же фильтры + cursor)
  useEffect(() => {
    if (!isBottom) return;
    if (!cursor) return;

    setIsBottom(false)
    setLoading(true);
    const url = buildUrl("/news/all", filters, { cursor });
    api.get(url)
      .then(r => r.json().then(data => {
        setNews((prev) => [...prev, ...(data?.items || [])]);
        setCursor(data?.next_cursor || null);
        setLoading(false);
      }))
      .catch(() => setErrorOpen(true));
  }, [isBottom, cursor, api, filters, buildUrl]);

  useEffect(() => {
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
      <TelemetryProvider
        endpoint="/api/telemetry/events"
        getAuthHeaders={async () => {
          const token = localStorage.getItem("auth_token");
          return token ? { Authorization: `Bearer ${token}` } : {};
        }}
      >
        <div className="min-h-screen bg-gray-100 dark:bg-gray-900 text-gray-900 dark:text-gray-100">
          <header className="flex justify-between items-center px-6 py-4 shadow bg-white dark:bg-gray-800 flex-wrap">
            <h1 className="text-2xl font-bold">📰 Новости</h1>
            <div className="flex items-center gap-3">
              <ThemeToggle theme={theme} setTheme={setTheme}/>
              {
                !isAuthed ? (
                    <button className="btn-secondary" onClick={openLogin}>Войти</button>
                ) : <button className="btn-secondary" onClick={logout}>Выйти</button>
              }
              <button className="btn-primary" onClick={isAuthed ? () => setSource(true) : onUnauthorized}>Источники</button>
            </div>
          </header>

          <main className="max-w-6xl mx-auto px-4 py-6">
            {/* Фильтры теперь работают через наш хук */}
            <NewsFilters
              api={api}
              state={filterState}
              set={filterSet}
              onReset={resetFilters}
            />

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

            {!isErrorOpen && <NewsList items={news} />}
            {loading && <DotBouncer />}
          </main>

          <SourceModal open={source} onClose={()=>setSource(false)} />
          {showLogin && <AuthPopup onClose={closeLogin} />}

          <Alert
            open={isErrorOpen}
            onClose={() => {setErrorOpen(false)}}
            title={"Ошибка загрузки"}
            description={"Войдите в аккаунт по номеру телефона"}
            variant={"destructive"}
          />
        </div>
      </TelemetryProvider>
  )
}
