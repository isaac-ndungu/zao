import { Component } from 'react'
import ErrorState from './ErrorState'

/**
 * Top-level error boundary for each role route tree.
 * Catches runtime JS errors and renders a friendly fallback instead of a
 * blank white screen — critical for farmer mobile users who won't know to
 * refresh when a JS exception crashes the page.
 */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, info) {
    // Surface the error to the console so DevTools / error tracking picks it up
    console.error('[ErrorBoundary]', error, info?.componentStack)
  }

  render() {
    if (this.state.hasError) {
      return (
        <ErrorState
          title="Something went wrong"
          message={
            this.state.error?.message ||
            'An unexpected error occurred. Please reload the page.'
          }
          action={{
            label: 'Reload page',
            onClick: () => window.location.reload(),
          }}
        />
      )
    }
    return this.props.children
  }
}
