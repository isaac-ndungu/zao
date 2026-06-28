import { useState, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useApi } from '../../admin/hooks/useApi'
import ErrorState from '../../shared/components/ErrorState'
import { TableSkeleton } from '../../admin/components/common/Skeleton'
import DataTable from '../../admin/components/common/DataTable'

const resourceTypes = ['', 'Farmer', 'Delivery', 'Grade', 'PaymentCycle', 'FarmerPayment', 'Loan', 'Deduction', 'DisbursementBatch', 'Sale', 'FarmInputCredit', 'Cooperative', 'User']

const actions = ['', 'CREATE', 'UPDATE', 'DELETE', 'LOCK', 'UNLOCK', 'RUN', 'DISBURSE', 'APPROVE', 'REJECT', 'LOGIN']

export default function AuditorAuditLog() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [page, setPage] = useState(1)
  const [resourceType, setResourceType] = useState(searchParams.get('resource_type') || '')
  const [actionFilter, setActionFilter] = useState(searchParams.get('action') || '')
  const [actionCategory, setActionCategory] = useState(searchParams.get('action_category') || '')
  const [dateFrom, setDateFrom] = useState(searchParams.get('date_from') || '')
  const [dateTo, setDateTo] = useState(searchParams.get('date_to') || '')
  const search = searchParams.get('search') || ''

  const queryParams = new URLSearchParams({ page, page_size: '25' })
  if (search) queryParams.set('search', search)
  if (resourceType) queryParams.set('resource_type', resourceType)
  if (actionFilter) queryParams.set('action', actionFilter)
  if (actionCategory) queryParams.set('action_category', actionCategory)
  if (dateFrom) queryParams.set('date_from', dateFrom)
  if (dateTo) queryParams.set('date_to', dateTo)

  const { data, loading, error, refetch } = useApi(`/api/statements/audit/?${queryParams}`)

  const logs = data?.results || data || []
  const totalCount = data?.count || logs.length

  const handleSearch = useCallback((e) => {
    e.preventDefault()
    const fd = new FormData(e.target)
    const q = fd.get('search')
    setSearchParams(q ? { search: q } : {})
    setPage(1)
  }, [setSearchParams])

  const handleExportCSV = () => {
    const headers = ['Timestamp', 'Actor', 'Action', 'Resource Type', 'Resource ID', 'Details']
    const rows = logs.map((l) => [
      l.created_at ? new Date(l.created_at).toISOString() : '',
      l.actor_name || l.actor?.email || '',
      l.action || '',
      l.resource_type || '',
      l.resource_id || '',
      (l.details ? JSON.stringify(l.details).replace(/"/g, '""') : ''),
    ])
    const csv = [headers.join(','), ...rows.map((r) => r.map((c) => `"${c}"`).join(','))].join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'audit_log.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  const columns = [
    { key: 'created_at', label: 'Timestamp', sortable: true, render: (row) => row.created_at ? new Date(row.created_at).toLocaleString() : '-' },
    { key: 'actor', label: 'Actor', render: (row) => row.actor_name || row.actor?.email || `#${row.actor}` },
    { key: 'action', label: 'Action', sortable: true },
    { key: 'resource_type', label: 'Resource', sortable: true },
    { key: 'resource_id', label: 'Resource ID', render: (row) => row.resource_id ? String(row.resource_id).slice(0, 8) + '...' : '-' },
    { key: 'details', label: 'Details', render: (row) => row.details ? JSON.stringify(row.details).slice(0, 60) + (JSON.stringify(row.details).length > 60 ? '...' : '') : '-' },
  ]

  return (
    <div>
      <header className="mb-6 flex justify-between items-start">
        <div>
          <h2 className="font-headline-lg text-display-md text-primary mb-1">Audit Log</h2>
          <p className="text-on-surface-variant font-body-md">{totalCount} entries</p>
        </div>
        <button onClick={handleExportCSV} className="px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold hover:bg-primary/90 transition-colors">Export CSV</button>
      </header>

      <div className="flex flex-wrap gap-3 mb-4 items-end">
        <form onSubmit={handleSearch} className="flex gap-2">
          <input name="search" defaultValue={search} placeholder="Search actor, action..." className="px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container w-48" />
          <button type="submit" className="px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold">Search</button>
        </form>
        <select value={resourceType} onChange={(e) => { setResourceType(e.target.value); setPage(1) }} className="px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container">
          {resourceTypes.map((r) => <option key={r} value={r}>{r || 'All Resources'}</option>)}
        </select>
        <select value={actionFilter} onChange={(e) => { setActionFilter(e.target.value); setPage(1) }} className="px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container">
          {actions.map((a) => <option key={a} value={a}>{a || 'All Actions'}</option>)}
        </select>
        <select value={actionCategory} onChange={(e) => { setActionCategory(e.target.value); setPage(1) }} className="px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container">
          <option value="">All Categories</option>
          <option value="financial">Financial Only</option>
        </select>
        <div className="flex gap-2 items-center">
          <label className="text-label-md text-on-surface-variant">From</label>
          <input type="date" value={dateFrom} onChange={(e) => { setDateFrom(e.target.value); setPage(1) }} className="px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container" />
          <label className="text-label-md text-on-surface-variant">To</label>
          <input type="date" value={dateTo} onChange={(e) => { setDateTo(e.target.value); setPage(1) }} className="px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container" />
        </div>
      </div>

      {loading ? <TableSkeleton rows={10} cols={6} /> : error ? <ErrorState message={error} action={{ label: 'Retry', onClick: refetch }} /> : (
        <DataTable
          columns={columns}
          data={logs}
        />
      )}
    </div>
  )
}
