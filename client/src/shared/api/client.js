const FARMER_TOKEN_KEY = 'zao_farmer_token'
const FARMER_USER_KEY = 'zao_farmer_user'

function resolveUrl(url) {
  const base = (import.meta.env.VITE_API_URL || '').replace(/\/+$/, '')
  return url.startsWith('/') ? `${base}${url}` : url
}

export function createApiClient({ tokenStorage = 'memory', features = [] } = {}) {
  let accessToken = null
  let refreshPromise = null
  let onSessionExpired = null

  function getToken() {
    if (tokenStorage === 'localStorage') {
      try { return localStorage.getItem(FARMER_TOKEN_KEY) } catch { return null }
    }
    return accessToken
  }

  function getAnyToken() {
    if (tokenStorage === 'localStorage') {
      try { return localStorage.getItem(FARMER_TOKEN_KEY) } catch { return null }
    }
    return accessToken
  }

  function setToken(token) {
    if (tokenStorage === 'localStorage') {
      try {
        if (token) localStorage.setItem(FARMER_TOKEN_KEY, token)
        else localStorage.removeItem(FARMER_TOKEN_KEY)
      } catch {}
    } else {
      accessToken = token
    }
  }

  function clearToken() {
    if (tokenStorage === 'localStorage') {
      try {
        localStorage.removeItem(FARMER_TOKEN_KEY)
        localStorage.removeItem(FARMER_USER_KEY)
      } catch {}
    } else {
      accessToken = null
    }
  }

  async function refreshAccessToken() {
    if (refreshPromise) return refreshPromise

    refreshPromise = (async () => {
      try {
        const res = await fetch(resolveUrl('/api/auth/refresh/'), { method: 'POST', credentials: 'include' })
        if (!res.ok) {
          clearToken()
          return null
        }
        const data = await res.json().catch(() => ({}))
        if (!data.access) {
          clearToken()
          return null
        }
        setToken(data.access)
        return data.access
      } finally {
        refreshPromise = null
      }
    })()

    return refreshPromise
  }

  async function apiFetch(url, options = {}) {
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
        onSessionExpired?.()
      }
    }

    return res
  }

  const client = {
    apiFetch,
    setOnSessionExpired: (cb) => { onSessionExpired = cb },
    getToken,
    setToken,
    clearToken,
  }

  if (features.includes('csv')) {
    client.exportCsv = async (url) => {
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
  }

  if (features.includes('impersonation')) {
    client.getImpersonation = () => {
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
    client.clearImpersonation = () => sessionStorage.removeItem('impersonation')
  }

  return client
}
