export default function KpiCard({ icon, label, value, subvalue, highlighted, trend, onClick }) {
  const Wrapper = onClick ? 'button' : 'div'
  
  const baseClasses = "relative p-6 rounded-2xl transition-all duration-300 ease-out text-left border"
  const clickClasses = onClick ? "cursor-pointer hover:-translate-y-1 hover:active:scale-[0.98]" : ""
  
  const styleClasses = highlighted
    ? "bg-gradient-to-br from-primary to-secondary text-white border-primary/10 shadow-[0_8px_30px_rgb(15,82,56,0.12)] " + 
      (onClick ? "hover:shadow-[0_15px_35px_rgb(15,82,56,0.22)]" : "")
    : "bg-white/80 backdrop-blur-md border-outline-variant/35 shadow-[0_8px_30px_rgb(0,0,0,0.015)] " +
      (onClick ? "hover:bg-white/95 hover:border-primary/20 hover:shadow-[0_15px_35px_rgba(0,0,0,0.05)]" : "")

  const trendBg = highlighted
    ? "bg-white/20 text-white"
    : trend >= 0
      ? "bg-primary/10 text-primary"
      : "bg-error/10 text-error"

  return (
    <Wrapper
      onClick={onClick}
      className={`${baseClasses} ${clickClasses} ${styleClasses}`}
      aria-label={onClick ? label : undefined}
    >
      <div className="flex justify-between items-start mb-5">
        <div className={`p-2.5 rounded-xl flex items-center justify-center ${
          highlighted ? 'bg-white/15 text-white' : 'bg-primary/10 text-primary'
        }`}>
          <span className="material-symbols-outlined text-[22px]" aria-hidden="true">{icon}</span>
        </div>

        {trend !== undefined && trend !== null && (
          <span className={`px-2.5 py-1 rounded-full text-[11px] font-bold flex items-center gap-1 ${trendBg}`}>
            <span className="material-symbols-outlined text-[13px] font-bold" aria-hidden="true">
              {trend >= 0 ? 'trending_up' : 'trending_down'}
            </span>
            {Math.abs(trend)}%
          </span>
        )}
      </div>

      <p className={`font-label-md text-[11px] uppercase tracking-wider font-semibold mb-1 ${
        highlighted ? 'text-white/80' : 'text-on-surface-variant/80'
      }`}>
        {label}
      </p>

      <h3 className={`font-data-mono text-2xl font-bold tracking-tight ${
        highlighted ? 'text-white' : 'text-on-surface'
      }`}>
        {value}
      </h3>
      
      {subvalue && (
        <p className={`text-[11px] mt-1.5 font-medium ${
          highlighted ? 'text-white/70' : 'text-on-surface-variant/70'
        }`}>
          {subvalue}
        </p>
      )}
    </Wrapper>
  )
}
