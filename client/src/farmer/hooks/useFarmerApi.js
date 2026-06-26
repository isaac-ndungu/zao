import { useState, useEffect, useCallback, useRef } from 'react'
import { apiFetch } from '../api/client'

export default function useFarmerApi(url) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(!!url)
  const [error, setError] = useState(null)
  const mountedRef = useRef(true)
  const fetchIdRef = useRef(0)

  useEffect(() => {
    mountedRef.current = true
    return () => { mountedRef.current = false }
  }, [])

  const fetchData = useCallback(async (overrideUrl) => {
    const targetUrl = overrideUrl || url
    if (!targetUrl) return
    const id = ++fetchIdRef.current
    if (mountedRef.current) setLoading(true)
    setError(null)
    try {
      const res = await apiFetch(targetUrl)
      if (!mountedRef.current || id !== fetchIdRef.current) return
      if (!res.ok) {
        const errData = await res.json().catch(() => ({ detail: 'Request failed' }))
        throw new Error(errData.detail || errData.message || `Error ${res.status}`)
      }
      const result = await res.json()
      if (mountedRef.current && id === fetchIdRef.current) setData(result)
    } catch (err) {
      if (mountedRef.current && id === fetchIdRef.current) setError(err.message)
    } finally {
      if (mountedRef.current && id === fetchIdRef.current) setLoading(false)
    }
  }, [url])

  useEffect(() => {
    if (url) {
      setLoading(true)
      fetchData()
    }
  }, [url])

  return { data, loading, error, refetch: fetchData }
}
