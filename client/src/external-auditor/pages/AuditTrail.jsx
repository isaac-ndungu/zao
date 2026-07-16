import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useApi } from '../../admin/hooks/useApi'
import ErrorState from '../../shared/components/ErrorState'
import { TableSkeleton } from '../../admin/components/common/Skeleton'
import DataTable from '../../admin/components/common/DataTable'
import { useFormAction, SubmitButton } from '../../shared/hooks/useFormAction'

export default function ExternalAuditTrail() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [page, setPage] = useState(1)
  const [actionFilter, setActionFilter] = useState(searchParams.get('action') || '')
  const [dateFrom, setDateFrom] = useState(searchParams.get('date_from') || '')
  const [dateTo, setDateTo] = useState(searchParams.get('date_to') || '')
  const search = searchParams.get('search') || ''

  const queryParams = new URLSearchParams({ page, page_size: '25' })
  if (search) queryParams.set('search', search)
  if (actionFilter) queryParams.set('action', actionFilter)
  if (dateFrom) queryParams.set('date_from', dateFrom)
  if (dateTo) queryParams.set('date_to', dateTo)

  const { data, loading, error, refetch } = useApi(`/api/statements/external-audit/?${queryParams}`)

  const logs = data?.results || data || []
  const totalCount = data?.count || logs.length

  const handleSearchAction = async (prev, formData) => {
    const q = formData.get('search')
    setSearchParams(q ? { search: q } : {})
    setPage(1)
  }

  const { formAction: searchAction } = useFormAction(handleSearchAction, {})

  const handleExportCSV = () => {
    const headers = ['Timestamp', 'Action', 'Resource Type', 'Resource ID', 'Details']
    const rows = logs.map((l) => [
      l.created_at ? new Date(l.created_at).toISOString() : '',
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
    a.download = 'external_audit_trail.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  const columns = [
    { header: 'Timestamp', accessor: (l) => l.created_at ? new Date(l.created_at).toLocaleString() : '-', sortable: true },
    { header: 'Action', accessor: 'action', sortable: true },
    { header: 'Resource', accessor: 'resource_type' },
    { header: 'Resource ID', accessor: (l) => l.resource_id ? String(l.resource_id).slice(0, 8) + '...' : '-' },
    { header: 'Details', accessor: (l) => l.details ? JSON.stringify(l.details).slice(0, 60) + (JSON.stringify(l.details).length > 60 ? '...' : '') : '-' },
  ]

  return (
    <div>
      <header className="mb-6 flex justify-between items-start">
        <div>
          <h2 className="font-headline-lg text-display-md text-primary mb-1">Audit Trail</h2>
          <p className="text-on-surface-variant font-body-md">{totalCount} financial entries</p>
        </div>
        <button onClick={handleExportCSV} aria-label="Export CSV" className="px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold hover:bg-primary/90 transition-colors">Export CSV</button>
      </header>

      <div className="flex flex-wrap gap-3 mb-4 items-end">
        <form action={searchAction} className="flex gap-2">
          <label htmlFor="audit-search" className="sr-only">Search audit logs</label>
          <input id="audit-search" name="search" defaultValue={search} placeholder="Search..." className="px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container w-48" />
          <SubmitButton className="px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold">Search</SubmitButton>
        </form>
        <label htmlFor="audit-action-filter" className="sr-only">Filter by action</label>
        <select id="audit-action-filter" value={actionFilter} onChange={(e) => { setActionFilter(e.target.value); setPage(1) }} className="px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container">
          <option value="">All Actions</option>
          <option value="LOCK">LOCK</option>
          <option value="UNLOCK">UNLOCK</option>
          <option value="RUN">RUN</option>
          <option value="DISBURSE">DISBURSE</option>
          <option value="CREATE">CREATE</option>
          <option value="UPDATE">UPDATE</option>
          <option value="DELETE">DELETE</option>
        </select>
        <div className="flex gap-2 items-center">
          <label htmlFor="audit-date-from" className="text-label-md text-on-surface-variant">From</label>
          <input id="audit-date-from" type="date" value={dateFrom} onChange={(e) => { setDateFrom(e.target.value); setPage(1) }} className="px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container" />
          <label htmlFor="audit-date-to" className="text-label-md text-on-surface-variant">To</label>
          <input id="audit-date-to" type="date" value={dateTo} onChange={(e) => { setDateTo(e.target.value); setPage(1) }} className="px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container" />
        </div>
      </div>

      {loading ? <TableSkeleton rows={10} cols={5} /> : error ? <ErrorState message={error} action={{ label: 'Retry', onClick: refetch }} /> : (
        <DataTable
          columns={columns}
          data={logs}
          page={page}
          totalPages={Math.ceil(totalCount / 25)}
          onPageChange={setPage}
        />
      )}
    </div>
  )
}
