import SharedSearchResults from '../../shared/pages/SearchResults'

const resourceLinks = {
  audit_log: '/auditor/audit-log',
  farmers: '/auditor/farmers',
  deliveries: '/auditor/deliveries',
  loans: '/auditor/loans',
  payment_cycles: '/auditor/cycles',
}

export default function AuditorSearchResults() {
  return <SharedSearchResults role="auditor" resourceLinks={resourceLinks} />
}
