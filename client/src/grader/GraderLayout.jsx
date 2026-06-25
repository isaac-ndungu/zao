import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import GraderAppBar from './AppBar'
import DashboardLayout from '../shared/components/DashboardLayout'

export default function GraderLayout({ children }) {
  return (
    <DashboardLayout
      sidebar={(props) => <Sidebar {...props} />}
      header={(props) => <GraderAppBar {...props} />}
    >
      {children ?? <Outlet />}
    </DashboardLayout>
  )
}
