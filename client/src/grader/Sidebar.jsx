import { Link, useLocation } from 'react-router-dom'
import { useState, useCallback } from 'react'

const navItems = [
  { to: '/grader/dashboard', icon: 'dashboard', label: 'Dashboard' },
  { to: '/grader/grade', icon: 'grading', label: 'Grade Delivery' },
  { to: '/grader/my-grades', icon: 'fact_check', label: 'My Grades' },
  { to: '/grader/sync', icon: 'sync', label: 'Sync' },
]

const bottomItems = [
  { to: '/grader/profile', icon: 'person', label: 'Profile' },
  { to: '/grader/settings', icon: 'settings', label: 'Settings' },
]

export default function Sidebar({ mobileOpen, onClose, minimized }) {
  const { pathname } = useLocation()
  const [tooltip, setTooltip] = useState({ show: false, label: '', x: 0, y: 0 })

  const showTooltip = useCallback((e, label) => {
    if (!minimized) return
    const rect = e.currentTarget.getBoundingClientRect()
    setTooltip({ show: true, label, x: rect.right + 8, y: rect.top + rect.height / 2 })
  }, [minimized])

  const hideTooltip = useCallback(() => {
    setTooltip({ show: false, label: '', x: 0, y: 0 })
  }, [])

  const sidebarContent = (
    <aside className={`${minimized ? 'w-16 px-2' : 'w-64 px-4'} h-full bg-primary flex flex-col py-6 overflow-y-auto transition-all duration-300`}>
      <div className={`mb-10 ${minimized ? 'px-0 text-center' : 'px-2'}`}>
        {minimized ? (
          <h1 className="font-headline-lg text-headline-lg font-bold text-on-primary">Z</h1>
        ) : (
          <h1 className="font-headline-lg text-headline-lg font-bold text-on-primary">Zao Grader</h1>
        )}
      </div>

      <nav className="flex-1 space-y-1">
        {navItems.map((item) => {
          const isActive = pathname.startsWith(item.to)
          return (
            <Link
              key={item.to}
              to={item.to}
              onClick={onClose}
              onMouseEnter={(e) => showTooltip(e, item.label)}
              onMouseLeave={hideTooltip}
              className={`flex items-center gap-3 px-4 py-3 transition-colors ${
                isActive
                  ? 'bg-secondary-container text-on-secondary-container rounded-lg'
                  : 'text-on-primary/80 hover:text-on-primary hover:bg-primary-fixed-dim/10 rounded-lg'
              }`}
            >
              <span className="material-symbols-outlined">{item.icon}</span>
              {!minimized && <span className="font-body-md text-body-md">{item.label}</span>}
            </Link>
          )
        })}
      </nav>

      <div className={`mt-auto pt-6 border-t border-on-primary/10 ${minimized ? 'space-y-2' : 'space-y-4'}`}>
        {bottomItems.map((item) => (
          <Link
            key={item.to}
            to={item.to}
            onMouseEnter={(e) => showTooltip(e, item.label)}
            onMouseLeave={hideTooltip}
            className="flex items-center gap-3 px-4 py-2 text-on-primary/80 hover:text-on-primary transition-colors"
          >
            <span className="material-symbols-outlined text-[20px]">{item.icon}</span>
            {!minimized && <span className="font-label-md text-label-md">{item.label}</span>}
          </Link>
        ))}
      </div>
    </aside>
  )

  return (
    <>
      {mobileOpen && (
        <div className="fixed inset-0 bg-black/40 z-40 lg:hidden" onClick={onClose} />
      )}
      <div className={`hidden lg:fixed lg:inset-y-0 lg:flex ${minimized ? 'lg:w-16' : 'lg:w-64'} z-50 transition-all duration-300`}>
        {sidebarContent}
      </div>
      <div className={`fixed inset-y-0 left-0 z-50 w-64 transform transition-transform duration-300 ease-in-out lg:hidden ${
        mobileOpen ? 'translate-x-0' : '-translate-x-full'
      }`}>
        {sidebarContent}
      </div>
      {minimized && tooltip.show && (
        <div
          className="fixed px-2 py-1 bg-gray-900 text-white text-xs rounded whitespace-nowrap pointer-events-none z-[999] shadow-lg"
          style={{ left: tooltip.x, top: tooltip.y, transform: 'translateY(-50%)' }}
        >
          {tooltip.label}
        </div>
      )}
    </>
  )
}
