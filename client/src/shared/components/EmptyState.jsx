/**
 * Empty state illustration shown when a list or page has no data.
 * @param {string}   title    - Primary heading
 * @param {string}   message  - Supporting text
 * @param {object}   action   - Optional { label, onClick } CTA button
 */
export default function EmptyState({ title = 'Nothing here yet', message, action }) {
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
      {/* Simple SVG illustration */}
      <svg width="80" height="80" viewBox="0 0 80 80" fill="none" aria-hidden="true">
        <circle cx="40" cy="40" r="38" stroke="currentColor" strokeWidth="2" strokeDasharray="4 4" opacity="0.3" />
        <path d="M28 40h24M40 28v24" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" opacity="0.4" />
      </svg>
      <h3 style={{ margin: 0, fontSize: '1.125rem', fontWeight: 600, color: 'var(--color-on-surface, #e2e8f0)' }}>
        {title}
      </h3>
      {message && (
        <p style={{ margin: 0, fontSize: '0.875rem', maxWidth: '20rem', lineHeight: 1.5 }}>
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
            border: '1px solid var(--color-primary, #3b82f6)',
            background: 'transparent',
            color: 'var(--color-primary, #3b82f6)',
            fontSize: '0.875rem',
            fontWeight: 500,
            cursor: 'pointer',
          }}
        >
          {action.label}
        </button>
      )}
    </div>
  )
}
