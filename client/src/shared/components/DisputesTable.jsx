import { useState } from 'react'
import DataTable from '../../admin/components/common/DataTable'
import Pagination from '../../admin/components/common/Pagination'
import StatusBadge from '../../admin/components/common/StatusBadge'
import SlideOutPanel from '../../admin/components/common/SlideOutPanel'
import ConfirmModal from '../../admin/components/common/ConfirmModal'
import { useApi } from '../../admin/hooks/useApi'
import { apiFetch } from '../../admin/api/client'
import { useToast } from '../../admin/contexts/ToastContext'

const statusColors = {
  PENDING: 'bg-warning-container text-warning',
  RESOLVED: 'bg-success-container text-success',
  REJECTED: 'bg-error-container text-error',
}

export default function DisputesTable({
  initialStatus = '',
  showResolve = true,
  showGrade = true,
  readOnly = false,
  title = 'Disputes',
  emptyMessage = 'No disputes found.'
}) {
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [selectedItem, setSelectedItem] = useState(null)
  const [resolveItem, setResolveItem] = useState(null)
  const [resolveData, setResolveData] = useState({ status: 'RESOLVED', resolution_notes: '' })
  const [filterStatus, setFilterStatus] = useState(initialStatus)
  const { showToast } = useToast()

  const params = new URLSearchParams({ page, page_size: pageSize })
  if (filterStatus) params.append('status', filterStatus)

  const { data, loading, error, refetch } = useApi(`/api/disputes/?${params}`)
  const disputes = data?.results || []

  const handleResolve = async () => {
    if (!resolveItem) return
    try {
      const res = await apiFetch(`/api/disputes/${resolveItem.id}/resolve/`, {
        method: 'POST',
        body: JSON.stringify(resolveData)
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Failed to resolve dispute')
      }
      showToast({ type: 'success', message: 'Dispute resolved successfully.' })
      setResolveItem(null)
      setResolveData({ status: 'RESOLVED', resolution_notes: '' })
      refetch()
    } catch (err) {
      showToast({ type: 'error', message: err.message })
    }
  }

  const columns = [
    {
      key: 'id',
      label: 'ID',
      render: (v, row) => (
        <span className="font-mono text-xs">{row.id?.slice(0, 8) || '-'}</span>
      )
    },
    ...(showGrade ? [{
      key: 'grade',
      label: 'Grade',
      render: (v, row) => row.grade ? (
        <div className="text-sm">
          <span className="font-semibold">{row.grade.grade_letter}</span>
          <span className="text-on-surface-variant ml-1 text-xs">
            {row.grade.delivery_id?.slice(0, 8) || ''}
          </span>
        </div>
      ) : '-'
    }] : []),
    {
      key: 'status',
      label: 'Status',
      render: (v) => (
        <span className={`px-2 py-1 rounded-full text-xs font-bold ${statusColors[v] || 'bg-surface-container text-on-surface'}`}>
          {v}
        </span>
      )
    },
    {
      key: 'reason',
      label: 'Reason',
      render: (v) => (
        <span className="text-sm line-clamp-2 max-w-[200px]">{v || '-'}</span>
      )
    },
    {
      key: 'raised_by',
      label: 'Raised By',
      render: (v) => v ? (
        <span className="text-sm">{v.name || v.first_name + ' ' + v.last_name || v.phone_number || v.id?.slice(0, 8)}</span>
      ) : '-'
    },
    {
      key: 'created_at',
      label: 'Date',
      render: (v) => v ? new Date(v).toLocaleDateString() : '-'
    },
    ...(readOnly ? [] : [{
      key: 'actions',
      label: '',
      render: (v, row) => (
        <div className="flex items-center justify-end gap-1">
          <button
            onClick={() => setSelectedItem(row)}
            className="p-1.5 text-on-surface-variant hover:text-primary transition-colors"
            title="View details"
          >
            <span className="material-symbols-outlined text-[18px]">visibility</span>
          </button>
          {!readOnly && row.status === 'PENDING' && (
            <button
              onClick={() => { setResolveItem(row); setResolveData({ status: 'RESOLVED', resolution_notes: '' }) }}
              className="p-1.5 text-on-surface-variant hover:text-primary transition-colors"
              title="Resolve"
            >
              <span className="material-symbols-outlined text-[18px]">check_circle</span>
            </button>
          )}
        </div>
      )
    }]),
    ...(readOnly ? [{
      key: 'actions',
      label: '',
      render: (v, row) => (
        <button
          onClick={() => setSelectedItem(row)}
          className="p-1.5 text-on-surface-variant hover:text-primary transition-colors"
          title="View details"
        >
          <span className="material-symbols-outlined text-[18px]">visibility</span>
        </button>
      )
    }] : [])
  ]

  return (
    <div>
      {!readOnly && (
        <div className="flex gap-2 mb-4">
          {['', 'PENDING', 'RESOLVED', 'REJECTED'].map(status => (
            <button
              key={status}
              onClick={() => { setFilterStatus(status); setPage(1) }}
              className={`px-3 py-1.5 rounded-lg text-label-md font-bold transition-colors ${
                filterStatus === status
                  ? 'bg-primary text-on-primary'
                  : 'bg-surface-container text-on-surface-variant hover:bg-surface-container-high'
              }`}
            >
              {status || 'All'}
            </button>
          ))}
        </div>
      )}

      <DataTable
        columns={columns}
        data={disputes}
        loading={loading}
        error={error}
        onRowClick={(row) => setSelectedItem(row)}
        emptyMessage={emptyMessage}
        rowClassName="cursor-pointer"
      />

      {data?.count > pageSize && (
        <div className="mt-4 flex justify-center">
          <Pagination
            page={page}
            totalPages={Math.ceil(data.count / pageSize)}
            onPageChange={setPage}
          />
        </div>
      )}

      {selectedItem && (
        <SlideOutPanel
          open={!!selectedItem}
          onClose={() => setSelectedItem(null)}
          title="Dispute Details"
        >
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-label-md text-on-surface-variant mb-1">Status</p>
                <StatusBadge status={selectedItem.status?.toLowerCase()} label={selectedItem.status} />
              </div>
              <div>
                <p className="text-label-md text-on-surface-variant mb-1">Date Filed</p>
                <p className="text-body-md text-on-surface">
                  {selectedItem.created_at ? new Date(selectedItem.created_at).toLocaleString() : '-'}
                </p>
              </div>
            </div>

            {showGrade && selectedItem.grade && (
              <div>
                <p className="text-label-md text-on-surface-variant mb-1">Grade</p>
                <div className="bg-surface-container rounded-lg p-3">
                  <p className="text-body-md font-semibold text-on-surface">
                    Grade: {selectedItem.grade.grade_letter}
                  </p>
                  <p className="text-label-md text-on-surface-variant">
                    Delivery: {selectedItem.grade.delivery_id?.slice(0, 8) || '-'}
                  </p>
                  <p className="text-label-md text-on-surface-variant">
                    Farmer: {selectedItem.grade.farmer_name || '-'}
                  </p>
                </div>
              </div>
            )}

            <div>
              <p className="text-label-md text-on-surface-variant mb-1">Raised By</p>
              <p className="text-body-md text-on-surface">
                {selectedItem.raised_by?.name || [selectedItem.raised_by?.first_name, selectedItem.raised_by?.last_name].filter(Boolean).join(' ') || selectedItem.raised_by?.phone_number || '-'}
              </p>
            </div>

            <div>
              <p className="text-label-md text-on-surface-variant mb-1">Reason</p>
              <p className="text-body-md text-on-surface">{selectedItem.reason || '-'}</p>
            </div>

            {selectedItem.resolved_by && (
              <>
                <div className="border-t border-outline-variant pt-4">
                  <p className="text-label-md text-on-surface-variant mb-1">Resolved By</p>
                  <p className="text-body-md text-on-surface">
                    {[selectedItem.resolved_by?.first_name, selectedItem.resolved_by?.last_name].filter(Boolean).join(' ') || '-'}
                  </p>
                </div>
                <div>
                  <p className="text-label-md text-on-surface-variant mb-1">Resolution Notes</p>
                  <p className="text-body-md text-on-surface">{selectedItem.resolution_notes || '-'}</p>
                </div>
                <div>
                  <p className="text-label-md text-on-surface-variant mb-1">Resolved At</p>
                  <p className="text-body-md text-on-surface">
                    {selectedItem.resolved_at ? new Date(selectedItem.resolved_at).toLocaleString() : '-'}
                  </p>
                </div>
              </>
            )}
          </div>
        </SlideOutPanel>
      )}

      {resolveItem && (
        <ConfirmModal
          open={!!resolveItem}
          onClose={() => setResolveItem(null)}
          title="Resolve Dispute"
          message={
            <div className="space-y-4">
              <p className="text-body-md text-on-surface">How would you like to resolve this dispute?</p>
              <div className="flex gap-3">
                <button
                  onClick={() => setResolveData(d => ({ ...d, status: 'RESOLVED' }))}
                  className={`flex-1 px-4 py-3 rounded-lg border-2 transition-colors ${
                    resolveData.status === 'RESOLVED'
                      ? 'border-success bg-success-container text-success'
                      : 'border-outline-variant text-on-surface-variant hover:border-success'
                  }`}
                >
                  <span className="material-symbols-outlined text-xl mb-1">check_circle</span>
                  <p className="text-label-md font-bold">Resolved</p>
                </button>
                <button
                  onClick={() => setResolveData(d => ({ ...d, status: 'REJECTED' }))}
                  className={`flex-1 px-4 py-3 rounded-lg border-2 transition-colors ${
                    resolveData.status === 'REJECTED'
                      ? 'border-error bg-error-container text-error'
                      : 'border-outline-variant text-on-surface-variant hover:border-error'
                  }`}
                >
                  <span className="material-symbols-outlined text-xl mb-1">cancel</span>
                  <p className="text-label-md font-bold">Rejected</p>
                </button>
              </div>
              <div>
                <label className="block text-label-md text-on-surface-variant mb-1">Resolution Notes (optional)</label>
                <textarea
                  value={resolveData.resolution_notes}
                  onChange={(e) => setResolveData(d => ({ ...d, resolution_notes: e.target.value }))}
                  placeholder="Add notes about your decision..."
                  rows={3}
                  className="w-full px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container resize-none"
                />
              </div>
            </div>
          }
          confirmLabel="Submit Resolution"
          cancelLabel="Cancel"
          onConfirm={handleResolve}
          loading={false}
        />
      )}
    </div>
  )
}
