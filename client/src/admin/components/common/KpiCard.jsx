export default function KpiCard({ icon, label, value, subvalue, highlighted, trend }) {
  return (
    <div
      className={
        highlighted
          ? 'bg-primary text-on-primary p-5 rounded-xl border border-primary-container'
          : 'bg-surface-container-lowest border border-outline-variant p-5 rounded-xl'
      }
    >
      <div className="flex justify-between items-start mb-4">
        <div className={`p-2 rounded-lg ${highlighted ? 'bg-white/10' : 'bg-primary/5 text-primary'}`}>
          <span className="material-symbols-outlined text-[20px]">{icon}</span>
        
        </div>


        {trend !== undefined && trend !== null && (
          <span className={`flex items-center gap-0.5 text-[11px] font-bold ${highlighted ? 'text-white/80' : trend >= 0 ? 'text-primary' : 'text-error'
            }`}>
            <span className="material-symbols-outlined text-[14px]">
              {trend >= 0 ? 'trending_up' : 'trending_down'}
            </span>
            {Math.abs(trend)}%
          </span>
        )}


      </div>


      <p className={`font-label-md mb-0.5 ${highlighted ? 'opacity-80' : 'text-on-surface-variant'}`}>
        {label}
      </p>


      <h3 className={`font-data-mono text-headline-sm ${highlighted ? '' : 'text-on-surface'}`}>
        {value}
      </h3>
      
      {subvalue && (
        <p className={`text-[11px] mt-0.5 ${highlighted ? 'opacity-60' : 'text-on-surface-variant'}`}>
          {subvalue}
        </p>
      )}
    </div>
  )
}
