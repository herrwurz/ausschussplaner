import { useState, useEffect } from 'react'
import api from '../api/client'
import { usePeriod } from '../contexts/PeriodContext'
import PageHeader from '../components/PageHeader'

export default function AusschuessProPeriode() {
  const { perioden, selectedPeriodeId: selectedPeriodId } = usePeriod()
  const [ausschuesse, setAusschuesse] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [showCopy, setShowCopy] = useState(false)
  const [copySourcePeriodId, setCopySourcePeriodId] = useState(null)
  const [formData, setFormData] = useState({
    name: '',
    typ: 'standard',
  })

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
      setError('')
      const payload = {
        name: formData.name,
        typ: 'standard',
        turnus: '',
        aktiv: true,
        mitglieder: []
      }
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

  const handleCopyFromPeriod = async (e) => {
    e.preventDefault()
    if (!copySourcePeriodId || !selectedPeriodId) return
    try {
      setError('')
      setSuccess('')
      const sourceRes = await api.get('/committees', {
        params: { periode_id: copySourcePeriodId }
      })
      const sourceList = sourceRes.data || []
      if (sourceList.length === 0) {
        setError('Quell-Periode hat keine Ausschüsse')
        return
      }
      let copied = 0
      let skipped = 0
      for (const src of sourceList) {
        try {
          await api.post(`/committees/${src.id}/copy-to-period`, null, {
            params: { target_periode_id: selectedPeriodId }
          })
          copied += 1
        } catch (err) {
          if (err.response?.status === 409) {
            skipped += 1
          } else {
            throw err
          }
        }
      }
      setSuccess(
        `${copied} Ausschuss/Ausschüsse kopiert (ohne Mitgliedschaften)` +
        (skipped ? `, ${skipped} übersprungen (bereits vorhanden)` : '') +
        '. Bitte Mitglieder neu zuweisen.'
      )
      setShowCopy(false)
      setCopySourcePeriodId(null)
      fetchAusschuesse()
    } catch (err) {
      setError(err.response?.data?.detail || 'Kopieren fehlgeschlagen')
    }
  }

  const handleDelete = async (id) => {
    if (!window.confirm('Ausschuss wirklich löschen?')) return
    try {
      await api.delete(`/committees/${id}`)
      fetchAusschuesse()
    } catch (err) {
      setError(err.response?.data?.detail || 'Löschen fehlgeschlagen')
    }
  }

  const handleCancel = () => {
    setShowForm(false)
    setFormData({ name: '', typ: 'standard' })
  }

  const currentPeriod = perioden.find(p => p.id === selectedPeriodId)
  const otherPeriods = perioden.filter(p => p.id !== selectedPeriodId)

  return (
    <>
      {error && <div className="alert alert-danger">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      <PageHeader
        title="Ausschüsse pro Gemeinderatsperiode"
        description="Jede Periode hat eigene Ausschuss-Instanzen. Beim Kopieren werden keine Mitgliedschaften übernommen. Periode oben in der Topbar wählen."
        actions={(
          <>
            <button className="btn btn-secondary" onClick={() => setShowCopy(true)} disabled={!selectedPeriodId || otherPeriods.length === 0}>
              Für Periode kopieren
            </button>
            <button className="btn btn-primary" onClick={() => setShowForm(true)}>
              + Neuer Ausschuss
            </button>
          </>
        )}
      />

      {showCopy && (
        <form className="admin-form" onSubmit={handleCopyFromPeriod}>
          <h3>Ausschüsse nach {currentPeriod?.name} kopieren</h3>
          <p style={{ fontSize: '0.9rem', color: 'var(--color-text-muted, #666)', marginBottom: '1rem' }}>
            Kopiert Name und Typ. Mitgliedschaften bleiben leer und müssen neu gesetzt werden.
          </p>
          <label style={{ fontWeight: '600', display: 'block', marginBottom: '0.5rem' }}>
            Quell-Periode:
          </label>
          <select
            value={copySourcePeriodId || ''}
            onChange={(e) => setCopySourcePeriodId(parseInt(e.target.value))}
            required
            style={{ padding: '0.5rem', marginBottom: '1rem', maxWidth: '400px', width: '100%' }}
          >
            <option value="">— wählen —</option>
            {otherPeriods.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} ({p.start_jahr}-{p.end_jahr})
              </option>
            ))}
          </select>
          <div className="form-buttons">
            <button type="submit" className="btn btn-success">Kopieren</button>
            <button type="button" className="btn btn-secondary" onClick={() => { setShowCopy(false); setCopySourcePeriodId(null) }}>
              Abbrechen
            </button>
          </div>
        </form>
      )}

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
          <div className="form-buttons">
            <button type="submit" className="btn btn-success">Erstellen</button>
            <button type="button" className="btn btn-secondary" onClick={handleCancel}>Abbrechen</button>
          </div>
        </form>
      )}

      {loading ? (
        <p>Lädt...</p>
      ) : ausschuesse.length === 0 ? (
        <div className="alert alert-info">
          <p>Keine Ausschüsse in {currentPeriod?.name}. Erstellen oder aus anderer Periode kopieren.</p>
        </div>
      ) : (
        <div className="table-responsive">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Obmann</th>
                <th>Mitglieder</th>
                <th>Status</th>
                <th>Aktionen</th>
              </tr>
            </thead>
            <tbody>
              {ausschuesse.map((ausschuss) => {
                const obmann = (ausschuss.mitglieder || []).find(
                  (m) => m.rolle === 'Obmann',
                )
                return (
                <tr key={ausschuss.id}>
                  <td>{ausschuss.name}</td>
                  <td>{obmann?.name || '—'}</td>
                  <td>{ausschuss.mitglieder?.length || 0}</td>
                  <td>{ausschuss.aktiv ? 'Aktiv' : 'Inaktiv'}</td>
                  <td className="actions">
                    <button className="btn btn-sm btn-danger" onClick={() => handleDelete(ausschuss.id)}>
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
