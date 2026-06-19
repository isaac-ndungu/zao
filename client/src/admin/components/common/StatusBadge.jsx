const statusStyles = {
  active: 'bg-primary-container text-on-primary-container',
  inactive: 'bg-surface-container-high text-on-surface-variant',
  pending: 'bg-tertiary-fixed-dim text-on-tertiary-fixed',
  completed: 'bg-primary text-on-primary',
  rejected: 'bg-error-container text-on-error-container',
  defaulted: 'bg-error text-on-error',
  draft: 'bg-surface-container-highest text-on-surface-variant',
  computing: 'bg-secondary-fixed text-on-secondary-fixed',
  computed: 'bg-primary-fixed text-on-primary-fixed-variant',
  locked: 'bg-secondary-container text-on-secondary-container',
  disbursed: 'bg-primary text-on-primary',
  processing: 'bg-secondary-fixed text-on-secondary-fixed',
  failed: 'bg-error-container text-on-error-container',
  paid: 'bg-primary text-on-primary',
  accepted: 'bg-primary-container text-on-primary-container',
  graded: 'bg-secondary-fixed text-on-secondary-fixed',
  true: 'bg-primary-container text-on-primary-container',
  false: 'bg-surface-container-high text-on-surface-variant',
}

export default function StatusBadge({ status, label }) {
  const style = statusStyles[status] || 'bg-surface-container-high text-on-surface-variant'
  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase tracking-wide ${style}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${status === 'active' || status === true || status === 'true' || status === 'completed' || status === 'paid' || status === 'accepted' || status === 'processing' ? 'bg-current' : 'bg-current opacity-50'}`} />
      {label || String(status)}
    </span>
  )
}
