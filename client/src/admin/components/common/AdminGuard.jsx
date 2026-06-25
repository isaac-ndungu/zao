import RoleGuard from '../../../shared/components/RoleGuard'

export default function AdminGuard({ children }) {
  return <RoleGuard roles={['admin', 'superadmin']}>{children}</RoleGuard>
}
