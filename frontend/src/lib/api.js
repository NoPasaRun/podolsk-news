import { clearTokens, loadTokens, saveTokens } from "./tokenStorage";
import {refreshPair} from "./auth.js";
const BASE = import.meta.env.VITE_API_BASE || "http://localhost/api";


export function createApi(onUnauthorized, baseURL = BASE, doRefreshFn = refreshPair) {
  let tokens = loadTokens();
  let isRefreshing = false;
  let refreshPromise = null;
  const queue = []; // {resolve, reject}

  function setTokens(next) {
    tokens = next;
    if (next) saveTokens(next);
    else clearTokens();
  }

  async function refreshTokens() {
    if (!tokens) throw new Error("No tokens");
    if (isRefreshing && refreshPromise) return refreshPromise;

    isRefreshing = true;
    refreshPromise = (async () => {
      try {
        const next = await doRefreshFn(tokens.refresh);
        setTokens(next);
        queue.forEach(({ resolve }) => resolve());
      } catch (e) {
        setTokens(null);
        queue.forEach(({ reject }) => reject(e));
        onUnauthorized && onUnauthorized();
        throw e;
      } finally {
        queue.length = 0;
        isRefreshing = false;
        refreshPromise = null;
      }
    })();

    return refreshPromise;
  }

  async function authFetch(path, options = {}) {
    const url = path.startsWith("http") ? path : `${baseURL}${path}`;
    const headers = new Headers(options.headers || {});
    if (tokens?.access) headers.set("Authorization", `Bearer ${tokens.access}`);
    const init = { ...options, headers };

    let res = await fetch(url, init);
    if (res.status !== 401) return res;

    if (init._retried) {
      onUnauthorized && onUnauthorized();
      return res;
    }
    init._retried = true;

    const waiter = new Promise((resolve, reject) => queue.push({ resolve, reject }));
    try {
      await refreshTokens();
      await waiter;
      const retryHeaders = new Headers(init.headers || {});
      if (tokens?.access) retryHeaders.set("Authorization", `Bearer ${tokens.access}`);
      const retryInit = { ...init, headers: retryHeaders };
      const retryRes = await fetch(url, retryInit);
      if (retryRes.status === 401) onUnauthorized && onUnauthorized();
      return retryRes;
    } catch {
      onUnauthorized && onUnauthorized();
      return res;
    }
  }

  return {
    get tokens() {
      return tokens;
    },
    set tokens(next) {
      setTokens(next);
    },
    clear() {
      setTokens(null);
    },
    fetch: authFetch,
    get: (p) => authFetch(p, { method: "GET" }),
    del: (p) => authFetch(p, { method: "DELETE" }),
    post: (p, body) =>
      authFetch(p, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: body ? JSON.stringify(body) : undefined,
      }),
    patch: (p, body) =>
      authFetch(p, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: body ? JSON.stringify(body) : undefined,
      }),
  };
}