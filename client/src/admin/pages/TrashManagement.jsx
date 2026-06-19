import { useState, useEffect, useCallback } from 'react'
import { apiFetch } from '../api/client'
import ConfirmModal from '../components/common/ConfirmModal'
import KpiCard from '../components/common/KpiCard'
import { useToast } from '../contexts/ToastContext'

const sections = [
  { key: 'user', label: 'Users', icon: 'group', listEndpoint: '/api/admin/bin/users/', restorePrefix: '/api/admin/users', purgePrefix: '/api/admin/bin/users' },
  { key: 'cooperative', label: 'Cooperatives', icon: 'apartment', listEndpoint: '/api/admin/bin/cooperatives/', restorePrefix: '/api/admin/cooperatives', purgePrefix: '/api/admin/bin/cooperatives' },
]

export default function TrashManagement() {
  const { showToast } = useToast()
  const [expanded, setExpanded] = useState(null)
  const [binSummary, setBinSummary] = useState(null)
  const [trashData, setTrashData] = useState({})
  const [loading, setLoading] = useState(true)
  const [actionLoadingId, setActionLoadingId] = useState(null)
  const [modalConfig, setModalConfig] = useState({ open: false })

  const fetchSummary = useCallback(async () => {
    setLoading(true)
    try {
      const res = await apiFetch('/api/admin/bin/')
      setBinSummary(res)
    } catch (e) {
      showToast({ type: 'error', message: 'Failed to fetch bin summary.' })
    } finally {
      setLoading(false)
    }
  }, [showToast])

  useEffect(() => { fetchSummary() }, [fetchSummary])

  const toggleSection = async (key) => {
    if (expanded === key) { setExpanded(null); return }
    setExpanded(key)
    if (!trashData[key]) {
      const section = sections.find(s => s.key === key)
      if (!section) return
      try {
        const res = await apiFetch(section.listEndpoint)
        setTrashData(prev => ({ ...prev, [key]: res }))
      } catch (e) {
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
          fetchSummary()
          showToast({ type: 'success', message: `${section.label} restored.` })
        } catch (e) {
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
          fetchSummary()
          showToast({ type: 'success', message: `${section.label} permanently deleted.` })
        } catch (e) {
          showToast({ type: 'error', message: `Failed to purge ${section.label.toLowerCase()}.` })
        } finally {
          setActionLoadingId(null)
        }
      },
      destructive: true,
    })
  }

  const totalTrashed = binSummary
    ? Object.values(binSummary).filter(v => typeof v === 'number').reduce((s, v) => s + v, 0)
    : 0

  return (
    <div>
      <header className="mb-6">
        <h2 className="font-headline-lg text-display-md text-primary mb-1">Trash Management</h2>
        <p className="text-on-surface-variant font-body-md">View, restore, or permanently delete soft-deleted records.</p>
      </header>

      {loading && !binSummary ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            {sections.map(({ key, label, icon }) => (
              <KpiCard
                key={key}
                icon={icon}
                label={label}
                value={binSummary?.[key] ?? binSummary?.[key + 's'] ?? 0}
                highlighted={(binSummary?.[key] ?? binSummary?.[key + 's'] ?? 0) > 0}
              />
            ))}
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
                        {trashData[section.key] && Array.isArray(trashData[section.key]) && trashData[section.key].length > 0 ? (
                          <div className="space-y-2">
                            {trashData[section.key].map((item) => (
                              <div key={item.id} className="flex items-center justify-between p-3 bg-surface-container rounded-lg">
                                <div>
                                  <p className="font-body-md font-medium text-on-surface">
                                    {item.first_name ? `${item.first_name} ${item.last_name}` : item.name || item.email || item.id}
                                  </p>
                                  <p className="text-label-md text-on-surface-variant">
                                    {item.email || item.phone_number || item.registration_number || `ID: ${item.id?.slice(0, 8)}...`}
                                  </p>
                                  {item.deleted_at && (
                                    <p className="text-[10px] text-on-surface-variant">
                                      Deleted: {new Date(item.deleted_at).toLocaleDateString()}
                                    </p>
                                  )}
                                </div>
                                <div className="flex gap-2">
                                  <button
                                    onClick={() => handleRestore(item, section)}
                                    disabled={actionLoadingId === item.id}
                                    className="px-3 py-1.5 text-[11px] font-bold bg-primary-container text-primary rounded-lg hover:bg-primary-fixed transition-colors disabled:opacity-50"
                                  >
                                    {actionLoadingId === item.id ? '...' : 'Restore'}
                                  </button>
                                  <button
                                    onClick={() => handlePurge(item, section)}
                                    disabled={actionLoadingId === item.id}
                                    className="px-3 py-1.5 text-[11px] font-bold bg-error-container text-error rounded-lg hover:bg-error/10 transition-colors disabled:opacity-50"
                                  >
                                    {actionLoadingId === item.id ? '...' : 'Purge'}
                                  </button>
                                </div>
                              </div>
                            ))}
                          </div>
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
