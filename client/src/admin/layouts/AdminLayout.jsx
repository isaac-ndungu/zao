import { Outlet } from 'react-router-dom'
import { AdminFilterProvider } from '../contexts/AdminFilterContext'
import Sidebar from '../components/layout/Sidebar'
import AppBar from '../components/layout/AppBar'
import DashboardLayout from '../../shared/components/DashboardLayout'

export default function AdminLayout({ children }) {
  return (
    <AdminFilterProvider>
      <DashboardLayout
        sidebar={(props) => <Sidebar {...props} />}
        header={(props) => <AppBar {...props} />}
      >
        {children ?? <Outlet />}
      </DashboardLayout>
    </AdminFilterProvider>
  )
}
