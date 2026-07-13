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
import PasswordInput from '../../shared/components/PasswordInput'

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

import { useLocation, useSearchParams } from 'react-router-dom'

export default function UserManagement() {
  const { showToast } = useToast()
  const location = useLocation()
  const [searchParams, setSearchParams] = useSearchParams()
  const selectedId = searchParams.get('selected')
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
  const [inviteFirstName, setInviteFirstName] = useState('')
  const [inviteLastName, setInviteLastName] = useState('')
  const [inviteLoading, setInviteLoading] = useState(false)
  const [inviteErrors, setInviteErrors] = useState({})
  const [superuserModal, setSuperuserModal] = useState(false)
  const [suForm, setSuForm] = useState({ email: '', first_name: '', last_name: '', phone_number: '', password: '' })
  const [suLoading, setSuLoading] = useState(false)
  const [suErrors, setSuErrors] = useState({})
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

  const users = data?.results || []

  useEffect(() => {
    if (selectedId && users.length > 0) {
      const found = users.find(i => String(i.id) === String(selectedId))
      if (found && !panelOpen) {
        setPanelUser(found)
        setPanelOpen(true)
      }
    }
  }, [selectedId, users])

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
      const result = await res.json().catch(() => ({}))
      let msg = url.includes('activate') ? 'activated' : url.includes('deactivate') ? 'deactivated' : url.includes('delete') ? 'soft-deleted' : url.includes('restore') ? 'restored' : url.includes('reset') ? 'password reset' : url.includes('logout') ? 'logged out' : url.includes('impersonate') ? 'impersonated' : 'action completed'
      if (url.includes('toggle-2fa') && result && result.two_fa_enabled !== undefined) {
        msg = result.two_fa_enabled ? '2FA enabled' : '2FA disabled'
      }
      showToast({ type: 'success', message: `User ${msg}.` })
      refetch()
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
      'toggle-2fa': { title: user.two_fa_enabled ? 'Disable 2FA' : 'Enable 2FA', message: user.two_fa_enabled ? `Disable 2FA for ${user.email}?` : `Enable 2FA for ${user.email}?`, destructive: !!user.two_fa_enabled },
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
        body: JSON.stringify({ confirm: action === 'delete', ...(action === 'toggle-2fa' ? { enabled: !user.two_fa_enabled } : {}) }),
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
    setInviteErrors({})
    try {
      const res = await apiFetch('/api/admin/auth/invite/', {
        method: 'POST',
        body: JSON.stringify({ email: inviteEmail, first_name: inviteFirstName, last_name: inviteLastName }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        if (data && typeof data === 'object' && !Array.isArray(data)) {
          setInviteErrors(data)
        }
        throw new Error(Object.values(data).flat().join(', ') || 'Invite failed')
      }
      showToast({ type: 'success', message: `Invite sent to ${inviteEmail}.` })
      setInviteEmail('')
      setInviteFirstName('')
      setInviteLastName('')
      setInviteErrors({})
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
    setSuErrors({})
    try {
      const res = await apiFetch('/api/admin/users/create-superuser/', {
        method: 'POST',
        body: JSON.stringify(suForm),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        if (data && typeof data === 'object' && !Array.isArray(data)) {
          setSuErrors(data)
        }
        throw new Error(Object.values(data).flat().join(', ') || 'Creation failed')
      }
      showToast({ type: 'success', message: `Superuser ${suForm.email} created.` })
      setSuForm({ email: '', first_name: '', last_name: '', phone_number: '', password: '' })
      setSuErrors({})
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
    { key: 'name', label: 'User', sortable: true, render: (_, r) => (
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
    { key: 'phone_number', label: 'Phone', render: (_, r) => <span className="text-on-surface-variant">{r.phone_number || '-'}</span> },
    { key: 'role', label: 'Role', render: (_, r) => {
      const m = roleBadgeMap[r.role] || { status: 'draft', label: r.role }
      return <StatusBadge status={m.status} label={m.label} />
    }},
    { key: 'is_active', label: 'Status', render: (_, r) => <StatusBadge status={r.is_active ? 'active' : 'inactive'} label={r.is_active ? 'Active' : 'Inactive'} /> },
    { key: 'two_fa_enabled', label: '2FA', render: (_, r) => <StatusBadge status={r.two_fa_enabled ? 'true' : 'false'} label={r.two_fa_enabled ? 'On' : 'Off'} /> },
    { key: 'date_joined', label: 'Joined', sortable: true, render: (_, r) => r.date_joined ? new Date(r.date_joined).toLocaleDateString() : '-' },
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
                  <span className="material-symbols-outlined text-[16px]" aria-hidden="true">admin_panel_settings</span>
                  <span className="hidden sm:inline">Create Superuser</span>
                </button>
                <button onClick={() => setInviteModal(true)} className="flex items-center gap-2 px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold hover:bg-primary/90 transition-colors">
                  <span className="material-symbols-outlined text-[16px]" aria-hidden="true">person_add</span>
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
                    className={`p-1.5 rounded-lg hover:bg-surface-container-high text-on-surface-variant transition-colors ${openDropdownId === user.id ? 'opacity-100' : ''}`}
                    aria-label="User actions"
                    aria-haspopup="true"
                    aria-expanded={openDropdownId === user.id}
                  >
                    <span className="material-symbols-outlined text-[18px]" aria-hidden="true">more_vert</span>
                  </button>
                  {openDropdownId === user.id && (
                    <div
                      className="absolute right-0 top-full mt-1 w-44 bg-surface-container-lowest border border-outline-variant rounded-lg shadow-lg z-50 py-1"
                      role="menu"
                    >
                      <button onClick={() => handleView(user)} role="menuitem" className="flex items-center gap-2 w-full px-3 py-2 text-label-md text-on-surface hover:bg-surface-container-high transition-colors">
                        <span className="material-symbols-outlined text-[16px]" aria-hidden="true">visibility</span>View Details
                      </button>
                      {user.is_active ? (
                        <button onClick={() => handleUserAction(user, 'deactivate')} role="menuitem" className="flex items-center gap-2 w-full px-3 py-2 text-label-md text-on-surface hover:bg-surface-container-high transition-colors">
                          <span className="material-symbols-outlined text-[16px]" aria-hidden="true">block</span>Deactivate
                        </button>
                      ) : (
                        <>
                          <button onClick={() => handleUserAction(user, 'activate')} role="menuitem" className="flex items-center gap-2 w-full px-3 py-2 text-label-md text-on-surface hover:bg-surface-container-high transition-colors">
                            <span className="material-symbols-outlined text-[16px]" aria-hidden="true">check_circle</span>Activate
                          </button>
                          <button onClick={() => handleUserAction(user, 'restore')} role="menuitem" className="flex items-center gap-2 w-full px-3 py-2 text-label-md text-on-surface hover:bg-surface-container-high transition-colors">
                            <span className="material-symbols-outlined text-[16px]" aria-hidden="true">restore</span>Restore
                          </button>
                        </>
                      )}
                      <button onClick={() => handleUserAction(user, 'toggle-2fa')} role="menuitem" className="flex items-center gap-2 w-full px-3 py-2 text-label-md text-on-surface hover:bg-surface-container-high transition-colors">
                        <span className="material-symbols-outlined text-[16px]" aria-hidden="true">security</span>Toggle 2FA
                      </button>
                      <button onClick={() => handleUserAction(user, 'reset-password')} role="menuitem" className="flex items-center gap-2 w-full px-3 py-2 text-label-md text-on-surface hover:bg-surface-container-high transition-colors">
                        <span className="material-symbols-outlined text-[16px]" aria-hidden="true">key</span>Reset Password
                      </button>
                      <button onClick={() => handleUserAction(user, 'force-logout')} role="menuitem" className="flex items-center gap-2 w-full px-3 py-2 text-label-md text-on-surface hover:bg-surface-container-high transition-colors">
                        <span className="material-symbols-outlined text-[16px]" aria-hidden="true">logout</span>Force Logout
                      </button>
                      <button onClick={() => handleImpersonate(user)} role="menuitem" className="flex items-center gap-2 w-full px-3 py-2 text-label-md text-on-surface hover:bg-surface-container-high transition-colors">
                        <span className="material-symbols-outlined text-[16px]" aria-hidden="true">switch_account</span>Impersonate
                      </button>
                      <div className="border-t border-outline-variant my-1" />
                      <button onClick={() => handleUserAction(user, 'delete')} role="menuitem" className="flex items-center gap-2 w-full px-3 py-2 text-label-md text-error hover:bg-error-container transition-colors">
                        <span className="material-symbols-outlined text-[16px]" aria-hidden="true">delete</span>Delete
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
                    <th scope="col" className="text-left px-4 py-3 text-label-md font-bold text-on-surface-variant">Email</th>
                    <th scope="col" className="text-left px-4 py-3 text-label-md font-bold text-on-surface-variant">Status</th>
                    <th scope="col" className="text-left px-4 py-3 text-label-md font-bold text-on-surface-variant">Role</th>
                    <th scope="col" className="text-left px-4 py-3 text-label-md font-bold text-on-surface-variant">Created</th>
                    <th scope="col" className="text-right px-4 py-3 text-label-md font-bold text-on-surface-variant">Actions</th>
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
                            <button onClick={() => handleResendInvite(inv)} disabled={actionLoading} className="p-1.5 rounded-lg text-primary hover:bg-primary-container transition-colors disabled:opacity-50" aria-label="Resend invite"><span className="material-symbols-outlined text-[16px]" aria-hidden="true">forward_to_inbox</span></button>
                            <button onClick={() => handleRevokeInvite(inv)} disabled={actionLoading} className="p-1.5 rounded-lg text-error hover:bg-error-container transition-colors disabled:opacity-50" aria-label="Revoke invite"><span className="material-symbols-outlined text-[16px]" aria-hidden="true">cancel</span></button>
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

      <SlideOutPanel open={panelOpen} onClose={() => { setPanelOpen(false); setPanelUser(null); const p = new URLSearchParams(searchParams); p.delete('selected'); setSearchParams(p, { replace: true }) }} title="User Details">
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
        <div className="fixed inset-0 z-[65] flex items-center justify-center" role="presentation">
          <div className="fixed inset-0 bg-black/30 cursor-pointer" onClick={() => { setInviteModal(false); setInviteErrors({}) }} />
          <div className="relative bg-surface-container-lowest border border-outline-variant rounded-xl p-6 max-w-sm w-full mx-4 shadow-xl" role="dialog" aria-modal="true" aria-labelledby="invite-user-title">
            <h3 id="invite-user-title" className="font-headline-sm text-headline-sm text-on-surface mb-2">Invite User</h3>
            <p className="text-body-md text-on-surface-variant mb-4">Send an invitation to join the platform.</p>
            <form onSubmit={handleInvite}>
              <div className="mb-4">
                <label htmlFor="invite-email" className="block text-label-md font-bold text-on-surface-variant mb-1">Email Address</label>
                <input id="invite-email" type="email" required value={inviteEmail} onChange={(e) => { setInviteEmail(e.target.value); setInviteErrors(p => { const n = { ...p }; delete n.email; return n }) }} className={`w-full bg-surface-container border rounded-lg px-3 py-2 text-body-md text-on-surface ${inviteErrors.email ? 'border-error' : 'border-outline-variant'}`} placeholder="user@example.com" />
                {inviteErrors.email && <p className="text-label-sm text-error mt-1" role="alert">{inviteErrors.email.join(', ')}</p>}
              </div>
              <div className="grid grid-cols-2 gap-3 mb-4">
                <div>
                  <label htmlFor="invite-firstname" className="block text-label-md font-bold text-on-surface-variant mb-1">First Name</label>
                  <input id="invite-firstname" type="text" required value={inviteFirstName} onChange={(e) => { setInviteFirstName(e.target.value); setInviteErrors(p => { const n = { ...p }; delete n.first_name; return n }) }} className={`w-full bg-surface-container border rounded-lg px-3 py-2 text-body-md text-on-surface ${inviteErrors.first_name ? 'border-error' : 'border-outline-variant'}`} placeholder="First" />
                  {inviteErrors.first_name && <p className="text-label-sm text-error mt-1" role="alert">{inviteErrors.first_name.join(', ')}</p>}
                </div>
                <div>
                  <label htmlFor="invite-lastname" className="block text-label-md font-bold text-on-surface-variant mb-1">Last Name</label>
                  <input id="invite-lastname" type="text" required value={inviteLastName} onChange={(e) => { setInviteLastName(e.target.value); setInviteErrors(p => { const n = { ...p }; delete n.last_name; return n }) }} className={`w-full bg-surface-container border rounded-lg px-3 py-2 text-body-md text-on-surface ${inviteErrors.last_name ? 'border-error' : 'border-outline-variant'}`} placeholder="Last" />
                  {inviteErrors.last_name && <p className="text-label-sm text-error mt-1" role="alert">{inviteErrors.last_name.join(', ')}</p>}
                </div>
              </div>
              <div className="flex justify-end gap-3">
                <button type="button" onClick={() => { setInviteModal(false); setInviteErrors({}) }} className="px-4 py-2 rounded-lg text-label-md font-bold text-on-surface-variant bg-surface-container-high hover:bg-surface-container-highest transition-colors">Cancel</button>
                <button type="submit" disabled={inviteLoading} className="px-4 py-2 rounded-lg text-label-md font-bold text-white bg-primary hover:bg-primary/90 transition-colors disabled:opacity-50">{inviteLoading ? 'Sending...' : 'Send Invite'}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {superuserModal && (
        <div className="fixed inset-0 z-[65] flex items-center justify-center" role="presentation">
          <div className="fixed inset-0 bg-black/30 cursor-pointer" onClick={() => { setSuperuserModal(false); setSuErrors({}) }} />
          <div className="relative bg-surface-container-lowest border border-outline-variant rounded-xl p-6 max-w-sm w-full mx-4 shadow-xl" role="dialog" aria-modal="true" aria-labelledby="create-superuser-title">
            <h3 id="create-superuser-title" className="font-headline-sm text-headline-sm text-on-surface mb-2">Create Superuser</h3>
            <p className="text-body-md text-on-surface-variant mb-4">Create a new admin with full system access.</p>
            <form onSubmit={handleCreateSuperuser} className="space-y-3">
              <div>
                <label htmlFor="su-email" className="block text-label-md font-bold text-on-surface-variant mb-1">Email</label>
                <input id="su-email" type="email" required value={suForm.email} onChange={(e) => { setSuForm(f => ({ ...f, email: e.target.value })); setSuErrors(p => { const n = { ...p }; delete n.email; return n }) }} className={`w-full bg-surface-container border rounded-lg px-3 py-2 text-body-md text-on-surface ${suErrors.email ? 'border-error' : 'border-outline-variant'}`} />
                {suErrors.email && <p className="text-label-sm text-error mt-1" role="alert">{suErrors.email.join(', ')}</p>}
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label htmlFor="su-firstname" className="block text-label-md font-bold text-on-surface-variant mb-1">First Name</label>
                  <input id="su-firstname" type="text" required value={suForm.first_name} onChange={(e) => { setSuForm(f => ({ ...f, first_name: e.target.value })); setSuErrors(p => { const n = { ...p }; delete n.first_name; return n }) }} className={`w-full bg-surface-container border rounded-lg px-3 py-2 text-body-md text-on-surface ${suErrors.first_name ? 'border-error' : 'border-outline-variant'}`} />
                  {suErrors.first_name && <p className="text-label-sm text-error mt-1" role="alert">{suErrors.first_name.join(', ')}</p>}
                </div>
                <div>
                  <label htmlFor="su-lastname" className="block text-label-md font-bold text-on-surface-variant mb-1">Last Name</label>
                  <input id="su-lastname" type="text" required value={suForm.last_name} onChange={(e) => { setSuForm(f => ({ ...f, last_name: e.target.value })); setSuErrors(p => { const n = { ...p }; delete n.last_name; return n }) }} className={`w-full bg-surface-container border rounded-lg px-3 py-2 text-body-md text-on-surface ${suErrors.last_name ? 'border-error' : 'border-outline-variant'}`} />
                  {suErrors.last_name && <p className="text-label-sm text-error mt-1" role="alert">{suErrors.last_name.join(', ')}</p>}
                </div>
              </div>
              <div>
                <label htmlFor="su-phone" className="block text-label-md font-bold text-on-surface-variant mb-1">Phone</label>
                <input id="su-phone" type="tel" value={suForm.phone_number} onChange={(e) => { setSuForm(f => ({ ...f, phone_number: e.target.value })); setSuErrors(p => { const n = { ...p }; delete n.phone_number; return n }) }} className={`w-full bg-surface-container border rounded-lg px-3 py-2 text-body-md text-on-surface ${suErrors.phone_number ? 'border-error' : 'border-outline-variant'}`} />
                {suErrors.phone_number && <p className="text-label-sm text-error mt-1" role="alert">{suErrors.phone_number.join(', ')}</p>}
              </div>
              <div>
                <PasswordInput
                  id="su-password"
                  label="Password"
                  value={suForm.password}
                  onChange={(e) => { setSuForm(f => ({ ...f, password: e.target.value })); setSuErrors(p => { const n = { ...p }; delete n.password; return n }) }}
                  required
                  error={suErrors.password ? suErrors.password.join(', ') : undefined}
                />
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button type="button" onClick={() => { setSuperuserModal(false); setSuErrors({}) }} className="px-4 py-2 rounded-lg text-label-md font-bold text-on-surface-variant bg-surface-container-high hover:bg-surface-container-highest transition-colors">Cancel</button>
                <button type="submit" disabled={suLoading} className="px-4 py-2 rounded-lg text-label-md font-bold text-white bg-primary hover:bg-primary/90 transition-colors disabled:opacity-50">{suLoading ? 'Creating...' : 'Create'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
