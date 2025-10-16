export const TOKEN_KEY = "paytrack_token";
export const USER_KEY = "paytrack_user";

export function saveToken(token) {
  try { localStorage.setItem(TOKEN_KEY, token); } catch {}
  // simple cookie (non-HttpOnly) for demo/client-side usage
  try { document.cookie = `${TOKEN_KEY}=${encodeURIComponent(token)}; path=/; max-age=${60*60*24*7}`; } catch {}
}

export function saveUser(user) {
  try { localStorage.setItem(USER_KEY, JSON.stringify(user)); } catch {}
  try { document.cookie = `${USER_KEY}=${encodeURIComponent(JSON.stringify(user))}; path=/; max-age=${60*60*24*7}`; } catch {}
}

export function getToken() {
  try { const t = localStorage.getItem(TOKEN_KEY); if (t) return t; } catch {}
  try {
    const m = document.cookie.match(new RegExp(`(?:^|; )${TOKEN_KEY}=([^;]*)`));
    return m ? decodeURIComponent(m[1]) : null;
  } catch { return null; }
}

export function getUser() {
  try { const u = localStorage.getItem(USER_KEY); if (u) return JSON.parse(u); } catch {}
  try {
    const m = document.cookie.match(new RegExp(`(?:^|; )${USER_KEY}=([^;]*)`));
    return m ? JSON.parse(decodeURIComponent(m[1])) : null;
  } catch { return null; }
}

export function clearAuth() {
  try { localStorage.removeItem(TOKEN_KEY); localStorage.removeItem(USER_KEY); } catch {}
  try {
    document.cookie = `${TOKEN_KEY}=; Max-Age=0; path=/`;
    document.cookie = `${USER_KEY}=; Max-Age=0; path=/`;
  } catch {}
}


