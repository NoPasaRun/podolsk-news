export async function fetchNews() {
  const res = await fetch("/api/news/list");
  if (!res.ok) throw new Error("Ошибка загрузки новостей");
  return res.json();
}

export async function requestAuth(phone) {
  return fetch("/api/auth/request", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ phone }),
  });
}

export async function verifyAuth(phone, code) {
  return fetch("/api/auth/verify", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ phone, code }),
  });
}