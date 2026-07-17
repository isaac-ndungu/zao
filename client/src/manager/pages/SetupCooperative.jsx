import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApi } from '../../admin/hooks/useApi'
import { apiFetch } from '../../admin/api/client'
import { useToast } from '../../admin/contexts/ToastContext'
import { useFormAction, formDataToObject } from '../../shared/hooks/useFormAction'
import CooperativeForm from '../components/CooperativeForm'

export default function SetupCooperative() {
  const navigate = useNavigate()
  const { showToast } = useToast()
  const { data: coop, loading: coopLoading } = useApi('/api/cooperatives/me/')

  const { formAction: coopAction } = useFormAction(async (_prev, formData) => {
    const body = {
      ...formDataToObject(formData),
      levy_percentage: parseFloat(formData.get('levy_percentage')),
      monthly_fee: parseFloat(formData.get('monthly_fee')),
    }
    const res = await apiFetch('/api/cooperatives/', { method: 'POST', body: JSON.stringify(body) })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || Object.values(err).flat().join(', ') || 'Failed to create cooperative')
    }
    showToast({ type: 'success', message: 'Cooperative created successfully!' })
    navigate('/manager/dashboard', { replace: true })
  }, {})

  useEffect(() => {
    if (!coopLoading && coop) {
      navigate('/manager/dashboard', { replace: true })
    }
  }, [coop, coopLoading, navigate])

  if (coopLoading) {
    return (
      <div className="max-w-2xl mx-auto py-12">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-surface-container rounded w-1/3" />
          <div className="h-4 bg-surface-container rounded w-2/3" />
          <div className="h-64 bg-surface-container rounded" />
        </div>
      </div>
    )
  }

  if (coop) return null

  return (
    <div className="max-w-2xl mx-auto py-8">
      <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6">
        <div className="mb-6">
          <span className="material-symbols-outlined text-4xl text-primary mb-2" aria-hidden="true">domain</span>
          <h2 className="text-2xl font-bold text-on-surface">Create Your Cooperative</h2>
          <p className="text-on-surface-variant text-sm mt-1">
            Set up your cooperative to start managing farmers, deliveries, and payments.
          </p>
        </div>
        <CooperativeForm
          formAction={coopAction}
          submitLabel="Create Cooperative"
        />
      </div>
    </div>
  )
}
