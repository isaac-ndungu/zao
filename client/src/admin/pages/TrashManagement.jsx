import { useState, useEffect, useMemo } from 'react'
import { apiFetch } from '../api/client'
import ConfirmModal from '../components/common/ConfirmModal'
import { useToast } from '../contexts/ToastContext'

const RESOURCE_TYPES = [
  { key: 'user', label: 'Users', icon: 'group', endpoint: '/api/admin/bin/users/', restorePrefix: '/api/admin/users', purgePrefix: '/api/admin/bin/users' },
  { key: 'cooperative', label: 'Cooperatives', icon: 'apartment', endpoint: '/api/admin/bin/cooperatives/', restorePrefix: '/api/admin/cooperatives', purgePrefix: '/api/admin/bin/cooperatives' },
  { key: 'farmer', label: 'Farmers', icon: 'agriculture', endpoint: '/api/admin/bin/farmers/', restorePrefix: '/api/admin/farmers', purgePrefix: null, skipPurge: true },
  { key: 'delivery', label: 'Deliveries', icon: 'local_shipping', endpoint: '/api/admin/bin/deliveries/', restorePrefix: '/api/admin/deliveries', purgePrefix: '/api/admin/bin/deliveries' },
  { key: 'loan', label: 'Loans', icon: 'account_balance', endpoint: '/api/admin/bin/loans/', restorePrefix: '/api/admin/loans', purgePrefix: '/api/admin/bin/loans' },
  { key: 'paymentcycle', label: 'Payment Cycles', icon: 'payments', endpoint: '/api/admin/bin/payment-cycles/', restorePrefix: '/api/admin/payment-cycles', purgePrefix: '/api/admin/bin/payment-cycles' },
]

function itemName(item, sectionKey) {
  if (sectionKey === 'user' || sectionKey === 'farmer') return `${item.first_name || ''} ${item.last_name || ''}`.trim() || item.email || item.id
  if (sectionKey === 'cooperative' || sectionKey === 'paymentcycle') return item.name || item.id
  if (sectionKey === 'delivery') return item.batch_id || `Delivery ${item.id?.slice(0, 8)}`
  if (sectionKey === 'loan') return item.farmer_name || item.id
  return item.id
}

function itemSecondary(item, sectionKey) {
  if (sectionKey === 'user') return item.email || item.phone_number || ''
  if (sectionKey === 'farmer') return item.email || item.phone_number || item.id_number || ''
  if (sectionKey === 'cooperative') return item.registration_number || ''
  if (sectionKey === 'delivery') return `${item.farmer_name || ''} — ${item.product_type || ''}`.trim().replace(/^ — /, '') || ''
  if (sectionKey === 'loan') return item.farmer_name || ''
  if (sectionKey === 'paymentcycle') return `${item.status || ''} — ${item.start_date || ''} to ${item.end_date || ''}`.replace(/^ — /, '') || ''
  return ''
}

function formatDeletedAt(isoString) {
  if (!isoString) return null
  try {
    return new Intl.DateTimeFormat('en-KE', {
      timeZone: 'Africa/Nairobi',
      dateStyle: 'medium',
      timeStyle: 'short',
    }).format(new Date(isoString))
  } catch {
    return new Date(isoString).toLocaleDateString()
  }
}

