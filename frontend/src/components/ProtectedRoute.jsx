import { Navigate } from 'react-router-dom'

export default function ProtectedRoute({ children, requiredRole }) {
  const token = localStorage.getItem('token')
  let user = {}
  try {
    user = JSON.parse(localStorage.getItem('user') || '{}')
  } catch {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    return <Navigate to="/admin/login" replace />
  }

  // Nicht authentifiziert
  if (!token || !user.id) {
    return <Navigate to="/admin/login" replace />
  }

  // Rolle nicht erforderlich (nur authentifiziert)
  if (!requiredRole) {
    return children
  }

  // Rolle nicht ausreichend
  if (requiredRole === 'admin') {
    if (!['super_admin', 'sekretariat', 'benutzer'].includes(user.rolle)) {
      return <Navigate to="/obmann/dashboard" replace />
    }
  } else if (requiredRole === 'obmann') {
    if (!['obmann', 'super_admin'].includes(user.rolle)) {
      return <Navigate to="/admin/login" replace />
    }
  } else if (requiredRole === 'super_admin') {
    if (user.rolle !== 'super_admin') {
      return <Navigate to="/admin/login" replace />
    }
  }

  return children
}
