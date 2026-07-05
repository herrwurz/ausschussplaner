import { useEffect, useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import api from '../api/client'

export default function PersonAbsences() {
  const [absences, setAbsences] = useState([])
  const [form, setForm] = useState({ von: '', bis: '', art: 'Urlaub', bemerkung: '' })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const navigate = useNavigate()

  const token = localStorage.getItem('personToken')

  useEffect(() => {
    if (!token) {
      navigate('/person/login')
      return
    }

    const fetchAbsences = async () => {
      try {
        const res = await api.get('/person/me/absences', {
          headers: { Authorization: `Bearer ${token}` }
        })
        setAbsences(res.data)
      } catch (err) {
        if (err.response?.status === 401) {
          navigate('/person/login')
        }
      } finally {
        setLoading(false)
      }
    }
    fetchAbsences()
  }, [token, navigate])

  const handleCreate = async (e) => {
    e.preventDefault()
    setSaving(true)

    try {
      await api.post('/person/me/absences', {
        person_id: 0, // wird vom Backend ignoriert
        ...form,
      }, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setForm({ von: '', bis: '', art: 'Urlaub', bemerkung: '' })
      // Reload
      const res = await api.get('/person/me/absences', {
        headers: { Authorization: `Bearer ${token}` }
      })
      setAbsences(res.data)
    } catch (err) {
      console.error('Error:', err)
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <div className="alert alert-info">Lädt...</div>

  return (
    <div className="container mt-5">
      <Link to="/person/dashboard" className="btn btn-secondary mb-3">
        ← Zurück zum Dashboard
      </Link>
      <h1>Meine Abwesenheiten</h1>

      <form onSubmit={handleCreate} className="card p-3 mb-4">
        <div className="row">
          <div className="col-md-3">
            <label className="form-label">Von</label>
            <input
              type="date"
              className="form-control"
              value={form.von}
              onChange={(e) => setForm({ ...form, von: e.target.value })}
              required
            />
          </div>
          <div className="col-md-3">
            <label className="form-label">Bis</label>
            <input
              type="date"
              className="form-control"
              value={form.bis}
              onChange={(e) => setForm({ ...form, bis: e.target.value })}
              required
            />
          </div>
          <div className="col-md-3">
            <label className="form-label">Art</label>
            <select
              className="form-control"
              value={form.art}
              onChange={(e) => setForm({ ...form, art: e.target.value })}
            >
              <option value="Urlaub">Urlaub</option>
              <option value="Krankheit">Krankheit</option>
              <option value="Sonstiges">Sonstiges</option>
            </select>
          </div>
          <div className="col-md-3">
            <label className="form-label">&nbsp;</label>
            <button
              type="submit"
              className="btn btn-primary w-100"
              disabled={saving}
            >
              Hinzufügen
            </button>
          </div>
        </div>
        <div className="col-md-12 mt-3">
          <label className="form-label">Bemerkung</label>
          <input
            type="text"
            className="form-control"
            value={form.bemerkung}
            onChange={(e) => setForm({ ...form, bemerkung: e.target.value })}
            placeholder="Optional"
          />
        </div>
      </form>

      <table className="table table-striped">
        <thead>
          <tr>
            <th>Von</th>
            <th>Bis</th>
            <th>Art</th>
            <th>Bemerkung</th>
          </tr>
        </thead>
        <tbody>
          {absences.map((a) => (
            <tr key={a.id}>
              <td>{a.von}</td>
              <td>{a.bis}</td>
              <td>{a.art}</td>
              <td>{a.bemerkung}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
