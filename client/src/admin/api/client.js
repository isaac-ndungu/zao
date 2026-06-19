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
      const res = await fetch('/api/auth/token/refresh/', { method: 'POST' })
      if (!res.ok) {
        accessToken = null
        return null
      }
      const data = await res.json()
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
