export default function VisuallyHidden({ children, className = '' }) {
  return (
    <span className={`sr-only ${className}`}>{children}</span>
  )
}
