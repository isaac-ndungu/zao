import { useState, useEffect, useCallback } from 'react'
import { useApi } from '../../admin/hooks/useApi'
import { apiFetch } from '../../admin/api/client'
import DataTable from '../../admin/components/common/DataTable'
import SlideOutPanel from '../../admin/components/common/SlideOutPanel'
import StatusBadge from '../../admin/components/common/StatusBadge'
import ConfirmModal from '../../admin/components/common/ConfirmModal'
import { useToast } from '../../admin/contexts/ToastContext'
import { TableSkeleton } from '../../admin/components/common/Skeleton'
import ErrorState from '../../shared/components/ErrorState'
import { useFormAction, formDataToObject, SubmitButton } from '../../shared/hooks/useFormAction'

export default function ManagerUsers() {
  const { showToast } = useToast()
  const [tab, setTab] = useState('all')
  const [showCreate, setShowCreate] = useState(false)
  const [deleting, setDeleting] = useState(null)
  const [usersData, setUsersData] = useState(null)
  const [usersLoading, setUsersLoading] = useState(false)
  const [usersError, setUsersError] = useState(null)

  const { data: coop } = useApi('/api/cooperatives/me/')

  const fetchUsers = useCallback(() => {
    if (!coop?.id) return
    setUsersLoading(true)
    setUsersError(null)
    apiFetch(`/api/users/?coop_id=${coop.id}&page_size=100`)
      .then(res => {
        if (!res.ok) throw new Error('Failed to fetch users')
        return res.json()
      })
      .then(data => { setUsersData(data); setUsersLoading(false) })
      .catch(err => { setUsersError(err.message); setUsersLoading(false) })
  }, [coop?.id])

  useEffect(() => {
    fetchUsers()
  }, [fetchUsers])

  const loading = usersLoading || !usersData
  const error = usersError
  const allUsers = usersData?.results || usersData || []

  const staffUsers = allUsers.filter(u => u.role === 'grader' || u.role === 'accountant' || u.role === 'auditor')
  const filteredUsers = tab === 'all' ? staffUsers : staffUsers.filter(u => u.role === tab)

  const [, createAction] = useFormAction(async (_prev, formData) => {
    const body = formDataToObject(formData)
    const res = await apiFetch('/api/users/', { method: 'POST', body: JSON.stringify(body) })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(Object.values(err).flat().join(', ') || err.detail || 'Failed to create user')
    }
    showToast({ type: 'success', message: `${body.first_name} ${body.last_name} added as ${body.role}. An email with login credentials has been sent.` })
    setShowCreate(false)
    fetchUsers()
  }, {})

  const handleToggleActive = async (user) => {
    try {
      const res = await apiFetch(`/api/users/${user.id}/`, { method: 'PATCH', body: JSON.stringify({ is_active: !user.is_active }) })
      if (!res.ok) throw new Error('Failed to update user')
      showToast({ type: 'success', message: `${user.first_name} ${user.last_name} ${user.is_active ? 'deactivated' : 'activated'}.` })
      fetchUsers()
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
      fetchUsers()
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
    { key: 'first_name', label: 'Name', sortable: true, render: (v, row) => `${row.first_name} ${row.last_name}` },
    { key: 'email', label: 'Email' },
    { key: 'phone_number', label: 'Phone' },
    { key: 'role', label: 'Role', render: (v, row) => <StatusBadge status={row.role} label={row.role} /> },
    { key: 'is_active', label: 'Status', render: (v, row) => <StatusBadge status={row.is_active ? 'active' : 'inactive'} label={row.is_active ? 'Active' : 'Inactive'} /> },
    { key: 'date_joined', label: 'Joined', render: (v, row) => row.date_joined ? new Date(row.date_joined).toLocaleDateString() : '-' },
    {
      key: 'actions', label: '', render: (v, row) => (
        <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-150">
          <button
            onClick={(e) => { e.stopPropagation(); handleToggleActive(row) }}
            className={`${row.is_active ? 'text-error hover:text-error/80' : 'text-primary hover:text-primary/80'}`}
            aria-label={row.is_active ? `Deactivate ${row.first_name} ${row.last_name}` : `Activate ${row.first_name} ${row.last_name}`}
          >
            <span className="material-symbols-outlined text-[18px]" aria-hidden="true">{row.is_active ? 'toggle_off' : 'toggle_on'}</span>
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); setDeleting(row) }}
            className="text-on-surface-variant hover:text-error"
            aria-label={`Remove ${row.first_name} ${row.last_name}`}
          >
            <span className="material-symbols-outlined text-[18px]" aria-hidden="true">person_remove</span>
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
          <span className="material-symbols-outlined text-[18px]" aria-hidden="true">person_add</span>Add Staff
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
        <ErrorState message={error} action={{ label: 'Retry', onClick: fetchUsers }} />
      ) : filteredUsers.length === 0 ? (
        <div className="text-center py-16">
          <span className="material-symbols-outlined text-5xl text-on-surface-variant mb-3" aria-hidden="true">group_off</span>
          <p className="text-on-surface-variant">No staff members found.</p>
          <button onClick={() => setShowCreate(true)} className="mt-4 text-primary text-label-md font-bold hover:underline">Add your first staff member</button>
        </div>
      ) : (
        <DataTable columns={columns} data={filteredUsers} />
      )}

      <SlideOutPanel open={showCreate} onClose={() => setShowCreate(false)} title="Add Staff Member" width="max-w-md">
        <form action={createAction} className="space-y-4">
          <div>
            <label htmlFor="create-first_name" className="block text-label-md text-on-surface-variant mb-1">First Name *</label>
            <input id="create-first_name" name="first_name" required className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container" />
          </div>
          <div>
            <label htmlFor="create-last_name" className="block text-label-md text-on-surface-variant mb-1">Last Name *</label>
            <input id="create-last_name" name="last_name" required className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container" />
          </div>
          <div>
            <label htmlFor="create-email" className="block text-label-md text-on-surface-variant mb-1">Email *</label>
            <input id="create-email" name="email" required type="email" className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container" />
          </div>
          <div>
            <label htmlFor="create-phone_number" className="block text-label-md text-on-surface-variant mb-1">Phone *</label>
            <input id="create-phone_number" name="phone_number" required placeholder="0712345678" className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container" />
          </div>
          <div>
            <label htmlFor="create-role" className="block text-label-md text-on-surface-variant mb-1">Role *</label>
            <select id="create-role" name="role" required defaultValue="grader" className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container">
              {roleOptions.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>
          <p className="text-xs text-on-surface-variant">An email with login credentials will be sent to the staff member.</p>
          <SubmitButton className="w-full bg-primary text-on-primary py-2 rounded-lg font-bold">
            Add Staff Member
          </SubmitButton>
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
