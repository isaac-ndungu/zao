import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

const { mockChangePassword, mockLogout } = vi.hoisted(() => ({
  mockChangePassword: vi.fn(),
  mockLogout: vi.fn(),
}))

vi.mock('../../hooks/useAuth', () => ({
  useAuth: () => ({
    changePassword: mockChangePassword,
    logout: mockLogout,
  }),
}))

import ForcePasswordChange from '../ForcePasswordChange'

describe('ForcePasswordChange', () => {
  const onComplete = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the password change form', () => {
    render(<ForcePasswordChange onComplete={onComplete} />)
    expect(screen.getByText('Change Your Password')).toBeInTheDocument()
    expect(screen.getByLabelText('Current Password')).toBeInTheDocument()
    expect(screen.getByLabelText('New Password')).toBeInTheDocument()
    expect(screen.getByLabelText('Confirm New Password')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /change password/i })).toBeInTheDocument()
  })

  it('shows warning message', () => {
    render(<ForcePasswordChange onComplete={onComplete} />)
    expect(screen.getByText(/must change your password/i)).toBeInTheDocument()
  })

  it('validates passwords match', async () => {
    render(<ForcePasswordChange onComplete={onComplete} />)
    fireEvent.change(screen.getByLabelText('Current Password'), { target: { value: 'oldpass123' } })
    fireEvent.change(screen.getByLabelText('New Password'), { target: { value: 'newpass123' } })
    fireEvent.change(screen.getByLabelText('Confirm New Password'), { target: { value: 'different123' } })
    fireEvent.click(screen.getByRole('button', { name: /change password/i }))
    expect(screen.getByText('Passwords do not match.')).toBeInTheDocument()
    expect(mockChangePassword).not.toHaveBeenCalled()
  })

  it('validates minimum password length', async () => {
    render(<ForcePasswordChange onComplete={onComplete} />)
    fireEvent.change(screen.getByLabelText('Current Password'), { target: { value: 'oldpass123' } })
    fireEvent.change(screen.getByLabelText('New Password'), { target: { value: 'short' } })
    fireEvent.change(screen.getByLabelText('Confirm New Password'), { target: { value: 'short' } })
    fireEvent.click(screen.getByRole('button', { name: /change password/i }))
    expect(screen.getByText('Password must be at least 8 characters.')).toBeInTheDocument()
    expect(mockChangePassword).not.toHaveBeenCalled()
  })

  it('calls changePassword and onComplete on success', async () => {
    mockChangePassword.mockResolvedValueOnce({ success: true })
    render(<ForcePasswordChange onComplete={onComplete} />)
    fireEvent.change(screen.getByLabelText('Current Password'), { target: { value: 'oldpass123' } })
    fireEvent.change(screen.getByLabelText('New Password'), { target: { value: 'newpass123' } })
    fireEvent.change(screen.getByLabelText('Confirm New Password'), { target: { value: 'newpass123' } })
    fireEvent.click(screen.getByRole('button', { name: /change password/i }))
    await waitFor(() => {
      expect(mockChangePassword).toHaveBeenCalledWith('oldpass123', 'newpass123')
      expect(onComplete).toHaveBeenCalled()
    })
  })

  it('displays server error on failure', async () => {
    mockChangePassword.mockRejectedValueOnce({ detail: 'Current password is incorrect.' })
    render(<ForcePasswordChange onComplete={onComplete} />)
    fireEvent.change(screen.getByLabelText('Current Password'), { target: { value: 'wrong' } })
    fireEvent.change(screen.getByLabelText('New Password'), { target: { value: 'newpass123' } })
    fireEvent.change(screen.getByLabelText('Confirm New Password'), { target: { value: 'newpass123' } })
    fireEvent.click(screen.getByRole('button', { name: /change password/i }))
    await waitFor(() => {
      expect(screen.getByText('Current password is incorrect.')).toBeInTheDocument()
    })
  })

  it('shows loading state while submitting', async () => {
    mockChangePassword.mockImplementation(() => new Promise(() => {}))
    render(<ForcePasswordChange onComplete={onComplete} />)
    fireEvent.change(screen.getByLabelText('Current Password'), { target: { value: 'oldpass123' } })
    fireEvent.change(screen.getByLabelText('New Password'), { target: { value: 'newpass123' } })
    fireEvent.change(screen.getByLabelText('Confirm New Password'), { target: { value: 'newpass123' } })
    fireEvent.click(screen.getByRole('button', { name: /change password/i }))
    await waitFor(() => {
      expect(screen.getByText('Changing...')).toBeInTheDocument()
    })
  })

  it('calls logout when log out button is clicked', () => {
    render(<ForcePasswordChange onComplete={onComplete} />)
    fireEvent.click(screen.getByText('Log out'))
    expect(mockLogout).toHaveBeenCalled()
  })
})
