import { useLocation, useNavigate } from 'react-router-dom'
import { useAdminAuth } from '../../hooks/useAdminAuth'
import PeriodPicker from './PeriodPicker'
import NotificationBell from '../../../shared/components/NotificationBell'

const appBarTabs = [
  { label: 'Analytics', path: '/admin/dashboard' },
  { label: 'Reports', path: '/admin/financials' },
  { label: 'Audit Trail', path: '/admin/audit' },
]

export default function AppBar({ onMenuClick }) {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const { user } = useAdminAuth()

  const initials = user
    ? `${user.first_name?.[0] || ''}${user.last_name?.[0] || ''}`.toUpperCase()
    : '??'

  return (
    <header className="fixed top-0 right-0 left-0 lg:left-64 h-16 bg-surface border-b border-outline-variant flex justify-between items-center px-4 lg:px-6 z-30">
      <div className="flex items-center gap-3 lg:gap-8 flex-1 min-w-0">
        <button
          onClick={onMenuClick}
          className="lg:hidden p-2 text-on-surface-variant hover:bg-surface-container-high rounded-lg transition-colors"
          aria-label="Toggle menu"
        >
          <span className="material-symbols-outlined">menu</span>
        </button>

        <form
          onSubmit={(e) => {
            e.preventDefault()
            const fd = new FormData(e.target)
            const q = fd.get('search')
            if (q?.trim()) navigate(`/admin/farmers?search=${encodeURIComponent(q.trim())}`)
          }}
          className="relative hidden sm:block sm:w-60 lg:w-72 flex-shrink-0"
        >
          <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-[20px]">
            search
          </span>
          <input
            name="search"
            className="w-full bg-surface-container border-none rounded-full py-2 pl-10 pr-4 text-body-md focus:ring-1 focus:ring-primary"
            placeholder="Search operations, records, or farmers..."
          />
        </form>

        {['/admin/dashboard', '/admin/ledger', '/admin/financials', '/admin/inventory', '/admin/logistics', '/admin/analytics/seasonal', '/admin/analytics/retention'].some(p => pathname.startsWith(p)) && (
          <div className="hidden md:block flex-shrink-0">
            <PeriodPicker />
          </div>
        )}

        <nav className="hidden xl:flex gap-6 ml-auto">
          {appBarTabs.map((tab) => {
            const isActive = pathname.startsWith(tab.path)
            return (
              <button
                key={tab.label}
                onClick={() => navigate(tab.path)}
                className={`font-label-md text-label-md transition-colors whitespace-nowrap ${
                  isActive
                    ? 'text-primary font-bold border-b-2 border-primary pb-1'
                    : 'text-on-surface-variant font-medium hover:text-primary'
                }`}
              >
                {tab.label}
              </button>
            )
          })}
        </nav>
      </div>

      <div className="flex items-center gap-2 lg:gap-4 flex-shrink-0">
        <NotificationBell />

        <button aria-label="Legal history" className="p-2 text-on-surface-variant hover:bg-surface-container-high rounded-full transition-colors hidden sm:block">
          <span className="material-symbols-outlined">history_edu</span>
        </button>

        <div className="flex items-center gap-3 pl-2 lg:pl-4 border-l border-outline-variant">
          <div className="text-right hidden xl:block">
            <p className="font-label-md font-bold text-on-surface leading-tight truncate max-w-[120px]">
              {user ? `${user.first_name} ${user.last_name}` : 'Loading...'}
            </p>
            <p className="text-[10px] text-on-surface-variant uppercase tracking-tighter">
              Super Admin
            </p>
          </div>
          <div className="w-9 h-9 lg:w-10 lg:h-10 rounded-full bg-primary-fixed flex items-center justify-center border border-outline-variant text-primary font-bold text-sm overflow-hidden flex-shrink-0">
            {user?.avatar ? (
              <img src={user.avatar} alt="" className="w-full h-full object-cover" />
            ) : (
              initials
            )}
          </div>
        </div>
      </div>
    </header>
  )
}
