import { useState, useMemo, useCallback } from 'react'
import { useApi } from '../hooks/useApi'
import { apiFetch } from '../api/client'
import KpiCard from '../components/common/KpiCard'
import FilterBar from '../components/common/FilterBar'
import DataTable from '../components/common/DataTable'
import Pagination from '../components/common/Pagination'
import StatusBadge from '../components/common/StatusBadge'
import SlideOutPanel from '../components/common/SlideOutPanel'
import ConfirmModal from '../components/common/ConfirmModal'

const roleOptions = [
  { value: 'admin', label: 'Admin' },
  { value: 'manager', label: 'Manager' },
  { value: 'accountant', label: 'Accountant' },
  { value: 'grader', label: 'Grader' },
  { value: 'farmer', label: 'Farmer' },
]

const roleBadgeMap = {
  admin: { status: 'locked', label: 'Admin' },
  manager: { status: 'completed', label: 'Manager' },
  accountant: { status: 'computing', label: 'Accountant' },
  grader: { status: 'draft', label: 'Grader' },
  farmer: { status: 'active', label: 'Farmer' },
}

export default function UserManagement() {
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [search, setSearch] = useState('')
  const [filters, setFilters] = useState({})
  const [sortField, setSortField] = useState('date_joined')
  const [sortOrder, setSortOrder] = useState('desc')
  const [selectedIds, setSelectedIds] = useState([])
  const [panelOpen, setPanelOpen] = useState(false)
  const [panelUser, setPanelUser] = useState(null)
  const [modalConfig, setModalConfig] = useState({ open: false })
  const [actionLoading, setActionLoading] = useState(false)
  const [inviteModal, setInviteModal] = useState(false)
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteLoading, setInviteLoading] = useState(false)

  const query = useMemo(() => {
    const params = new URLSearchParams()
    params.set('page', page)
    params.set('page_size', pageSize)
    if (search) params.set('search', search)
    if (filters.role) params.set('role', filters.role)
    if (filters.is_active) params.set('is_active', filters.is_active)
    if (sortField) params.set('ordering', sortOrder === 'desc' ? `-${sortField}` : sortField)
    return params.toString()
  }, [page, pageSize, search, filters, sortField, sortOrder])

  const { data, loading, error, refetch } = useApi(`/api/admin/users/?${query}`)

  const handleSort = useCallback((field) => {
    if (sortField === field) setSortOrder(o => o === 'asc' ? 'desc' : 'asc')
    else { setSortField(field); setSortOrder('asc') }
  }, [sortField])

  const handleView = (user) => {
    setPanelUser(user)
    setPanelOpen(true)
  }

  const execAction = async (url, opts = {}) => {
    setActionLoading(true)
    setModalConfig({ open: false })
    try {
      await apiFetch(url, { method: 'POST', ...opts })
      refetch()
    } catch (e) {
      console.error('Action failed', e)
    } finally {
      setActionLoading(false)
    }
  }

  const handleBulkAction = (action) => {
    if (selectedIds.length === 0) return
    const label = action === 'activate' ? 'Activate' : 'Deactivate'
    setModalConfig({
      open: true,
      title: `${label} Users`,
      message: `${label} ${selectedIds.length} selected users?`,
      onConfirm: () => execAction('/api/admin/users/bulk-action/', {
        body: JSON.stringify({ action, ids: selectedIds }),
        headers: { 'Content-Type': 'application/json' },
      }),
      destructive: action === 'deactivate',
    })
  }

  const handleUserAction = (user, action) => {
    const actionMap = {
      activate: { title: 'Activate User', message: `Activate ${user.email}?` },
      deactivate: { title: 'Deactivate User', message: `Deactivate ${user.email}? They will lose access.` },
      delete: { title: 'Delete User', message: `Soft-delete ${user.email}? This can be undone.` },
      restore: { title: 'Restore User', message: `Restore ${user.email}?` },
      'toggle-2fa': { title: 'Toggle 2FA', message: `Toggle 2FA for ${user.email}?` },
      'reset-password': { title: 'Reset Password', message: `Send password reset for ${user.email}?` },
    }
    const cfg = actionMap[action]
    if (!cfg) return
    setModalConfig({
      open: true,
      ...cfg,
      onConfirm: () => execAction(`/api/admin/users/${user.id}/${action}/`, {
        body: JSON.stringify({ confirm: true }),
        headers: { 'Content-Type': 'application/json' },
      }),
      destructive: ['deactivate', 'delete'].includes(action),
    })
  }

  const handleInvite = async (e) => {
    e.preventDefault()
    setInviteLoading(true)
    try {
      await apiFetch('/api/admin/auth/invite/', {
        method: 'POST',
        body: JSON.stringify({ email: inviteEmail }),
      })
      setInviteEmail('')
      setInviteModal(false)
      refetch()
    } catch (e) {
      console.error('Invite failed', e)
    } finally {
      setInviteLoading(false)
    }
  }

  const columns = useMemo(() => [
    { key: 'name', label: 'User', sortable: true, render: (r) => (
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-full bg-primary-fixed flex items-center justify-center text-primary font-bold text-xs">
          {r.first_name?.[0]}{r.last_name?.[0]}
        </div>
        <div>
          <p className="font-medium text-body-md">{r.first_name} {r.last_name}</p>
          <p className="text-label-md text-on-surface-variant">{r.email}</p>
        </div>
      </div>
    )},
    { key: 'phone_number', label: 'Phone', render: (r) => <span className="text-on-surface-variant">{r.phone_number || '-'}</span> },
    { key: 'role', label: 'Role', render: (r) => {
      const m = roleBadgeMap[r.role] || { status: 'draft', label: r.role }
      return <StatusBadge status={m.status} label={m.label} />
    }},
    { key: 'is_active', label: 'Status', render: (r) => <StatusBadge status={r.is_active ? 'active' : 'inactive'} label={r.is_active ? 'Active' : 'Inactive'} /> },
    { key: 'two_fa_enabled', label: '2FA', render: (r) => <StatusBadge status={r.two_fa_enabled ? 'true' : 'false'} label={r.two_fa_enabled ? 'On' : 'Off'} /> },
    { key: 'date_joined', label: 'Joined', sortable: true, render: (r) => r.date_joined ? new Date(r.date_joined).toLocaleDateString() : '-' },
  ], [])

  if (error) {
    return <div className="bg-error-container text-error p-4 rounded-xl">Failed to load users: {error}</div>
  }

  return (
    <div>
      <header className="mb-6">
        <div className="flex items-center justify-between mb-1">
          <h2 className="font-headline-lg text-display-md text-primary">User Management</h2>
          <button onClick={() => setInviteModal(true)} className="flex items-center gap-2 px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold hover:bg-primary/90 transition-colors">
            <span className="material-symbols-outlined text-[16px]">person_add</span>
            Invite User
          </button>
        </div>
        <p className="text-on-surface-variant font-body-md">Manage admin users, managers, and system access.</p>
      </header>

      <FilterBar
        search={search}
        onSearchChange={setSearch}
        placeholder="Search by name, email, phone..."
        filters={[
          { key: 'role', label: 'Role', options: roleOptions },
          { key: 'is_active', label: 'Status', options: [{ value: 'true', label: 'Active' }, { value: 'false', label: 'Inactive' }] },
        ]}
        filterValues={filters}
        onFilterChange={setFilters}
        onClear={() => { setSearch(''); setFilters({}); setPage(1) }}
      />

      {selectedIds.length > 0 && (
        <div className="flex items-center gap-3 mb-4 px-4 py-2 bg-primary-container/50 border border-primary-container rounded-lg">
          <span className="text-label-md font-medium text-on-primary-container">{selectedIds.length} selected</span>
          <button onClick={() => handleBulkAction('activate')} className="px-3 py-1 text-label-md font-bold bg-primary text-on-primary rounded-lg hover:bg-primary/90 transition-colors">Activate</button>
          <button onClick={() => handleBulkAction('deactivate')} className="px-3 py-1 text-label-md font-bold bg-error text-on-error rounded-lg hover:bg-error/90 transition-colors">Deactivate</button>
          <button onClick={() => setSelectedIds([])} className="text-label-md text-on-surface-variant hover:text-on-surface ml-auto">Clear selection</button>
        </div>
      )}

      <DataTable
        columns={columns}
        data={data?.results || []}
        selectedIds={selectedIds}
        onSelectionChange={setSelectedIds}
        sortField={sortField}
        sortOrder={sortOrder}
        onSort={handleSort}
        loading={loading}
        emptyMessage="No users found."
        rowActions={(user) => (
          <div className="flex gap-0.5">
            <button onClick={() => handleView(user)} className="p-1.5 rounded-lg hover:bg-surface-container-high text-on-surface-variant hover:text-primary transition-colors" title="View">
              <span className="material-symbols-outlined text-[18px]">visibility</span>
            </button>
            <div className="relative group">
              <button className="p-1.5 rounded-lg hover:bg-surface-container-high text-on-surface-variant transition-colors" title="More">
                <span className="material-symbols-outlined text-[18px]">more_vert</span>
              </button>
              <div className="absolute right-0 top-full mt-1 w-44 bg-surface-container-lowest border border-outline-variant rounded-lg shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-50">
                {user.is_active && (
                  <button onClick={() => handleUserAction(user, 'deactivate')} className="flex items-center gap-2 w-full px-3 py-2 text-label-md text-on-surface hover:bg-surface-container-high transition-colors">
                    <span className="material-symbols-outlined text-[16px]">block</span>Deactivate
                  </button>
                )}
                {!user.is_active && (
                  <button onClick={() => handleUserAction(user, 'activate')} className="flex items-center gap-2 w-full px-3 py-2 text-label-md text-on-surface hover:bg-surface-container-high transition-colors">
                    <span className="material-symbols-outlined text-[16px]">check_circle</span>Activate
                  </button>
                )}
                <button onClick={() => handleUserAction(user, 'toggle-2fa')} className="flex items-center gap-2 w-full px-3 py-2 text-label-md text-on-surface hover:bg-surface-container-high transition-colors">
                  <span className="material-symbols-outlined text-[16px]">security</span>Toggle 2FA
                </button>
                <button onClick={() => handleUserAction(user, 'reset-password')} className="flex items-center gap-2 w-full px-3 py-2 text-label-md text-on-surface hover:bg-surface-container-high transition-colors">
                  <span className="material-symbols-outlined text-[16px]">key</span>Reset Password
                </button>
                <div className="border-t border-outline-variant my-1" />
                <button onClick={() => handleUserAction(user, 'delete')} className="flex items-center gap-2 w-full px-3 py-2 text-label-md text-error hover:bg-error-container transition-colors">
                  <span className="material-symbols-outlined text-[16px]">delete</span>Delete
                </button>
              </div>
            </div>
          </div>
        )}
      />

      <div className="mt-2">
        <Pagination page={page} pageSize={pageSize} total={data?.count || 0} onPageChange={setPage} onPageSizeChange={setPageSize} />
      </div>

      <SlideOutPanel open={panelOpen} onClose={() => { setPanelOpen(false); setPanelUser(null) }} title="User Details">
        {panelUser && (
          <div className="space-y-4">
            <div className="flex items-center gap-4 mb-4">
              <div className="w-14 h-14 rounded-full bg-primary-fixed flex items-center justify-center text-primary font-bold text-lg">
                {panelUser.first_name?.[0]}{panelUser.last_name?.[0]}
              </div>
              <div>
                <h4 className="font-headline-sm text-headline-sm text-on-surface">{panelUser.first_name} {panelUser.last_name}</h4>
                <StatusBadge status={panelUser.is_active ? 'active' : 'inactive'} label={panelUser.is_active ? 'Active' : 'Inactive'} />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="p-3 bg-surface-container rounded-lg">
                <p className="text-[10px] uppercase font-bold text-on-surface-variant">Email</p>
                <p className="font-body-md text-on-surface">{panelUser.email || '-'}</p>
              </div>
              <div className="p-3 bg-surface-container rounded-lg">
                <p className="text-[10px] uppercase font-bold text-on-surface-variant">Phone</p>
                <p className="font-body-md text-on-surface">{panelUser.phone_number || '-'}</p>
              </div>
              <div className="p-3 bg-surface-container rounded-lg">
                <p className="text-[10px] uppercase font-bold text-on-surface-variant">Role</p>
                <p className="font-body-md text-on-surface">{panelUser.role}</p>
              </div>
              <div className="p-3 bg-surface-container rounded-lg">
                <p className="text-[10px] uppercase font-bold text-on-surface-variant">2FA</p>
                <p className="font-body-md text-on-surface">{panelUser.two_fa_enabled ? 'Enabled' : 'Disabled'}</p>
              </div>
              <div className="p-3 bg-surface-container rounded-lg">
                <p className="text-[10px] uppercase font-bold text-on-surface-variant">Joined</p>
                <p className="font-body-md text-on-surface">{panelUser.date_joined ? new Date(panelUser.date_joined).toLocaleDateString() : '-'}</p>
              </div>
              <div className="p-3 bg-surface-container rounded-lg">
                <p className="text-[10px] uppercase font-bold text-on-surface-variant">Last Login</p>
                <p className="font-body-md text-on-surface">{panelUser.last_login ? new Date(panelUser.last_login).toLocaleDateString() : 'Never'}</p>
              </div>
            </div>
            <div className="pt-2 flex gap-2">
              <button onClick={() => handleUserAction(panelUser, panelUser.is_active ? 'deactivate' : 'activate')} className={`flex-1 px-4 py-2 rounded-lg text-label-md font-bold transition-colors ${panelUser.is_active ? 'border border-error text-error hover:bg-error-container' : 'bg-primary text-on-primary hover:bg-primary/90'}`}>
                {panelUser.is_active ? 'Deactivate' : 'Activate'}
              </button>
              <button onClick={() => handleUserAction(panelUser, 'reset-password')} className="flex-1 px-4 py-2 border border-outline-variant text-on-surface-variant rounded-lg text-label-md font-bold hover:bg-surface-container transition-colors">
                Reset Password
              </button>
            </div>
          </div>
        )}
      </SlideOutPanel>

      <ConfirmModal
        open={modalConfig.open}
        title={modalConfig.title}
        message={modalConfig.message}
        onConfirm={modalConfig.onConfirm}
        onCancel={() => setModalConfig({ open: false })}
        loading={actionLoading}
        destructive={modalConfig.destructive}
      />

      {inviteModal && (
        <div className="fixed inset-0 z-[65] flex items-center justify-center">
          <div className="fixed inset-0 bg-black/30" onClick={() => setInviteModal(false)} />
          <div className="relative bg-surface-container-lowest border border-outline-variant rounded-xl p-6 max-w-sm w-full mx-4 shadow-xl">
            <h3 className="font-headline-sm text-headline-sm text-on-surface mb-2">Invite User</h3>
            <p className="text-body-md text-on-surface-variant mb-4">Send an invitation to join the platform.</p>
            <form onSubmit={handleInvite}>
              <div className="mb-4">
                <label className="block text-label-md font-bold text-on-surface-variant mb-1">Email Address</label>
                <input
                  type="email"
                  required
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface"
                  placeholder="user@example.com"
                />
              </div>
              <div className="flex justify-end gap-3">
                <button type="button" onClick={() => setInviteModal(false)} className="px-4 py-2 rounded-lg text-label-md font-bold text-on-surface-variant bg-surface-container-high hover:bg-surface-container-highest transition-colors">
                  Cancel
                </button>
                <button type="submit" disabled={inviteLoading} className="px-4 py-2 rounded-lg text-label-md font-bold text-white bg-primary hover:bg-primary/90 transition-colors disabled:opacity-50">
                  {inviteLoading ? 'Sending...' : 'Send Invite'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
