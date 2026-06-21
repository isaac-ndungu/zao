import { CHART_DEFAULTS } from './chartTheme'

export default function ChartCard({ title, subtitle, action, children, empty, emptyMessage = 'No data available.' }) {
  return (
    <div className="bg-surface-container-lowest border border-outline-variant p-6 rounded-xl">
      {(title || action) && (
        <div className="flex items-center justify-between mb-6">
          <div>
            {title && <h4 className="font-headline-sm text-headline-sm text-on-surface">{title}</h4>}
            {subtitle && <p className="text-label-md text-on-surface-variant mt-0.5">{subtitle}</p>}
          </div>
          {action && <div>{action}</div>}
        </div>
      )}
      {empty ? (
        <div className="flex flex-col items-center justify-center py-12 text-on-surface-variant">
          <span className="material-symbols-outlined text-[40px] mb-2 text-outline-variant">bar_chart</span>
          <p className="text-body-md">{emptyMessage}</p>
        </div>
      ) : (
        children
      )}
    </div>
  )
}
