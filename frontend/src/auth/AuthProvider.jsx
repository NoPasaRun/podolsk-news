import React, { createContext, useContext, useEffect, useMemo, useRef, useState } from "react";
import { createApi } from "../lib/api";
import { loadTokens, saveTokens, clearTokens } from "../lib/tokenStorage";
import SessionExpiredModal from "./SessionExpiredModal";
import {refreshPair} from "../lib/auth.js";

const AuthCtx = createContext(null);

// за сколько миллисекунд до истечения access делаем проактивный рефреш:
const REFRESH_EARLY_MS = 1_000;

export function AuthProvider({ children }) {
  const [tokens, setTokens] = useState(() => loadTokens());
  const [expiredOpen, setExpiredOpen] = useState(false);
  const timerRef = useRef(null);

  const [showLogin, setShowLogin] = useState(false);

  const openLogin = () => setShowLogin(true);
  const closeLogin = () => setShowLogin(false);
  const onUnauthorized = () => setExpiredOpen(true);

  const api = useMemo(() => createApi(onUnauthorized), []);

  // применяем токены в клиент
  useEffect(() => { api.tokens = tokens; }, [api, tokens]);

  // синхрон вкладок
  useEffect(() => {
    const onStorage = (e) => {
      if (e.key === "auth.tokens.v1") {
        const next = loadTokens();
        setTokens(next);
        api.tokens = next;
      }
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, [api]);

  // планирование проактивного рефреша
  function scheduleProactiveRefresh(toks) {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    if (!toks?.accessExpAt) return;
    const delay = Math.max(0, toks.accessExpAt - Date.now() - REFRESH_EARLY_MS);
    timerRef.current = setTimeout(async () => {
      try {
        // тихий проактивный refresh
        const next = await refreshPair(toks.refresh);
        login(next)           // обновить клиент
        scheduleProactiveRefresh(next); // перепланировать
      } catch {
        // не удалось — откроем модалку; последующие запросы словят 401
        setExpiredOpen(true);
      }
    }, delay);
  }

  useEffect(() => {
    scheduleProactiveRefresh(tokens);
    return () => timerRef.current && clearTimeout(timerRef.current);
  }, [tokens]);

  const login = (t) => {
    setTokens(t);
    saveTokens(t);
    api.tokens = t;
    setExpiredOpen(false);
  };

  const logout = () => {
    setTokens(null);
    clearTokens();
    api.clear();
    setExpiredOpen(false);
  };

  const value = { api, showLogin, openLogin, closeLogin, isAuthed: !!tokens, login, logout };

  return (
    <AuthCtx.Provider value={value}>
      {children}
      <SessionExpiredModal
        open={expiredOpen}
        onRelogin={() => {
          openLogin()
          logout()
        }}
        onClose={() => setExpiredOpen(false)}
      />
    </AuthCtx.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthCtx);
  if (!ctx) throw new Error("useAuth must be used within <AuthProvider>");
  return ctx;
}
