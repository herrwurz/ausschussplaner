import { useEffect, useState } from 'react'
import api from '../api/client'

export default function Dashboard() {
  const [stats, setStats] = useState({ persons: 0, committees: 0, absences: 0, yearplans: 0 })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const [persons, committees, absences, yearplans] = await Promise.all([
          api.get('/persons'),
          api.get('/committees'),
          api.get('/absences'),
          api.get('/jahresplan'),
        ])
        setStats({
          persons: persons.data.length,
          committees: committees.data.length,
          absences: absences.data.length,
          yearplans: yearplans.data.length,
        })
      } catch (error) {
        console.error('Error fetching stats:', error)
      } finally {
        setLoading(false)
      }
    }
    fetchStats()
  }, [])

  if (loading) return <div className="alert alert-info">Lädt...</div>

  return (
    <div>
      <h1>Dashboard</h1>
      <div className="row">
        <div className="col-md-3">
          <div className="card">
            <div className="card-body">
              <h5 className="card-title">Personen</h5>
              <p className="display-4">{stats.persons}</p>
            </div>
          </div>
        </div>
        <div className="col-md-3">
          <div className="card">
            <div className="card-body">
              <h5 className="card-title">Ausschüsse</h5>
              <p className="display-4">{stats.committees}</p>
            </div>
          </div>
        </div>
        <div className="col-md-3">
          <div className="card">
            <div className="card-body">
              <h5 className="card-title">Abwesenheiten</h5>
              <p className="display-4">{stats.absences}</p>
            </div>
          </div>
        </div>
        <div className="col-md-3">
          <div className="card">
            <div className="card-body">
              <h5 className="card-title">Jahrespläne</h5>
              <p className="display-4">{stats.yearplans}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