export default function TrashManagement() {
  const { showToast } = useToast()
  const [binSummary, setBinSummary] = useState(null)
  const [cache, setCache] = useState({})
  const [loading, setLoading] = useState({})
  const [activeFilter, setActiveFilter] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [actionLoadingId, setActionLoadingId] = useState(null)
  const [modalConfig, setModalConfig] = useState({ open: false })

  const refetchSummary = async () => {
    try {
      const res = await apiFetch('/api/admin/bin/')
      setBinSummary(await res.json())
    } catch {
      showToast({ type: 'error', message: 'Failed to fetch bin summary.' })
    }
  }

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const res = await apiFetch('/api/admin/bin/')
        const data = await res.json()
        if (!cancelled) setBinSummary(data)
      } catch {
        if (!cancelled) showToast({ type: 'error', message: 'Failed to fetch bin summary.' })
      }
    })()
    return () => { cancelled = true }
  }, [showToast])

  const fetchResource = async (type) => {
    if (cache[type]) return
    setLoading(prev => ({ ...prev, [type]: true }))
    try {
      const section = RESOURCE_TYPES.find(r => r.key === type)
      if (!section) return
      const res = await apiFetch(section.endpoint)
      const data = await res.json()
      const items = Array.isArray(data) ? data : data?.results || []
      setCache(prev => ({ ...prev, [type]: items }))
    } catch {
      showToast({ type: 'error', message: `Failed to load ${type} records.` })
    } finally {
      setLoading(prev => ({ ...prev, [type]: false }))
    }
  }

  const handleFilterClick = (type) => {
    if (activeFilter === type) {
      setActiveFilter(null)
      return
    }
    setActiveFilter(type)
    if (type === '__all') {
      RESOURCE_TYPES.forEach(r => fetchResource(r.key))
    } else {
      fetchResource(type)
    }
  }

  const handleRestore = (item, section) => {
    const isCoop = section.key === 'cooperative'
    let impactSummary = null
    if (isCoop && binSummary) {
      impactSummary = RESOURCE_TYPES
        .filter(r => r.key !== 'cooperative')
        .map(r => ({ icon: r.icon, label: r.label, count: binSummary[r.key] || 0 }))
        .filter(r => r.count > 0)
      if (impactSummary.length === 0) impactSummary = null
    }

    setModalConfig({
      open: true,
      title: 'Restore Item',
      message: `Restore this ${section.label.toLowerCase()}?${isCoop ? ' All associated data will be recovered.' : ''}`,
      impactSummary,
      onConfirm: async () => {
        setActionLoadingId(item.id)
        setModalConfig({ open: false })
        try {
          await apiFetch(`${section.restorePrefix}/${item.id}/restore/`, {
            method: 'POST',
            body: JSON.stringify({ confirm: true }),
          })
          setCache(prev => ({
            ...prev,
            [section.key]: prev[section.key]?.filter(i => i.id !== item.id) || [],
          }))
          refetchSummary()
          showToast({ type: 'success', message: `${section.label} restored.` })
        } catch {
          showToast({ type: 'error', message: `Failed to restore ${section.label.toLowerCase()}.` })
        } finally {
          setActionLoadingId(null)
        }
      },
      destructive: false,
    })
  }

  const handlePurge = (item, section) => {
    setModalConfig({
      open: true,
      title: 'Permanently Purge',
      message: `Permanently delete this ${section.label.toLowerCase()}? This action CANNOT be undone.`,
      confirmLabel: 'Permanently Delete',
      onConfirm: async () => {
        setActionLoadingId(item.id)
        setModalConfig({ open: false })
        try {
          await apiFetch(`${section.purgePrefix}/${item.id}/purge/`, {
            method: 'POST',
            body: JSON.stringify({ confirm: true }),
          })
          setCache(prev => ({
            ...prev,
            [section.key]: prev[section.key]?.filter(i => i.id !== item.id) || [],
          }))
          refetchSummary()
          showToast({ type: 'success', message: `${section.label} permanently deleted.` })
        } catch {
          showToast({ type: 'error', message: `Failed to purge ${section.label.toLowerCase()}.` })
        } finally {
          setActionLoadingId(null)
        }
      },
      destructive: true,
    })
  }

  const totalTrashed = useMemo(() => {
    if (!binSummary) return 0
    return RESOURCE_TYPES.reduce((s, r) => s + (binSummary[r.key] || 0), 0)
  }, [binSummary])

  const filteredItems = useMemo(() => {
    const typesToShow = activeFilter === '__all'
      ? RESOURCE_TYPES
      : RESOURCE_TYPES.filter(r => r.key === activeFilter)

    const results = []
    for (const section of typesToShow) {
      const items = cache[section.key]
      if (!items || loading[section.key]) {
        if (loading[section.key]) {
          results.push({ _section: section, _loading: true, key: `loading-${section.key}` })
        }
        continue
      }
      for (const item of items) {
        const name = itemName(item, section.key)
        const secondary = itemSecondary(item, section.key)
        if (searchQuery) {
          const q = searchQuery.toLowerCase()
          if (!name.toLowerCase().includes(q) && !secondary.toLowerCase().includes(q) && !(item.id || '').toLowerCase().includes(q)) continue
        }
        results.push({ ...item, _section: section, _name: name, _secondary: secondary })
      }
    }
    return results
  }, [cache, loading, activeFilter, searchQuery])

  const pills = useMemo(() => {
    const allCount = totalTrashed
    const items = [
      { key: '__all', label: 'All', count: allCount },
      ...RESOURCE_TYPES.map(r => ({ key: r.key, label: r.label, icon: r.icon, count: binSummary?.[r.key] || 0 })),
    ]
    return items
  }, [binSummary, totalTrashed])

  return (
    <div>
      <header className="mb-6">
        <h2 className="font-headline-lg text-display-md text-primary mb-1">Trash Management</h2>
        <p className="text-on-surface-variant font-body-md">View, restore, or permanently delete soft-deleted records.</p>
      </header>

      {!binSummary ? (
        <div className="flex gap-2 mb-6">
          {[1, 2, 3, 4, 5, 6, 7].map(i => (
            <div key={i} className="h-8 w-24 bg-surface-container-high rounded-full animate-pulse" />
          ))}
        </div>
      ) : (
        <>
          <div className="flex flex-wrap gap-2 mb-6">
            {pills.map(({ key, label, icon, count }) => (
              <button
                key={key ?? 'all'}
                onClick={() => handleFilterClick(key)}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[12px] font-semibold transition-colors cursor-pointer ${
                  activeFilter === key
                    ? 'bg-primary text-on-primary shadow-sm'
                    : count > 0
                      ? 'bg-error-container text-error hover:bg-error-container/80'
                      : 'bg-surface-container-high text-on-surface-variant hover:bg-surface-container-highest'
                }`}
              >
                {icon && <span className="material-symbols-outlined text-[14px]">{icon}</span>}
                <span>{label}</span>
                <span className={`ml-0.5 min-w-[14px] text-center ${activeFilter === key ? 'text-on-primary' : count > 0 ? '' : 'text-outline'}`}>
                  {count}
                </span>
              </button>
            ))}
          </div>

          <div className="flex items-center justify-between mb-4 gap-3 flex-wrap">
            <div className="relative flex-1 max-w-sm">
              <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-[16px] text-outline">search</span>
              <input
                type="text"
                placeholder="Search across loaded items..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-3 py-2 bg-surface-container rounded-lg text-body-sm text-on-surface placeholder:text-outline border border-outline-variant focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
            <div className="flex items-center gap-3">
              {searchQuery && activeFilter !== '__all' && (
                <span className="text-[11px] text-on-surface-variant">Searching across loaded resource types</span>
              )}
              <button
                onClick={() => { const p = new URLSearchParams(); p.set('export', 'csv'); window.open(`/api/admin/bin/?${p}`, '_blank') }}
                className="flex items-center gap-1.5 px-3 py-2 text-label-md font-bold text-on-surface-variant hover:text-primary transition-colors"
                title="Export CSV"
              >
                <span className="material-symbols-outlined text-[18px]">download</span>
                <span className="hidden sm:inline">Export</span>
              </button>
            </div>
          </div>

          <div className="bg-surface-container-lowest border border-outline-variant rounded-xl overflow-hidden">
            {!activeFilter && totalTrashed > 0 ? (
              <div className="text-center py-12">
                <span className="material-symbols-outlined text-[48px] block mb-2 text-outline-variant">filter_alt</span>
                <p className="text-body-md text-on-surface-variant">Click a filter above to view trashed items.</p>
              </div>
            ) : totalTrashed === 0 && !activeFilter ? (
              <div className="text-center py-12">
                <span className="material-symbols-outlined text-[48px] block mb-2 text-outline-variant">delete_sweep</span>
                <p className="text-body-md text-on-surface-variant">Trash is empty. No soft-deleted records.</p>
              </div>
            ) : filteredItems.length === 0 && Object.keys(loading).some(k => loading[k]) ? (
              <div className="space-y-2 p-4">
                {RESOURCE_TYPES.filter(r => activeFilter === '__all' || r.key === activeFilter).map(section => (
                  <div key={section.key} className="flex items-center gap-3 p-3 bg-surface-container rounded-lg animate-pulse">
                    <div className="h-5 w-5 rounded-full bg-surface-container-high" />
                    <div className="flex-1 space-y-1.5">
                      <div className="h-4 w-40 bg-surface-container-high rounded" />
                      <div className="h-3 w-24 bg-surface-container-high rounded" />
                    </div>
                    <div className="h-6 w-16 bg-surface-container-high rounded" />
                  </div>
                ))}
              </div>
            ) : filteredItems.length === 0 ? (
              <div className="text-center py-12">
                <span className="material-symbols-outlined text-[48px] block mb-2 text-outline-variant">search_off</span>
                <p className="text-body-md text-on-surface-variant">No items match your search or filter.</p>
              </div>
            ) : (
              <div className="divide-y divide-outline-variant/50">
                {filteredItems.map((item) => {
                  if (item._loading) {
                    return (
                      <div key={item.key} className="flex items-center gap-3 px-6 py-4 animate-pulse">
                        <div className="h-5 w-5 rounded-full bg-surface-container-high" />
                        <div className="flex-1 space-y-1.5">
                          <div className="h-4 w-40 bg-surface-container-high rounded" />
                          <div className="h-3 w-24 bg-surface-container-high rounded" />
                        </div>
                      </div>
                    )
                  }
                  const section = item._section
                  const deletedStr = formatDeletedAt(item.deleted_at)
                  return (
                    <div key={item.id} className="flex items-center justify-between px-6 py-3 hover:bg-surface-container transition-colors">
                      <div className="flex items-center gap-3 min-w-0 flex-1">
                        <span className={`material-symbols-outlined text-[18px] shrink-0 ${activeFilter === section.key ? 'text-primary' : 'text-on-surface-variant'}`}>
                          {section.icon}
                        </span>
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2 flex-wrap">
                            {activeFilter !== section.key && (
                              <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold uppercase ${
                                section.key === 'user' ? 'bg-blue-100 text-blue-700' :
                                section.key === 'cooperative' ? 'bg-purple-100 text-purple-700' :
                                section.key === 'farmer' ? 'bg-green-100 text-green-700' :
                                section.key === 'delivery' ? 'bg-amber-100 text-amber-700' :
                                section.key === 'loan' ? 'bg-rose-100 text-rose-700' :
                                'bg-gray-100 text-gray-700'
                              }`}>
                                {section.label}
                              </span>
                            )}
                            <span className="font-body-md font-medium text-on-surface truncate">{item._name}</span>
                          </div>
                          {item._secondary && (
                            <p className="text-label-md text-on-surface-variant truncate">{item._secondary}</p>
                          )}
                          {deletedStr && (
                            <p className="text-[10px] text-on-surface-variant">Deleted: {deletedStr}</p>
                          )}
                        </div>
                      </div>
                      <div className="flex gap-1 shrink-0 ml-3 items-center">
                        <button
                          onClick={() => handleRestore(item, section)}
                          disabled={actionLoadingId === item.id}
                          className="p-1.5 rounded-lg bg-primary-container text-primary hover:bg-primary-fixed transition-colors disabled:opacity-50"
                          title="Restore"
                        >
                          {actionLoadingId === item.id ? <span className="material-symbols-outlined text-[16px] animate-spin">sync</span> : <span className="material-symbols-outlined text-[16px]">restore</span>}
                        </button>
                        {section.purgePrefix && (
                          <button
                            onClick={() => handlePurge(item, section)}
                            disabled={actionLoadingId === item.id}
                            className="p-1.5 rounded-lg bg-error-container text-error hover:bg-error/10 transition-colors disabled:opacity-50"
                            title="Purge"
                          >
                            {actionLoadingId === item.id ? <span className="material-symbols-outlined text-[16px] animate-spin">sync</span> : <span className="material-symbols-outlined text-[16px]">delete_forever</span>}
                          </button>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          <ConfirmModal
            open={modalConfig.open}
            title={modalConfig.title}
            message={modalConfig.message}
            confirmLabel={modalConfig.confirmLabel}
            onConfirm={modalConfig.onConfirm}
            onCancel={() => setModalConfig({ open: false })}
            loading={actionLoadingId !== null}
            destructive={modalConfig.destructive}
            impactSummary={modalConfig.impactSummary}
          />
        </>
      )}
    </div>
  )
}
