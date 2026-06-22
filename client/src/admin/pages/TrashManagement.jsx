import { useState, useEffect } from 'react'
import { apiFetch } from '../api/client'
import ConfirmModal from '../components/common/ConfirmModal'
import { useToast } from '../contexts/ToastContext'

const sectionDefaults = {
  user: { label: 'Users', icon: 'group', listEndpoint: '/api/admin/bin/users/', restorePrefix: '/api/admin/users', purgePrefix: '/api/admin/bin/users' },
  cooperative: { label: 'Cooperatives', icon: 'apartment', listEndpoint: '/api/admin/bin/cooperatives/', restorePrefix: '/api/admin/cooperatives', purgePrefix: '/api/admin/bin/cooperatives' },
  farmer: { label: 'Farmers', icon: 'agriculture', listEndpoint: '/api/admin/bin/farmers/', restorePrefix: '/api/admin/farmers', purgePrefix: '/api/admin/bin/farmers' },
  delivery: { label: 'Deliveries', icon: 'local_shipping', listEndpoint: '/api/admin/bin/deliveries/', restorePrefix: '/api/admin/deliveries', purgePrefix: '/api/admin/bin/deliveries' },
  loan: { label: 'Loans', icon: 'account_balance', listEndpoint: '/api/admin/bin/loans/', restorePrefix: '/api/admin/loans', purgePrefix: '/api/admin/bin/loans' },
  paymentcycle: { label: 'Payment Cycles', icon: 'payments', listEndpoint: '/api/admin/bin/payment-cycles/', restorePrefix: '/api/admin/payment-cycles', purgePrefix: '/api/admin/bin/payment-cycles' },
}

const sections = Object.keys(sectionDefaults)
  .map(key => ({ key, ...sectionDefaults[key] }))
  .sort((a, b) => a.label.localeCompare(b.label))

