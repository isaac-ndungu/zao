import RoleAppBar from '../shared/components/RoleAppBar'

export default function AuditorAppBar(props) {
  return (
    <RoleAppBar
      role="auditor"
      searchPlaceholder="Search audit log, farmers, loans..."
      profilePath="/auditor/profile"
      showNotificationBell={false}
      {...props}
    />
  )
}
