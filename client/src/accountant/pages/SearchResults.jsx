import SharedSearchResults from '../../shared/pages/SearchResults'

const resourceLinks = {
  farmers: '/accountant/farmers',
  loans: '/accountant/loans',
  payment_cycles: '/accountant/cycles',
  disbursements: '/accountant/disbursements',
  deductions: '/accountant/deductions',
}

export default function AccountantSearchResults() {
  return <SharedSearchResults role="accountant" resourceLinks={resourceLinks} />
}
