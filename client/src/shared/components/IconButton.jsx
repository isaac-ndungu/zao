export default function IconButton({
  icon,
  label,
  onClick,
  className = '',
  iconClassName = '',
  size = 'md',
  disabled = false,
  ...props
}) {
  const sizeClasses = {
    sm: 'w-8 h-8',
    md: 'w-10 h-10',
    lg: 'w-12 h-12',
  }

  const iconSizes = {
    sm: 'text-[16px]',
    md: 'text-[20px]',
    lg: 'text-[24px]',
  }

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={label}
      className={`inline-flex items-center justify-center rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed hover:bg-surface-container-high focus-visible:ring-2 focus-visible:ring-primary focus-visible:outline-none ${sizeClasses[size]} ${className}`}
      {...props}
    >
      <span className={`material-symbols-outlined ${iconSizes[size]} ${iconClassName}`} aria-hidden="true">
        {icon}
      </span>
    </button>
  )
}
