import { useState, useEffect } from 'react'
import api from '../api/client'

export default function PeriodenManagement() {
  const [perioden, setPerioden] = useState([])
  const [ausschuessPerPeriode, setAusschuessPerPeriode] = useState({})
  const [allAusschuesse, setAllAusschuesse] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [formData, setFormData] = useState({
    name: '',
    start_jahr: new Date().getFullYear(),
    end_jahr: new Date().getFullYear() + 4,
    ausschuss_ids: [],
  })

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    try {
      setLoading(true)
      // Lade Perioden
      const periRes = await api.get('/perioden')
      setPerioden(periRes.data)

      // Lade Ausschüsse pro Periode
      const ausschuessMap = {}
      for (const periode of periRes.data) {
        const ausRes = await api.get('/committees', { params: { periode_id: periode.id } })
        ausschuessMap[periode.id] = ausRes.data
      }
      setAusschuessPerPeriode(ausschuessMap)

      // Lade alle Ausschüsse (für Zuordnungs-Dropdown)
      const allRes = await api.get('/committees')
      setAllAusschuesse(allRes.data)
    } catch (err) {
      setError('Daten laden fehlgeschlagen')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleEdit = (periode) => {
    const ausIds = (ausschuessPerPeriode[periode.id] || []).map(a => a.id)
    setFormData({
      name: periode.name,
      start_jahr: periode.start_jahr,
      end_jahr: periode.end_jahr,
      ausschuss_ids: ausIds,
    })
    setEditingId(periode.id)
    setShowForm(true)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    try {
      if (editingId) {
        // Update Periode
        await api.patch(`/perioden/${editingId}`, {
          name: formData.name,
          start_jahr: formData.start_jahr,
          end_jahr: formData.end_jahr,
        })
        // Update Ausschuss-Zuordnungen
        await updateAusschuessZuordnung(editingId, formData.ausschuss_ids)
      } else {
        // Create Periode
        const res = await api.post('/perioden', {
          name: formData.name,
          start_jahr: formData.start_jahr,
          end_jahr: formData.end_jahr,
        })
        // Zuordne Ausschüsse
        await updateAusschuessZuordnung(res.data.id, formData.ausschuss_ids)
      }
      setShowForm(false)
      setEditingId(null)
      setFormData({ name: '', start_jahr: new Date().getFullYear(), end_jahr: new Date().getFullYear() + 4, ausschuss_ids: [] })
      fetchData()
    } catch (err) {
      setError(err.response?.data?.detail || 'Fehler beim Speichern')
    }
  }

  const updateAusschuessZuordnung = async (periodeId, ausschussIds) => {
    try {
      // Hole aktuelle Ausschüsse dieser Periode
      const current = ausschuessPerPeriode[periodeId] || []
      const currentIds = current.map(a => a.id)

      // Zu löschende Ausschüsse (waren drin, sollen aber weg)
      for (const id of currentIds) {
        if (!ausschussIds.includes(id)) {
          // Entferne Periode von diesem Ausschuss
          await api.patch(`/committees/${id}`, { periode_id: null })
        }
      }

      // Zu hinzufügende Ausschüsse (sollen drin, waren aber nicht drin)
      for (const id of ausschussIds) {
        if (!currentIds.includes(id)) {
          // Weise Periode zu
          await api.patch(`/committees/${id}`, { periode_id: periodeId })
        }
      }
    } catch (err) {
      console.error('Fehler bei Ausschuss-Zuordnung:', err)
      throw err
    }
  }

  const handleCancel = () => {
    setShowForm(false)
    setEditingId(null)
    setFormData({ name: '', start_jahr: new Date().getFullYear(), end_jahr: new Date().getFullYear() + 4, ausschuss_ids: [] })
  }

  const handleDelete = async (id) => {
    if (!window.confirm('Periode wirklich löschen?')) return
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

          {/* Ausschuss-Zuordnung */}
          <div style={{ marginTop: '1.5rem', paddingTop: '1.5rem', borderTop: '1px solid #e5e7eb' }}>
            <label style={{ fontWeight: '600', marginBottom: '0.75rem', display: 'block' }}>
              Ausschüsse für diese Periode:
            </label>
            <div style={{ maxHeight: '300px', overflowY: 'auto', border: '1px solid #d1d5db', borderRadius: '4px', padding: '0.75rem' }}>
              {allAusschuesse.length === 0 ? (
                <p style={{ color: '#999', fontSize: '0.9rem' }}>Keine Ausschüsse verfügbar</p>
              ) : (
                allAusschuesse.map((ausschuss) => (
                  <div key={ausschuss.id} style={{ marginBottom: '0.5rem' }}>
                    <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
                      <input
                        type="checkbox"
                        checked={formData.ausschuss_ids.includes(ausschuss.id)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setFormData({
                              ...formData,
                              ausschuss_ids: [...formData.ausschuss_ids, ausschuss.id]
                            })
                          } else {
                            setFormData({
                              ...formData,
                              ausschuss_ids: formData.ausschuss_ids.filter(id => id !== ausschuss.id)
                            })
                          }
                        }}
                        style={{ marginRight: '0.5rem' }}
                      />
                      <span>{ausschuss.name}</span>
                    </label>
                  </div>
                ))
              )}
            </div>
          </div>

          <p style={{ fontSize: '0.85rem', color: '#666', marginTop: '1rem' }}>
            Eine Periode umfasst 5 Jahre und hat die gleichen Ausschüsse für alle Jahre dieser Periode.
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
          <p>Keine Gemeinderatsperioden vorhanden. <a href="#" onClick={() => setShowForm(true)}>Erstellen Sie eine neue Periode</a>.</p>
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
                    <td>{periode.aktiv ? '✅ Aktiv' : '❌ Inaktiv'}</td>
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
