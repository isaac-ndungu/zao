import { useNavigate } from 'react-router-dom'
import { useFarmerAuth } from '../context/FarmerAuthContext'
import NotificationBell from './NotificationBell'

export default function FarmerAppBar() {
  const navigate = useNavigate()
  const { user } = useFarmerAuth()

  return (
    <header
      role="banner"
      className="fixed top-0 left-0 right-0 h-14 bg-surface/95 backdrop-blur border-b border-outline-variant z-30"
    >
      <div className="max-w-lg mx-auto h-full px-4 flex items-center justify-between">
        <button
          onClick={() => navigate('/farmer/dashboard')}
          className="flex items-center gap-2 min-w-0"
          aria-label="Go to dashboard"
        >
          <div className="w-8 h-8 rounded-lg bg-primary text-on-primary flex items-center justify-center shrink-0">
            <span className="material-symbols-outlined text-[18px]" aria-hidden="true">eco</span>
          </div>
          <div className="min-w-0 text-left">
            <p className="text-label-md font-bold text-on-surface leading-tight truncate">
              Zao
            </p>
            {user?.first_name && (
              <p className="text-[10px] text-on-surface-variant uppercase tracking-tighter leading-tight truncate">
                {user.first_name}
              </p>
            )}
          </div>
        </button>

        <NotificationBell viewAllPath="/farmer/notifications" />
      </div>
    </header>
  )
}
