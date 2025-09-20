const KEY = "auth.tokens.v1";

export function saveTokens(t) {
  localStorage.setItem(KEY, JSON.stringify(t));
}
export function loadTokens() {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}
export function clearTokens() {
  localStorage.removeItem(KEY);
}