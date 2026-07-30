import { useEffect, useState } from 'react'
import api from '../api/client'

export default function Abwesenheiten() {
  const [absences, setAbsences] = useState([])
  const [persons, setPersons] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [sortBy, setSortBy] = useState('date') // 'date' or 'person'
  const [filterPersonId, setFilterPersonId] = useState('')
  const [form, setForm] = useState({
    person_id: '',
    von: '',
    bis: '',
    art: 'Urlaub',
    bemerkung: '',
  })
  const [validationError, setValidationError] = useState('')

  const fetchData = async () => {
    try {
      setError('')
      const [abs, pers] = await Promise.all([
        api.get('/absences'),
        api.get('/persons'),
      ])
      setAbsences(abs.data)
      setPersons(pers.data)
    } catch (error) {
      const message =
        error.response?.data?.detail || error.message || 'Fehler beim Laden'
      setError(message)
      console.error('Error loading data:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const handleShowForm = () => {
    setEditingId(null)
    setForm({ person_id: '', von: '', bis: '', art: 'Urlaub', bemerkung: '' })
    setValidationError('')
    setShowForm(true)
  }

  const handleEdit = (absence) => {
    setForm({
      person_id: absence.person_id.toString(),
      von: absence.von,
      bis: absence.bis,
      art: absence.art,
      bemerkung: absence.bemerkung || '',
    })
    setEditingId(absence.id)
    setValidationError('')
    setShowForm(true)
  }

  const handleCancel = () => {
    setShowForm(false)
    setEditingId(null)
    setForm({ person_id: '', von: '', bis: '', art: 'Urlaub', bemerkung: '' })
    setValidationError('')
  }

  const validateForm = () => {
    if (!form.person_id) {
      setValidationError('Person erforderlich')
      return false
    }
    if (!form.von) {
      setValidationError('Von-Datum erforderlich')
      return false
    }
    if (!form.bis) {
      setValidationError('Bis-Datum erforderlich')
      return false
    }
    if (form.bis < form.von) {
      setValidationError('Bis-Datum muss nach oder gleich Von-Datum sein')
      return false
    }
    return true
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!validateForm()) return

    try {
      setError('')
      const payload = {
        person_id: parseInt(form.person_id),
        von: form.von,
        bis: form.bis,
        art: form.art,
        bemerkung: form.bemerkung,
      }

      if (editingId) {
        await api.put(`/absences/${editingId}`, payload)
      } else {
        await api.post('/absences', payload)
      }

      handleCancel()
      await fetchData()
    } catch (err) {
      const message =
        err.response?.data?.detail || err.message || 'Fehler beim Speichern'
      setError(message)
      console.error('Error saving absence:', err)
    }
  }

  const handleDelete = async (id) => {
    if (!window.confirm('Abwesenheit wirklich löschen?')) return

    try {
      setError('')
      await api.delete(`/absences/${id}`)
      await fetchData()
    } catch (err) {
      const message =
        err.response?.data?.detail || err.message || 'Fehler beim Löschen'
      setError(message)
      console.error('Error deleting absence:', err)
    }
  }

  // Filter absences
  const filteredAbsences = filterPersonId
    ? absences.filter((a) => a.person_id.toString() === filterPersonId)
    : absences

  // Sort absences
  const sortedAbsences = [...filteredAbsences].sort((a, b) => {
    if (sortBy === 'person') {
      return (a.person_name || '').localeCompare(b.person_name || '')
    } else {
      // sort by date
      return new Date(a.von) - new Date(b.von)
    }
  })

  return (
    <div className="absences-container">
      {error && <div className="alert alert-danger">{error}</div>}

      <div className="section-header">
        <h2>Abwesenheiten-Verwaltung</h2>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={async () => {
              try {
                setError('')
                const res = await api.get('/export/formular/abwesenheit.pdf', {
                  params: { mit_namen: true },
                  responseType: 'blob',
                })
                const blob = new Blob([res.data], { type: 'application/pdf' })
                const url = window.URL.createObjectURL(blob)
                const a = document.createElement('a')
                a.href = url
                a.download = 'formular_abwesenheit_personen.pdf'
                document.body.appendChild(a)
                a.click()
                a.remove()
                window.URL.revokeObjectURL(url)
              } catch (err) {
                setError(`PDF-Download fehlgeschlagen: ${err.message}`)
              }
            }}
            title="Eine Seite je aktiver Person – zum Verteilen in der GR"
          >
            📄 Formular (alle Personen)
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={async () => {
              try {
                setError('')
                const res = await api.get('/export/formular/abwesenheit.pdf', {
                  params: { mit_namen: false },
                  responseType: 'blob',
                })
                const blob = new Blob([res.data], { type: 'application/pdf' })
                const url = window.URL.createObjectURL(blob)
                const a = document.createElement('a')
                a.href = url
                a.download = 'formular_abwesenheit_leer.pdf'
                document.body.appendChild(a)
                a.click()
                a.remove()
                window.URL.revokeObjectURL(url)
              } catch (err) {
                setError(`PDF-Download fehlgeschlagen: ${err.message}`)
              }
            }}
            title="Leeres Blatt ohne Namen"
          >
            📄 Leeres Formular
          </button>
          <button className="btn btn-primary" onClick={handleShowForm}>
            + Abwesenheit hinzufügen
          </button>
        </div>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="admin-form">
          <h3>{editingId ? 'Abwesenheit bearbeiten' : 'Neue Abwesenheit'}</h3>

          {validationError && (
            <div className="alert alert-danger">{validationError}</div>
          )}

          <div className="form-grid">
            <div>
              <label htmlFor="person_id">Person *</label>
              <select
                id="person_id"
                className="form-control"
                value={form.person_id}
                onChange={(e) => setForm({ ...form, person_id: e.target.value })}
                required
              >
                <option value="">-- Wählen --</option>
                {persons.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.vorname} {p.nachname}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="von">Von (Datum) *</label>
              <input
                id="von"
                type="date"
                className="form-control"
                value={form.von}
                onChange={(e) => setForm({ ...form, von: e.target.value })}
                required
              />
            </div>

            <div>
              <label htmlFor="bis">Bis (Datum) *</label>
              <input
                id="bis"
                type="date"
                className="form-control"
                value={form.bis}
                onChange={(e) => setForm({ ...form, bis: e.target.value })}
                required
              />
            </div>

            <div>
              <label htmlFor="art">Grund *</label>
              <select
                id="art"
                className="form-control"
                value={form.art}
                onChange={(e) => setForm({ ...form, art: e.target.value })}
                required
              >
                <option value="Urlaub">Urlaub</option>
                <option value="Krankheit">Krankheit</option>
                <option value="Dienstreise">Dienstreise</option>
                <option value="Entschuldigt">Entschuldigt</option>
                <option value="Sonstiges">Sonstiges</option>
              </select>
            </div>
          </div>

          <div>
            <label htmlFor="bemerkung">Notiz</label>
            <textarea
              id="bemerkung"
              className="form-control"
              value={form.bemerkung}
              onChange={(e) => setForm({ ...form, bemerkung: e.target.value })}
              rows="3"
              placeholder="Optionale Notiz"
            />
          </div>

          <div className="form-buttons">
            <button type="submit" className="btn btn-success">
              {editingId ? 'Aktualisieren' : 'Erstellen'}
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={handleCancel}
            >
              Abbrechen
            </button>
          </div>
        </form>
      )}

      <div className="table-controls">
        <div className="control-group">
          <label htmlFor="filter-person">Filter nach Person:</label>
          <select
            id="filter-person"
            className="form-control"
            value={filterPersonId}
            onChange={(e) => setFilterPersonId(e.target.value)}
          >
            <option value="">-- Alle Personen --</option>
            {persons.map((p) => (
              <option key={p.id} value={p.id}>
                {p.vorname} {p.nachname}
              </option>
            ))}
          </select>
        </div>

        <div className="control-group">
          <label htmlFor="sort-by">Sortieren nach:</label>
          <select
            id="sort-by"
            className="form-control"
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
          >
            <option value="date">Datum (aufsteigend)</option>
            <option value="person">Person (alphabetisch)</option>
          </select>
        </div>
      </div>

      {loading ? (
        <div className="alert alert-info">Lädt...</div>
      ) : sortedAbsences.length === 0 ? (
        <div className="alert alert-info">Keine Abwesenheiten vorhanden</div>
      ) : (
        <div className="table-responsive">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Person</th>
                <th>Von</th>
                <th>Bis</th>
                <th>Grund</th>
                <th>Notiz</th>
                <th>Aktionen</th>
              </tr>
            </thead>
            <tbody>
              {sortedAbsences.map((absence) => (
                <tr key={absence.id}>
                  <td>{absence.person_name}</td>
                  <td>{absence.von}</td>
                  <td>{absence.bis}</td>
                  <td>{absence.art}</td>
                  <td>{absence.bemerkung || '-'}</td>
                  <td className="actions">
                    <button
                      className="btn btn-sm btn-warning"
                      onClick={() => handleEdit(absence)}
                    >
                      Bearbeiten
                    </button>
                    <button
                      className="btn btn-sm btn-danger"
                      onClick={() => handleDelete(absence.id)}
                    >
                      Löschen
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
