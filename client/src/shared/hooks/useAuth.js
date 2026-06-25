import { useContext } from 'react'
import { AdminAuthContext, getLoginRedirect } from '../../admin/contexts/AdminAuthContext'

export { getLoginRedirect }

export function useAuth() {
  const ctx = useContext(AdminAuthContext)
  if (!ctx) {
    throw new Error('useAuth must be used within an AdminAuthProvider')
  }
  return ctx
}
