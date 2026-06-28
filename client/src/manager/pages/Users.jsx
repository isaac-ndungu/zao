import { useState, useEffect, useRef } from 'react'
import { useApi } from '../../admin/hooks/useApi'
import { apiFetch } from '../../admin/api/client'
import DataTable from '../../admin/components/common/DataTable'
import SlideOutPanel from '../../admin/components/common/SlideOutPanel'
import StatusBadge from '../../admin/components/common/StatusBadge'
import ConfirmModal from '../../admin/components/common/ConfirmModal'
import { useToast } from '../../admin/contexts/ToastContext'
import { TableSkeleton } from '../../admin/components/common/Skeleton'
import ErrorState from '../../shared/components/ErrorState'

export default function ManagerUsers() {
  const { showToast } = useToast()
  const [tab, setTab] = useState('all')
  const [showCreate, setShowCreate] = useState(false)
  const [createForm, setCreateForm] = useState({ email: '', phone_number: '', first_name: '', last_name: '', role: 'grader' })
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState(null)

  const { data, loading, error, refetch } = useApi('/api/users/?page_size=100')
  const allUsers = data?.results || data || []

  const staffUsers = allUsers.filter(u => u.role === 'grader' || u.role === 'accountant' || u.role === 'auditor')
  const filteredUsers = tab === 'all' ? staffUsers : staffUsers.filter(u => u.role === tab)

  const handleCreate = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      const res = await apiFetch('/api/users/', { method: 'POST', body: JSON.stringify(createForm) })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(Object.values(err).flat().join(', ') || err.detail || 'Failed to create user')
      }
      showToast({ type: 'success', message: `${createForm.first_name} ${createForm.last_name} added as ${createForm.role}. An email with login credentials has been sent.` })
      setShowCreate(false)
      setCreateForm({ email: '', phone_number: '', first_name: '', last_name: '', role: 'grader' })
      refetch()
    } catch (err) {
      showToast({ type: 'error', message: err.message })
    } finally {
      setSaving(false)
    }
  }

  const handleToggleActive = async (user) => {
    try {
      const res = await apiFetch(`/api/users/${user.id}/`, { method: 'PATCH', body: JSON.stringify({ is_active: !user.is_active }) })
      if (!res.ok) throw new Error('Failed to update user')
      showToast({ type: 'success', message: `${user.first_name} ${user.last_name} ${user.is_active ? 'deactivated' : 'activated'}.` })
      refetch()
    } catch (err) {
      showToast({ type: 'error', message: err.message })
    }
  }

  const handleDelete = async () => {
    if (!deleting) return
    try {
      const res = await apiFetch(`/api/users/${deleting.id}/`, { method: 'DELETE' })
      if (!res.ok) throw new Error('Failed to remove staff member')
      showToast({ type: 'success', message: `${deleting.first_name} ${deleting.last_name} removed from cooperative.` })
      setDeleting(null)
      refetch()
    } catch (err) {
      showToast({ type: 'error', message: err.message })
    }
  }

  const roleOptions = [
    { value: 'grader', label: 'Grader' },
    { value: 'accountant', label: 'Accountant' },
    { value: 'auditor', label: 'Auditor' },
  ]

  const columns = [
    { key: 'first_name', label: 'Name', sortable: true, render: (row) => `${row.first_name} ${row.last_name}` },
    { key: 'email', label: 'Email' },
    { key: 'phone_number', label: 'Phone' },
    { key: 'role', label: 'Role', render: (row) => <StatusBadge status={row.role} label={row.role} /> },
    { key: 'is_active', label: 'Status', render: (row) => <StatusBadge status={row.is_active ? 'active' : 'inactive'} label={row.is_active ? 'Active' : 'Inactive'} /> },
    { key: 'date_joined', label: 'Joined', render: (row) => row.date_joined ? new Date(row.date_joined).toLocaleDateString() : '-' },
    {
      key: 'actions', label: '', render: (row) => (
        <div className="flex gap-3">
          <button
            onClick={(e) => { e.stopPropagation(); handleToggleActive(row) }}
            className={`text-label-md hover:underline ${row.is_active ? 'text-error' : 'text-primary'}`}
          >
            {row.is_active ? 'Deactivate' : 'Activate'}
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); setDeleting(row) }}
            className="text-label-md text-on-surface-variant hover:text-error hover:underline"
          >
            Remove
          </button>
        </div>
      ),
    },
  ]

  return (
    <div className="max-w-5xl mx-auto">
      <header className="mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-3xl font-bold text-on-surface mb-1">Staff</h2>
          <p className="text-sm text-on-surface-variant">{staffUsers.length} staff members</p>
        </div>
        <button onClick={() => setShowCreate(true)} className="px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold hover:bg-primary/90 transition-colors flex items-center gap-2">
          <span className="material-symbols-outlined text-[18px]">person_add</span>Add Staff
        </button>
      </header>

      <div className="flex gap-2 mb-4 border-b border-outline-variant pb-2">
        {['all', 'grader', 'accountant', 'auditor'].map(t => (
          <button key={t} onClick={() => setTab(t)} className={`px-3 py-1.5 rounded-lg text-label-md font-bold transition-colors ${tab === t ? 'bg-primary text-white' : 'text-on-surface-variant hover:bg-surface-container'}`}>
            {t === 'all' ? 'All' : t.charAt(0).toUpperCase() + t.slice(1)}s
          </button>
        ))}
      </div>

      {loading ? (
        <TableSkeleton rows={8} cols={6} />
      ) : error ? (
        <ErrorState message={error} action={{ label: 'Retry', onClick: refetch }} />
      ) : filteredUsers.length === 0 ? (
        <div className="text-center py-16">
          <span className="material-symbols-outlined text-5xl text-on-surface-variant mb-3">group_off</span>
          <p className="text-on-surface-variant">No staff members found.</p>
          <button onClick={() => setShowCreate(true)} className="mt-4 text-primary text-label-md font-bold hover:underline">Add your first staff member</button>
        </div>
      ) : (
        <DataTable columns={columns} data={filteredUsers} />
      )}

      <SlideOutPanel open={showCreate} onClose={() => setShowCreate(false)} title="Add Staff Member" width="max-w-md">
        <form onSubmit={handleCreate} className="space-y-4">
          <div>
            <label className="block text-label-md text-on-surface-variant mb-1">First Name *</label>
            <input required value={createForm.first_name} onChange={(e) => setCreateForm(p => ({ ...p, first_name: e.target.value }))} className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container" />
          </div>
          <div>
            <label className="block text-label-md text-on-surface-variant mb-1">Last Name *</label>
            <input required value={createForm.last_name} onChange={(e) => setCreateForm(p => ({ ...p, last_name: e.target.value }))} className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container" />
          </div>
          <div>
            <label className="block text-label-md text-on-surface-variant mb-1">Email *</label>
            <input required type="email" value={createForm.email} onChange={(e) => setCreateForm(p => ({ ...p, email: e.target.value }))} className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container" />
          </div>
          <div>
            <label className="block text-label-md text-on-surface-variant mb-1">Phone *</label>
            <input required value={createForm.phone_number} onChange={(e) => setCreateForm(p => ({ ...p, phone_number: e.target.value }))} placeholder="0712345678" className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container" />
          </div>
          <div>
            <label className="block text-label-md text-on-surface-variant mb-1">Role *</label>
            <select required value={createForm.role} onChange={(e) => setCreateForm(p => ({ ...p, role: e.target.value }))} className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container">
              {roleOptions.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>
          <p className="text-xs text-on-surface-variant">An email with login credentials will be sent to the staff member.</p>
          <button type="submit" disabled={saving} className="w-full bg-primary text-on-primary py-2 rounded-lg font-bold disabled:opacity-50">
            {saving ? 'Adding...' : 'Add Staff Member'}
          </button>
        </form>
      </SlideOutPanel>

      <ConfirmModal
        open={!!deleting}
        onClose={() => setDeleting(null)}
        onConfirm={handleDelete}
        title="Remove Staff Member"
        message={deleting ? `Are you sure you want to remove ${deleting.first_name} ${deleting.last_name} from the cooperative? This action cannot be undone.` : ''}
        confirmLabel="Remove"
        confirmClassName="bg-error text-on-error"
      />
    </div>
  )
}
