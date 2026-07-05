import { useEffect, useState } from 'react'
import api from '../api/client'

export default function Ausschuesse() {
  const [committees, setCommittees] = useState([])
  const [loading, setLoading] = useState(true)
  const [form, setForm] = useState({ name: '', typ: 'Standard' })

  const fetchCommittees = async () => {
    try {
      const res = await api.get('/committees')
      setCommittees(res.data)
    } catch (error) {
      console.error('Error:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchCommittees()
  }, [])

  const handleCreate = async (e) => {
    e.preventDefault()
    try {
      await api.post('/committees', { ...form, mitglieder: [] })
      setForm({ name: '', typ: 'Standard' })
      fetchCommittees()
    } catch (error) {
      console.error('Error creating committee:', error)
    }
  }

  const handleDelete = async (id) => {
    if (!confirm('Ausschuss löschen?')) return
    try {
      await api.delete(`/committees/${id}`)
      fetchCommittees()
    } catch (error) {
      console.error('Error:', error)
    }
  }

  return (
    <div>
      <h1>Ausschüsse</h1>
      <form onSubmit={handleCreate} className="card p-3 mb-4">
        <div className="row">
          <div className="col-md-6">
            <input
              type="text"
              className="form-control"
              placeholder="Name"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              required
            />
          </div>
          <div className="col-md-3">
            <select
              className="form-control"
              value={form.typ}
              onChange={(e) => setForm({ ...form, typ: e.target.value })}
            >
              <option value="Standard">Standard</option>
              <option value="poly">Poly</option>
              <option value="kontroll">Kontroll</option>
            </select>
          </div>
          <div className="col-md-3">
            <button type="submit" className="btn btn-primary w-100">Hinzufügen</button>
          </div>
        </div>
      </form>

      {loading ? (
        <div className="alert alert-info">Lädt...</div>
      ) : (
        <table className="table table-striped">
          <thead>
            <tr>
              <th>Name</th>
              <th>Typ</th>
              <th>Mitglieder</th>
              <th>Aktionen</th>
            </tr>
          </thead>
          <tbody>
            {committees.map((c) => (
              <tr key={c.id}>
                <td>{c.name}</td>
                <td>{c.typ}</td>
                <td>{c.mitglieder?.length || 0}</td>
                <td>
                  <button
                    className="btn btn-sm btn-danger"
                    onClick={() => handleDelete(c.id)}
                  >
                    Löschen
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
