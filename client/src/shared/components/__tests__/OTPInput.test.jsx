import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import OTPInput from '../OTPInput'

describe('OTPInput', () => {
  it('renders an input field', () => {
    render(<OTPInput value="" onChange={() => {}} />)
    expect(screen.getByRole('textbox')).toBeInTheDocument()
  })

  it('calls onChange with cleaned digits', () => {
    const onChange = vi.fn()
    render(<OTPInput value="" onChange={onChange} />)
    fireEvent.change(screen.getByRole('textbox'), { target: { value: '123456' } })
    expect(onChange).toHaveBeenCalledWith('123456')
  })

  it('strips non-digit characters', () => {
    const onChange = vi.fn()
    render(<OTPInput value="" onChange={onChange} />)
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'abc123' } })
    expect(onChange).toHaveBeenCalledWith('123')
  })

  it('trims to max length (6)', () => {
    const onChange = vi.fn()
    render(<OTPInput value="" onChange={onChange} />)
    fireEvent.change(screen.getByRole('textbox'), { target: { value: '1234567890' } })
    expect(onChange).toHaveBeenCalledWith('123456')
  })

  it('calls onSubmit when value reaches full length', () => {
    const onChange = vi.fn()
    const onSubmit = vi.fn()
    render(<OTPInput value="12345" onChange={onChange} onSubmit={onSubmit} />)
    fireEvent.change(screen.getByRole('textbox'), { target: { value: '123456' } })
    expect(onSubmit).toHaveBeenCalled()
  })

  it('does not call onSubmit when below full length', () => {
    const onChange = vi.fn()
    const onSubmit = vi.fn()
    render(<OTPInput value="123" onChange={onChange} onSubmit={onSubmit} />)
    fireEvent.change(screen.getByRole('textbox'), { target: { value: '1234' } })
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('calls onSubmit on Enter key when complete', () => {
    const onSubmit = vi.fn()
    render(<OTPInput value="123456" onChange={() => {}} onSubmit={onSubmit} />)
    fireEvent.keyDown(screen.getByRole('textbox'), { key: 'Enter' })
    expect(onSubmit).toHaveBeenCalled()
  })

  it('displays error message when provided', () => {
    render(<OTPInput value="" onChange={() => {}} error="Invalid code" />)
    expect(screen.getByText('Invalid code')).toBeInTheDocument()
  })

  it('is disabled when disabled prop is true', () => {
    render(<OTPInput value="" onChange={() => {}} disabled />)
    expect(screen.getByRole('textbox')).toBeDisabled()
  })

  it('uses custom length when provided', () => {
    const onChange = vi.fn()
    render(<OTPInput value="" onChange={onChange} length={4} />)
    fireEvent.change(screen.getByRole('textbox'), { target: { value: '12345' } })
    expect(onChange).toHaveBeenCalledWith('1234')
  })
})
