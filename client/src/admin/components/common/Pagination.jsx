export default function Pagination({ page, pageSize, total, onPageChange, onPageSizeChange }) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  const start = total === 0 ? 0 : (page - 1) * pageSize + 1
  const end = Math.min(page * pageSize, total)

  return (
    <div className="flex items-center justify-between px-4 py-3 border-t border-outline-variant">
      <div className="flex items-center gap-3">
        <span className="text-label-md text-on-surface-variant" aria-live="polite">
          {start}–{end} of {total}
        </span>
        <label className="sr-only" htmlFor="page-size-select">Items per page</label>
        <select
          id="page-size-select"
          value={pageSize}
          onChange={(e) => { onPageSizeChange(Number(e.target.value)); onPageChange(1) }}
          className="bg-surface-container border border-outline-variant rounded-lg px-2 py-1 text-label-md text-on-surface-variant"
        >
          {[10, 20, 50, 100].map(n => (
            <option key={n} value={n}>{n} / page</option>
          ))}
        </select>
      </div>
      <div className="flex items-center gap-1">
        <button
          onClick={() => onPageChange(1)}
          disabled={page <= 1}
          className="p-1.5 rounded-lg hover:bg-surface-container-high disabled:opacity-30 text-on-surface-variant transition-colors"
          aria-label="Go to first page"
        >
          <span className="material-symbols-outlined text-[18px]" aria-hidden="true">first_page</span>
        </button>
        <button
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
          className="p-1.5 rounded-lg hover:bg-surface-container-high disabled:opacity-30 text-on-surface-variant transition-colors"
          aria-label="Go to previous page"
        >
          <span className="material-symbols-outlined text-[18px]" aria-hidden="true">chevron_left</span>
        </button>
        {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
          let pageNum
          if (totalPages <= 5) {
            pageNum = i + 1
          } else if (page <= 3) {
            pageNum = i + 1
          } else if (page >= totalPages - 2) {
            pageNum = totalPages - 4 + i
          } else {
            pageNum = page - 2 + i
          }
          return (
            <button
              key={pageNum}
              onClick={() => onPageChange(pageNum)}
              className={`w-8 h-8 rounded-lg text-label-md font-bold transition-colors ${
                pageNum === page
                  ? 'bg-primary text-on-primary'
                  : 'text-on-surface-variant hover:bg-surface-container-high'
              }`}
              aria-current={pageNum === page ? 'page' : undefined}
              aria-label={`Go to page ${pageNum}`}
            >
              {pageNum}
            </button>
          )
        })}
        <button
          onClick={() => onPageChange(page + 1)}
          disabled={page >= totalPages}
          className="p-1.5 rounded-lg hover:bg-surface-container-high disabled:opacity-30 text-on-surface-variant transition-colors"
          aria-label="Go to next page"
        >
          <span className="material-symbols-outlined text-[18px]" aria-hidden="true">chevron_right</span>
        </button>
        <button
          onClick={() => onPageChange(totalPages)}
          disabled={page >= totalPages}
          className="p-1.5 rounded-lg hover:bg-surface-container-high disabled:opacity-30 text-on-surface-variant transition-colors"
          aria-label="Go to last page"
        >
          <span className="material-symbols-outlined text-[18px]" aria-hidden="true">last_page</span>
        </button>
      </div>
    </div>
  )
}
