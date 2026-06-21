import { useState, useEffect, useCallback, useRef } from 'react'
import { apiFetch } from '../api/client'

export function useApi(url, options = {}) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const fetchId = useRef(0)
  const optionsRef = useRef(options)
  optionsRef.current = options

  const refetch = useCallback(async () => {
    if (!url) return
    const id = ++fetchId.current
    setLoading(true)
    setError(null)
    try {
      const res = await apiFetch(url, optionsRef.current)
      if (id !== fetchId.current) return
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw { status: res.status, ...body }
      }
      const json = await res.json()
      if (id === fetchId.current) setData(json)
    } catch (err) {
      if (id === fetchId.current) setError(err.detail || err.message || 'Request failed')
    } finally {
      if (id === fetchId.current) setLoading(false)
    }
  }, [url])

  useEffect(() => {
    if (url) refetch()
  }, [url, refetch])

  return { data, error, loading, refetch }
}
