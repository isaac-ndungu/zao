import { createApiClient } from '../../shared/api/client'

const farmerClient = createApiClient({ tokenStorage: 'localStorage', features: [] })

export const apiFetch = farmerClient.apiFetch
export const setOnSessionExpired = farmerClient.setOnSessionExpired
export const setToken = farmerClient.setToken
export const setUser = (user) => {
  try { if (user) localStorage.setItem('zao_farmer_user', JSON.stringify(user)); else localStorage.removeItem('zao_farmer_user') } catch {}
}
export const getToken = farmerClient.getToken
export const getUser = () => {
  try {
    const raw = localStorage.getItem('zao_farmer_user')
    return raw ? JSON.parse(raw) : null
  } catch { return null }
}
