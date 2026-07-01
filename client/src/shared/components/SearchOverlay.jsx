export default function SearchOverlay({ results, loading, onResultClick, onViewAll }) {
  if (!results || results.length === 0) return null

  return (
    <div className="absolute left-0 right-0 top-full mt-2 bg-surface-container-lowest border border-outline-variant rounded-xl shadow-xl z-[999] overflow-hidden max-h-[70vh] overflow-y-auto">
      {loading && (
        <div className="p-3 text-center text-sm text-on-surface-variant">
          <span className="inline-block animate-spin h-4 w-4 border-2 border-primary border-t-transparent rounded-full mr-2 align-middle" />
          Searching...
        </div>
      )}

      {results.map((group) => (
        <div key={group.key}>
          <div className="px-4 py-2 text-[10px] uppercase tracking-wider text-on-surface-variant font-bold bg-surface-container/50">
            {group.label}
          </div>
          {group.items.map((item) => (
            <button
              key={`${item.type}-${item.id}`}
              onMouseDown={(e) => { e.preventDefault(); onResultClick(item) }}
              className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-surface-container transition-colors text-left"
            >
              <span className="material-symbols-outlined text-[18px] text-on-surface-variant shrink-0">{item.icon || 'search'}</span>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-on-surface truncate">{item.label}</p>
                <p className="text-xs text-on-surface-variant truncate">{item.subtitle}</p>
              </div>
            </button>
          ))}
        </div>
      ))}

      <button
        onMouseDown={(e) => { e.preventDefault(); onViewAll() }}
        className="w-full px-4 py-3 text-center text-sm font-bold text-primary hover:bg-surface-container transition-colors border-t border-outline-variant/50"
      >
        View all results
      </button>
    </div>
  )
}
