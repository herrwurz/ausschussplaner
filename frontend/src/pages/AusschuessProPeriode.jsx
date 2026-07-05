import { useState, useEffect } from 'react'
import api from '../api/client'

export default function AusschuessProPeriode() {
  const [perioden, setPerioden] = useState([])
  const [selectedPeriodId, setSelectedPeriodId] = useState(null)
  const [ausschuesse, setAusschuesse] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [formData, setFormData] = useState({
    name: '',
    typ: 'standard',
  })

  useEffect(() => {
    fetchPerioden()
  }, [])

  const fetchPerioden = async () => {
    try {
      setLoading(true)
      const res = await api.get('/perioden')
      setPerioden(res.data)
      if (res.data.length > 0) {
        setSelectedPeriodId(res.data[0].id)
      }
    } catch (err) {
      setError('Perioden laden fehlgeschlagen')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (selectedPeriodId) {
      fetchAusschuesse()
    }
  }, [selectedPeriodId])

  const fetchAusschuesse = async () => {
    try {
      setLoading(true)
      const res = await api.get('/committees', {
        params: { periode_id: selectedPeriodId }
      })
      setAusschuesse(res.data)
    } catch (err) {
      setError('Ausschüsse laden fehlgeschlagen')
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    try {
      const payload = {
        name: formData.name,
        typ: 'standard',
        turnus: '',
        aktiv: true,
        mitglieder: []
      }
      // Add periode_id as query param
      await api.post('/committees', payload, {
        params: { periode_id: selectedPeriodId }
      })
      setShowForm(false)
      setFormData({ name: '', typ: 'standard' })
      fetchAusschuesse()
    } catch (err) {
      setError(err.response?.data?.detail || 'Fehler beim Speichern')
    }
  }

  const handleCancel = () => {
    setShowForm(false)
    setFormData({ name: '', typ: 'standard' })
  }

  const currentPeriod = perioden.find(p => p.id === selectedPeriodId)

  return (
    <>
      {error && <div className="alert alert-danger">{error}</div>}

      <div className="section-header">
        <div>
          <h2>Ausschüsse pro Gemeinderatsperiode</h2>
          <p style={{ marginTop: '0.5rem', color: '#666', fontSize: '0.9rem' }}>
            Jede Periode hat die gleichen Ausschüsse für alle Jahre (Mitglieder können sich ändern)
          </p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowForm(true)}>
          + Neuer Ausschuss
        </button>
      </div>

      {/* Periode Selector */}
      <div style={{ marginBottom: '1.5rem', padding: '1rem', background: '#f3f4f6', borderRadius: '4px' }}>
        <label style={{ fontWeight: '600', marginBottom: '0.5rem', display: 'block' }}>
          Gemeinderatsperiode:
        </label>
        <select
          value={selectedPeriodId || ''}
          onChange={(e) => setSelectedPeriodId(parseInt(e.target.value))}
          style={{
            padding: '0.5rem',
            border: '1px solid #d1d5db',
            borderRadius: '4px',
            fontSize: '0.95rem',
            width: '100%',
            maxWidth: '400px'
          }}
        >
          {perioden.map((periode) => (
            <option key={periode.id} value={periode.id}>
              {periode.name} ({periode.start_jahr}-{periode.end_jahr})
            </option>
          ))}
        </select>
      </div>

      {showForm && (
        <form className="admin-form" onSubmit={handleSubmit}>
          <h3>Neuer Ausschuss für Periode {currentPeriod?.name}</h3>
          <div className="form-grid">
            <input
              type="text"
              placeholder="Name (z.B. Sport, Bildung, Frauen)"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              required
            />
          </div>
          <p style={{ fontSize: '0.85rem', color: '#666', marginBottom: '1rem' }}>
            Dieser Ausschuss wird für alle 5 Jahre dieser Periode ({currentPeriod?.start_jahr}-{currentPeriod?.end_jahr}) hinzugefügt.
          </p>
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
          <p>Keine Ausschüsse in {currentPeriod?.name}.
            <a href="#" onClick={(e) => { e.preventDefault(); setShowForm(true); }}> Erstelle einen neuen</a>.</p>
        </div>
      ) : (
        <div className="table-responsive">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Typ</th>
                <th>Mitglieder</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {ausschuesse.map((ausschuss) => (
                <tr key={ausschuss.id}>
                  <td>{ausschuss.name}</td>
                  <td>{ausschuss.typ}</td>
                  <td>{ausschuss.mitglieder?.length || 0}</td>
                  <td>{ausschuss.aktiv ? '✅' : '❌'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}
