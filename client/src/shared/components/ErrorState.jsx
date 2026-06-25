/**
 * Error state component — shown when a data fetch fails.
 * Always provides a retry action so users aren't stuck.
 *
 * @param {string}   title   - Heading text
 * @param {string}   message - Error detail text
 * @param {object}   action  - { label, onClick } — defaults to "Retry"
 */
export default function ErrorState({ title = 'Something went wrong', message, action }) {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '4rem 2rem',
      textAlign: 'center',
      gap: '1rem',
      color: 'var(--color-muted, #94a3b8)',
    }}>
      {/* Warning icon */}
      <svg width="56" height="56" viewBox="0 0 56 56" fill="none" aria-hidden="true">
        <path
          d="M28 6L4 50h48L28 6z"
          stroke="#f87171"
          strokeWidth="2.5"
          strokeLinejoin="round"
          fill="rgba(248,113,113,0.08)"
        />
        <path d="M28 24v12" stroke="#f87171" strokeWidth="2.5" strokeLinecap="round" />
        <circle cx="28" cy="42" r="1.5" fill="#f87171" />
      </svg>
      <h3 style={{
        margin: 0,
        fontSize: '1.125rem',
        fontWeight: 600,
        color: 'var(--color-on-surface, #e2e8f0)',
      }}>
        {title}
      </h3>
      {message && (
        <p style={{ margin: 0, fontSize: '0.875rem', maxWidth: '22rem', lineHeight: 1.5 }}>
          {message}
        </p>
      )}
      {action && (
        <button
          onClick={action.onClick}
          style={{
            marginTop: '0.5rem',
            padding: '0.5rem 1.25rem',
            borderRadius: '0.375rem',
            background: '#dc2626',
            border: 'none',
            color: '#fff',
            fontSize: '0.875rem',
            fontWeight: 500,
            cursor: 'pointer',
          }}
        >
          {action.label ?? 'Retry'}
        </button>
      )}
    </div>
  )
}
