import { useEffect, useState } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import PersonLayout from './PersonLayout'
import api from '../api/client'

const PATH_TO_ID = {
  '/person/dashboard': 'dashboard',
  '/person/verfuegbarkeiten': 'verfuegbarkeiten',
  '/person/absences': 'absences',
  '/person/sitzungen': 'sitzungen',
  '/person/committees': 'committees',
  '/person/profile': 'profile',
  '/person/password': 'password',
}

export default function PersonPortalLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const [user, setUser] = useState(() => ({
    email: localStorage.getItem('personEmail') || '',
    name: '',
  }))
  const [ready, setReady] = useState(false)

  useEffect(() => {
    const token = localStorage.getItem('personToken')
    if (!token) {
      navigate('/person/login', { replace: true })
      return
    }

    let cancelled = false
    const load = async () => {
      try {
        const res = await api.get('/person/me/dashboard')
        if (!cancelled) {
          setUser({
            email: localStorage.getItem('personEmail') || '',
            name: res.data?.name || '',
            vorname: res.data?.name?.split(' ')[0],
            nachname: res.data?.name?.split(' ').slice(1).join(' '),
          })
        }
      } catch (err) {
        if (err.response?.status === 401) {
          localStorage.removeItem('personToken')
          navigate('/person/login', { replace: true })
          return
        }
      } finally {
        if (!cancelled) setReady(true)
      }
    }
    load()
    return () => { cancelled = true }
  }, [navigate])

  const handleLogout = () => {
    localStorage.removeItem('personToken')
    localStorage.removeItem('personEmail')
    navigate('/person/login')
  }

  if (!ready) {
    return <div className="alert alert-info" style={{ margin: '2rem' }}>Lädt...</div>
  }

  const activeId = PATH_TO_ID[location.pathname] || 'dashboard'

  return (
    <PersonLayout activeId={activeId} user={user} onLogout={handleLogout}>
      <Outlet />
    </PersonLayout>
  )
}
