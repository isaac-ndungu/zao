import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import ExternalAuditorAppBar from './AppBar'
import DashboardLayout from '../shared/components/DashboardLayout'

export default function ExternalAuditorLayout({ children }) {
  return (
    <DashboardLayout
      sidebar={(props) => <Sidebar {...props} />}
      header={(props) => <ExternalAuditorAppBar {...props} />}
    >
      {children ?? <Outlet />}
    </DashboardLayout>
  )
}
