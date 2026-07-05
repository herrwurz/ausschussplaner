import { useEffect, useState } from 'react'
import api from '../api/client'

export default function Sitzungsregeln() {
  const [rules, setRules] = useState(null)
  const [loading, setLoading] = useState(true)
  const [form, setForm] = useState({})

  useEffect(() => {
    const fetchRules = async () => {
      try {
        const res = await api.get('/rules')
        setRules(res.data)
        setForm(res.data)
      } catch (error) {
        console.error('Error:', error)
      } finally {
        setLoading(false)
      }
    }
    fetchRules()
  }, [])

  const handleSubmit = async (e) => {
    e.preventDefault()
    try {
      await api.put('/rules', form)
      alert('Sitzungsregeln gespeichert!')
    } catch (error) {
      console.error('Error saving rules:', error)
    }
  }

  if (loading) return <div className="alert alert-info">Lädt...</div>

  return (
    <div>
      <h1>Sitzungsregeln</h1>
      {rules && (
        <form onSubmit={handleSubmit} className="card p-4">
          <div className="row">
            <div className="col-md-6 mb-3">
              <label className="form-label">Block-Minuten</label>
              <input
                type="number"
                className="form-control"
                value={form.block_minuten || ''}
                onChange={(e) => setForm({ ...form, block_minuten: parseInt(e.target.value) })}
              />
            </div>
            <div className="col-md-6 mb-3">
              <label className="form-label">Sitzung-Minuten</label>
              <input
                type="number"
                className="form-control"
                value={form.sitzung_minuten || ''}
                onChange={(e) => setForm({ ...form, sitzung_minuten: parseInt(e.target.value) })}
              />
            </div>
          </div>

          <div className="row">
            <div className="col-md-6 mb-3">
              <label className="form-label">Pause-Minuten</label>
              <input
                type="number"
                className="form-control"
                value={form.pause_minuten || ''}
                onChange={(e) => setForm({ ...form, pause_minuten: parseInt(e.target.value) })}
              />
            </div>
            <div className="col-md-6 mb-3">
              <label className="form-label">Council-Minuten</label>
              <input
                type="number"
                className="form-control"
                value={form.council_minuten || ''}
                onChange={(e) => setForm({ ...form, council_minuten: parseInt(e.target.value) })}
              />
            </div>
          </div>

          <div className="row">
            <div className="col-md-4 mb-3">
              <label className="form-label">Quorum Standard</label>
              <input
                type="number"
                className="form-control"
                value={form.quorum_standard || ''}
                onChange={(e) => setForm({ ...form, quorum_standard: parseInt(e.target.value) })}
              />
            </div>
            <div className="col-md-4 mb-3">
              <label className="form-label">Quorum Poly</label>
              <input
                type="number"
                className="form-control"
                value={form.quorum_poly || ''}
                onChange={(e) => setForm({ ...form, quorum_poly: parseInt(e.target.value) })}
              />
            </div>
            <div className="col-md-4 mb-3">
              <label className="form-label">Quorum Kontroll</label>
              <input
                type="number"
                className="form-control"
                value={form.quorum_kontroll || ''}
                onChange={(e) => setForm({ ...form, quorum_kontroll: parseInt(e.target.value) })}
              />
            </div>
          </div>

          <button type="submit" className="btn btn-primary">Speichern</button>
        </form>
      )}
    </div>
  )
}
