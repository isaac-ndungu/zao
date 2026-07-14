import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import RoleGuard from '../RoleGuard'

vi.mock('../../hooks/useAuth', () => ({
  useAuth: vi.fn(),
}))

import { useAuth } from '../../hooks/useAuth'

function renderWithRouter(ui, { route = '/' } = {}) {
  return render(
    <MemoryRouter initialEntries={[route]}>
      {ui}
    </MemoryRouter>
  )
}

describe('RoleGuard', () => {
  it('renders loading spinner while auth is loading', () => {
    useAuth.mockReturnValue({ loading: true, isAuthenticated: false, role: null })
    renderWithRouter(<RoleGuard roles={['admin']}>Content</RoleGuard>)
    expect(document.querySelector('.animate-spin')).toBeInTheDocument()
  })

  it('redirects to login when not authenticated', () => {
    useAuth.mockReturnValue({ loading: false, isAuthenticated: false, role: null })
    const { container } = renderWithRouter(<RoleGuard roles={['admin']}>Content</RoleGuard>)
    expect(screen.queryByText('Content')).not.toBeInTheDocument()
    expect(container.querySelector('[data-testid]') || screen.queryByText('Content')).not.toBeInTheDocument()
  })

  it('renders children when authenticated with correct role', () => {
    useAuth.mockReturnValue({ loading: false, isAuthenticated: true, role: 'admin' })
    renderWithRouter(<RoleGuard roles={['admin']}>Dashboard</RoleGuard>)
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
  })

  it('redirects to root when role is not in allowed list', () => {
    useAuth.mockReturnValue({ loading: false, isAuthenticated: true, role: 'farmer' })
    renderWithRouter(<RoleGuard roles={['admin', 'manager']}>Admin Only</RoleGuard>)
    expect(screen.queryByText('Admin Only')).not.toBeInTheDocument()
  })

  it('renders children when no roles prop is specified', () => {
    useAuth.mockReturnValue({ loading: false, isAuthenticated: true, role: 'any' })
    renderWithRouter(<RoleGuard>Open Content</RoleGuard>)
    expect(screen.getByText('Open Content')).toBeInTheDocument()
  })

  it('allows access when user role is in the roles array', () => {
    useAuth.mockReturnValue({ loading: false, isAuthenticated: true, role: 'manager' })
    renderWithRouter(<RoleGuard roles={['admin', 'manager', 'grader']}>Manager View</RoleGuard>)
    expect(screen.getByText('Manager View')).toBeInTheDocument()
  })
})
