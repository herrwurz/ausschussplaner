import { useEffect, useState } from 'react'
import api from '../api/client'
import PageHeader from '../components/PageHeader'

export default function PersonCommittees() {
  const [committees, setCommittees] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchCommittees = async () => {
      try {
        const res = await api.get('/person/me/committees')
        setCommittees(res.data)
      } catch {
        /* Auth via layout */
      } finally {
        setLoading(false)
      }
    }
    fetchCommittees()
  }, [])

  if (loading) return <div className="alert alert-info">Lädt...</div>

  return (
    <div>
      <PageHeader title="Meine Ausschüsse" />

      <div className="table-responsive">
        <table className="admin-table">
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
                <td><span className="badge bg-primary">{c.rolle}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {committees.length === 0 && (
        <div className="alert alert-info">Du bist noch in keinem Ausschuss Mitglied.</div>
      )}
    </div>
  )
}
