import { useState, useMemo } from 'react'
import { useApi } from '../hooks/useApi'
import FilterBar from '../components/common/FilterBar'
import Pagination from '../components/common/Pagination'

const actionOptions = [
  { value: 'CREATE', label: 'Create' },
  { value: 'UPDATE', label: 'Update' },
  { value: 'DELETE', label: 'Delete' },
  { value: 'RESTORE', label: 'Restore' },
  { value: 'PURGE', label: 'Purge' },
  { value: 'ACTIVATE', label: 'Activate' },
  { value: 'DEACTIVATE', label: 'Deactivate' },
  { value: 'LOGIN', label: 'Login' },
  { value: 'LOGOUT', label: 'Logout' },
  { value: 'FORCE_LOGOUT', label: 'Force Logout' },
  { value: 'INVITE', label: 'Invite' },
  { value: 'RESET_PASSWORD', label: 'Reset Password' },
  { value: 'TOGGLE_2FA', label: 'Toggle 2FA' },
  { value: 'IMPERSONATE', label: 'Impersonate' },
  { value: 'FORCE_STATUS', label: 'Force Status' },
  { value: 'LOCK', label: 'Lock' },
  { value: 'UNLOCK', label: 'Unlock' },
  { value: 'APPROVE', label: 'Approve' },
  { value: 'REJECT', label: 'Reject' },
  { value: 'MARK_DEFAULTED', label: 'Mark Defaulted' },
  { value: 'MARK_COMPLETED', label: 'Mark Completed' },
  { value: 'BULK_ACTION', label: 'Bulk Action' },
]

const resourceOptions = [
  { value: 'user', label: 'User' },
  { value: 'cooperative', label: 'Cooperative' },
  { value: 'farmer', label: 'Farmer' },
  { value: 'delivery', label: 'Delivery' },
  { value: 'paymentcycle', label: 'Payment Cycle' },
  { value: 'farmerpayment', label: 'Farmer Payment' },
  { value: 'disbursementbatch', label: 'Disbursement Batch' },
  { value: 'loan', label: 'Loan' },
  { value: 'otptoken', label: 'OTP Token' },
  { value: 'invite', label: 'Invite' },
]

function formatAuditAction(action) {
  return action.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

export default function AuditTrail() {
  const [filters, setFilters] = useState({})
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)

  const query = useMemo(() => {
    const params = new URLSearchParams()
    if (filters.action) params.set('action', filters.action)
    if (filters.resource_type) params.set('resource_type', filters.resource_type)
    if (search) params.set('actor', search)
    params.set('page', page)
    params.set('page_size', pageSize)
    params.set('ordering', '-created_at')
    return params.toString()
  }, [filters, search, page, pageSize])

  const { data, loading, error, refetch } = useApi(`/api/admin/audit-logs/?${query}`)

  const logs = data?.results || []

  if (error) {
    return <div className="bg-error-container text-error p-4 rounded-xl">Failed to load audit logs: {error}</div>
  }

  return (
    <div>
      <header className="mb-6">
        <h2 className="font-headline-lg text-display-md text-primary mb-1">System Audit Log</h2>
        <p className="text-on-surface-variant font-body-md">Track all administrative actions and system changes.</p>
      </header>

      <FilterBar
        search={search}
        onSearchChange={setSearch}
        placeholder="Filter by actor ID..."
        filters={[
          { key: 'action', label: 'Action', options: actionOptions },
          { key: 'resource_type', label: 'Resource', options: resourceOptions },
        ]}
        filterValues={filters}
        onFilterChange={setFilters}
        onClear={() => { setSearch(''); setFilters({}); setPage(1) }}
        onExport={() => { const p = new URLSearchParams(); if (search) p.set('actor', search); if (filters.action) p.set('action', filters.action); if (filters.resource_type) p.set('resource_type', filters.resource_type); p.set('export', 'csv'); window.open(`/api/admin/audit-logs/?${p}`, '_blank') }}
      />

      <div className="bg-surface-container-lowest border border-outline-variant rounded-xl overflow-hidden">
        {loading ? (
          <div className="p-8 flex items-center justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
          </div>
        ) : logs.length === 0 ? (
          <div className="p-12 text-center">
            <span className="material-symbols-outlined text-[48px] block mb-2 text-outline-variant">history</span>
            <p className="text-body-md text-on-surface-variant">No audit log entries found.</p>
          </div>
        ) : (
          <div className="divide-y divide-outline-variant/50">
            {logs.map((log) => (
              <div key={log.id} className="px-6 py-4 hover:bg-surface-container transition-colors">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                        log.action === 'DELETE' || log.action === 'PURGE' || log.action === 'DEACTIVATE'
                          ? 'bg-error-container text-error'
                          : log.action === 'CREATE' || log.action === 'RESTORE' || log.action === 'ACTIVATE' || log.action === 'APPROVE'
                          ? 'bg-primary-container text-primary'
                          : 'bg-surface-container-high text-on-surface-variant'
                      }`}>
                        {formatAuditAction(log.action)}
                      </span>
                      <span className="text-label-md text-on-surface-variant">{log.resource_type ? formatAuditAction(log.resource_type) : '-'}</span>
                      {log.resource_id && (
                        <span className="font-data-mono text-[11px] text-on-surface-variant">{log.resource_id?.slice(0, 8)}...</span>
                      )}
                    </div>
                    <p className="text-body-md text-on-surface">
                      {log.description || `${log.action} on ${log.resource_type || 'unknown'}${log.resource_id ? ` (${log.resource_id})` : ''}`}
                    </p>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <p className="text-label-md text-on-surface-variant">
                      {log.created_at ? new Date(log.created_at).toLocaleString() : ''}
                    </p>
                    {log.actor && (
                      <p className="text-[11px] text-on-surface-variant font-data-mono">
                        Actor: {log.actor?.slice(0, 8)}...
                      </p>
                    )}
                  </div>
                </div>
                {log.changes && Object.keys(log.changes).length > 0 && (
                  <details className="mt-2 group">
                    <summary className="text-[11px] font-bold text-on-surface-variant cursor-pointer hover:text-on-surface">
                      View changes ({Object.keys(log.changes).length} fields)
                    </summary>
                    <pre className="mt-2 p-3 bg-surface-container rounded-lg text-[11px] font-data-mono text-on-surface-variant overflow-x-auto">
                      {JSON.stringify(log.changes, null, 2)}
                    </pre>
                  </details>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="mt-2">
        <Pagination page={page} pageSize={pageSize} total={data?.count || 0} onPageChange={setPage} onPageSizeChange={setPageSize} />
      </div>
    </div>
  )
}
