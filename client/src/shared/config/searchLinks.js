const adminLinks = {
  cooperatives: '/admin/cooperatives',
  users: '/admin/users',
  deliveries: '/admin/receipts',
  loans: '/admin/loans',
  payments: '/admin/farmer-payments',
  inventory: '/admin/inventory',
  audit_log: '/admin/audit',
}

const managerLinks = {
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

const accountantLinks = {
  loans: '/accountant/loans',
  payment_cycles: '/accountant/cycles',
  disbursements: '/accountant/disbursements',
  deductions: '/accountant/deductions',
}

const graderLinks = {
  deliveries: '/grader/grade',
  grades: '/grader/my-grades',
}

const auditorLinks = {
  audit_log: '/auditor/audit-log',
  loans: '/auditor/loans',
}

const externalAuditorLinks = {
  audit_log: '/external-auditor/audit-trail',
  loans: '/external-auditor/loan-portfolio',
}

const roleLinks = {
  admin: adminLinks,
  manager: managerLinks,
  accountant: accountantLinks,
  grader: graderLinks,
  auditor: auditorLinks,
  'external-auditor': externalAuditorLinks,
}

export function getResourceLinks(role) {
  return roleLinks[role] || {}
}

export function getListUrl(role, resourceType) {
  const links = roleLinks[role]
  return links?.[resourceType] || null
}
