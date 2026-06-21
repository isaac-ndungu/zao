import { useState, useMemo, useCallback, useRef, useEffect } from 'react'
import { useApi } from '../hooks/useApi'
import { apiFetch, exportCsv, setAccessToken } from '../api/client'
import FilterBar from '../components/common/FilterBar'
import DataTable from '../components/common/DataTable'
import Pagination from '../components/common/Pagination'
import StatusBadge from '../components/common/StatusBadge'
import SlideOutPanel from '../components/common/SlideOutPanel'
import ConfirmModal from '../components/common/ConfirmModal'
import { useToast } from '../contexts/ToastContext'
import { TableSkeleton } from '../components/common/Skeleton'

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

import { useLocation } from 'react-router-dom'

export default function UserManagement() {
  const { showToast } = useToast()
  const location = useLocation()
  const [tab, setTab] = useState('users')
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
  const [inviteModal, setInviteModal] = useState(location.state?.openModal === true)
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteLoading, setInviteLoading] = useState(false)
  const [superuserModal, setSuperuserModal] = useState(false)
  const [suForm, setSuForm] = useState({ email: '', first_name: '', last_name: '', phone_number: '', password: '' })
  const [suLoading, setSuLoading] = useState(false)
  const [openDropdownId, setOpenDropdownId] = useState(null)
  const dropdownRef = useRef(null)

  const [invitePage, setInvitePage] = useState(1)
  const [inviteFilters, setInviteFilters] = useState({})

  useEffect(() => {
    const handler = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setOpenDropdownId(null)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

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

  const inviteQuery = useMemo(() => {
    const params = new URLSearchParams()
    params.set('page', invitePage)
    params.set('page_size', 20)
    if (inviteFilters.status) params.set('status', inviteFilters.status)
    return params.toString()
  }, [invitePage, inviteFilters])
  const { data: inviteData, loading: inviteListLoading, refetch: refetchInvites } = useApi(`/api/admin/auth/invites/?${inviteQuery}`)

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
    try {
      const res = await apiFetch(url, { method: 'POST', ...opts })
      if (!res.ok) throw new Error(await res.text())
      const msg = url.includes('activate') ? 'activated' : url.includes('deactivate') ? 'deactivated' : url.includes('delete') ? 'soft-deleted' : url.includes('restore') ? 'restored' : url.includes('toggle') ? '2FA toggled' : url.includes('reset') ? 'password reset' : url.includes('logout') ? 'logged out' : url.includes('impersonate') ? 'impersonated' : 'action completed'
      showToast({ type: 'success', message: `User ${msg}.` })
      refetch()
      const result = await res.json().catch(() => ({}))
      if (panelUser && typeof result === 'object') {
        const { detail, message, error, status, ...updates } = result
        const safeUpdates = Object.fromEntries(
          Object.entries(updates).filter(([, v]) => v !== null && typeof v !== 'object')
        )
        if (Object.keys(safeUpdates).length > 0) {
          setPanelUser(prev => ({ ...prev, ...safeUpdates }))
        }
      }
      setModalConfig({ open: false })
    } catch (e) {
      showToast({ type: 'error', message: `Action failed: ${e.message}` })
    } finally {
      setActionLoading(false)
    }
  }

  const handleBulkAction = async (action) => {
    if (selectedIds.length === 0) return
    setModalConfig({ open: false })
    setActionLoading(true)
    try {
      const res = await apiFetch('/api/admin/users/bulk-action/', {
        method: 'POST',
        body: JSON.stringify({ action, ids: selectedIds }),
      })
      if (!res.ok) throw new Error(await res.text())
      showToast({ type: 'success', message: `Bulk ${action} completed for ${selectedIds.length} users.` })
      setSelectedIds([])
      refetch()
    } catch (e) {
      showToast({ type: 'error', message: `Bulk action failed: ${e.message}` })
    } finally {
      setActionLoading(false)
    }
  }

  const handleUserAction = (user, action) => {
    const actionMap = {
      activate: { title: 'Activate User', message: `Activate ${user.email}?`, destructive: false },
      deactivate: { title: 'Deactivate User', message: `Deactivate ${user.email}? They will lose access.`, destructive: true },
      delete: { title: 'Delete User', message: `Soft-delete ${user.email}? This can be undone.`, destructive: true },
      restore: { title: 'Restore User', message: `Restore ${user.email}?`, destructive: false },
      'toggle-2fa': { title: 'Toggle 2FA', message: `Toggle 2FA for ${user.email}?`, destructive: false },
      'reset-password': { title: 'Reset Password', message: `Send password reset for ${user.email}?`, destructive: false },
      'force-logout': { title: 'Force Logout', message: `Force logout ${user.email}? All sessions will be terminated.`, destructive: false },
    }
    const cfg = actionMap[action]
    if (!cfg) return
    setOpenDropdownId(null)
    setModalConfig({
      open: true,
      ...cfg,
      onConfirm: () => execAction(`/api/admin/users/${user.id}/${action}/`, {
        body: JSON.stringify({ confirm: action === 'delete' }),
        headers: { 'Content-Type': 'application/json' },
      }),
    })
  }

  const handleImpersonate = async (user) => {
    setOpenDropdownId(null)
    setActionLoading(true)
    try {
      const res = await apiFetch(`/api/admin/impersonate/${user.id}/`, { method: 'POST' })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      setAccessToken(data.access_token)
      sessionStorage.setItem('impersonation', JSON.stringify({
        access_token: data.access_token,
        expires_at: Date.now() + (data.expires_in || 900) * 1000,
        user_id: data.user_id,
        role: data.role,
        cooperative_id: data.cooperative_id,
      }))
      showToast({ type: 'success', message: `Impersonating ${user.email}. Redirecting...` })
      setTimeout(() => window.location.href = '/', 1000)
    } catch (e) {
      showToast({ type: 'error', message: `Impersonation failed: ${e.message}` })
    } finally {
      setActionLoading(false)
    }
  }

  const handleInvite = async (e) => {
    e.preventDefault()
    setInviteLoading(true)
    try {
      const res = await apiFetch('/api/admin/auth/invite/', {
        method: 'POST',
        body: JSON.stringify({ email: inviteEmail }),
      })
      if (!res.ok) throw new Error(await res.text())
      showToast({ type: 'success', message: `Invite sent to ${inviteEmail}.` })
      setInviteEmail('')
      setInviteModal(false)
      refetch()
    } catch (e) {
      showToast({ type: 'error', message: `Invite failed: ${e.message}` })
    } finally {
      setInviteLoading(false)
    }
  }

  const handleCreateSuperuser = async (e) => {
    e.preventDefault()
    setSuLoading(true)
    try {
      const res = await apiFetch('/api/admin/users/create-superuser/', {
        method: 'POST',
        body: JSON.stringify(suForm),
      })
      if (!res.ok) throw new Error(await res.text())
      showToast({ type: 'success', message: `Superuser ${suForm.email} created.` })
      setSuForm({ email: '', first_name: '', last_name: '', phone_number: '', password: '' })
      setSuperuserModal(false)
      refetch()
    } catch (e) {
      showToast({ type: 'error', message: `Creation failed: ${e.message}` })
    } finally {
      setSuLoading(false)
    }
  }

  const toggleDropdown = (id) => {
    setOpenDropdownId(openDropdownId === id ? null : id)
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

  const handleRevokeInvite = async (invite) => {
    setActionLoading(true)
    try {
      const res = await apiFetch(`/api/admin/auth/invite/${invite.id}/revoke/`, { method: 'POST', body: JSON.stringify({ confirm: true }), headers: { 'Content-Type': 'application/json' } })
      if (!res.ok) throw new Error(await res.text())
      showToast({ type: 'success', message: `Invite for ${invite.email} revoked.` })
      refetchInvites()
    } catch (e) {
      showToast({ type: 'error', message: `Revoke failed: ${e.message}` })
    } finally {
      setActionLoading(false)
    }
  }

  const handleResendInvite = async (invite) => {
    setActionLoading(true)
    try {
      const res = await apiFetch(`/api/admin/auth/invite/${invite.id}/resend/`, { method: 'POST' })
      if (!res.ok) throw new Error(await res.text())
      showToast({ type: 'success', message: `Invite resent to ${invite.email}.` })
    } catch (e) {
      showToast({ type: 'error', message: `Resend failed: ${e.message}` })
    } finally {
      setActionLoading(false)
    }
  }

  if (error) {
    return <div className="bg-error-container text-error p-4 rounded-xl">Failed to load users: {error}</div>
  }

  return (
    <div ref={dropdownRef}>
      <header className="mb-6">
        <div className="flex items-center justify-between mb-1">
          <h2 className="font-headline-lg text-display-md text-primary">User Management</h2>
          <div className="flex gap-2">
            {tab === 'users' && (
              <>
                <button onClick={() => setSuperuserModal(true)} className="flex items-center gap-2 px-3 py-2 border border-outline-variant text-on-surface-variant rounded-lg text-label-md font-bold hover:bg-surface-container transition-colors">
                  <span className="material-symbols-outlined text-[16px]">admin_panel_settings</span>
                  <span className="hidden sm:inline">Create Superuser</span>
                </button>
                <button onClick={() => setInviteModal(true)} className="flex items-center gap-2 px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold hover:bg-primary/90 transition-colors">
                  <span className="material-symbols-outlined text-[16px]">person_add</span>
                  Invite User
                </button>
              </>
            )}
          </div>
        </div>
        <p className="text-on-surface-variant font-body-md">Manage admin users, managers, and system access.</p>
        <div className="flex gap-1 mt-4 border-b border-outline-variant">
          <button onClick={() => setTab('users')} className={`px-4 py-2 text-label-md font-bold border-b-2 transition-colors ${tab === 'users' ? 'border-primary text-primary' : 'border-transparent text-on-surface-variant hover:text-on-surface'}`}>Users</button>
          <button onClick={() => setTab('invites')} className={`px-4 py-2 text-label-md font-bold border-b-2 transition-colors ${tab === 'invites' ? 'border-primary text-primary' : 'border-transparent text-on-surface-variant hover:text-on-surface'}`}>Invites</button>
        </div>
      </header>

      {tab === 'users' ? (
        <>
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
            onExport={() => { const p = new URLSearchParams(); if (search) p.set('search', search); if (filters.role) p.set('role', filters.role); if (filters.is_active) p.set('is_active', filters.is_active); p.set('export', 'csv'); exportCsv(`/api/admin/users/?${p}`) }}
          />

          {selectedIds.length > 0 && (
            <div className="flex items-center gap-3 mb-4 px-4 py-2 bg-primary-container/50 border border-primary-container rounded-lg">
              <span className="text-label-md font-medium text-on-primary-container">{selectedIds.length} selected</span>
              <button onClick={() => handleBulkAction('activate')} className="px-3 py-1 text-label-md font-bold bg-primary text-on-primary rounded-lg hover:bg-primary/90 transition-colors">Activate</button>
              <button onClick={() => handleBulkAction('deactivate')} className="px-3 py-1 text-label-md font-bold bg-error text-on-error rounded-lg hover:bg-error/90 transition-colors">Deactivate</button>
              <button onClick={() => setSelectedIds([])} className="text-label-md text-on-surface-variant hover:text-on-surface ml-auto">Clear selection</button>
            </div>
          )}

          {loading ? <TableSkeleton /> : (
            <DataTable
              columns={columns}
              data={data?.results || []}
              selectedIds={selectedIds}
              onSelectionChange={setSelectedIds}
              sortField={sortField}
              sortOrder={sortOrder}
              onSort={handleSort}
              loading={false}
              emptyMessage="No users found."
              rowActions={(user) => (
                <div className="relative">
                  <button
                    onClick={() => toggleDropdown(user.id)}
                    className="p-1.5 rounded-lg hover:bg-surface-container-high text-on-surface-variant transition-colors"
                    aria-label="User actions"
                    aria-haspopup="true"
                    aria-expanded={openDropdownId === user.id}
                  >
                    <span className="material-symbols-outlined text-[18px]">more_vert</span>
                  </button>
                  {openDropdownId === user.id && (
                    <div
                      className="absolute right-0 top-full mt-1 w-44 bg-surface-container-lowest border border-outline-variant rounded-lg shadow-lg z-50 py-1"
                      role="menu"
                    >
                      <button onClick={() => handleView(user)} role="menuitem" className="flex items-center gap-2 w-full px-3 py-2 text-label-md text-on-surface hover:bg-surface-container-high transition-colors">
                        <span className="material-symbols-outlined text-[16px]">visibility</span>View Details
                      </button>
                      {user.is_active ? (
                        <button onClick={() => handleUserAction(user, 'deactivate')} role="menuitem" className="flex items-center gap-2 w-full px-3 py-2 text-label-md text-on-surface hover:bg-surface-container-high transition-colors">
                          <span className="material-symbols-outlined text-[16px]">block</span>Deactivate
                        </button>
                      ) : (
                        <>
                          <button onClick={() => handleUserAction(user, 'activate')} role="menuitem" className="flex items-center gap-2 w-full px-3 py-2 text-label-md text-on-surface hover:bg-surface-container-high transition-colors">
                            <span className="material-symbols-outlined text-[16px]">check_circle</span>Activate
                          </button>
                          <button onClick={() => handleUserAction(user, 'restore')} role="menuitem" className="flex items-center gap-2 w-full px-3 py-2 text-label-md text-on-surface hover:bg-surface-container-high transition-colors">
                            <span className="material-symbols-outlined text-[16px]">restore</span>Restore
                          </button>
                        </>
                      )}
                      <button onClick={() => handleUserAction(user, 'toggle-2fa')} role="menuitem" className="flex items-center gap-2 w-full px-3 py-2 text-label-md text-on-surface hover:bg-surface-container-high transition-colors">
                        <span className="material-symbols-outlined text-[16px]">security</span>Toggle 2FA
                      </button>
                      <button onClick={() => handleUserAction(user, 'reset-password')} role="menuitem" className="flex items-center gap-2 w-full px-3 py-2 text-label-md text-on-surface hover:bg-surface-container-high transition-colors">
                        <span className="material-symbols-outlined text-[16px]">key</span>Reset Password
                      </button>
                      <button onClick={() => handleUserAction(user, 'force-logout')} role="menuitem" className="flex items-center gap-2 w-full px-3 py-2 text-label-md text-on-surface hover:bg-surface-container-high transition-colors">
                        <span className="material-symbols-outlined text-[16px]">logout</span>Force Logout
                      </button>
                      <button onClick={() => handleImpersonate(user)} role="menuitem" className="flex items-center gap-2 w-full px-3 py-2 text-label-md text-on-surface hover:bg-surface-container-high transition-colors">
                        <span className="material-symbols-outlined text-[16px]">switch_account</span>Impersonate
                      </button>
                      <div className="border-t border-outline-variant my-1" />
                      <button onClick={() => handleUserAction(user, 'delete')} role="menuitem" className="flex items-center gap-2 w-full px-3 py-2 text-label-md text-error hover:bg-error-container transition-colors">
                        <span className="material-symbols-outlined text-[16px]">delete</span>Delete
                      </button>
                    </div>
                  )}
                </div>
              )}
            />
          )}

          <div className="mt-2">
            <Pagination page={page} pageSize={pageSize} total={data?.count || 0} onPageChange={setPage} onPageSizeChange={setPageSize} />
          </div>
        </>
      ) : (
        <>
          <FilterBar
            search=""
            onSearchChange={() => {}}
            placeholder=""
            filters={[
              { key: 'status', label: 'Status', options: [{ value: 'PENDING', label: 'Pending' }, { value: 'ACCEPTED', label: 'Accepted' }, { value: 'REVOKED', label: 'Revoked' }] },
            ]}
            filterValues={inviteFilters}
            onFilterChange={setInviteFilters}
            onClear={() => { setInviteFilters({}); setInvitePage(1) }}
            onExport={() => { const p = new URLSearchParams(); if (inviteFilters.status) p.set('status', inviteFilters.status); p.set('export', 'csv'); exportCsv(`/api/admin/auth/invites/?${p}`) }}
          />
          {inviteListLoading ? <TableSkeleton /> : (
            <div className="bg-surface-container-lowest border border-outline-variant rounded-xl overflow-hidden">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-outline-variant">
                    <th className="text-left px-4 py-3 text-label-md font-bold text-on-surface-variant">Email</th>
                    <th className="text-left px-4 py-3 text-label-md font-bold text-on-surface-variant">Status</th>
                    <th className="text-left px-4 py-3 text-label-md font-bold text-on-surface-variant">Role</th>
                    <th className="text-left px-4 py-3 text-label-md font-bold text-on-surface-variant">Created</th>
                    <th className="text-right px-4 py-3 text-label-md font-bold text-on-surface-variant">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-outline-variant/50">
                  {(inviteData?.results || []).length === 0 ? (
                    <tr><td colSpan={5} className="px-4 py-12 text-center text-body-md text-on-surface-variant">No invites found.</td></tr>
                  ) : (inviteData?.results || []).map((inv) => (
                    <tr key={inv.id} className="hover:bg-surface-container transition-colors">
                      <td className="px-4 py-3 text-body-md text-on-surface">{inv.email}</td>
                      <td className="px-4 py-3"><StatusBadge status={inv.status === 'PENDING' ? 'computing' : inv.status === 'ACCEPTED' ? 'completed' : 'error'} label={inv.status || '-'} /></td>
                      <td className="px-4 py-3 text-label-md text-on-surface-variant">{inv.role || '-'}</td>
                      <td className="px-4 py-3 text-label-md text-on-surface-variant">{inv.created_at ? new Date(inv.created_at).toLocaleDateString() : '-'}</td>
                      <td className="px-4 py-3 text-right">
                        {inv.status === 'PENDING' && (
                          <div className="flex items-center justify-end gap-1">
                            <button onClick={() => handleResendInvite(inv)} disabled={actionLoading} className="px-2 py-1 text-[11px] font-bold text-primary hover:bg-primary-container rounded-lg transition-colors" title="Resend Invite">Resend</button>
                            <button onClick={() => handleRevokeInvite(inv)} disabled={actionLoading} className="px-2 py-1 text-[11px] font-bold text-error hover:bg-error-container rounded-lg transition-colors" title="Revoke Invite">Revoke</button>
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <div className="mt-2">
            <Pagination page={invitePage} pageSize={20} total={inviteData?.count || 0} onPageChange={setInvitePage} onPageSizeChange={() => {}} />
          </div>
        </>
      )}

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
            <div className="pt-2 grid grid-cols-2 gap-2">
              <button onClick={() => handleUserAction(panelUser, panelUser.is_active ? 'deactivate' : 'activate')} className={`px-4 py-2 rounded-lg text-label-md font-bold transition-colors ${panelUser.is_active ? 'border border-error text-error hover:bg-error-container' : 'bg-primary text-on-primary hover:bg-primary/90'}`}>
                {panelUser.is_active ? 'Deactivate' : 'Activate'}
              </button>
              <button onClick={() => handleUserAction(panelUser, 'force-logout')} className="px-4 py-2 border border-outline-variant text-on-surface-variant rounded-lg text-label-md font-bold hover:bg-surface-container transition-colors">
                Force Logout
              </button>
              <button onClick={() => handleUserAction(panelUser, 'toggle-2fa')} className="px-4 py-2 border border-outline-variant text-on-surface-variant rounded-lg text-label-md font-bold hover:bg-surface-container transition-colors">
                Toggle 2FA
              </button>
              <button onClick={() => handleUserAction(panelUser, 'reset-password')} className="px-4 py-2 border border-outline-variant text-on-surface-variant rounded-lg text-label-md font-bold hover:bg-surface-container transition-colors">
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
                <input type="email" required value={inviteEmail} onChange={(e) => setInviteEmail(e.target.value)} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" placeholder="user@example.com" />
              </div>
              <div className="flex justify-end gap-3">
                <button type="button" onClick={() => setInviteModal(false)} className="px-4 py-2 rounded-lg text-label-md font-bold text-on-surface-variant bg-surface-container-high hover:bg-surface-container-highest transition-colors">Cancel</button>
                <button type="submit" disabled={inviteLoading} className="px-4 py-2 rounded-lg text-label-md font-bold text-white bg-primary hover:bg-primary/90 transition-colors disabled:opacity-50">{inviteLoading ? 'Sending...' : 'Send Invite'}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {superuserModal && (
        <div className="fixed inset-0 z-[65] flex items-center justify-center">
          <div className="fixed inset-0 bg-black/30" onClick={() => setSuperuserModal(false)} />
          <div className="relative bg-surface-container-lowest border border-outline-variant rounded-xl p-6 max-w-sm w-full mx-4 shadow-xl">
            <h3 className="font-headline-sm text-headline-sm text-on-surface mb-2">Create Superuser</h3>
            <p className="text-body-md text-on-surface-variant mb-4">Create a new admin with full system access.</p>
            <form onSubmit={handleCreateSuperuser} className="space-y-3">
              <div>
                <label className="block text-label-md font-bold text-on-surface-variant mb-1">Email</label>
                <input type="email" required value={suForm.email} onChange={(e) => setSuForm(f => ({ ...f, email: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-label-md font-bold text-on-surface-variant mb-1">First Name</label>
                  <input type="text" required value={suForm.first_name} onChange={(e) => setSuForm(f => ({ ...f, first_name: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" />
                </div>
                <div>
                  <label className="block text-label-md font-bold text-on-surface-variant mb-1">Last Name</label>
                  <input type="text" required value={suForm.last_name} onChange={(e) => setSuForm(f => ({ ...f, last_name: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" />
                </div>
              </div>
              <div>
                <label className="block text-label-md font-bold text-on-surface-variant mb-1">Phone</label>
                <input type="tel" value={suForm.phone_number} onChange={(e) => setSuForm(f => ({ ...f, phone_number: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" />
              </div>
              <div>
                <label className="block text-label-md font-bold text-on-surface-variant mb-1">Password</label>
                <input type="password" required value={suForm.password} onChange={(e) => setSuForm(f => ({ ...f, password: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" />
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button type="button" onClick={() => setSuperuserModal(false)} className="px-4 py-2 rounded-lg text-label-md font-bold text-on-surface-variant bg-surface-container-high hover:bg-surface-container-highest transition-colors">Cancel</button>
                <button type="submit" disabled={suLoading} className="px-4 py-2 rounded-lg text-label-md font-bold text-white bg-primary hover:bg-primary/90 transition-colors disabled:opacity-50">{suLoading ? 'Creating...' : 'Create'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