export default function TrashManagement() {
  const { showToast } = useToast()
  const [expanded, setExpanded] = useState(null)
  const [binSummary, setBinSummary] = useState(null)
  const [trashData, setTrashData] = useState({})
  const [searchFilters, setSearchFilters] = useState({})
  const [loading, setLoading] = useState(true)
  const [actionLoadingId, setActionLoadingId] = useState(null)
  const [modalConfig, setModalConfig] = useState({ open: false })

  const refetchSummary = async () => {
    try {
      const res = await apiFetch('/api/admin/bin/')
      const data = await res.json()
      setBinSummary(data)
    } catch {
      showToast({ type: 'error', message: 'Failed to fetch bin summary.' })
    }
  }

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setLoading(true)
      try {
        const res = await apiFetch('/api/admin/bin/')
        const data = await res.json()
        if (!cancelled) setBinSummary(data)
      } catch {
        if (!cancelled) showToast({ type: 'error', message: 'Failed to fetch bin summary.' })
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => { cancelled = true }
  }, [showToast])

  const toggleSection = async (key) => {
    if (expanded === key) { setExpanded(null); return }
    setExpanded(key)
    if (!trashData[key]) {
      const section = sections.find(s => s.key === key)
      if (!section) return
      try {
        const res = await apiFetch(section.listEndpoint)
        const data = await res.json()
        setTrashData(prev => ({ ...prev, [key]: Array.isArray(data) ? data : data?.results || [] }))
      } catch {
        showToast({ type: 'error', message: `Failed to load ${key} records.` })
      }
    }
  }

  const handleRestore = (item, section) => {
    setModalConfig({
      open: true,
      title: 'Restore Item',
      message: `Restore this ${section.label.toLowerCase()}? All associated data will be recovered.`,
      onConfirm: async () => {
        setActionLoadingId(item.id)
        setModalConfig({ open: false })
        try {
          await apiFetch(`${section.restorePrefix}/${item.id}/restore/`, {
            method: 'POST',
            body: JSON.stringify({ confirm: true }),
          })
          setTrashData(prev => ({
            ...prev,
            [section.key]: Array.isArray(prev[section.key]) ? prev[section.key].filter(i => i.id !== item.id) : [],
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
          setTrashData(prev => ({
            ...prev,
            [section.key]: Array.isArray(prev[section.key]) ? prev[section.key].filter(i => i.id !== item.id) : [],
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

  const totalTrashed = binSummary
    ? Object.keys(sectionDefaults).reduce((s, key) => s + ((binSummary[key] ?? binSummary[key + 's'] ?? 0)), 0)
    : 0

  const itemsForSection = (section) => {
    const items = trashData[section.key]
    if (!Array.isArray(items)) return items
    const search = (searchFilters[section.key] || '').toLowerCase()
    if (!search) return items
    return items.filter(item => {
      const name = item.first_name ? `${item.first_name} ${item.last_name}` : item.name || item.email || item.id
      return name.toLowerCase().includes(search) || (item.email || '').toLowerCase().includes(search) || (item.id || '').toLowerCase().includes(search)
    })
  }

  const canPurge = (sectionKey) => {
    return sectionKey !== 'farmer'
  }

  return (
    <div>
      <header className="mb-6">
        <h2 className="font-headline-lg text-display-md text-primary mb-1">Trash Management</h2>
        <p className="text-on-surface-variant font-body-md">View, restore, or permanently delete soft-deleted records.</p>
      </header>

      {loading && !binSummary ? (
        <div className="flex gap-2 mb-6">
          {[1, 2, 3, 4, 5, 6].map(i => (
            <div key={i} className="h-8 w-24 bg-surface-container-high rounded-full animate-pulse" />
          ))}
        </div>
      ) : (
        <>
          <div className="flex flex-wrap gap-2 mb-6">
            {sections.map(({ key, label, icon }) => {
              const count = binSummary?.[key] ?? binSummary?.[key + 's'] ?? 0
              return (
                <div
                  key={key}
                  className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[12px] font-semibold ${
                    count > 0
                      ? 'bg-error-container text-error'
                      : 'bg-surface-container-high text-on-surface-variant'
                  }`}
                >
                  <span className="material-symbols-outlined text-[14px]">{icon}</span>
                  <span>{label}</span>
                  <span className={`ml-0.5 min-w-[14px] text-center ${count > 0 ? '' : 'text-outline'}`}>
                    {count}
                  </span>
                </div>
              )
            })}
          </div>

          <div className="flex items-center justify-end mb-4">
            <button
              onClick={() => { const p = new URLSearchParams(); p.set('export', 'csv'); window.open(`/api/admin/bin/?${p}`, '_blank') }}
              className="flex items-center gap-1.5 px-3 py-2 text-label-md font-bold text-on-surface-variant hover:text-primary transition-colors"
              title="Export CSV"
            >
              <span className="material-symbols-outlined text-[18px]">download</span>
              <span className="hidden sm:inline">Export</span>
            </button>
          </div>

          <div className="bg-surface-container-lowest border border-outline-variant rounded-xl overflow-hidden">
            {!binSummary || totalTrashed === 0 ? (
              <div className="text-center py-12">
                <span className="material-symbols-outlined text-[48px] block mb-2 text-outline-variant">delete_sweep</span>
                <p className="text-body-md text-on-surface-variant">Trash is empty. No soft-deleted records.</p>
              </div>
            ) : (
              <div className="divide-y divide-outline-variant/50">
                {sections.filter(s => (binSummary?.[s.key] ?? binSummary?.[s.key + 's'] ?? 0) > 0).map((section) => (
                  <div key={section.key}>
                    <button
                      onClick={() => toggleSection(section.key)}
                      className="w-full flex items-center justify-between px-6 py-4 hover:bg-surface-container transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <span className="material-symbols-outlined text-on-surface-variant">{section.icon}</span>
                        <span className="font-headline-sm text-headline-sm text-on-surface">{section.label}</span>
                        <span className="px-2 py-0.5 bg-surface-container-high rounded-full text-[11px] font-bold text-on-surface-variant">
                          {binSummary?.[section.key] ?? binSummary?.[section.key + 's'] ?? 0}
                        </span>
                      </div>
                      <span className={`material-symbols-outlined text-on-surface-variant transition-transform ${expanded === section.key ? 'rotate-180' : ''}`}>
                        expand_more
                      </span>
                    </button>
                    {expanded === section.key && (
                      <div className="px-6 pb-4">
                        <div className="relative mb-3">
                          <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-[16px] text-outline">search</span>
                          <input
                            type="text"
                            placeholder={`Search ${section.label.toLowerCase()}...`}
                            value={searchFilters[section.key] || ''}
                            onChange={e => setSearchFilters(prev => ({ ...prev, [section.key]: e.target.value }))}
                            className="w-full pl-9 pr-3 py-2 bg-surface-container rounded-lg text-body-sm text-on-surface placeholder:text-outline border border-outline-variant focus:outline-none focus:ring-2 focus:ring-primary"
                          />
                        </div>
                        {trashData[section.key] && Array.isArray(trashData[section.key]) && trashData[section.key].length > 0 ? (
                          (() => {
                            const filtered = itemsForSection(section)
                            return filtered.length > 0 ? (
                              <div className="space-y-2">
                                {filtered.map((item) => (
                                  <div key={item.id} className="flex items-center justify-between p-3 bg-surface-container rounded-lg">
                                    <div className="min-w-0 flex-1">
                                      <p className="font-body-md font-medium text-on-surface truncate">
                                        {item.first_name ? `${item.first_name} ${item.last_name}` : item.name || item.email || item.id}
                                      </p>
                                      <p className="text-label-md text-on-surface-variant truncate">
                                        {item.email || item.phone_number || item.registration_number || `ID: ${item.id?.slice(0, 8)}...`}
                                      </p>
                                      {item.deleted_at && (
                                        <p className="text-[10px] text-on-surface-variant">
                                          Deleted: {new Date(item.deleted_at).toLocaleDateString()}
                                        </p>
                                      )}
                                    </div>
                                    <div className="flex gap-2 shrink-0 ml-3">
                                      <button
                                        onClick={() => handleRestore(item, section)}
                                        disabled={actionLoadingId === item.id}
                                        className="px-3 py-1.5 text-[11px] font-bold bg-primary-container text-primary rounded-lg hover:bg-primary-fixed transition-colors disabled:opacity-50"
                                      >
                                        {actionLoadingId === item.id ? '...' : 'Restore'}
                                      </button>
                                      {canPurge(section.key) && (
                                        <button
                                          onClick={() => handlePurge(item, section)}
                                          disabled={actionLoadingId === item.id}
                                          className="px-3 py-1.5 text-[11px] font-bold bg-error-container text-error rounded-lg hover:bg-error/10 transition-colors disabled:opacity-50"
                                        >
                                          {actionLoadingId === item.id ? '...' : 'Purge'}
                                        </button>
                                      )}
                                    </div>
                                  </div>
                                ))}
                              </div>
                            ) : (
                              <p className="text-center text-body-sm text-on-surface-variant py-4">No matches found.</p>
                            )
                          })()
                        ) : (
                          <div className="flex items-center justify-center py-4">
                            <div className="animate-spin rounded-full h-5 w-5 border-b border-primary" />
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
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
          />
        </>
      )}
    </div>
  )
}
