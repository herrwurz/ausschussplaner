import { useState, useEffect } from 'react'
import api from '../api/client'

export default function AusschuessManagement() {
  const [ausschuesse, setAusschuesse] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [formData, setFormData] = useState({
    name: '',
    typ: 'standard', // Always standard
    turnus: '',
  })

  useEffect(() => {
    fetchAusschuesse()
  }, [])

  const fetchAusschuesse = async () => {
    try {
      setLoading(true)
      const res = await api.get('/committees')
      setAusschuesse(res.data)
    } catch (err) {
      setError('Ausschüsse laden fehlgeschlagen')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    try {
      await api.post('/committees', { ...formData, mitglieder: [] })
      setShowForm(false)
      setFormData({ name: '', typ: 'STANDARD', turnus: '' })
      fetchAusschuesse()
    } catch (err) {
      setError(err.response?.data?.detail || 'Fehler beim Speichern')
    }
  }

  const handleCancel = () => {
    setShowForm(false)
    setFormData({ name: '', typ: 'standard', turnus: '' })
  }

  return (
    <>
      {error && <div className="alert alert-danger">{error}</div>}

      <div className="section-header">
        <h2>Ausschüsse-Verwaltung</h2>
        <button className="btn btn-primary" onClick={() => setShowForm(true)}>
          + Neuer Ausschuss
        </button>
      </div>

      {showForm && (
        <form className="admin-form" onSubmit={handleSubmit}>
          <h3>Neuer Ausschuss</h3>
          <div className="form-grid">
            <input
              type="text"
              placeholder="Name (z.B. Bildung, Infrastruktur)"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              required
            />
            <input
              type="text"
              placeholder="Turnus (z.B. Monatlich)"
              value={formData.turnus}
              onChange={(e) => setFormData({ ...formData, turnus: e.target.value })}
            />
          </div>
          <div className="form-buttons">
            <button type="submit" className="btn btn-success">
              Erstellen
            </button>
            <button type="button" className="btn btn-secondary" onClick={handleCancel}>
              Abbrechen
            </button>
          </div>
        </form>
      )}

      {loading ? (
        <p>Lädt...</p>
      ) : ausschuesse.length === 0 ? (
        <div className="alert alert-info">
          <p>Keine Ausschüsse vorhanden. <a href="#" onClick={() => setShowForm(true)}>Erstellen Sie einen neuen Ausschuss</a>.</p>
        </div>
      ) : (
        <div className="table-responsive">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Typ</th>
                <th>Turnus</th>
                <th>Mitglieder</th>
              </tr>
            </thead>
            <tbody>
              {ausschuesse.map((ausschuss) => (
                <tr key={ausschuss.id}>
                  <td>{ausschuss.name}</td>
                  <td>{ausschuss.typ}</td>
                  <td>{ausschuss.turnus}</td>
                  <td>{ausschuss.mitglieder?.length || 0}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}
