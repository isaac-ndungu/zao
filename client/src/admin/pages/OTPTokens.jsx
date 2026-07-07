import { useState, useMemo } from 'react'
import { useApi } from '../hooks/useApi'
import { apiFetch, exportCsv } from '../api/client'
import FilterBar from '../components/common/FilterBar'
import DataTable from '../components/common/DataTable'
import Pagination from '../components/common/Pagination'
import StatusBadge from '../components/common/StatusBadge'
import ConfirmModal from '../components/common/ConfirmModal'
import { TableSkeleton } from '../components/common/Skeleton'
import { useToast } from '../contexts/ToastContext'

const purposeOptions = [
  { value: 'LOGIN', label: 'Login' },
  { value: 'PASSWORD_RESET', label: 'Password Reset' },
  { value: 'ACTION_CONFIRM', label: 'Action Confirm' },
  { value: 'FARMER_LOGIN', label: 'Farmer Login' },
]

export default function OTPTokens() {
  const { showToast } = useToast()
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [search, setSearch] = useState('')
  const [filters, setFilters] = useState({})
  const [sortField, setSortField] = useState('created_at')
  const [sortOrder, setSortOrder] = useState('desc')
  const [selectedIds, setSelectedIds] = useState([])
  const [modalConfig, setModalConfig] = useState({ open: false })
  const [invalidateUserId, setInvalidateUserId] = useState(null)
  const [actionLoading, setActionLoading] = useState(false)

  const query = useMemo(() => {
    const params = new URLSearchParams()
    params.set('page', page)
    params.set('page_size', pageSize)
    if (search) params.set('user', search)
    if (filters.purpose) params.set('purpose', filters.purpose)
    if (filters.is_used) params.set('is_used', filters.is_used)
    if (sortField) params.set('ordering', sortOrder === 'desc' ? `-${sortField}` : sortField)
    return params.toString()
  }, [page, pageSize, search, filters, sortField, sortOrder])

  const { data, loading, error, refetch } = useApi(`/api/admin/otp-tokens/?${query}`)

  const handleSort = (field) => {
    if (sortField === field) setSortOrder(o => o === 'asc' ? 'desc' : 'asc')
    else { setSortField(field); setSortOrder('asc') }
  }

  const handleInvalidateAll = (userId) => {
    setInvalidateUserId(userId)
    setModalConfig({
      open: true,
      title: 'Invalidate All OTPs',
      message: 'Mark all unused OTP tokens for this user as used? This will force them to request new codes.',
      destructive: true,
      onConfirm: async () => {
        setActionLoading(true)
        setModalConfig({ open: false })
        try {
          const res = await apiFetch(`/api/admin/otp-tokens/${userId}/invalidate-all/`, { method: 'POST' })
          if (!res.ok) throw new Error(await res.text())
          showToast({ type: 'success', message: 'All pending OTPs invalidated.' })
          refetch()
        } catch (e) {
          showToast({ type: 'error', message: `Failed to invalidate OTPs: ${e.message}` })
        } finally {
          setActionLoading(false)
          setInvalidateUserId(null)
        }
      },
    })
  }

  const columns = useMemo(() => [
    {
      key: 'user_email',
      label: 'User',
      sortable: true,
      render: (r) => (
        <div>
          <span className="font-medium">{r.user_email || r.user?.email || r.user || '-'}</span>
          {r.user_id && <span className="block text-[10px] font-data-mono text-on-surface-variant">{r.user_id?.slice(0, 8)}...</span>}
        </div>
      ),
    },
    { key: 'purpose', label: 'Purpose', sortable: true, render: (r) => <StatusBadge status={r.purpose?.toLowerCase() === 'login' ? 'active' : r.purpose?.toLowerCase() === 'password_reset' ? 'computing' : 'draft'} label={r.purpose?.replace(/_/g, ' ').toLowerCase() || '-'} /> },
    { key: 'attempts', label: 'Attempts', sortable: true, render: (r) => <span className="font-data-mono">{r.attempts || 0}</span> },
    {
      key: 'expires_at',
      label: 'Expires',
      sortable: true,
      render: (r) => {
        const expired = r.expires_at && new Date(r.expires_at) < new Date()
        return <span className={`font-data-mono ${expired ? 'text-error' : ''}`}>{r.expires_at ? new Date(r.expires_at).toLocaleString() : '-'}</span>
      },
    },
    { key: 'is_used', label: 'Used', sortable: true, render: (r) => <StatusBadge status={r.is_used ? 'completed' : 'pending'} label={r.is_used ? 'Yes' : 'No'} /> },
    { key: 'created_at', label: 'Created', sortable: true, render: (r) => <span className="text-on-surface-variant text-label-md">{r.created_at ? new Date(r.created_at).toLocaleString() : '-'}</span> },
  ], [])

  if (error) {
    return <div className="bg-error-container text-error p-4 rounded-xl">Failed to load OTP tokens: {error}</div>
  }

  return (
    <div>
      <header className="mb-6">
        <h2 className="font-headline-lg text-display-md text-primary mb-1">OTP Tokens</h2>
        <p className="text-on-surface-variant font-body-md">Monitor and manage one-time password tokens across the system.</p>
      </header>

      <FilterBar
        search={search}
        onSearchChange={setSearch}
        placeholder="Filter by user ID..."
        filters={[
          { key: 'purpose', label: 'Purpose', options: purposeOptions },
          { key: 'is_used', label: 'Status', options: [{ value: 'true', label: 'Used' }, { value: 'false', label: 'Unused' }] },
        ]}
        filterValues={filters}
        onFilterChange={setFilters}
        onClear={() => { setSearch(''); setFilters({}); setPage(1) }}
        onExport={() => { const p = new URLSearchParams(); if (search) p.set('user', search); if (filters.purpose) p.set('purpose', filters.purpose); if (filters.is_used) p.set('is_used', filters.is_used); p.set('export', 'csv'); exportCsv(`/api/admin/otp-tokens/?${p}`) }}
      />

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
          emptyMessage="No OTP tokens found."
          rowActions={(row) => (
            <div className="flex gap-1">
              {!row.is_used && row.user_id && (
                <button
                  onClick={() => handleInvalidateAll(row.user_id)}
                  disabled={actionLoading && invalidateUserId === row.user_id}
                  className="p-1.5 rounded-lg hover:bg-error-container text-error transition-colors"
                  aria-label="Invalidate all tokens for this user"
                >
                  <span className="material-symbols-outlined text-[18px]" aria-hidden="true">block</span>
                </button>
              )}
            </div>
          )}
        />
      )}

      <div className="mt-2">
        <Pagination page={page} pageSize={pageSize} total={data?.count || 0} onPageChange={setPage} onPageSizeChange={setPageSize} />
      </div>

      <ConfirmModal
        open={modalConfig.open}
        title={modalConfig.title}
        message={modalConfig.message}
        onConfirm={modalConfig.onConfirm}
        onCancel={() => setModalConfig({ open: false })}
        loading={actionLoading}
        destructive={modalConfig.destructive}
      />
    </div>
  )
}
