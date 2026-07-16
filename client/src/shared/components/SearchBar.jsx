import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiFetch } from '../../admin/api/client'
import SearchOverlay from './SearchOverlay'
import { getResourceLinks } from '../config/searchLinks'
import { useFormAction } from '../hooks/useFormAction'

const DEBOUNCE_MS = 300

export default function SearchBar({ role, placeholder = 'Search...' }) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [showOverlay, setShowOverlay] = useState(false)
  const navigate = useNavigate()
  const timerRef = useRef(null)
  const formRef = useRef(null)

  useEffect(() => {
    return () => { if (timerRef.current) clearTimeout(timerRef.current) }
  }, [])

  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current)

    timerRef.current = setTimeout(() => {
      if (query.length < 2) {
        setResults([])
        setShowOverlay(false)
        return
      }
      setLoading(true)
      apiFetch(`/api/search/?q=${encodeURIComponent(query)}`)
        .then((res) => {
          if (!res.ok) throw new Error(`Search failed: ${res.status} ${res.statusText}`)
          return res.json()
        })
        .then((data) => {
          setResults(data.results || [])
          setShowOverlay(true)
        })
        .catch((err) => {
          console.error('Search error:', err)
          setResults([])
          setShowOverlay(false)
        })
        .finally(() => setLoading(false))
    }, DEBOUNCE_MS)
  }, [query])

  const [, searchAction] = useFormAction(async (prev, formData) => {
    const q = formData.get('q')?.trim()
    if (q && q.length >= 2) {
      setShowOverlay(false)
      navigate(`/${role}/search?q=${encodeURIComponent(q)}`)
    }
    return { success: true }
  }, {})

  const resourceLinks = getResourceLinks(role)

  const handleResultClick = (item) => {
    setShowOverlay(false)
    const listUrl = resourceLinks?.[item.type]
    if (listUrl) {
      navigate(`${listUrl}?selected=${item.id}`)
    } else if (item.url) {
      navigate(item.url)
    }
  }

  const handleViewAll = () => {
    if (query.trim().length >= 2) {
      setShowOverlay(false)
      navigate(`/${role}/search?q=${encodeURIComponent(query.trim())}`)
    }
  }

  return (
    <form
      ref={formRef}
      action={searchAction}
      className="relative hidden sm:block sm:w-60 lg:w-72 flex-shrink-0"
    >
      <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-[20px]" aria-hidden="true">
        search
      </span>
      <input
        name="q"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onFocus={() => { if (results.length > 0 && query.length >= 2) setShowOverlay(true) }}
        onBlur={() => setTimeout(() => setShowOverlay(false), 200)}
        className="w-full bg-surface-container border-none rounded-full py-2 pl-10 pr-4 text-body-md focus:ring-1 focus:ring-primary"
        placeholder={placeholder}
        aria-label={placeholder}
      />
      {showOverlay && (results.length > 0 || loading) && (
        <SearchOverlay
          results={results}
          loading={loading}
          onResultClick={handleResultClick}
          onViewAll={handleViewAll}
        />
      )}
    </form>
  )
}
