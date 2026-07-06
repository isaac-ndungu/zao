export default function ErrorState({ title = 'Something went wrong', message, action }) {
  return (
    <div role="alert" className="flex flex-col items-center justify-center py-16 px-8 text-center gap-4 text-on-surface-variant" aria-labelledby="error-state-title">
      <svg width="56" height="56" viewBox="0 0 56 56" fill="none" aria-hidden="true">
        <path d="M28 6L4 50h48L28 6z" stroke="#f87171" strokeWidth="2.5" strokeLinejoin="round" fill="rgba(248,113,113,0.08)" />
        <path d="M28 24v12" stroke="#f87171" strokeWidth="2.5" strokeLinecap="round" />
        <circle cx="28" cy="42" r="1.5" fill="#f87171" />
      </svg>
      <h3 id="error-state-title" className="font-headline-sm text-headline-sm text-on-surface">{title}</h3>
      {message && (
        <p className="text-body-md text-on-surface-variant max-w-sm leading-relaxed">{message}</p>
      )}
      {action && (
        <button
          onClick={action.onClick}
          className="mt-2 px-5 py-2 rounded-lg bg-error text-on-error text-label-md font-medium hover:bg-error/90 transition-colors cursor-pointer border-none"
        >
          {action.label ?? 'Retry'}
        </button>
      )}
    </div>
  )
}
