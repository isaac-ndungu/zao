import { createContext, useState, useEffect, useCallback } from 'react'
import { apiFetch, setAccessToken, clearAccessToken } from '../api/client'

// eslint-disable-next-line react-refresh/only-export-components
export const AdminAuthContext = createContext(null)

export function AdminAuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    ;(async () => {
      try {
        // Try refreshing token on mount to check if user is already logged in
        const res = await apiFetch('/api/auth/refresh/', {
          method: 'POST',
          requireAuth: false,
          credentials: 'include',
        })

        if (!res.ok) {
          setLoading(false)
          return
        }

        const _data = await res.json().catch(() => ({}))
        const { access } = _data || {}
        if (!access) {
          setLoading(false)
          return
        }
        setAccessToken(access)
        
        // Fetch current user info after refreshing token
        const meRes = await apiFetch('/api/users/me/')

        if (meRes.ok) {
          const me = await meRes.json()
          setUser(me)
        }
      } catch {
        clearAccessToken()
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  const login = useCallback(async (email, password) => {
    const res = await apiFetch('/api/auth/login/', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
      requireAuth: false,
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) {
      throw { ...data, status: res.status }
    }
    if (data.requires_2fa) {
      return { requires_2fa: true, loginToken: data.login_token }
    }
    setAccessToken(data.access)
    setUser(data.user)
    return { success: true, user: data.user }
  }, [])

  const requestOtp = useCallback(async (loginToken) => {
    const res = await apiFetch('/api/auth/request-otp/', {
      method: 'POST',
      body: JSON.stringify({ login_token: loginToken }),
      requireAuth: false,
    })
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw { ...data, status: res.status }
    }
  }, [])

  const verifyOtp = useCallback(async (loginToken, otpCode) => {
    const res = await apiFetch('/api/auth/verify-otp/', {
      method: 'POST',
      body: JSON.stringify({ login_token: loginToken, otp_code: otpCode }),
      requireAuth: false,
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) {
      throw { ...data, status: res.status }
    }
    setAccessToken(data.access)
    setUser(data.user)
    return { success: true }
  }, [])

  const refreshUser = useCallback(async () => {
    try {
      const meRes = await apiFetch('/api/users/me/')
      if (meRes.ok) {
        const me = await meRes.json()
        setUser(me)
      }
    } catch {
      // ignore
    }
  }, [])

  const logout = useCallback(async () => {
    try {
      await apiFetch('/api/auth/logout/', { method: 'POST' })
    } catch {
      // ignore
    }
    clearAccessToken()
    setUser(null)
  }, [])

  const value = {
    user,
    loading,
    isAuthenticated: !!user,
    isAdmin: user?.role === 'admin',
    login,
    requestOtp,
    verifyOtp,
    logout,
    refreshUser,
  }

  return (
    <AdminAuthContext.Provider value={value}>
      {children}
    </AdminAuthContext.Provider>
  )
}
