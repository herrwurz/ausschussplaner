import { useEffect, useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import api from '../api/client'
import '../styles/PersonDashboard.css'

export default function PersonDashboard() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [email, setEmail] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    const token = localStorage.getItem('personToken')
    if (!token) {
      navigate('/person/login')
      return
    }

    const fetchDashboard = async () => {
      try {
        const res = await api.get('/person/me/dashboard', {
          headers: { Authorization: `Bearer ${token}` }
        })
        setStats(res.data)
        setEmail(localStorage.getItem('personEmail'))
      } catch (err) {
        if (err.response?.status === 401) {
          localStorage.removeItem('personToken')
          navigate('/person/login')
        }
      } finally {
        setLoading(false)
      }
    }

    fetchDashboard()
  }, [navigate])

  const handleLogout = () => {
    localStorage.removeItem('personToken')
    localStorage.removeItem('personEmail')
    navigate('/person/login')
  }

  if (loading) return <div className="alert alert-info">Lädt...</div>

  return (
    <div className="person-dashboard-container">
      <div className="person-dashboard-content">
        <div className="person-dashboard-header">
          <h1>Willkommen, {stats?.name}!</h1>
          <button onClick={handleLogout} className="person-dashboard-logout">
            Logout
          </button>
        </div>

        {/* Stats Grid */}
        <div className="person-stats-grid">
          <div className="person-stat-card">
            <h5 className="person-stat-title">Ausschüsse</h5>
            <p className="person-stat-value">{stats?.ausschuesse}</p>
          </div>
          <div className="person-stat-card">
            <h5 className="person-stat-title">Abwesenheiten</h5>
            <p className="person-stat-value">{stats?.abwesenheiten}</p>
          </div>
          <div className="person-stat-card">
            <h5 className="person-stat-title">Email</h5>
            <p className="person-stat-label">{email}</p>
          </div>
        </div>

        {/* Navigation Cards */}
        <div className="person-nav-grid">
          <div className="person-nav-card">
            <div className="person-nav-card-header">
              <h5>Stammdaten</h5>
            </div>
            <div className="person-nav-card-body">
              <Link to="/person/profile" className="person-nav-card-link primary full-width">
                Profil bearbeiten
              </Link>
              <Link to="/person/password" className="person-nav-card-link secondary full-width">
                Passwort ändern
              </Link>
            </div>
          </div>

          <div className="person-nav-card">
            <div className="person-nav-card-header">
              <h5>Planung</h5>
            </div>
            <div className="person-nav-card-body">
              <Link to="/person/verfuegbarkeiten" className="person-nav-card-link primary full-width">
                Verfügbarkeiten
              </Link>
              <Link to="/person/absences" className="person-nav-card-link primary full-width">
                Abwesenheiten
              </Link>
              <Link to="/person/committees" className="person-nav-card-link secondary full-width">
                Meine Ausschüsse
              </Link>
            </div>
          </div>

          <div className="person-nav-card">
            <div className="person-nav-card-header">
              <h5>Sitzungen</h5>
            </div>
            <div className="person-nav-card-body">
              <Link to="/person/sitzungen" className="person-nav-card-link primary full-width">
                Sitzungstermine
              </Link>
              <Link to="/person/my-bookings" className="person-nav-card-link info full-width">
                📋 Meine Buchungen
              </Link>
              <Link to="/smart-search" className="person-nav-card-link success full-width">
                📊 Intelligente Terminsuche
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
