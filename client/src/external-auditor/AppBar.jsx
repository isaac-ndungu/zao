import RoleAppBar from '../shared/components/RoleAppBar'

export default function ExternalAuditorAppBar(props) {
  return (
    <RoleAppBar
      role="external-auditor"
      searchPlaceholder="Search audit trail or loans..."
      profilePath="/external-auditor/profile"
      showNotificationBell={false}
      {...props}
    />
  )
}
