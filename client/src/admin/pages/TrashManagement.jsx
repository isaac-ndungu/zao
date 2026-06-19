import { useState, useEffect, useCallback } from 'react'
import { apiFetch } from '../api/client'
import DataTable from '../components/common/DataTable'
import StatusBadge from '../components/common/StatusBadge'
import ConfirmModal from '../components/common/ConfirmModal'
import KpiCard from '../components/common/KpiCard'

const sections = [
  { key: 'user', label: 'Users', icon: 'group', endpoint: 'users' },
  { key: 'cooperative', label: 'Cooperatives', icon: 'apartment', endpoint: 'cooperatives' },
  { key: 'farmer', label: 'Farmers', icon: 'agriculture', endpoint: '' },
  { key: 'delivery', label: 'Deliveries', icon: 'inventory_2', endpoint: '' },
]

export default function TrashManagement() {
  const [expanded, setExpanded] = useState(null)
  const [binSummary, setBinSummary] = useState(null)
  const [trashData, setTrashData] = useState({})
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [modalConfig, setModalConfig] = useState({ open: false })

  const fetchSummary = useCallback(async () => {
    setLoading(true)
    try {
      const res = await apiFetch('/api/admin/bin/')
      setBinSummary(res)
    } catch (e) {
      console.error('Failed to fetch bin summary', e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchSummary()
  }, [fetchSummary])

  const toggleSection = async (key) => {
    if (expanded === key) {
      setExpanded(null)
      return
    }
    setExpanded(key)
    if (!trashData[key]) {
      try {
        const res = await apiFetch(`/api/admin/bin/${key}s/`)
        setTrashData(prev => ({ ...prev, [key]: res }))
      } catch (e) {
        console.error(`Failed to fetch ${key}s`, e)
      }
    }
  }

  const handleRestore = async (item, type) => {
    setModalConfig({
      open: true,
      title: 'Restore Item',
      message: `Restore this ${type}? All associated data will be recovered.`,
      onConfirm: async () => {
        setActionLoading(true)
        setModalConfig({ open: false })
        try {
          await apiFetch(`/api/admin/bin/${type}s/${item.id}/restore/`, {
            method: 'POST',
            body: JSON.stringify({ confirm: true }),
          })
          setTrashData(prev => ({
            ...prev,
            [type]: Array.isArray(prev[type]) ? prev[type].filter(i => i.id !== item.id) : [],
          }))
          fetchSummary()
        } catch (e) {
          console.error('Restore failed', e)
        } finally {
          setActionLoading(false)
        }
      },
      destructive: false,
    })
  }

  const handlePurge = async (item, type) => {
    setModalConfig({
      open: true,
      title: 'Permanently Purge',
      message: `Permanently delete this ${type}? This action CANNOT be undone.`,
      confirmLabel: 'Permanently Delete',
      onConfirm: async () => {
        setActionLoading(true)
        setModalConfig({ open: false })
        try {
          await apiFetch(`/api/admin/bin/${type}s/${item.id}/purge/`, {
            method: 'POST',
            body: JSON.stringify({ confirm: true }),
          })
          setTrashData(prev => ({
            ...prev,
            [type]: Array.isArray(prev[type]) ? prev[type].filter(i => i.id !== item.id) : [],
          }))
          fetchSummary()
        } catch (e) {
          console.error('Purge failed', e)
        } finally {
          setActionLoading(false)
        }
      },
      destructive: true,
    })
  }

  const totalTrashed = binSummary
    ? Object.values(binSummary).reduce((s, v) => s + v, 0)
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
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
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
                {sections.map(({ key, label, icon, endpoint }) => {
                  const count = binSummary?.[key] ?? binSummary?.[key + 's'] ?? 0
                  return (
                    <div key={key}>
                      <button
                        onClick={() => toggleSection(key)}
                        className="w-full flex items-center justify-between px-6 py-4 hover:bg-surface-container transition-colors"
                      >
                        <div className="flex items-center gap-3">
                          <span className="material-symbols-outlined text-on-surface-variant">{icon}</span>
                          <span className="font-headline-sm text-headline-sm text-on-surface">{label}</span>
                          <span className="px-2 py-0.5 bg-surface-container-high rounded-full text-[11px] font-bold text-on-surface-variant">{count}</span>
                        </div>
                        <span className={`material-symbols-outlined text-on-surface-variant transition-transform ${expanded === key ? 'rotate-180' : ''}`}>
                          expand_more
                        </span>
                      </button>
                      {expanded === key && (
                        <div className="px-6 pb-4">
                          {trashData[key] && Array.isArray(trashData[key]) && trashData[key].length > 0 ? (
                            <div className="space-y-2">
                              {(trashData[key]).map((item) => (
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
                                      onClick={() => handleRestore(item, key)}
                                      disabled={actionLoading}
                                      className="px-3 py-1.5 text-[11px] font-bold bg-primary-container text-primary rounded-lg hover:bg-primary-fixed transition-colors disabled:opacity-50"
                                    >
                                      Restore
                                    </button>
                                    <button
                                      onClick={() => handlePurge(item, key)}
                                      disabled={actionLoading}
                                      className="px-3 py-1.5 text-[11px] font-bold bg-error-container text-error rounded-lg hover:bg-error/10 transition-colors disabled:opacity-50"
                                    >
                                      Purge
                                    </button>
                                  </div>
                                </div>
                              ))}
                            </div>
                          ) : (
                            <p className="text-label-md text-on-surface-variant py-4 text-center">Loading...</p>
                          )}
                        </div>
                      )}
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
            loading={actionLoading}
            destructive={modalConfig.destructive}
          />
        </>
      )}
    </div>
  )
}
