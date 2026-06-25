import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { ToastProvider } from './ToastProvider'
import OfflineBanner from './OfflineBanner'

export default function DashboardLayout({ sidebar, header, children }) {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <ToastProvider>
      <div className="flex min-h-screen bg-background">
        {sidebar && (
          <>
            {typeof sidebar === 'function'
              ? sidebar({ mobileOpen: sidebarOpen, onClose: () => setSidebarOpen(false) })
              : sidebar}
          </>
        )}
        <div className={sidebar ? 'flex-1 lg:ml-64' : 'flex-1'}>
          {header && (
            typeof header === 'function'
              ? header({ onMenuClick: () => setSidebarOpen(!sidebarOpen) })
              : header
          )}
          <OfflineBanner />
          <main className={`${header ? 'mt-16' : ''} p-container-margin min-h-[calc(100vh-4rem)] max-w-[1600px] mx-auto w-full`}>
            {children || <Outlet />}
          </main>
        </div>
      </div>
    </ToastProvider>
  )
}
