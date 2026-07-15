import RoleAppBar from '../shared/components/RoleAppBar'

export default function GraderAppBar(props) {
  return (
    <RoleAppBar
      role="grader"
      searchPlaceholder="Search deliveries or grades..."
      profilePath="/grader/profile"
      showNotificationBell={true}
      {...props}
    />
  )
}
