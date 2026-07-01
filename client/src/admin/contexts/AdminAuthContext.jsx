import { createContext, useState, useEffect, useCallback, useMemo } from 'react'
import {
  apiFetch,
  setAccessToken,
  clearAccessToken,
  setOnSessionExpired,
  getImpersonation,
  clearImpersonation,
} from '../api/client'

// eslint-disable-next-line react-refresh/only-export-components
export const AdminAuthContext = createContext(null)

const ROLE_BASED_REDIRECT = {
  admin: '/admin/dashboard',
  superadmin: '/admin/dashboard',
  manager: '/manager/dashboard',
  grader: '/grader/dashboard',
  accountant: '/accountant/dashboard',
  farmer: '/farmer/dashboard',
  auditor: '/auditor/dashboard',
  external_auditor: '/external-auditor/dashboard',
}

// eslint-disable-next-line react-refresh/only-export-components
export function getLoginRedirect(role) {
  return ROLE_BASED_REDIRECT[role] || '/admin/login'
}

export function AdminAuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  const handleSessionExpired = useCallback(() => {
    setUser(null)
    clearAccessToken()
    window.location.href = '/admin/login?expired=1'
  }, [])

  useEffect(() => {
    setOnSessionExpired(handleSessionExpired)
  }, [handleSessionExpired])

  useEffect(() => {
    ;(async () => {
      try {
        const imp = getImpersonation()
        if (imp) {
          setAccessToken(imp.access_token)
          const meRes = await apiFetch('/api/users/me/')
          if (meRes.ok) {
            const me = await meRes.json()
            me.is_impersonated = true
            setUser(me)
            setLoading(false)
            return
          }
          clearImpersonation()
        }

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
    const res = await apiFetch('/api/auth/2fa/request/', {
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
    const res = await apiFetch('/api/auth/2fa/verify/', {
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

  const farmerLogin = useCallback(async (phoneNumber) => {
    const res = await apiFetch('/api/auth/farmer/request/', {
      method: 'POST',
      body: JSON.stringify({ phone_number: phoneNumber }),
      requireAuth: false,
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) {
      throw { ...data, status: res.status }
    }
    return { loginToken: data.login_token }
  }, [])

  const farmerVerify = useCallback(async (loginToken, otpCode) => {
    const res = await apiFetch('/api/auth/farmer/verify/', {
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
    return { success: true, user: data.user }
  }, [])

  const googleLogin = useCallback(async (credential) => {
    const res = await apiFetch('/api/auth/google/', {
      method: 'POST',
      body: JSON.stringify({ credential }),
      requireAuth: false,
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) {
      throw { ...data, status: res.status }
    }
    setAccessToken(data.access)
    setUser(data.user)
    return { success: true, user: data.user }
  }, [])

  const changePassword = useCallback(async (currentPassword, newPassword) => {
    const res = await apiFetch('/api/auth/change-password/', {
      method: 'POST',
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
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
    clearImpersonation()
    try {
      await apiFetch('/api/auth/logout/', { method: 'POST' })
    } catch {
      // ignore
    }
    clearAccessToken()
    setUser(null)
  }, [])

  const stopImpersonation = useCallback(() => {
    clearImpersonation()
    clearAccessToken()
    window.location.href = '/'
  }, [])

  const role = user?.role
  const loginRedirect = getLoginRedirect(role)

  const value = useMemo(() => ({
    user,
    loading,
    role,
    loginRedirect,
    isAuthenticated: !!user,
    isImpersonated: user?.is_impersonated || false,
    isAdmin: role === 'admin' || role === 'superadmin',
    isManager: role === 'manager',
    isGrader: role === 'grader',
    isAccountant: role === 'accountant',
    isFarmer: role === 'farmer',
    isAuditor: role === 'auditor',
    isExternalAuditor: role === 'external_auditor',
    cooperativeId: user?.cooperative_id || null,
    login,
    requestOtp,
    verifyOtp,
    farmerLogin,
    farmerVerify,
    googleLogin,
    changePassword,
    logout,
    refreshUser,
    stopImpersonation,
  }), [user, role, loginRedirect, loading, login, requestOtp, verifyOtp, farmerLogin, farmerVerify, googleLogin, changePassword, logout, refreshUser, stopImpersonation])

  return (
    <AdminAuthContext.Provider value={value}>
      {children}
    </AdminAuthContext.Provider>
  )
}
