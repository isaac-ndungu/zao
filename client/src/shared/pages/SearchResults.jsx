import { useReducer, useEffect } from 'react'
import { useSearchParams, useNavigate, Link } from 'react-router-dom'
import { apiFetch } from '../../admin/api/client'

const resourceIcons = {
  farmers: 'person',
  cooperatives: 'groups',
  users: 'group',
  deliveries: 'inventory_2',
  grades: 'grading',
  loans: 'account_balance',
  payment_cycles: 'payments',
  payments: 'payments',
  disbursements: 'account_balance_wallet',
  inventory: 'inventory_2',
  buyers: 'store',
  sales: 'receipt_long',
  deductions: 'money_off',
  audit_log: 'history',
}

const initialState = { results: [], loading: false, error: null }

function searchReducer(state, action) {
  switch (action.type) {
    case 'FETCH_START': return { ...state, loading: true, error: null }
    case 'FETCH_SUCCESS': return { loading: false, results: action.results, error: null }
    case 'FETCH_ERROR': return { loading: false, results: [], error: action.error }
    case 'RESET': return { ...initialState }
    default: return state
  }
}

export default function SearchResults({ resourceLinks }) {
  const [searchParams] = useSearchParams()
  const query = searchParams.get('q') || ''
  const navigate = useNavigate()
  const [state, dispatch] = useReducer(searchReducer, initialState)
  const { results, loading, error } = state

  useEffect(() => {
    if (!query || query.length < 2) return

    dispatch({ type: 'FETCH_START' })
    let cancelled = false
    apiFetch(`/api/search/?q=${encodeURIComponent(query)}`)
      .then(async (res) => {
        if (cancelled) return
        if (!res.ok) throw new Error('Search failed')
        const data = await res.json()
        if (!cancelled) dispatch({ type: 'FETCH_SUCCESS', results: data.results || [] })
      })
      .catch((err) => {
        if (!cancelled) dispatch({ type: 'FETCH_ERROR', error: err.message })
      })
    return () => { cancelled = true }
  }, [query])

  const hasResults = results.length > 0 && results.some((g) => g.total > 0)
  const allEmpty = results.length > 0 && results.every((g) => g.total === 0)

  return (
    <div className="p-4 lg:p-6 max-w-3xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-on-surface">Search Results</h1>
        <p className="text-sm text-on-surface-variant mt-1">
          {query ? `Results for "${query}"` : 'Enter a search query to find resources.'}
        </p>
      </div>

      {loading && (
        <div className="flex items-center gap-3 text-on-surface-variant py-12 justify-center">
          <span className="inline-block animate-spin h-5 w-5 border-2 border-primary border-t-transparent rounded-full" />
          <span>Searching...</span>
        </div>
      )}

      {error && (
        <div className="p-4 bg-error-container/20 rounded-xl text-error text-sm">
          {error}
        </div>
      )}

      {!loading && !error && !query && (
        <div className="text-center py-12 text-on-surface-variant">
          <span className="material-symbols-outlined text-4xl mb-2" aria-hidden="true">search</span>
          <p>Type a query above to start searching.</p>
        </div>
      )}

      {!loading && !error && allEmpty && (
        <div className="text-center py-12 text-on-surface-variant">
          <span className="material-symbols-outlined text-4xl mb-2" aria-hidden="true">search_off</span>
          <p className="text-lg font-medium text-on-surface">No results found</p>
          <p className="text-sm mt-1">Try adjusting your search terms.</p>
        </div>
      )}

      {!loading && hasResults && (
        <div className="space-y-6">
          {results.map((group) => {
            if (group.total === 0) return null
            const listUrl = resourceLinks?.[group.key]
            return (
              <div key={group.key} className="bg-surface-container-lowest border border-outline-variant rounded-xl overflow-hidden">
                <div className="px-4 py-3 border-b border-outline-variant/50 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="material-symbols-outlined text-[18px] text-on-surface-variant" aria-hidden="true">
                      {resourceIcons[group.key] || 'search'}
                    </span>
                    <h2 className="text-sm font-bold text-on-surface uppercase tracking-wider">{group.label}</h2>
                    <span className="text-xs text-on-surface-variant">({group.total})</span>
                  </div>
                  {listUrl && (
                    <Link
                      to={`${listUrl}?search=${encodeURIComponent(query)}`}
                      className="text-xs font-bold text-primary hover:underline"
                    >
                      View all
                    </Link>
                  )}
                </div>
                <div>
                    {group.items.map((item) => {
                      const listUrl = resourceLinks?.[group.key]
                      return (
                        <button
                          key={`${item.type}-${item.id}`}
                          onClick={() => {
                            if (listUrl) {
                              navigate(`${listUrl}?selected=${item.id}`)
                            }
                          }}
                          className="w-full flex items-center gap-3 px-4 py-3 hover:bg-surface-container transition-colors text-left border-b border-outline-variant/30 last:border-none"
                        >
                          <span className="material-symbols-outlined text-[20px] text-on-surface-variant shrink-0" aria-hidden="true">
                            {item.icon || resourceIcons[group.key] || 'search'}
                          </span>
                          <div className="min-w-0 flex-1">
                            <p className="text-sm font-medium text-on-surface truncate">{item.label}</p>
                            <p className="text-xs text-on-surface-variant truncate">{item.subtitle}</p>
                          </div>
                          <span className="material-symbols-outlined text-[16px] text-on-surface-variant shrink-0" aria-hidden="true">
                            chevron_right
                          </span>
                        </button>
                      )
                    })}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
