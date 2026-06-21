import { useState } from 'react'

export default function FilterBar({ search, onSearchChange, filters = [], filterValues = {}, onFilterChange, onClear, onExport, placeholder = 'Search...' }) {
  const [localSearch, setLocalSearch] = useState(search || '')

  const handleSearchChange = (e) => {
    setLocalSearch(e.target.value)
  }

  const handleSearchKeyDown = (e) => {
    if (e.key === 'Enter') {
      onSearchChange(localSearch)
    }
  }

  const handleClear = () => {
    setLocalSearch('')
    onClear()
  }

  const hasActiveFilters = localSearch || Object.values(filterValues).some(v => v && v !== '')

  return (
    <div className="flex flex-wrap items-center gap-3 mb-4">
      <div className="relative flex-1 min-w-[200px] max-w-sm">
        <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-[18px]">
          search
        </span>
        
        <input
          type="text"
          value={localSearch}
          onChange={handleSearchChange}
          onKeyDown={handleSearchKeyDown}
          placeholder={placeholder}
          className="w-full bg-surface-container border border-outline-variant rounded-lg py-2 pl-9 pr-3 text-body-md text-on-surface placeholder:text-on-surface-variant/60 focus:outline-none focus:ring-1 focus:ring-primary"
        />

      </div>


      {filters.map((filter) => (
        <select
          key={filter.key}
          value={filterValues[filter.key] || ''}
          onChange={(e) => onFilterChange({ ...filterValues, [filter.key]: e.target.value })}
          className="bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface-variant focus:outline-none focus:ring-1 focus:ring-primary"
        >

          <option value="">{filter.label}</option>

          {filter.options.map(opt => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
          
        </select>
      ))}
      <div className="flex items-center gap-1 ml-auto">
        {hasActiveFilters && (
          <button
            onClick={handleClear}
            className="flex items-center gap-1 px-3 py-2 text-label-md font-bold text-on-surface-variant hover:text-error transition-colors"
          >
            <span className="material-symbols-outlined text-[16px]">close</span>
            Clear
          </button>
        )}
        {onExport && (
          <button
            onClick={onExport}
            className="flex items-center gap-1.5 px-3 py-2 text-label-md font-bold text-on-surface-variant hover:text-primary transition-colors cursor-pointer"
            title="Export CSV"
          >
            <span className="material-symbols-outlined text-[18px]">download</span>
            <span className="hidden sm:inline">Export</span>
          </button>
        )}
      </div>
    </div>
  )
}
