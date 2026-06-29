let onSessionExpired = null

function resolveUrl(url) {
  const base = (import.meta.env.VITE_API_URL || '').replace(/\/+$/, '')
  return url.startsWith('/') ? `${base}${url}` : url
}

function getToken() {
  try { return localStorage.getItem('zao_farmer_token') } catch { return null }
}

function setToken(token) {
  try { if (token) localStorage.setItem('zao_farmer_token', token); else localStorage.removeItem('zao_farmer_token') } catch {/* ignore */}
}

function getUser() {
  try {
    const raw = localStorage.getItem('zao_farmer_user')
    return raw ? JSON.parse(raw) : null
  } catch { return null }
}

function setUser(user) {
  try { if (user) localStorage.setItem('zao_farmer_user', JSON.stringify(user)); else localStorage.removeItem('zao_farmer_user') } catch {}
}

let refreshPromise = null

async function refreshAccessToken() {
  if (refreshPromise) return refreshPromise
  refreshPromise = (async () => {
    try {
      const res = await fetch(resolveUrl('/api/auth/refresh/'), { method: 'POST', credentials: 'include' })
      if (!res.ok) { setToken(null); return null }
      const data = await res.json().catch(() => ({}))
      if (!data.access) return null
      setToken(data.access)
      return data.access
    } finally { refreshPromise = null }
  })()
  return refreshPromise
}

export function setOnSessionExpired(cb) {
  onSessionExpired = cb
}

export async function apiFetch(url, options = {}) {
  const { requireAuth = true, headers = {}, ...rest } = options
  const token = getToken()
  const resolvedUrl = resolveUrl(url)

  const config = {
    headers: { 'Content-Type': 'application/json', ...headers },
    ...rest,
  }

  if (requireAuth && token) {
    config.headers['Authorization'] = `Bearer ${token}`
  }

  let res = await fetch(resolvedUrl, config)

  if (res.status === 401 && requireAuth && token) {
    const newToken = await refreshAccessToken()
    if (newToken) {
      config.headers['Authorization'] = `Bearer ${newToken}`
      res = await fetch(resolvedUrl, config)
    } else {
      setToken(null)
      setUser(null)
      onSessionExpired?.()
    }
  }

  return res
}

export { setToken, setUser, getToken, getUser }
