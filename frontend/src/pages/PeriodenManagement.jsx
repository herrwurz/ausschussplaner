import { useState, useEffect } from 'react'
import api from '../api/client'

export default function PeriodenManagement() {
  const [perioden, setPerioden] = useState([])
  const [ausschuessPerPeriode, setAusschuessPerPeriode] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [formData, setFormData] = useState({
    name: '',
    start_jahr: new Date().getFullYear(),
    end_jahr: new Date().getFullYear() + 4,
  })

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    try {
      setLoading(true)
      const periRes = await api.get('/perioden')
      setPerioden(periRes.data)

      const ausschuessMap = {}
      for (const periode of periRes.data) {
        const ausRes = await api.get('/committees', { params: { periode_id: periode.id } })
        ausschuessMap[periode.id] = ausRes.data
      }
      setAusschuessPerPeriode(ausschuessMap)
    } catch (err) {
      setError('Daten laden fehlgeschlagen')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleEdit = (periode) => {
    setFormData({
      name: periode.name,
      start_jahr: periode.start_jahr,
      end_jahr: periode.end_jahr,
    })
    setEditingId(periode.id)
    setShowForm(true)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    try {
      if (editingId) {
        await api.patch(`/perioden/${editingId}`, {
          name: formData.name,
          start_jahr: formData.start_jahr,
          end_jahr: formData.end_jahr,
        })
      } else {
        await api.post('/perioden', {
          name: formData.name,
          start_jahr: formData.start_jahr,
          end_jahr: formData.end_jahr,
        })
      }
      setShowForm(false)
      setEditingId(null)
      setFormData({ name: '', start_jahr: new Date().getFullYear(), end_jahr: new Date().getFullYear() + 4 })
      fetchData()
    } catch (err) {
      setError(err.response?.data?.detail || 'Fehler beim Speichern')
    }
  }

  const handleCancel = () => {
    setShowForm(false)
    setEditingId(null)
    setFormData({ name: '', start_jahr: new Date().getFullYear(), end_jahr: new Date().getFullYear() + 4 })
  }

  const handleDelete = async (id) => {
    if (!window.confirm('Periode wirklich löschen? Zugehörige Ausschüsse werden mitgelöscht.')) return
    try {
      await api.delete(`/perioden/${id}`)
      fetchData()
    } catch (err) {
      setError('Löschen fehlgeschlagen')
    }
  }

  return (
    <>
      {error && <div className="alert alert-danger">{error}</div>}

      <div className="section-header">
        <h2>Perioden-Verwaltung</h2>
        <button className="btn btn-primary" onClick={() => setShowForm(true)}>
          + Neue Periode
        </button>
      </div>

      {showForm && (
        <form className="admin-form" onSubmit={handleSubmit}>
          <h3>{editingId ? 'Periode bearbeiten' : 'Neue Gemeinderatsperiode'}</h3>
          <div className="form-grid">
            <input
              type="text"
              placeholder="Name (z.B. P2)"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              required
            />
            <input
              type="number"
              placeholder="Startjahr"
              value={formData.start_jahr}
              onChange={(e) => setFormData({ ...formData, start_jahr: parseInt(e.target.value) })}
              required
            />
            <input
              type="number"
              placeholder="Endjahr"
              value={formData.end_jahr}
              onChange={(e) => setFormData({ ...formData, end_jahr: parseInt(e.target.value) })}
              required
            />
          </div>

          <p style={{ fontSize: '0.85rem', color: 'var(--color-text-muted, #666)', marginTop: '1rem' }}>
            Ausschüsse gehören fest zu einer Periode. Für eine neue Periode Ausschüsse unter
            „Ausschüsse“ mit „Für Periode kopieren“ anlegen (ohne Mitgliedschaften).
          </p>
          <div className="form-buttons">
            <button type="submit" className="btn btn-success">
              {editingId ? 'Aktualisieren' : 'Erstellen'}
            </button>
            <button type="button" className="btn btn-secondary" onClick={handleCancel}>
              Abbrechen
            </button>
          </div>
        </form>
      )}

      {loading ? (
        <p>Lädt...</p>
      ) : perioden.length === 0 ? (
        <div className="alert alert-info">
          <p>Keine Gemeinderatsperioden vorhanden.</p>
        </div>
      ) : (
        <div className="table-responsive">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Periode</th>
                <th>Jahre</th>
                <th>Ausschüsse</th>
                <th>Status</th>
                <th>Aktionen</th>
              </tr>
            </thead>
            <tbody>
              {perioden.map((periode) => {
                const ausschuesse = ausschuessPerPeriode[periode.id] || []
                return (
                  <tr key={periode.id}>
                    <td><strong>{periode.name}</strong></td>
                    <td>{periode.start_jahr}–{periode.end_jahr}</td>
                    <td>
                      {ausschuesse.length === 0 ? (
                        <span style={{ color: '#999' }}>Keine Ausschüsse</span>
                      ) : (
                        <span>{ausschuesse.length} Ausschüsse</span>
                      )}
                    </td>
                    <td>{periode.aktiv ? 'Aktiv' : 'Inaktiv'}</td>
                    <td className="actions">
                      <button className="btn btn-sm btn-warning" onClick={() => handleEdit(periode)}>
                        Edit
                      </button>
                      <button className="btn btn-sm btn-danger" onClick={() => handleDelete(periode.id)}>
                        Delete
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}
