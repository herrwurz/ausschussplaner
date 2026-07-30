import { useEffect, useState } from 'react'
import api from '../api/client'
import PageHeader from '../components/PageHeader'

export default function PersonAbsences() {
  const [absences, setAbsences] = useState([])
  const [form, setForm] = useState({ von: '', bis: '', art: 'Urlaub', bemerkung: '' })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    const fetchAbsences = async () => {
      try {
        const res = await api.get('/person/me/absences')
        setAbsences(res.data)
      } catch {
        /* Auth via layout */
      } finally {
        setLoading(false)
      }
    }
    fetchAbsences()
  }, [])

  const handleCreate = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      await api.post('/person/me/absences', { person_id: 0, ...form })
      setForm({ von: '', bis: '', art: 'Urlaub', bemerkung: '' })
      const res = await api.get('/person/me/absences')
      setAbsences(res.data)
    } catch (err) {
      console.error('Error:', err)
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <div className="alert alert-info">Lädt...</div>

  return (
    <div>
      <PageHeader title="Meine Abwesenheiten" />

      <form onSubmit={handleCreate} className="admin-form" style={{ marginBottom: '1.5rem' }}>
        <div className="form-grid">
          <div className="form-group">
            <label>Von</label>
            <input type="date" value={form.von} onChange={(e) => setForm({ ...form, von: e.target.value })} required />
          </div>
          <div className="form-group">
            <label>Bis</label>
            <input type="date" value={form.bis} onChange={(e) => setForm({ ...form, bis: e.target.value })} required />
          </div>
          <div className="form-group">
            <label>Art</label>
            <select value={form.art} onChange={(e) => setForm({ ...form, art: e.target.value })}>
              <option value="Urlaub">Urlaub</option>
              <option value="Krankheit">Krankheit</option>
              <option value="Sonstiges">Sonstiges</option>
            </select>
          </div>
          <div className="form-group">
            <label>Bemerkung</label>
            <input
              type="text"
              value={form.bemerkung}
              onChange={(e) => setForm({ ...form, bemerkung: e.target.value })}
              placeholder="Optional"
            />
          </div>
        </div>
        <button type="submit" className="btn btn-primary" disabled={saving}>Hinzufügen</button>
      </form>

      <div className="table-responsive">
        <table className="admin-table">
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
    </div>
  )
}
