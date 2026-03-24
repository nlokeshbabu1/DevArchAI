import { Navigate } from 'react-router-dom'

// Redirect to unified scan page
export function Home() {
  return <Navigate to="/scan" replace />
}
