import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { AdminAuthProvider, AdminAuthContext, getLoginRedirect } from '../AdminAuthContext'
import { useContext } from 'react'

vi.mock('../../api/client', () => ({
  apiFetch: vi.fn(),
  setAccessToken: vi.fn(),
  clearAccessToken: vi.fn(),
  setOnSessionExpired: vi.fn(),
  getImpersonation: vi.fn(() => null),
  clearImpersonation: vi.fn(),
}))

import { apiFetch, setAccessToken, clearAccessToken } from '../../api/client'

function AuthWrapper({ children }) {
  return <AdminAuthProvider>{children}</AdminAuthProvider>
}

function useTestAuth() {
  return useContext(AdminAuthContext)
}

describe('getLoginRedirect', () => {
  it('returns correct paths for each role', () => {
    expect(getLoginRedirect('admin')).toBe('/admin/dashboard')
    expect(getLoginRedirect('superadmin')).toBe('/admin/dashboard')
    expect(getLoginRedirect('manager')).toBe('/manager/dashboard')
    expect(getLoginRedirect('grader')).toBe('/grader/dashboard')
    expect(getLoginRedirect('accountant')).toBe('/accountant/dashboard')
    expect(getLoginRedirect('farmer')).toBe('/farmer/dashboard')
    expect(getLoginRedirect('auditor')).toBe('/auditor/dashboard')
    expect(getLoginRedirect('external_auditor')).toBe('/external-auditor/dashboard')
  })

  it('falls back to /admin/login for unknown roles', () => {
    expect(getLoginRedirect('unknown')).toBe('/admin/login')
    expect(getLoginRedirect(undefined)).toBe('/admin/login')
  })
})

describe('AdminAuthContext login', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('sets access token and returns user on successful login', async () => {
    const mockUser = { role: 'admin', email: 'admin@test.com' }
    apiFetch
      .mockResolvedValueOnce({ ok: false, json: () => Promise.resolve({}) }) // refresh init
      .mockResolvedValueOnce({ ok: false }) // me init fallback
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ access: 'tok123', user: mockUser }) }) // login

    const { result } = renderHook(() => useTestAuth(), { wrapper: AuthWrapper })

    await waitFor(() => expect(result.current.loading).toBe(false))

    await act(async () => {
      const res = await result.current.login('admin@test.com', 'pass123')
      expect(res).toEqual({ success: true, user: mockUser })
      expect(setAccessToken).toHaveBeenCalledWith('tok123')
    })
  })

  it('returns requires_2fa when server responds with 2FA required', async () => {
    apiFetch
      .mockResolvedValueOnce({ ok: false, json: () => Promise.resolve({}) }) // refresh
      .mockResolvedValueOnce({ ok: false }) // me
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ requires_2fa: true, login_token: 'lt_abc' }) }) // login

    const { result } = renderHook(() => useTestAuth(), { wrapper: AuthWrapper })

    await waitFor(() => expect(result.current.loading).toBe(false))

    await act(async () => {
      const res = await result.current.login('user@test.com', 'pass')
      expect(res).toEqual({ requires_2fa: true, loginToken: 'lt_abc' })
    })
  })

  it('throws on failed login', async () => {
    apiFetch
      .mockResolvedValueOnce({ ok: false, json: () => Promise.resolve({}) }) // refresh
      .mockResolvedValueOnce({ ok: false }) // me
      .mockResolvedValueOnce({ ok: false, json: () => Promise.resolve({ detail: 'Invalid credentials' }) }) // login

    const { result } = renderHook(() => useTestAuth(), { wrapper: AuthWrapper })

    await waitFor(() => expect(result.current.loading).toBe(false))

    await act(async () => {
      try {
        await result.current.login('user@test.com', 'wrong')
        expect.fail('should have thrown')
      } catch (e) {
        expect(e.detail).toBe('Invalid credentials')
      }
    })
  })
})

