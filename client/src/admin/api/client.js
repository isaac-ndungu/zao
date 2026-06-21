let accessToken = null
let refreshPromise = null

export function getAccessToken() {
  return accessToken
}

export function setAccessToken(token) {
  accessToken = token
}

export function clearAccessToken() {
  accessToken = null
}

async function refreshAccessToken() {
  if (refreshPromise) return refreshPromise

  refreshPromise = (async () => {
    // Attempt to refresh the access token
    try {
      const res = await fetch('/api/auth/refresh/', { method: 'POST', credentials: 'include' })
      if (!res.ok) {
        accessToken = null
        return null
      }
      const data = await res.json().catch(() => ({}))
      if (!data.access) return null
      accessToken = data.access
      return data.access
    } finally {
      refreshPromise = null
    }
  })()

  return refreshPromise
}

// Wrapper around fetch to automatically include access token and handle refresh
export async function apiFetch(url, options = {}) {
  const { requireAuth = true, headers = {}, ...rest } = options

// Build headers, including Authorization if required and access token is available
  const config = {
    headers: { 'Content-Type': 'application/json', ...headers },
    ...rest,
  }

  if (requireAuth && accessToken) {
    config.headers['Authorization'] = `Bearer ${accessToken}`
  }

  let res = await fetch(url, config)

  if (res.status === 401 && requireAuth && accessToken) {
    const newToken = await refreshAccessToken()
    
    if (newToken) {
      config.headers['Authorization'] = `Bearer ${newToken}`
      res = await fetch(url, config)
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
