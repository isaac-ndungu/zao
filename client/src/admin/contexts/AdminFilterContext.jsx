import { createContext, useState, useCallback } from 'react'

// eslint-disable-next-line react-refresh/only-export-components
export const AdminFilterContext = createContext(null)

export function AdminFilterProvider({ children }) {
  const [period, setPeriod] = useState('30d')
  const [customRange, setCustomRange] = useState({ startDate: '', endDate: '' })

  const handleSetPeriod = useCallback((p) => {
    setPeriod(p)
    setCustomRange({ startDate: '', endDate: '' })
  }, [])

  const handleSetCustomRange = useCallback((startDate, endDate) => {
    setPeriod('custom')
    setCustomRange({ startDate, endDate })
  }, [])

  return (
    <AdminFilterContext.Provider
      value={{
        period,
        customRange,
        setPeriod: handleSetPeriod,
        setCustomRange: handleSetCustomRange,
      }}
    >
      {children}
    </AdminFilterContext.Provider>
  )
}
