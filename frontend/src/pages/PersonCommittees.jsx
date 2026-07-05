import { useEffect, useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import api from '../api/client'

export default function PersonCommittees() {
  const [committees, setCommittees] = useState([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    const token = localStorage.getItem('personToken')
    if (!token) {
      navigate('/person/login')
      return
    }

    const fetchCommittees = async () => {
      try {
        const res = await api.get('/person/me/committees', {
          headers: { Authorization: `Bearer ${token}` }
        })
        setCommittees(res.data)
      } catch (err) {
        if (err.response?.status === 401) {
          navigate('/person/login')
        }
      } finally {
        setLoading(false)
      }
    }
    fetchCommittees()
  }, [navigate])

  if (loading) return <div className="alert alert-info">Lädt...</div>

  return (
    <div className="container mt-5">
      <Link to="/person/dashboard" className="btn btn-secondary mb-3">
        ← Zurück zum Dashboard
      </Link>
      <h1>Meine Ausschüsse</h1>

      <table className="table table-striped">
        <thead>
          <tr>
            <th>Ausschuss</th>
            <th>Typ</th>
            <th>Rolle</th>
          </tr>
        </thead>
        <tbody>
          {committees.map((c, idx) => (
            <tr key={idx}>
              <td>{c.ausschuss_name}</td>
              <td>{c.typ}</td>
              <td>
                <span className="badge bg-primary">
                  {c.rolle}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {committees.length === 0 && (
        <div className="alert alert-info">
          Du bist noch in keinem Ausschuss Mitglied.
        </div>
      )}
    </div>
  )
}
