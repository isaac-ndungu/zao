import SharedSearchResults from '../../shared/pages/SearchResults'

const resourceLinks = {
  audit_log: '/external-auditor/audit-trail',
  loans: '/external-auditor/loan-portfolio',
}

export default function ExternalAuditorSearchResults() {
  return <SharedSearchResults role="external-auditor" resourceLinks={resourceLinks} />
}
