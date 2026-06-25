import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import ManagerAppBar from './AppBar'
import DashboardLayout from '../shared/components/DashboardLayout'

export default function ManagerLayout({ children }) {
  return (
    <DashboardLayout
      sidebar={(props) => <Sidebar {...props} />}
      header={(props) => <ManagerAppBar {...props} />}
    >
      {children ?? <Outlet />}
    </DashboardLayout>
  )
}
