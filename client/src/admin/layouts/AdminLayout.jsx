import { Outlet } from 'react-router-dom'
import { AdminFilterProvider } from '../contexts/AdminFilterContext'
import { ToastProvider } from '../contexts/ToastContext'
import Sidebar from '../components/layout/Sidebar'
import AppBar from '../components/layout/AppBar'

export default function AdminLayout() {
  return (
    <AdminFilterProvider>
      <ToastProvider>
        <div className="flex min-h-screen bg-background">
          <Sidebar />
          <div className="flex-1 ml-64">
            <AppBar />
            <main className="mt-16 p-container-margin min-h-[calc(100vh-4rem)] max-w-[1600px] mx-auto w-full">
              <Outlet />
            </main>
          </div>
        </div>
      </ToastProvider>
    </AdminFilterProvider>
  )
}
