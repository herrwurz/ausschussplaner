import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/client'
import PageHeader from '../components/PageHeader'
import '../styles/PersonDashboard.css'

export default function PersonDashboard() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [email, setEmail] = useState('')

  useEffect(() => {
    const fetchDashboard = async () => {
      try {
        const res = await api.get('/person/me/dashboard')
        setStats(res.data)
        setEmail(localStorage.getItem('personEmail') || '')
      } catch {
        /* Auth handled by PersonPortalLayout */
      } finally {
        setLoading(false)
      }
    }
    fetchDashboard()
  }, [])

  if (loading) return <div className="alert alert-info">Lädt...</div>

  return (
    <div>
      <PageHeader
        title={`Willkommen, ${stats?.name || ''}!`}
        description="Kurzübersicht und Schnellzugriff auf Ihre Daten."
      />

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

      <div className="person-nav-grid" style={{ marginTop: '1.5rem' }}>
        <div className="person-nav-card">
          <div className="person-nav-card-header">
            <h5>Schnellzugriff</h5>
          </div>
          <div className="person-nav-card-body">
            <Link to="/person/verfuegbarkeiten" className="person-nav-card-link primary full-width">
              Verfügbarkeiten pflegen
            </Link>
            <Link to="/person/absences" className="person-nav-card-link primary full-width">
              Abwesenheiten melden
            </Link>
            <Link to="/person/sitzungen" className="person-nav-card-link secondary full-width">
              Sitzungstermine ansehen
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
