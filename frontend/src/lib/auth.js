const BASE = import.meta?.env?.VITE_API_URL || "http://localhost/api";


function mapTokens(data) {
  const now = Date.now();
  const ttlMs = (data.access_expires_in ?? 0) * 1000;
  return {
    access: data.access,
    refresh: data.refresh,
    accessExpAt: now + ttlMs,
  };
}

export async function requestAuth(phone) {
  const res = await fetch(`${BASE}/auth/request`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ phone }),
    credentials: "include",
  });
  if (!res.ok) {
    const d = await res.json().catch(() => ({}));
    throw new Error(d?.detail || "Не удалось отправить код");
  }
  return true;
}

export async function verifyAuth(phone, code) {
  const res = await fetch(`${BASE}/auth/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ phone, code }),
    credentials: "include",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data?.detail || "Код не подошёл");
  return mapTokens(data); // { access, refresh, accessExpAt }
}

export async function refreshPair(refresh) {
  const res = await fetch(`${BASE}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh }),
    credentials: "include",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data?.detail || "Не удалось обновить сессию");
  return mapTokens(data);
}