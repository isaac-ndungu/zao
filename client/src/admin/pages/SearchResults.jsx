import SharedSearchResults from '../../shared/pages/SearchResults'

const resourceLinks = {
  farmers: '/admin/farmers',
  cooperatives: '/admin/cooperatives',
  users: '/admin/users',
  deliveries: '/admin/deliveries',
  grades: '/admin/grades',
  loans: '/admin/loans',
  payment_cycles: '/admin/cycles',
  payments: '/admin/farmer-payments',
  disbursements: '/admin/disbursements',
  inventory: '/admin/inventory',
  buyers: '/admin/buyers',
  sales: '/admin/sales',
  deductions: '/admin/deductions',
  audit_log: '/admin/audit',
}

export default function AdminSearchResults() {
  return <SharedSearchResults role="admin" resourceLinks={resourceLinks} />
}
