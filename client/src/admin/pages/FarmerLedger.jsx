import { useContext, useState, useMemo, useCallback, useRef, useEffect } from 'react'
import { useApi } from '../hooks/useApi'
import { apiFetch, exportCsv } from '../api/client'
import KpiCard from '../components/common/KpiCard'
import FilterBar from '../components/common/FilterBar'
import DataTable from '../components/common/DataTable'
import Pagination from '../components/common/Pagination'
import StatusBadge from '../components/common/StatusBadge'
import SlideOutPanel from '../components/common/SlideOutPanel'
import ConfirmModal from '../components/common/ConfirmModal'
import { AdminFilterContext } from '../contexts/AdminFilterContext'
import { useToast } from '../contexts/ToastContext'
import { KpiSkeleton, TableSkeleton } from '../components/common/Skeleton'
import LineChartCard from '../components/charts/LineChartCard'
import BarChartCard from '../components/charts/BarChartCard'

import { useLocation } from 'react-router-dom'

export default function FarmerLedger() {
  const { showToast } = useToast()
  const { period } = useContext(AdminFilterContext)
  const location = useLocation()
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [search, setSearch] = useState(new URLSearchParams(location.search).get('search') || '')
  const [filters, setFilters] = useState({})
  const [sortField, setSortField] = useState('date_joined')
  const [sortOrder, setSortOrder] = useState('desc')
  const [selectedIds, setSelectedIds] = useState([])
  const [panelOpen, setPanelOpen] = useState(false)
  const [panelFarmer, setPanelFarmer] = useState(null)
  const [modalConfig, setModalConfig] = useState({ open: false })
  const [actionLoading, setActionLoading] = useState(false)
  const [openDropdownId, setOpenDropdownId] = useState(null)
  const [createOpen, setCreateOpen] = useState(location.state?.openModal === true)
  const [createForm, setCreateForm] = useState({ first_name: '', last_name: '', email: '', phone_number: '', id_number: '', county: '', sub_county: '', ward: '', village: '', date_of_birth: '', cooperative: '' })
  const [formLoading, setFormLoading] = useState(false)
  const [editOpen, setEditOpen] = useState(false)
  const [editFarmer, setEditFarmer] = useState(null)
  const [editForm, setEditForm] = useState({ first_name: '', last_name: '', email: '', phone_number: '', id_number: '', county: '', sub_county: '', ward: '', village: '', date_of_birth: '', cooperative: '' })
  const [coopSearch, setCoopSearch] = useState('')
  const [coopOptions, setCoopOptions] = useState([])
  const [coopSearchOpen, setCoopSearchOpen] = useState(false)
  const [selectedCoopName, setSelectedCoopName] = useState('')
  const coopRef = useRef(null)
  const [editLoading, setEditLoading] = useState(false)
  const dropdownRef = useRef(null)

  useEffect(() => {
    const handler = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setOpenDropdownId(null)
      }
      if (coopRef.current && !coopRef.current.contains(e.target)) {
        setCoopSearchOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  useEffect(() => {
    if (!coopSearch || coopSearch.length < 2) { setCoopOptions([]); return }
    const timer = setTimeout(async () => {
      try {
        const res = await apiFetch(`/api/admin/cooperatives/?search=${encodeURIComponent(coopSearch)}&page_size=10`)
        const data = await res.json()
        setCoopOptions(data?.results || [])
      } catch { setCoopOptions([]) }
    }, 300)
    return () => clearTimeout(timer)
  }, [coopSearch])

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
  const { data: analytics, loading: analyticsLoading } = useApi(`/api/admin/analytics/farmers/?period=${period}`)

  const registrationTrend = useMemo(() => {
    if (!analytics?.data?.registration_monthly_series) return []
    return Object.entries(analytics.data.registration_monthly_series).map(([month, count]) => ({
      month,
      registered: count,
    }))
  }, [analytics])

  const countyData = useMemo(() => {
    if (!analytics?.data?.by_county) return []
    return Object.entries(analytics.data.by_county)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 10)
      .map(([key, val]) => ({ county: key, farmers: Number(val) }))
  }, [analytics])

  const handleSort = useCallback((field) => {
    if (sortField === field) setSortOrder(o => o === 'asc' ? 'desc' : 'asc')
    else { setSortField(field); setSortOrder('asc') }
  }, [sortField])

  const handleViewFarmer = (farmer) => {
    setPanelFarmer(farmer)
    setPanelOpen(true)
  }

  const execAction = async (url, opts = {}) => {
    setActionLoading(true)
    try {
      const res = await apiFetch(url, { method: 'POST', ...opts })
      if (!res.ok) throw new Error(await res.text())
      const msg = url.includes('activate') ? 'activated' : url.includes('deactivate') ? 'deactivated' : url.includes('delete') ? 'deleted' : 'updated'
      showToast({ type: 'success', message: `Farmer ${msg}.` })
      setOpenDropdownId(null)
      refetch()
      const result = await res.json().catch(() => ({}))
      if (panelFarmer && typeof result === 'object') {
        const { detail, message, error, status, ...updates } = result
        const safeUpdates = Object.fromEntries(
          Object.entries(updates).filter(([, v]) => v !== null && typeof v !== 'object')
        )
        if (Object.keys(safeUpdates).length > 0) {
          setPanelFarmer(prev => ({ ...prev, ...safeUpdates }))
        }
      }
      setModalConfig({ open: false })
    } catch (e) {
      showToast({ type: 'error', message: `Action failed: ${e.message}` })
    } finally {
      setActionLoading(false)
    }
  }

  const handleFarmerAction = (farmer, action) => {
    const actionMap = {
      activate: { title: 'Activate Farmer', message: `Activate ${farmer.first_name} ${farmer.last_name}?`, destructive: false },
      deactivate: { title: 'Deactivate Farmer', message: `Deactivate ${farmer.first_name} ${farmer.last_name}?`, destructive: true },
      delete: { title: 'Delete Farmer', message: `Soft-delete ${farmer.first_name} ${farmer.last_name}?`, destructive: true },
    }
    const cfg = actionMap[action]
    if (!cfg) return
    setOpenDropdownId(null)
    setModalConfig({ open: true, ...cfg, onConfirm: () => execAction(`/api/admin/farmers/${farmer.id}/${action}/`, { body: JSON.stringify({ confirm: action === 'delete' }), headers: { 'Content-Type': 'application/json' } }) })
  }

  const handleBulkAction = async (action) => {
    if (selectedIds.length === 0) return
    setModalConfig({ open: false })
    setActionLoading(true)
    try {
      await apiFetch(`/api/admin/farmers/bulk-action/`, { method: 'POST', body: JSON.stringify({ action, ids: selectedIds }) })
      setSelectedIds([])
      showToast({ type: 'success', message: `Bulk ${action} for ${selectedIds.length} farmers.` })
      refetch()
    } catch (e) {
      showToast({ type: 'error', message: `Bulk action failed: ${e.message}` })
    } finally {
      setActionLoading(false)
    }
  }

  const handleEditFarmer = async (e) => {
    e.preventDefault()
    if (!editFarmer) return
    setEditLoading(true)
    try {
      const res = await apiFetch(`/api/admin/farmers/${editFarmer.id}/`, { method: 'PATCH', body: JSON.stringify(editForm) })
      if (!res.ok) throw new Error(await res.text())
      showToast({ type: 'success', message: `Farmer ${editForm.first_name} ${editForm.last_name} updated.` })
      setEditOpen(false)
      setEditFarmer(null)
      refetch()
    } catch (e) {
      showToast({ type: 'error', message: `Update failed: ${e.message}` })
    } finally {
      setEditLoading(false)
    }
  }

  const openEditFarmer = (farmer) => {
    setEditFarmer(farmer)
    setEditForm({
      first_name: farmer.first_name || '',
      last_name: farmer.last_name || '',
      email: farmer.email || '',
      phone_number: farmer.phone_number || '',
      id_number: farmer.id_number || '',
      county: farmer.county || '',
      sub_county: farmer.sub_county || '',
      ward: farmer.ward || '',
      village: farmer.village || '',
      date_of_birth: farmer.date_of_birth || '',
      cooperative: farmer.cooperative || '',
    })
    setEditOpen(true)
  }

  const handleCreateFarmer = async (e) => {
    e.preventDefault()
    setFormLoading(true)
    try {
      const res = await apiFetch('/api/admin/farmers/', { method: 'POST', body: JSON.stringify(createForm) })
      if (!res.ok) throw new Error(await res.text())
      showToast({ type: 'success', message: `Farmer ${createForm.first_name} ${createForm.last_name} created.` })
      setCreateOpen(false)
      setCreateForm({ first_name: '', last_name: '', email: '', phone_number: '', id_number: '', county: '', sub_county: '', ward: '', village: '', date_of_birth: '', cooperative: '' })
      setSelectedCoopName('')
      setCoopSearch('')
      refetch()
    } catch (e) {
      showToast({ type: 'error', message: `Creation failed: ${e.message}` })
    } finally {
      setFormLoading(false)
    }
  }

  const toggleDropdown = (id) => setOpenDropdownId(openDropdownId === id ? null : id)

  const totalFarmers = analytics?.data?.total_active || 0
  const newFarmers = analytics?.data?.new_this_period || 0
  const regionCount = analytics?.data?.by_county ? Object.keys(analytics.data.by_county).length : 0

  const columns = useMemo(() => [
    { key: 'name', label: 'Name', sortable: true, render: (r) => <span className="font-medium">{r.first_name} {r.last_name}</span> },
    { key: 'email', label: 'Email', sortable: true, render: (r) => <span className="text-on-surface-variant">{r.email}</span> },
    { key: 'phone_number', label: 'Phone', sortable: true },
    { key: 'county', label: 'County', sortable: true },
    { key: 'id_number', label: 'ID No.', sortable: false, render: (r) => (
      <span title={r.id_number} className="max-w-[120px] truncate inline-block align-middle">
        {r.id_number}
      </span>
    ) },
    { key: 'is_active', label: 'Status', render: (r) => <StatusBadge status={r.is_active ? 'active' : 'inactive'} label={r.is_active ? 'Active' : 'Inactive'} /> },
    { key: 'date_joined', label: 'Joined', sortable: true, render: (r) => r.date_joined ? new Date(r.date_joined).toLocaleDateString() : '-' },
  ], [])

  if (error) {
    return <div className="bg-error-container text-error p-4 rounded-xl">Failed to load farmers: {error}</div>
  }

  return (
    <div ref={dropdownRef}>
      <header className="mb-6">
        <div className="flex items-center justify-between mb-1">
          <h2 className="font-headline-lg text-display-md text-primary">Farmer Ledger</h2>
          <button onClick={() => setCreateOpen(true)} className="flex items-center gap-2 px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold hover:bg-primary/90 transition-colors">
            <span className="material-symbols-outlined text-[16px]" aria-hidden="true">person_add</span>
            Register Farmer
          </button>
        </div>
        <p className="text-on-surface-variant font-body-md">Manage registered farmers across all cooperatives.</p>
      </header>

      {analyticsLoading && !analytics ? (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6"><KpiSkeleton count={4} /></div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <KpiCard icon="people" label="Total Farmers" value={data?.count || 0} />
          <KpiCard icon="person_check" label="Active" value={totalFarmers} />
          <KpiCard icon="person_add" label="New This Period" value={newFarmers} subvalue={`Across ${regionCount} counties`} />
          <KpiCard icon="map" label="Counties" value={regionCount} />
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {registrationTrend.length > 0 && (
          <LineChartCard
            title="Farmer Registration Trend"
            data={registrationTrend}
            xKey="month"
            lines={[
              { key: 'registered', name: 'New Farmers', color: '#2563eb' },
            ]}
            height={280}
            emptyMessage="No registration trend data available."
          />
        )}
        {countyData.length > 0 && (
          <BarChartCard
            title="Farmers by County (Top 10)"
            data={countyData}
            categoryKey="county"
            dataKeys={['farmers']}
            layout="horizontal"
            height={280}
            emptyMessage="No county data available."
          />
        )}
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
        onExport={() => { const p = new URLSearchParams(); if (search) p.set('search', search); if (filters.is_active) p.set('is_active', filters.is_active); p.set('export', 'csv'); exportCsv(`/api/admin/farmers/?${p}`) }}
      />

      {selectedIds.length > 0 && (
        <div className="flex items-center gap-3 mb-4 px-4 py-2 bg-primary-container/50 border border-primary-container rounded-lg">
          <span className="text-label-md font-medium text-on-primary-container">{selectedIds.length} selected</span>
          <button onClick={() => setModalConfig({ open: true, title: 'Activate Farmers', message: `Activate ${selectedIds.length} farmers?`, onConfirm: () => handleBulkAction('activate'), destructive: false })} className="px-3 py-1 text-label-md font-bold bg-primary text-on-primary rounded-lg hover:bg-primary/90 transition-colors">Activate</button>
          <button onClick={() => setModalConfig({ open: true, title: 'Deactivate Farmers', message: `Deactivate ${selectedIds.length} farmers?`, onConfirm: () => handleBulkAction('deactivate'), destructive: true })} className="px-3 py-1 text-label-md font-bold bg-error text-on-error rounded-lg hover:bg-error/90 transition-colors">Deactivate</button>
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
        emptyMessage="No farmers found matching your criteria."
        rowActions={(farmer) => (
          <div className="relative flex items-center">
            <button onClick={() => handleViewFarmer(farmer)} className="p-1.5 rounded-lg hover:bg-surface-container-high text-on-surface-variant hover:text-primary transition-colors" aria-label="View farmer details">
              <span className="material-symbols-outlined text-[18px]" aria-hidden="true">visibility</span>
            </button>
            <button onClick={() => toggleDropdown(farmer.id)} className={`p-1.5 rounded-lg hover:bg-surface-container-high text-on-surface-variant transition-colors ${openDropdownId === farmer.id ? 'opacity-100' : ''}`} aria-label="Farmer actions" aria-haspopup="true" aria-expanded={openDropdownId === farmer.id}>
              <span className="material-symbols-outlined text-[18px]" aria-hidden="true">more_vert</span>
            </button>
            {openDropdownId === farmer.id && (
              <div className="absolute right-0 top-full mt-1 w-44 bg-surface-container-lowest border border-outline-variant rounded-lg shadow-lg z-50 py-1" role="menu">
                <button onClick={() => { setOpenDropdownId(null); openEditFarmer(farmer) }} role="menuitem" className="flex items-center gap-2 w-full px-3 py-2 text-label-md text-on-surface hover:bg-surface-container-high transition-colors">
                  <span className="material-symbols-outlined text-[16px]" aria-hidden="true">edit</span>Edit
                </button>
                {farmer.is_active ? (
                  <button onClick={() => handleFarmerAction(farmer, 'deactivate')} role="menuitem" className="flex items-center gap-2 w-full px-3 py-2 text-label-md text-on-surface hover:bg-surface-container-high transition-colors">
                    <span className="material-symbols-outlined text-[16px]" aria-hidden="true">block</span>Deactivate
                  </button>
                ) : (
                  <button onClick={() => handleFarmerAction(farmer, 'activate')} role="menuitem" className="flex items-center gap-2 w-full px-3 py-2 text-label-md text-on-surface hover:bg-surface-container-high transition-colors">
                    <span className="material-symbols-outlined text-[16px]" aria-hidden="true">check_circle</span>Activate
                  </button>
                )}
                <div className="border-t border-outline-variant my-1" />
                <button onClick={() => handleFarmerAction(farmer, 'delete')} role="menuitem" className="flex items-center gap-2 w-full px-3 py-2 text-label-md text-error hover:bg-error-container transition-colors">
                  <span className="material-symbols-outlined text-[16px]" aria-hidden="true">delete</span>Delete
                </button>
              </div>
            )}
          </div>
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
              <div className="p-3 bg-surface-container rounded-lg"><p className="text-[10px] uppercase font-bold text-on-surface-variant">Email</p><p className="font-body-md text-on-surface">{panelFarmer.email || '-'}</p></div>
              <div className="p-3 bg-surface-container rounded-lg"><p className="text-[10px] uppercase font-bold text-on-surface-variant">Phone</p><p className="font-body-md text-on-surface">{panelFarmer.phone_number || '-'}</p></div>
              <div className="p-3 bg-surface-container rounded-lg"><p className="text-[10px] uppercase font-bold text-on-surface-variant">County</p><p className="font-body-md text-on-surface">{panelFarmer.county || '-'}</p></div>
              <div className="p-3 bg-surface-container rounded-lg"><p className="text-[10px] uppercase font-bold text-on-surface-variant">Sub-County</p><p className="font-body-md text-on-surface">{panelFarmer.sub_county || '-'}</p></div>
              <div className="p-3 bg-surface-container rounded-lg"><p className="text-[10px] uppercase font-bold text-on-surface-variant">ID Number</p><p className="font-body-md text-on-surface">{panelFarmer.id_number || '-'}</p></div>
              <div className="p-3 bg-surface-container rounded-lg"><p className="text-[10px] uppercase font-bold text-on-surface-variant">Joined</p><p className="font-body-md text-on-surface">{panelFarmer.date_joined ? new Date(panelFarmer.date_joined).toLocaleDateString() : '-'}</p></div>
            </div>
            {panelFarmer.primary_membership && (
              <div className="p-3 bg-surface-container rounded-lg">
                <p className="text-[10px] uppercase font-bold text-on-surface-variant mb-1">Primary Membership</p>
                <p className="font-body-md text-on-surface">Member #{panelFarmer.primary_membership.member_number}</p>
                <p className="text-label-md text-on-surface-variant">{panelFarmer.primary_membership.payment_method}</p>
              </div>
            )}
            <div className="pt-2 flex gap-2">
              <button onClick={() => { setPanelOpen(false); handleFarmerAction(panelFarmer, panelFarmer.is_active ? 'deactivate' : 'activate') }} className={`flex-1 px-4 py-2 rounded-lg text-label-md font-bold ${panelFarmer.is_active ? 'border border-error text-error hover:bg-error-container' : 'bg-primary text-on-primary hover:bg-primary/90'}`}>
                {panelFarmer.is_active ? 'Deactivate' : 'Activate'}
              </button>
              <button onClick={() => { setPanelOpen(false); handleFarmerAction(panelFarmer, 'delete') }} className="flex-1 px-4 py-2 border border-outline-variant text-on-surface-variant rounded-lg text-label-md font-bold hover:bg-surface-container transition-colors">
                Delete
              </button>
            </div>
          </div>
        )}
      </SlideOutPanel>

      <ConfirmModal open={modalConfig.open} title={modalConfig.title} message={modalConfig.message} onConfirm={modalConfig.onConfirm} onCancel={() => setModalConfig({ open: false })} loading={actionLoading} destructive={modalConfig.destructive} />

      {editOpen && (
        <div className="fixed inset-0 z-[65] flex items-center justify-center" role="presentation">
          <div className="fixed inset-0 bg-black/30" onClick={() => { setEditOpen(false); setEditFarmer(null) }} />
          <div className="relative bg-surface-container-lowest border border-outline-variant rounded-xl p-6 max-w-lg w-full mx-4 shadow-xl max-h-[90vh] overflow-y-auto" role="dialog" aria-modal="true" aria-labelledby="edit-farmer-title">
            <h3 id="edit-farmer-title" className="font-headline-sm text-headline-sm text-on-surface mb-2">Edit Farmer</h3>
            <p className="text-body-md text-on-surface-variant mb-4">Update farmer details.</p>
            <form onSubmit={handleEditFarmer} className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div><label htmlFor="farmer-edit-firstname" className="block text-label-md font-bold text-on-surface-variant mb-1">First Name</label><input id="farmer-edit-firstname" required value={editForm.first_name} onChange={(e) => setEditForm(f => ({ ...f, first_name: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
                <div><label htmlFor="farmer-edit-lastname" className="block text-label-md font-bold text-on-surface-variant mb-1">Last Name</label><input id="farmer-edit-lastname" required value={editForm.last_name} onChange={(e) => setEditForm(f => ({ ...f, last_name: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div><label htmlFor="farmer-edit-email" className="block text-label-md font-bold text-on-surface-variant mb-1">Email</label><input id="farmer-edit-email" type="email" value={editForm.email} onChange={(e) => setEditForm(f => ({ ...f, email: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
                <div><label htmlFor="farmer-edit-phone" className="block text-label-md font-bold text-on-surface-variant mb-1">Phone</label><input id="farmer-edit-phone" required value={editForm.phone_number} onChange={(e) => setEditForm(f => ({ ...f, phone_number: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div><label htmlFor="farmer-edit-id" className="block text-label-md font-bold text-on-surface-variant mb-1">ID Number</label><input id="farmer-edit-id" value={editForm.id_number} onChange={(e) => setEditForm(f => ({ ...f, id_number: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
                <div><label htmlFor="farmer-edit-dob" className="block text-label-md font-bold text-on-surface-variant mb-1">Date of Birth</label><input id="farmer-edit-dob" type="date" value={editForm.date_of_birth} onChange={(e) => setEditForm(f => ({ ...f, date_of_birth: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div><label htmlFor="farmer-edit-county" className="block text-label-md font-bold text-on-surface-variant mb-1">County</label><input id="farmer-edit-county" value={editForm.county} onChange={(e) => setEditForm(f => ({ ...f, county: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
                <div><label htmlFor="farmer-edit-subcounty" className="block text-label-md font-bold text-on-surface-variant mb-1">Sub-County</label><input id="farmer-edit-subcounty" value={editForm.sub_county} onChange={(e) => setEditForm(f => ({ ...f, sub_county: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div><label htmlFor="farmer-edit-ward" className="block text-label-md font-bold text-on-surface-variant mb-1">Ward</label><input id="farmer-edit-ward" value={editForm.ward} onChange={(e) => setEditForm(f => ({ ...f, ward: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
                <div><label htmlFor="farmer-edit-village" className="block text-label-md font-bold text-on-surface-variant mb-1">Village</label><input id="farmer-edit-village" value={editForm.village} onChange={(e) => setEditForm(f => ({ ...f, village: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button type="button" onClick={() => { setEditOpen(false); setEditFarmer(null) }} className="px-4 py-2 rounded-lg text-label-md font-bold text-on-surface-variant bg-surface-container-high hover:bg-surface-container-highest transition-colors">Cancel</button>
                <button type="submit" disabled={editLoading} className="px-4 py-2 rounded-lg text-label-md font-bold text-white bg-primary hover:bg-primary/90 disabled:opacity-50">{editLoading ? 'Saving...' : 'Save'}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {createOpen && (
        <div className="fixed inset-0 z-[65] flex items-center justify-center" role="presentation">
          <div className="fixed inset-0 bg-black/30" onClick={() => { if (!formLoading) { setCreateOpen(false); setSelectedCoopName(''); setCoopSearch('') } }} />
          <div className="relative bg-surface-container-lowest border border-outline-variant rounded-xl p-6 max-w-lg w-full mx-4 shadow-xl max-h-[90vh] overflow-y-auto" role="dialog" aria-modal="true" aria-labelledby="create-farmer-title">
            <h3 id="create-farmer-title" className="font-headline-sm text-headline-sm text-on-surface mb-2">Register Farmer</h3>
            <p className="text-body-md text-on-surface-variant mb-4">Create a new farmer record and user account.</p>
            <form onSubmit={handleCreateFarmer} className="space-y-3">
              <div ref={coopRef} className="relative">
                <label htmlFor="farmer-create-coop" className="block text-label-md font-bold text-on-surface-variant mb-1">Cooperative *</label>
                <input
                  id="farmer-create-coop"
                  type="text"
                  value={selectedCoopName || coopSearch}
                  onChange={(e) => { setCoopSearch(e.target.value); setSelectedCoopName(''); setCreateForm(f => ({ ...f, cooperative: '' })); setCoopSearchOpen(true) }}
                  onFocus={() => { if (coopSearch.length >= 2) setCoopSearchOpen(true) }}
                  placeholder="Search cooperative..."
                  className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 pr-10 text-body-md text-on-surface placeholder:text-on-surface-variant"
                  disabled={formLoading}
                  autoComplete="off"
                  aria-autocomplete="list"
                  aria-controls="coop-search-list"
                />
                {coopSearchOpen && coopOptions.length > 0 && (
                  <div id="coop-search-list" className="absolute z-10 mt-1 w-full bg-surface-container-lowest border border-outline-variant rounded-lg shadow-lg max-h-48 overflow-y-auto" role="listbox">
                    {coopOptions.map(c => (
                      <button
                        key={c.id}
                        type="button"
                        role="option"
                        aria-selected="false"
                        onClick={() => { setSelectedCoopName(`${c.name} (${c.registration_number})`); setCreateForm(ff => ({ ...ff, cooperative: c.id })); setCoopSearchOpen(false); setCoopSearch('') }}
                        className="w-full text-left px-3 py-2 text-body-md text-on-surface hover:bg-surface-container transition-colors"
                      >
                        {c.name}
                        <span className="text-on-surface-variant text-label-sm ml-2">{c.registration_number}</span>
                      </button>
                    ))}
                  </div>
                )}
                {coopSearchOpen && coopSearch.length >= 2 && coopOptions.length === 0 && (
                  <div className="absolute z-10 mt-1 w-full bg-surface-container-lowest border border-outline-variant rounded-lg shadow-lg p-3 text-center text-on-surface-variant text-body-md">
                    No cooperatives found.
                  </div>
                )}
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div><label htmlFor="farmer-create-firstname" className="block text-label-md font-bold text-on-surface-variant mb-1">First Name *</label><input id="farmer-create-firstname" required value={createForm.first_name} onChange={(e) => setCreateForm(f => ({ ...f, first_name: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
                <div><label htmlFor="farmer-create-lastname" className="block text-label-md font-bold text-on-surface-variant mb-1">Last Name *</label><input id="farmer-create-lastname" required value={createForm.last_name} onChange={(e) => setCreateForm(f => ({ ...f, last_name: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div><label htmlFor="farmer-create-email" className="block text-label-md font-bold text-on-surface-variant mb-1">Email</label><input id="farmer-create-email" type="email" value={createForm.email} onChange={(e) => setCreateForm(f => ({ ...f, email: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
                <div><label htmlFor="farmer-create-phone" className="block text-label-md font-bold text-on-surface-variant mb-1">Phone *</label><input id="farmer-create-phone" required value={createForm.phone_number} onChange={(e) => setCreateForm(f => ({ ...f, phone_number: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div><label htmlFor="farmer-create-id" className="block text-label-md font-bold text-on-surface-variant mb-1">ID Number</label><input id="farmer-create-id" value={createForm.id_number} onChange={(e) => setCreateForm(f => ({ ...f, id_number: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
                <div><label htmlFor="farmer-create-dob" className="block text-label-md font-bold text-on-surface-variant mb-1">Date of Birth</label><input id="farmer-create-dob" type="date" value={createForm.date_of_birth} onChange={(e) => setCreateForm(f => ({ ...f, date_of_birth: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div><label htmlFor="farmer-create-county" className="block text-label-md font-bold text-on-surface-variant mb-1">County *</label><input id="farmer-create-county" required value={createForm.county} onChange={(e) => setCreateForm(f => ({ ...f, county: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
                <div><label htmlFor="farmer-create-subcounty" className="block text-label-md font-bold text-on-surface-variant mb-1">Sub-County</label><input id="farmer-create-subcounty" value={createForm.sub_county} onChange={(e) => setCreateForm(f => ({ ...f, sub_county: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div><label htmlFor="farmer-create-ward" className="block text-label-md font-bold text-on-surface-variant mb-1">Ward</label><input id="farmer-create-ward" value={createForm.ward} onChange={(e) => setCreateForm(f => ({ ...f, ward: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
                <div><label htmlFor="farmer-create-village" className="block text-label-md font-bold text-on-surface-variant mb-1">Village</label><input id="farmer-create-village" value={createForm.village} onChange={(e) => setCreateForm(f => ({ ...f, village: e.target.value }))} className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface" /></div>
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button type="button" onClick={() => { setCreateOpen(false); setSelectedCoopName(''); setCoopSearch('') }} className="px-4 py-2 rounded-lg text-label-md font-bold text-on-surface-variant bg-surface-container-high hover:bg-surface-container-highest transition-colors">Cancel</button>
                <button type="submit" disabled={formLoading || !createForm.cooperative} className="px-4 py-2 rounded-lg text-label-md font-bold text-white bg-primary hover:bg-primary/90 disabled:opacity-50">{formLoading ? 'Creating...' : 'Register'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
