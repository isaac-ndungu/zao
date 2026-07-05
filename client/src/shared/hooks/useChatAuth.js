import { useState, useEffect } from 'react'
import { getAccessToken } from '../../admin/api/client'
import { getToken as getFarmerToken } from '../../farmer/api/client'

export function useChatAuth() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const checkAuth = () => {
      const adminToken = getAccessToken()
      const farmerToken = getFarmerToken()
      setIsAuthenticated(!!adminToken || !!farmerToken)
      setLoading(false)
    }

    checkAuth()
    window.addEventListener('storage', checkAuth)
    return () => window.removeEventListener('storage', checkAuth)
  }, [])

  return { isAuthenticated, loading }
}

export function getChatToken() {
  return getAccessToken() || getFarmerToken()
}