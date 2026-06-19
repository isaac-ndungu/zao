import { useContext } from 'react'
import { AdminFilterContext } from '../../contexts/AdminFilterContext'

const periods = [
  { value: '7d', label: '7d' },
  { value: '30d', label: '30d' },
  { value: '90d', label: '90d' },
  { value: '1y', label: '1y' },
]

export default function PeriodPicker() {
  const { period, setPeriod } = useContext(AdminFilterContext)

  return (
    <div className="flex items-center gap-2">
      <div className="bg-surface-container p-0.5 rounded-lg flex">
        {periods.map((p) => (
          <button
            key={p.value}
            onClick={() => setPeriod(p.value)}
            className={`px-3 py-1.5 text-label-md rounded-md transition-colors ${
              period === p.value
                ? 'bg-white shadow-sm text-on-surface font-bold'
                : 'text-on-surface-variant hover:text-on-surface'
            }`}
          >
            {p.label}
          </button>
        ))}
      </div>
    </div>
  )
}
