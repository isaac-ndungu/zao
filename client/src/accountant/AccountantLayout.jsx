import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import AccountantAppBar from './AppBar'
import DashboardLayout from '../shared/components/DashboardLayout'

export default function AccountantLayout({ children }) {
  return (
    <DashboardLayout
      sidebar={(props) => <Sidebar {...props} />}
      header={(props) => <AccountantAppBar {...props} />}
    >
      {children ?? <Outlet />}
    </DashboardLayout>
  )
}
