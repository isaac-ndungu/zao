import { useState, useEffect } from 'react'

const CRITICAL_KEY = 'urgency_critical_hours'
const WARNING_KEY = 'urgency_warning_hours'
const DEFAULTS = { critical: 3, warning: 1 }

export function useUrgencyThresholds() {
  const [thresholds, setThresholds] = useState(() => {
    return {
      critical: Number(localStorage.getItem(CRITICAL_KEY)) || DEFAULTS.critical,
      warning: Number(localStorage.getItem(WARNING_KEY)) || DEFAULTS.warning,
    }
  })

  useEffect(() => {
    localStorage.setItem(CRITICAL_KEY, String(thresholds.critical))
    localStorage.setItem(WARNING_KEY, String(thresholds.warning))
  }, [thresholds])

  const setCritical = (val) => setThresholds((t) => ({ ...t, critical: val }))
  const setWarning = (val) => setThresholds((t) => ({ ...t, warning: val }))

  return { ...thresholds, setCritical, setWarning }
}

export function getUrgencyLevel(dateDelivered, thresholds) {
  if (!dateDelivered) return 'fresh'
  const diffMs = Date.now() - new Date(dateDelivered).getTime()
  const diffHours = diffMs / (1000 * 60 * 60)

  if (diffHours > thresholds.critical) return 'critical'
  if (diffHours > thresholds.warning) return 'warning'
  return 'fresh'
}
