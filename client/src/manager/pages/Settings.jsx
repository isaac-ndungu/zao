import { useState } from 'react'
import { useApi } from '../../admin/hooks/useApi'
import { apiFetch } from '../../admin/api/client'
import { KpiSkeleton } from '../../admin/components/common/Skeleton'
import { useToast } from '../../admin/contexts/ToastContext'
import ErrorState from '../../shared/components/ErrorState'

export default function Settings() {
  const { data: coop, loading, error, refetch } = useApi('/api/cooperatives/me/')
  const [editing, setEditing] = useState(null)
  const [formData, setFormData] = useState({})
  const [saving, setSaving] = useState(false)
  const { showToast } = useToast()

  if (loading) return <div className="max-w-2xl mx-auto"><KpiSkeleton count={4} /></div>
  if (error) return <ErrorState message={error} action={{ label: 'Retry', onClick: refetch }} />

  const startEdit = (field) => {
    setEditing(field)
    setFormData({ [field]: coop?.[field] || '' })
  }

  const handleSave = async (field) => {
    setSaving(true)
    try {
      const res = await apiFetch(`/api/cooperatives/${coop.id}/`, { method: 'PATCH', body: JSON.stringify({ [field]: formData[field] }) })
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Failed to update') }
      showToast({ type: 'success', message: `${field.replace(/_/g, ' ')} updated.` })
      setEditing(null); refetch()
    } catch (err) { showToast({ type: 'error', message: err.message }) }
    finally { setSaving(false) }
  }

  const readOnlyFields = ['name', 'registration_number', 'county', 'sub_county', 'ward', 'location', 'email', 'phone_number', 'member_count']
  const editableFields = [
    { key: 'milk_levy_per_litre', label: 'Milk Levy per Litre (KES)', type: 'number', step: '0.01' },
    { key: 'coffee_levy_per_kg', label: 'Coffee Levy per kg (KES)', type: 'number', step: '0.01' },
    { key: 'honey_levy_per_kg', label: 'Honey Levy per kg (KES)', type: 'number', step: '0.01' },
    { key: 'membership_fee', label: 'Membership Fee (KES)', type: 'number', step: '0.01' },
    { key: 'transport_fee_per_km', label: 'Transport Fee per km (KES)', type: 'number', step: '0.01' },
  ]

  return (
    <div className="max-w-2xl mx-auto">
      <header className="mb-8">
        <h2 className="font-headline-lg text-display-md text-primary mb-1">Settings</h2>
        <p className="text-on-surface-variant font-body-md">Cooperative profile and configuration</p>
      </header>

      <section className="mb-8">
        <h3 className="font-headline-sm text-headline-sm text-on-surface mb-4">Cooperative Information</h3>
        <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6">
          <div className="grid grid-cols-2 gap-6">
            {readOnlyFields.map(f => (
              <div key={f}>
                <p className="text-label-md text-on-surface-variant capitalize mb-1">{f.replace(/_/g, ' ')}</p>
                <p className="text-body-md text-on-surface font-medium">{coop ? String(coop[f] ?? '-') : '-'}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section>
        <h3 className="font-headline-sm text-headline-sm text-on-surface mb-4">Fees & Levies</h3>
        <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 space-y-4">
          {editableFields.map(({ key, label, type, step }) => (
            <div key={key} className="flex items-center justify-between py-3 border-b border-outline-variant/50 last:border-0">
              <div>
                <p className="text-body-md text-on-surface font-medium">{label}</p>
                <p className="text-label-md text-on-surface-variant">
                  Current: {coop ? `KES ${Number(coop[key] || 0).toLocaleString()}` : '-'}
                </p>
              </div>
              {editing === key ? (
                <div className="flex items-center gap-2">
                  <input
                    type={type}
                    step={step}
                    min="0"
                    value={formData[key] || ''}
                    onChange={(e) => setFormData(p => ({ ...p, [key]: e.target.value }))}
                    className="w-32 px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container text-right"
                  />
                  <button onClick={() => handleSave(key)} disabled={saving} className="px-3 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold">{saving ? '...' : 'Save'}</button>
                  <button onClick={() => setEditing(null)} className="px-3 py-2 border border-outline-variant rounded-lg text-label-md font-bold">Cancel</button>
                </div>
              ) : (
                <button onClick={() => startEdit(key)} className="px-3 py-2 border border-outline-variant rounded-lg text-label-md font-bold text-primary hover:bg-surface-container-high transition-colors">Edit</button>
              )}
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
