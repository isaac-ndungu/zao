import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { AdminFilterProvider } from '../contexts/AdminFilterContext'
import { ToastProvider } from '../contexts/ToastContext'
import Sidebar from '../components/layout/Sidebar'
import AppBar from '../components/layout/AppBar'

export default function AdminLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <AdminFilterProvider>
      <ToastProvider>
        <div className="flex min-h-screen bg-background">
          <Sidebar mobileOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
          <div className="flex-1 lg:ml-64">
            <AppBar onMenuClick={() => setSidebarOpen(!sidebarOpen)} />
            <main className="mt-16 p-container-margin min-h-[calc(100vh-4rem)] max-w-[1600px] mx-auto w-full">
              <Outlet />
            </main>
          </div>
        </div>
      </ToastProvider>
    </AdminFilterProvider>
  )
}
