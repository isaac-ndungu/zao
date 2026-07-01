import SharedSearchResults from '../../shared/pages/SearchResults'

const resourceLinks = {
  farmers: '/manager/farmers',
  deliveries: '/manager/deliveries',
  grades: '/manager/grading',
  loans: '/manager/loans',
  payment_cycles: '/manager/cycles',
  disbursements: '/manager/disbursements',
  inventory: '/manager/inventory',
  buyers: '/manager/sales',
  sales: '/manager/sales',
  deductions: '/manager/deductions',
  users: '/manager/users',
  audit_log: '/manager/audit-log',
}

export default function ManagerSearchResults() {
  return <SharedSearchResults role="manager" resourceLinks={resourceLinks} />
}
