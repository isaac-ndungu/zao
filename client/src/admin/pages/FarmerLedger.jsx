import { useContext, useState, useMemo, useCallback } from 'react'
import { useApi } from '../hooks/useApi'
import { apiFetch } from '../api/client'
import KpiCard from '../components/common/KpiCard'
import FilterBar from '../components/common/FilterBar'
import DataTable from '../components/common/DataTable'
import Pagination from '../components/common/Pagination'
import StatusBadge from '../components/common/StatusBadge'
import SlideOutPanel from '../components/common/SlideOutPanel'
import ConfirmModal from '../components/common/ConfirmModal'
import { AdminFilterContext } from '../contexts/AdminFilterContext'

export default function FarmerLedger() {
  const { period } = useContext(AdminFilterContext)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [search, setSearch] = useState('')
  const [filters, setFilters] = useState({})
  const [sortField, setSortField] = useState('date_joined')
  const [sortOrder, setSortOrder] = useState('desc')
  const [selectedIds, setSelectedIds] = useState([])
  const [panelOpen, setPanelOpen] = useState(false)
  const [panelFarmer, setPanelFarmer] = useState(null)
  const [modalConfig, setModalConfig] = useState({ open: false })
  const [actionLoading, setActionLoading] = useState(false)

  const query = useMemo(() => {
    const params = new URLSearchParams()
    params.set('page', page)
    params.set('page_size', pageSize)
    if (search) params.set('search', search)
    if (filters.cooperative) params.set('cooperative', filters.cooperative)
    if (filters.is_active) params.set('is_active', filters.is_active)
    if (sortField) params.set('ordering', sortOrder === 'desc' ? `-${sortField}` : sortField)
    return params.toString()
  }, [page, pageSize, search, filters, sortField, sortOrder])

  const { data, loading, error, refetch } = useApi(`/api/admin/farmers/?${query}`)
  const { data: analytics } = useApi(`/api/admin/analytics/farmers/?period=${period}`)

  const handleSort = useCallback((field) => {
    if (sortField === field) {
      setSortOrder(o => o === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortOrder('asc')
    }
  }, [sortField])

  const handleViewFarmer = (farmer) => {
    setPanelFarmer(farmer)
    setPanelOpen(true)
  }
  // 
  const handleBulkAction = async (action) => {
    if (selectedIds.length === 0) return
    setModalConfig({ open: false })
    setActionLoading(true)
    try {
      await apiFetch(`/api/admin/farmers/bulk-action/`, {
        method: 'POST',
        body: JSON.stringify({ action, ids: selectedIds }),
      })
      setSelectedIds([])
      refetch()
    } catch (e) {
      console.error('Bulk action failed', e)
    } finally {
      setActionLoading(false)
    }
  }

  const totalFarmers = analytics?.data?.total_active || 0
  const newFarmers = analytics?.data?.new_this_period || 0
  const regionCount = analytics?.data?.by_county ? Object.keys(analytics.data.by_county).length : 0

  const columns = useMemo(() => [
    { key: 'name', label: 'Name', sortable: true, render: (r) => <span className="font-medium">{r.first_name} {r.last_name}</span> },
    { key: 'email', label: 'Email', sortable: true, render: (r) => <span className="text-on-surface-variant">{r.email}</span> },
    { key: 'phone_number', label: 'Phone', sortable: true },
    { key: 'county', label: 'County', sortable: true },
    { key: 'id_number', label: 'ID No.', sortable: false },
    { key: 'is_active', label: 'Status', render: (r) => <StatusBadge status={r.is_active ? 'active' : 'inactive'} label={r.is_active ? 'Active' : 'Inactive'} /> },
    { key: 'date_joined', label: 'Joined', sortable: true, render: (r) => r.date_joined ? new Date(r.date_joined).toLocaleDateString() : '-' },
  ], [])

  if (error) {
    return <div className="bg-error-container text-error p-4 rounded-xl">Failed to load farmers: {error}</div>
  }

  return (
    <div>
      <header className="mb-6">
        <h2 className="font-headline-lg text-display-md text-primary mb-1">Farmer Ledger</h2>
        <p className="text-on-surface-variant font-body-md">Manage registered farmers across all cooperatives.</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <KpiCard icon="people" label="Total Farmers" value={data?.count || 0} />
        <KpiCard icon="person_check" label="Active" value={totalFarmers} />
        <KpiCard icon="person_add" label="New This Period" value={newFarmers} subvalue={`Across ${regionCount} counties`} />
        <KpiCard icon="map" label="Counties" value={regionCount} />
      </div>

      <FilterBar
        search={search}
        onSearchChange={setSearch}
        placeholder="Search by name, ID, phone, email..."
        filters={[
          { key: 'is_active', label: 'Status', options: [{ value: 'true', label: 'Active' }, { value: 'false', label: 'Inactive' }] },
        ]}
        filterValues={filters}
        onFilterChange={setFilters}
        onClear={() => { setSearch(''); setFilters({}); setPage(1) }}
      />

      {selectedIds.length > 0 && (
        <div className="flex items-center gap-3 mb-4 px-4 py-2 bg-primary-container/50 border border-primary-container rounded-lg">
          <span className="text-label-md font-medium text-on-primary-container">{selectedIds.length} selected</span>
          <button
            onClick={() => setModalConfig({ open: true, title: 'Activate Farmers', message: `Activate ${selectedIds.length} farmers?`, onConfirm: () => handleBulkAction('activate'), destructive: false })}
            className="px-3 py-1 text-label-md font-bold bg-primary text-on-primary rounded-lg hover:bg-primary/90 transition-colors"
          >
            Activate
          </button>
          <button
            onClick={() => setModalConfig({ open: true, title: 'Deactivate Farmers', message: `Deactivate ${selectedIds.length} farmers?`, onConfirm: () => handleBulkAction('deactivate'), destructive: true })}
            className="px-3 py-1 text-label-md font-bold bg-error text-on-error rounded-lg hover:bg-error/90 transition-colors"
          >
            Deactivate
          </button>
          <button onClick={() => setSelectedIds([])} className="text-label-md text-on-surface-variant hover:text-on-surface ml-auto">
            Clear selection
          </button>
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
        emptyMessage="No farmers found matching your criteria."
        rowActions={(farmer) => (
          <>
            <button onClick={() => handleViewFarmer(farmer)} className="p-1.5 rounded-lg hover:bg-surface-container-high text-on-surface-variant hover:text-primary transition-colors">
              <span className="material-symbols-outlined text-[18px]">visibility</span>
            </button>
            <button className="p-1.5 rounded-lg hover:bg-surface-container-high text-on-surface-variant transition-colors">
              <span className="material-symbols-outlined text-[18px]">more_vert</span>
            </button>
          </>
        )}
      />

      <div className="mt-2">
        <Pagination page={page} pageSize={pageSize} total={data?.count || 0} onPageChange={setPage} onPageSizeChange={setPageSize} />
      </div>

      <SlideOutPanel open={panelOpen} onClose={() => { setPanelOpen(false); setPanelFarmer(null) }} title="Farmer Details">
        {panelFarmer && (
          <div className="space-y-4">
            <div className="flex items-center gap-4 mb-4">
              <div className="w-14 h-14 rounded-full bg-primary-fixed flex items-center justify-center text-primary font-bold text-lg">
                {panelFarmer.first_name?.[0]}{panelFarmer.last_name?.[0]}
              </div>
              <div>
                <h4 className="font-headline-sm text-headline-sm text-on-surface">{panelFarmer.first_name} {panelFarmer.last_name}</h4>
                <StatusBadge status={panelFarmer.is_active ? 'active' : 'inactive'} label={panelFarmer.is_active ? 'Active' : 'Inactive'} />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="p-3 bg-surface-container rounded-lg">
                <p className="text-[10px] uppercase font-bold text-on-surface-variant">Email</p>
                <p className="font-body-md text-on-surface">{panelFarmer.email || '-'}</p>
              </div>
              <div className="p-3 bg-surface-container rounded-lg">
                <p className="text-[10px] uppercase font-bold text-on-surface-variant">Phone</p>
                <p className="font-body-md text-on-surface">{panelFarmer.phone_number || '-'}</p>
              </div>
              <div className="p-3 bg-surface-container rounded-lg">
                <p className="text-[10px] uppercase font-bold text-on-surface-variant">County</p>
                <p className="font-body-md text-on-surface">{panelFarmer.county || '-'}</p>
              </div>
              <div className="p-3 bg-surface-container rounded-lg">
                <p className="text-[10px] uppercase font-bold text-on-surface-variant">Sub-County</p>
                <p className="font-body-md text-on-surface">{panelFarmer.sub_county || '-'}</p>
              </div>
              <div className="p-3 bg-surface-container rounded-lg">
                <p className="text-[10px] uppercase font-bold text-on-surface-variant">ID Number</p>
                <p className="font-body-md text-on-surface">{panelFarmer.id_number || '-'}</p>
              </div>
              <div className="p-3 bg-surface-container rounded-lg">
                <p className="text-[10px] uppercase font-bold text-on-surface-variant">Joined</p>
                <p className="font-body-md text-on-surface">{panelFarmer.date_joined ? new Date(panelFarmer.date_joined).toLocaleDateString() : '-'}</p>
              </div>
            </div>
            {panelFarmer.primary_membership && (
              <div className="p-3 bg-surface-container rounded-lg">
                <p className="text-[10px] uppercase font-bold text-on-surface-variant mb-1">Primary Membership</p>
                <p className="font-body-md text-on-surface">Member #{panelFarmer.primary_membership.member_number}</p>
                <p className="text-label-md text-on-surface-variant">{panelFarmer.primary_membership.payment_method}</p>
              </div>
            )}
            <div className="pt-2 flex gap-2">
              <button className="flex-1 px-4 py-2 border border-primary text-primary rounded-lg text-label-md font-bold hover:bg-primary/5 transition-colors">
                Edit Farmer
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
    </div>
  )
}
