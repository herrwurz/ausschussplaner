import { useEffect, useState } from 'react'
import api from '../api/client'

export default function Jahresplaene() {
  const [yearplans, setYearplans] = useState([])
  const [loading, setLoading] = useState(true)
  const [form, setForm] = useState({ jahr: new Date().getFullYear(), bezeichnung: '' })

  const fetchYearplans = async () => {
    try {
      const res = await api.get('/jahresplan')
      setYearplans(res.data)
    } catch (error) {
      console.error('Error:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchYearplans()
  }, [])

  const handleCreate = async (e) => {
    e.preventDefault()
    try {
      await api.post('/jahresplan', form)
      setForm({ jahr: new Date().getFullYear(), bezeichnung: '' })
      fetchYearplans()
    } catch (error) {
      console.error('Error creating yearplan:', error)
    }
  }

  return (
    <div>
      <h1>Jahrespläne</h1>
      <form onSubmit={handleCreate} className="card p-3 mb-4">
        <div className="row">
          <div className="col-md-4">
            <input
              type="number"
              className="form-control"
              placeholder="Jahr"
              value={form.jahr}
              onChange={(e) => setForm({ ...form, jahr: parseInt(e.target.value) })}
              required
            />
          </div>
          <div className="col-md-5">
            <input
              type="text"
              className="form-control"
              placeholder="Bezeichnung"
              value={form.bezeichnung}
              onChange={(e) => setForm({ ...form, bezeichnung: e.target.value })}
            />
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
              <th>Jahr</th>
              <th>Bezeichnung</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {yearplans.map((yp) => (
              <tr key={yp.id}>
                <td>{yp.jahr}</td>
                <td>{yp.bezeichnung}</td>
                <td>{yp.aktiv ? 'Aktiv' : 'Inaktiv'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
