export default function EmptyState({ title = 'Nothing here yet', message, action }) {
  return (
    <div role="status" className="flex flex-col items-center justify-center py-16 px-8 text-center gap-4 text-on-surface-variant" aria-live="polite">
      <svg width="80" height="80" viewBox="0 0 80 80" fill="none" aria-hidden="true">
        <circle cx="40" cy="40" r="38" stroke="currentColor" strokeWidth="2" strokeDasharray="4 4" opacity="0.3" />
        <path d="M28 40h24M40 28v24" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" opacity="0.4" />
      </svg>
      <h3 className="font-headline-sm text-headline-sm text-on-surface">{title}</h3>
      {message && (
        <p className="text-body-md text-on-surface-variant max-w-sm leading-relaxed">{message}</p>
      )}
      {action && (
        <button
          onClick={action.onClick}
          className="mt-2 px-5 py-2 rounded-lg border border-primary text-primary text-label-md font-medium hover:bg-primary/5 transition-colors cursor-pointer"
        >
          {action.label}
        </button>
      )}
    </div>
  )
}
