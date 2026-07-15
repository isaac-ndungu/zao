import RoleAppBar from '../shared/components/RoleAppBar'

export default function ManagerAppBar(props) {
  return (
    <RoleAppBar
      role="manager"
      searchPlaceholder="Search farmers, deliveries, loans..."
      profilePath="/manager/profile"
      showNotificationBell={true}
      {...props}
    />
  )
}
