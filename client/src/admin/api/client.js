let accessToken = null
let refreshPromise = null
let onSessionExpired = null

function resolveUrl(url) {
  const base = (import.meta.env.VITE_API_URL || '').replace(/\/+$/, '')
  return url.startsWith('/') ? `${base}${url}` : url
}

export function getAccessToken() {
  return accessToken
}

export function setAccessToken(token) {
  accessToken = token
}

export function clearAccessToken() {
  accessToken = null
}

/**
 * Register a callback invoked when session refresh fails permanently.
 * Typically used by AuthContext to redirect to login.
 */
export function setOnSessionExpired(cb) {
  onSessionExpired = cb
}

async function refreshAccessToken() {
  if (refreshPromise) return refreshPromise

  refreshPromise = (async () => {
    try {
      const res = await fetch(resolveUrl('/api/auth/refresh/'), { method: 'POST', credentials: 'include' })
      if (!res.ok) {
        accessToken = null
        setStoredToken(null)
        return null
      }
      const data = await res.json().catch(() => ({}))
      if (!data.access) return null
      accessToken = data.access
      setStoredToken(data.access)
      return data.access
    } finally {
      refreshPromise = null
    }
  })()

  return refreshPromise
}

export async function apiFetch(url, options = {}) {
  const { requireAuth = true, headers = {}, credentials, ...rest } = options
  const resolvedUrl = resolveUrl(url)
  const token = getAccessToken()

  const config = {
    headers: { 'Content-Type': 'application/json', ...headers },
    credentials: credentials || (requireAuth ? 'include' : undefined),
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
      onSessionExpired?.()
    }
  }

  return res
}

export async function exportCsv(url) {
  const res = await apiFetch(url)
  if (!res.ok) throw new Error(`Export failed: ${res.status}`)
  const disposition = res.headers.get('Content-Disposition') || ''
  const match = disposition.match(/filename="?(.+?)"?$/)
  const filename = match ? match[1] : 'export.csv'
  const blob = await res.blob()
  const blobUrl = URL.createObjectURL(blob)
  const a = document.createElement('a')

  a.href = blobUrl
  a.download = filename
  document.body.appendChild(a)
  
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(blobUrl)
}

export function getImpersonation() {
  try {
    const raw = sessionStorage.getItem('impersonation')
    if (!raw) return null
    const data = JSON.parse(raw)
    if (Date.now() >= data.expires_at) {
      sessionStorage.removeItem('impersonation')
      return null
    }
    return data
  } catch {
    sessionStorage.removeItem('impersonation')
    return null
  }
}

export function clearImpersonation() {
  sessionStorage.removeItem('impersonation')
}
