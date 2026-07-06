import { useState, useEffect, useRef } from 'react'

export default function LiveRegion({ children, mode = 'polite', className = '' }) {
  const [announced, setAnnounced] = useState('')
  const timeoutRef = useRef(null)

  useEffect(() => {
    if (children && children !== announced) {
      setAnnounced('')
      if (timeoutRef.current) clearTimeout(timeoutRef.current)
      timeoutRef.current = setTimeout(() => {
        setAnnounced(children)
      }, 100)
    }
    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current)
    }
  }, [children])

  return (
    <div
      role="status"
      aria-live={mode}
      aria-atomic="true"
      className={className}
    >
      {announced}
    </div>
  )
}
