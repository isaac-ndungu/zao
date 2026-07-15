import RoleAppBar from '../shared/components/RoleAppBar'

export default function AccountantAppBar(props) {
  return (
    <RoleAppBar
      role="accountant"
      searchPlaceholder="Search loans, disbursements, deductions..."
      profilePath="/accountant/profile"
      showNotificationBell={true}
      {...props}
    />
  )
}
