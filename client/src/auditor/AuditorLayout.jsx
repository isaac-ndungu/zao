import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import AuditorAppBar from './AppBar'
import DashboardLayout from '../shared/components/DashboardLayout'

export default function AuditorLayout({ children }) {
  return (
    <DashboardLayout
      sidebar={(props) => <Sidebar {...props} />}
      header={(props) => <AuditorAppBar {...props} />}
    >
      {children ?? <Outlet />}
    </DashboardLayout>
  )
}
