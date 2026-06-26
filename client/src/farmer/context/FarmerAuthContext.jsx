import { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react'
import { apiFetch, setToken, setUser as storeUser, getToken, getUser as storedUser, setOnSessionExpired } from '../api/client'

const FarmerAuthContext = createContext(null)

export function FarmerAuthProvider({ children }) {
  const [user, setUserState] = useState(storedUser)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = getToken()
    if (token) {
      apiFetch('/api/farmers/me/').then(async (res) => {
        if (res.ok) {
          const data = await res.json()
          setUserState(data)
          storeUser(data)
        } else {
          setToken(null)
          storeUser(null)
          setUserState(null)
        }
      }).catch(() => {}).finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    setOnSessionExpired(() => {
      setUserState(null)
      storeUser(null)
      window.location.href = '/farmer/login?expired=1'
    })
  }, [])

  const farmerLogin = useCallback(async (phoneNumber) => {
    const res = await apiFetch('/api/auth/farmer/request/', {
      method: 'POST',
      body: JSON.stringify({ phone_number: phoneNumber }),
      requireAuth: false,
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) throw { ...data, status: res.status }
    return { loginToken: data.login_token }
  }, [])

  const farmerVerify = useCallback(async (loginToken, otpCode) => {
    const res = await apiFetch('/api/auth/farmer/verify/', {
      method: 'POST',
      body: JSON.stringify({ login_token: loginToken, otp_code: otpCode }),
      requireAuth: false,
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) throw { ...data, status: res.status }
    setToken(data.access)
    storeUser(data.user)
    setUserState(data.user)
    return { success: true, user: data.user }
  }, [])

  const logout = useCallback(async () => {
    try { await apiFetch('/api/auth/logout/', { method: 'POST' }) } catch {}
    setToken(null)
    storeUser(null)
    setUserState(null)
    window.location.href = '/farmer/login'
  }, [])

  const value = useMemo(() => ({
    user,
    loading,
    isAuthenticated: !!user,
    farmerLogin,
    farmerVerify,
    logout,
  }), [user, loading, farmerLogin, farmerVerify, logout])

  return (
    <FarmerAuthContext.Provider value={value}>
      {children}
    </FarmerAuthContext.Provider>
  )
}

export function useFarmerAuth() {
  const ctx = useContext(FarmerAuthContext)
  if (!ctx) throw new Error('useFarmerAuth must be used within FarmerAuthProvider')
  return ctx
}
