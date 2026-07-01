import SharedSearchResults from '../../shared/pages/SearchResults'

const resourceLinks = {
  deliveries: '/grader/grade',
  grades: '/grader/my-grades',
}

export default function GraderSearchResults() {
  return <SharedSearchResults role="grader" resourceLinks={resourceLinks} />
}
