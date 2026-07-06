export default function DataTable({ columns, data = [], selectedIds = [], onSelectionChange, sortField, sortOrder, onSort, loading, emptyMessage = 'No records found.', rowActions, onRowClick }) {
  const allSelected = data.length > 0 && data.every(row => selectedIds.includes(row.id))
  const someSelected = !allSelected && data.some(row => selectedIds.includes(row.id))

  const handleSelectAll = () => {
    if (allSelected) {
      onSelectionChange([])
    } else {
      onSelectionChange(data.map(r => r.id))
    }
  }

  const handleSelectRow = (id) => {
    if (selectedIds.includes(id)) {
      onSelectionChange(selectedIds.filter(i => i !== id))
    } else {
      onSelectionChange([...selectedIds, id])
    }
  }

  if (loading) {
    return (
      <div className="bg-surface-container-lowest border border-outline-variant rounded-xl overflow-hidden">
        <div className="p-8 flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" role="status" aria-label="Loading data" />
        </div>
      </div>
    )
  }

  return (
    <div className="bg-surface-container-lowest border border-outline-variant rounded-xl overflow-hidden">
      <div className="overflow-x-auto min-w-0">
        <table className="w-full min-w-[800px]">
          <thead>
            <tr className="border-b border-outline-variant bg-surface-container">
              {onSelectionChange && (
                <th className="w-10 px-4 py-3 text-left">
                  <input
                    type="checkbox"
                    checked={allSelected}
                    ref={(el) => { if (el) el.indeterminate = someSelected }}
                    onChange={handleSelectAll}
                    className="accent-primary rounded"
                    aria-label={someSelected ? 'Select some rows' : allSelected ? 'Deselect all rows' : 'Select all rows'}
                  />
                </th>
              )}
              {columns.map((col) => (
                <th
                  key={col.key}
                  className={`px-4 py-3 text-left text-label-md font-bold text-on-surface-variant uppercase tracking-wider ${col.sortable ? 'cursor-pointer hover:text-on-surface select-none' : ''
                    }`}
                  onClick={() => {
                    if (col.sortable && onSort) {
                      onSort(col.key, sortField === col.key && sortOrder === 'asc' ? 'desc' : 'asc')
                    }
                  }}
                  aria-sort={col.sortable && sortField === col.key ? (sortOrder === 'asc' ? 'ascending' : 'descending') : col.sortable ? 'none' : undefined}
                >
                  <span className="flex items-center gap-1">
                    {col.sortable && (
                      <span className="sr-only">{sortField === col.key ? `Sorted by ${col.label} ${sortOrder === 'asc' ? 'ascending' : 'descending'}. Select to ${sortOrder === 'asc' ? 'sort descending' : 'sort ascending'}` : `Sort by ${col.label}`}</span>
                    )}
                    {col.label}
                    {col.sortable && sortField === col.key && (
                      <span className="material-symbols-outlined text-[14px]" aria-hidden="true">
                        {sortOrder === 'asc' ? 'arrow_upward' : 'arrow_downward'}
                      </span>
                    )}
                  </span>
                </th>
              ))}
              {rowActions && <th className="w-16 px-4 py-3" />}
            </tr>
          </thead>
          <tbody>
              {data.length === 0 ? (
              <tr>
                <td colSpan={columns.length + (onSelectionChange ? 1 : 0) + (rowActions ? 1 : 0)} className="px-4 py-12 text-center text-body-md text-on-surface-variant">
                  <span className="material-symbols-outlined text-[32px] block mb-2 text-outline-variant" aria-hidden="true">inbox</span>
                  <span className="sr-only">No data:</span> {emptyMessage}
                </td>
              </tr>
            ) : data.filter(row => row != null).map((row, idx) => (
              <tr
                key={row.id}
                className={`group border-b border-outline-variant/50 transition-colors ${idx % 2 === 0 ? 'bg-surface-container-lowest' : 'bg-surface-container'
                  } ${onRowClick ? 'cursor-pointer hover:bg-surface-container-high' : ''}`}
                onClick={() => onRowClick?.(row)}
              >
                {onSelectionChange && (
                  <td className="px-4 py-3">
                    <input
                      type="checkbox"
                      checked={selectedIds.includes(row.id)}
                      onChange={() => handleSelectRow(row.id)}
                      className="accent-primary rounded"
                      onClick={(e) => e.stopPropagation()}
                      aria-label={`Select row ${row.id}`}
                    />
                  </td>
                )}
                {columns.map((col) => (
                  <td key={col.key} className="px-4 py-3 text-body-md text-on-surface">
                    {col.render ? col.render(row) : row?.[col.key]}
                  </td>
                ))}
                {rowActions && (
                  <td className="px-4 py-3 text-right" onClick={(e) => e.stopPropagation()}>
                    <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-150">
                      {rowActions(row)}
                    </div>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
