import { CHART_DEFAULTS } from './chartTheme'

export default function ChartCard({ title, subtitle, action, children, empty, emptyMessage = 'No data available.' }) {
  return (
    <div className="bg-white/70 backdrop-blur-md border border-outline-variant/35 p-6 rounded-2xl shadow-[0_8px_30px_rgba(0,0,0,0.015)]">
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
