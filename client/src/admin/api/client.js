import { createApiClient } from '../../shared/api/client'

const adminClient = createApiClient({ tokenStorage: 'memory', features: ['csv', 'impersonation'] })

export const apiFetch = adminClient.apiFetch
export const getAccessToken = adminClient.getToken
export const setAccessToken = adminClient.setToken
export const clearAccessToken = adminClient.clearToken
export const setOnSessionExpired = adminClient.setOnSessionExpired
export const exportCsv = adminClient.exportCsv
export const getImpersonation = adminClient.getImpersonation
export const clearImpersonation = adminClient.clearImpersonation

export function getChatToken() {
  const adminToken = adminClient.getToken()
  try {
    const farmerToken = localStorage.getItem('zao_farmer_token')
    return adminToken || farmerToken
  } catch {
    return adminToken
  }
}
