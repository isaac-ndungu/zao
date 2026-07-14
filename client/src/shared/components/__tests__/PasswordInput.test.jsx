import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import PasswordInput from '../PasswordInput'

describe('PasswordInput', () => {
  it('renders with label', () => {
    render(<PasswordInput id="pw" label="Password" value="" onChange={() => {}} />)
    expect(screen.getByLabelText('Password')).toBeInTheDocument()
  })

  it('defaults to password type (hidden)', () => {
    render(<PasswordInput id="pw" label="Password" value="" onChange={() => {}} />)
    expect(screen.getByLabelText('Password')).toHaveAttribute('type', 'password')
  })

  it('toggles visibility on button click', () => {
    render(<PasswordInput id="pw" label="Password" value="" onChange={() => {}} />)
    const input = screen.getByLabelText('Password')
    const toggle = screen.getByRole('button', { name: /show password/i })

    fireEvent.click(toggle)
    expect(input).toHaveAttribute('type', 'text')
    expect(screen.getByRole('button', { name: /hide password/i })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /hide password/i }))
    expect(input).toHaveAttribute('type', 'password')
  })

  it('calls onChange when typing', () => {
    const onChange = vi.fn()
    render(<PasswordInput id="pw" label="Password" value="" onChange={onChange} />)
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'secret' } })
    expect(onChange).toHaveBeenCalled()
  })

  it('displays error message when provided', () => {
    render(<PasswordInput id="pw" label="Password" value="" onChange={() => {}} error="Too short" />)
    expect(screen.getByText('Too short')).toBeInTheDocument()
  })

  it('applies autoComplete attribute', () => {
    render(<PasswordInput id="pw" label="Password" value="" onChange={() => {}} autoComplete="current-password" />)
    expect(screen.getByLabelText('Password')).toHaveAttribute('autocomplete', 'current-password')
  })
})
