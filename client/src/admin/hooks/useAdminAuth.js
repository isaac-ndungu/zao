import { useContext } from 'react'
import { AdminAuthContext } from '../contexts/AdminAuthContext'

// Custom hook to access admin authentication context
export function useAdminAuth() {
  const ctx = useContext(AdminAuthContext)

  if (!ctx) {
    throw new Error('useAdminAuth must be used within AdminAuthProvider')
  }
  return ctx
}