describe('AdminAuthContext 2FA flow', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('verifyOtp sets access token on success', async () => {
    const mockUser = { role: 'admin', email: 'admin@test.com' }
    apiFetch
      .mockResolvedValueOnce({ ok: false, json: () => Promise.resolve({}) }) // refresh
      .mockResolvedValueOnce({ ok: false }) // me
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ access: 'otp_token', user: mockUser }) }) // verifyOtp

    const { result } = renderHook(() => useTestAuth(), { wrapper: AuthWrapper })

    await waitFor(() => expect(result.current.loading).toBe(false))

    await act(async () => {
      const res = await result.current.verifyOtp('lt_abc', '123456')
      expect(res).toEqual({ success: true })
      expect(setAccessToken).toHaveBeenCalledWith('otp_token')
    })
  })

  it('requestOtp succeeds', async () => {
    apiFetch
      .mockResolvedValueOnce({ ok: false, json: () => Promise.resolve({}) }) // refresh
      .mockResolvedValueOnce({ ok: false }) // me
      .mockResolvedValueOnce({ ok: true }) // requestOtp

    const { result } = renderHook(() => useTestAuth(), { wrapper: AuthWrapper })

    await waitFor(() => expect(result.current.loading).toBe(false))

    await act(async () => {
      await expect(result.current.requestOtp('lt_abc')).resolves.toBeUndefined()
    })
  })

  it('requestOtp throws on failure', async () => {
    apiFetch
      .mockResolvedValueOnce({ ok: false, json: () => Promise.resolve({}) }) // refresh
      .mockResolvedValueOnce({ ok: false }) // me
      .mockResolvedValueOnce({ ok: false, json: () => Promise.resolve({ detail: 'OTP send failed' }) }) // requestOtp

    const { result } = renderHook(() => useTestAuth(), { wrapper: AuthWrapper })

    await waitFor(() => expect(result.current.loading).toBe(false))

    await act(async () => {
      try {
        await result.current.requestOtp('lt_abc')
        expect.fail('should have thrown')
      } catch (e) {
        expect(e.detail).toBe('OTP send failed')
      }
    })
  })
})

describe('AdminAuthContext logout', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('calls logout endpoint and clears token', async () => {
    apiFetch
      .mockResolvedValueOnce({ ok: false, json: () => Promise.resolve({}) }) // refresh
      .mockResolvedValueOnce({ ok: false }) // me
      .mockResolvedValueOnce({ ok: true }) // logout

    const { result } = renderHook(() => useTestAuth(), { wrapper: AuthWrapper })

    await waitFor(() => expect(result.current.loading).toBe(false))

    await act(async () => {
      await result.current.logout()
    })

    expect(clearAccessToken).toHaveBeenCalled()
  })
})

describe('AdminAuthContext changePassword', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('returns success on valid password change', async () => {
    apiFetch
      .mockResolvedValueOnce({ ok: false, json: () => Promise.resolve({}) }) // refresh
      .mockResolvedValueOnce({ ok: false }) // me
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ access: 'new_token', user: { role: 'admin' } }) }) // changePassword

    const { result } = renderHook(() => useTestAuth(), { wrapper: AuthWrapper })

    await waitFor(() => expect(result.current.loading).toBe(false))

    await act(async () => {
      const res = await result.current.changePassword('old', 'newpass123')
      expect(res).toEqual({ success: true })
    })
  })

  it('throws on invalid current password', async () => {
    apiFetch
      .mockResolvedValueOnce({ ok: false, json: () => Promise.resolve({}) }) // refresh
      .mockResolvedValueOnce({ ok: false }) // me
      .mockResolvedValueOnce({ ok: false, json: () => Promise.resolve({ detail: 'Current password is incorrect.' }) }) // changePassword

    const { result } = renderHook(() => useTestAuth(), { wrapper: AuthWrapper })

    await waitFor(() => expect(result.current.loading).toBe(false))

    await act(async () => {
      try {
        await result.current.changePassword('wrong', 'newpass123')
        expect.fail('should have thrown')
      } catch (e) {
        expect(e.detail).toBe('Current password is incorrect.')
      }
    })
  })
})
