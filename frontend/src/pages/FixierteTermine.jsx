import { useState, useEffect } from 'react'
import api from '../api/client'
import { usePeriod } from '../contexts/PeriodContext'
import PageHeader from '../components/PageHeader'

const SLOT_OPTIONS = [
  { start: 7 * 60, end: 8 * 60 + 30, label: '07:00–08:30' },
  { start: 16 * 60, end: 17 * 60 + 30, label: '16:00–17:30' },
  { start: 16 * 60 + 30, end: 18 * 60, label: '16:30–18:00' },
  { start: 17 * 60, end: 18 * 60 + 30, label: '17:00–18:30' },
  { start: 17 * 60 + 30, end: 19 * 60, label: '17:30–19:00' },
  { start: 18 * 60, end: 19 * 60 + 30, label: '18:00–19:30' },
  { start: 18 * 60 + 30, end: 20 * 60, label: '18:30–20:00' },
  { start: 19 * 60, end: 20 * 60 + 30, label: '19:00–20:30' },
]

const WOCHENTAGE = [
  { value: 'MO', label: 'Mo' },
  { value: 'DI', label: 'Di' },
  { value: 'MI', label: 'Mi' },
  { value: 'DO', label: 'Do' },
  { value: 'FR', label: 'Fr' },
]

function formatMinutesAsTime(minutes) {
  if (!minutes && minutes !== 0) return '--:--'
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`
}

function wochentagKey(termin) {
  const raw = typeof termin.wochentag === 'string' ? termin.wochentag : String(termin.wochentag)
  return raw.substring(0, 2).toUpperCase()
}

export default function FixierteTermine() {
  const { selectedPeriodeId, selectedPeriode } = usePeriod()
  const [termine, setTermine] = useState([])
  const [ausschuesse, setAusschuesse] = useState([])
  const [loading, setLoading] = useState(true)
  const [exporting, setExporting] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [moveTermin, setMoveTermin] = useState(null)
  const [moveForm, setMoveForm] = useState({ woche: 1, wochentag: 'MO', start_minute: 16 * 60 })
  const [absageTermin, setAbsageTermin] = useState(null)
  const [absageNotiz, setAbsageNotiz] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    fetchAusschuesse()
  }, [])

  const fetchAusschuesse = async () => {
    try {
      const res = await api.get('/committees')
      setAusschuesse(res.data)
    } catch (err) {
      console.error('Ausschüsse laden fehlgeschlagen:', err)
    }
  }

  useEffect(() => {
    if (selectedPeriodeId) {
      fetchTermine()
    }
  }, [selectedPeriodeId])

  const fetchTermine = async () => {
    try {
      setLoading(true)
      const res = await api.get('/calculate/results')
      setTermine(res.data || [])
    } catch (err) {
      setError('Termine laden fehlgeschlagen')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const flash = (text) => {
    setMessage(text)
    setTimeout(() => setMessage(''), 4000)
  }

  const openMove = (termin) => {
    setMoveTermin(termin)
    setMoveForm({
      woche: termin.woche,
      wochentag: wochentagKey(termin),
      start_minute: termin.start_minute,
    })
  }

  const handleMove = async (e) => {
    e.preventDefault()
    if (!moveTermin) return
    const slot = SLOT_OPTIONS.find((s) => s.start === Number(moveForm.start_minute)) || SLOT_OPTIONS[1]
    try {
      setSaving(true)
      await api.patch(`/calculate/results/${moveTermin.id}`, {
        woche: Number(moveForm.woche),
        wochentag: moveForm.wochentag,
        start_minute: slot.start,
        end_minute: slot.end,
      })
      flash('Termin verschoben')
      setMoveTermin(null)
      fetchTermine()
    } catch (err) {
      flash(`Verschieben fehlgeschlagen: ${err.response?.data?.detail || err.message}`)
    } finally {
      setSaving(false)
    }
  }

  const handleAbsagen = async (e) => {
    e.preventDefault()
    if (!absageTermin) return
    try {
      setSaving(true)
      await api.post(`/calculate/results/${absageTermin.id}/absagen`, {
        notiz: absageNotiz.trim(),
      })
      flash('Termin abgesagt')
      setAbsageTermin(null)
      setAbsageNotiz('')
      fetchTermine()
    } catch (err) {
      flash(`Absagen fehlgeschlagen: ${err.response?.data?.detail || err.message}`)
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (vorschlagId, ausschussId, wochentag, zeit) => {
    if (!window.confirm(`Termin endgültig löschen? Ausschuss ${ausschussId} ${wochentag} ${zeit}`)) {
      return
    }
    try {
      await api.delete(`/calculate/results/${vorschlagId}`)
      flash('Termin gelöscht')
      fetchTermine()
    } catch (err) {
      flash(`Löschen fehlgeschlagen: ${err.response?.data?.detail || err.message}`)
    }
  }

  const handlePdfExport = async () => {
    try {
      setExporting(true)
      const res = await api.get('/calculate/results/pdf', { responseType: 'blob' })
      const blob = new Blob([res.data], { type: 'application/pdf' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `sitzungsplan_${new Date().toISOString().slice(0, 10)}.pdf`
      document.body.appendChild(a)
      a.click()
      a.remove()
      window.URL.revokeObjectURL(url)
      flash('PDF heruntergeladen')
    } catch (err) {
      flash(`PDF-Export fehlgeschlagen: ${err.response?.data?.detail || err.message}`)
    } finally {
      setExporting(false)
    }
  }

  const grupiertNachWoche = {}
  termine.forEach((termin) => {
    if (!grupiertNachWoche[termin.woche]) {
      grupiertNachWoche[termin.woche] = {}
    }
    const tag = wochentagKey(termin)
    if (!grupiertNachWoche[termin.woche][tag]) {
      grupiertNachWoche[termin.woche][tag] = []
    }
    grupiertNachWoche[termin.woche][tag].push(termin)
  })

  const wochen = Object.keys(grupiertNachWoche).sort((a, b) => parseInt(a, 10) - parseInt(b, 10))

  return (
    <>
      {error && <div className="alert alert-danger">{error}</div>}

      <PageHeader
        title="Fixierte Termine"
        description={selectedPeriode ? `${selectedPeriode.name} · Kalenderansicht` : 'Periode in der Topbar wählen'}
        actions={(
          <>
            <button
              className="btn btn-primary"
              onClick={handlePdfExport}
              disabled={loading || exporting || termine.length === 0}
            >
              {exporting ? 'PDF wird erstellt…' : 'PDF herunterladen'}
            </button>
            <button
              className="btn btn-secondary"
              disabled={loading || termine.length === 0}
              onClick={async () => {
                try {
                  const res = await api.get('/export/sitzungen.ics', { responseType: 'blob' })
                  const blob = new Blob([res.data], { type: 'text/calendar' })
                  const url = window.URL.createObjectURL(blob)
                  const a = document.createElement('a')
                  a.href = url
                  a.download = `sitzungen_${new Date().toISOString().slice(0, 10)}.ics`
                  document.body.appendChild(a)
                  a.click()
                  a.remove()
                  window.URL.revokeObjectURL(url)
                  flash('Kalenderdatei (.ics) heruntergeladen')
                } catch (err) {
                  flash(`ICS-Export fehlgeschlagen: ${err.message}`)
                }
              }}
            >
              ICS
            </button>
          </>
        )}
      />

      {message && (
        <div className={`alert ${message.includes('fehlgeschlagen') ? 'alert-danger' : 'alert-success'}`}>
          {message}
        </div>
      )}

      {loading ? (
        <p>Lädt...</p>
      ) : termine.length === 0 ? (
        <div className="alert alert-info">
          <p>Keine fixierten Termine. Über Berechnung Vorschläge erzeugen und fixieren.</p>
        </div>
      ) : (
        <div style={{ display: 'grid', gap: '2rem' }}>
          {wochen.map((woche) => (
            <div
              key={woche}
              style={{
                border: '1px solid #e5e7eb',
                borderRadius: '8px',
                padding: '1.5rem',
                background: '#f9fafb',
              }}
            >
              <h4 style={{ marginBottom: '1rem', marginTop: 0 }}>Woche {woche}</h4>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '1rem' }}>
                {['MO', 'DI', 'MI', 'DO', 'FR'].map((tag) => (
                  <div
                    key={tag}
                    style={{
                      border: '1px solid #d1d5db',
                      borderRadius: '6px',
                      padding: '1rem',
                      background: 'white',
                      minHeight: '200px',
                    }}
                  >
                    <h5 style={{ marginTop: 0, marginBottom: '1rem', color: '#1e3a8a' }}>{tag}</h5>
                    {!grupiertNachWoche[woche]?.[tag]?.length ? (
                      <p style={{ color: '#999', fontSize: '0.85rem' }}>Keine Termine</p>
                    ) : (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                        {grupiertNachWoche[woche][tag].map((termin) => {
                          const ausschuss = ausschuesse.find((a) => a.id === termin.ausschuss_id)
                          const ausschussName = ausschuss ? ausschuss.name : `Ausschuss ${termin.ausschuss_id}`
                          return (
                            <div
                              key={termin.id}
                              style={{
                                padding: '0.75rem',
                                background: '#f0f4ff',
                                borderRadius: '4px',
                                fontSize: '0.85rem',
                                borderLeft: '3px solid #2563eb',
                              }}
                            >
                              <div style={{ fontWeight: 600, marginBottom: '0.25rem' }}>{ausschussName}</div>
                              <div style={{ color: '#666', fontSize: '0.8rem', marginBottom: '0.5rem' }}>
                                {formatMinutesAsTime(termin.start_minute)}–{formatMinutesAsTime(termin.end_minute)}
                              </div>
                              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem' }}>
                                <button type="button" className="btn btn-sm btn-secondary" onClick={() => openMove(termin)}>
                                  Verschieben
                                </button>
                                <button
                                  type="button"
                                  className="btn btn-sm btn-secondary"
                                  onClick={() => {
                                    setAbsageTermin(termin)
                                    setAbsageNotiz('')
                                  }}
                                >
                                  Absagen
                                </button>
                                <button
                                  type="button"
                                  className="btn btn-sm btn-danger"
                                  onClick={() => handleDelete(
                                    termin.id,
                                    termin.ausschuss_id,
                                    tag,
                                    `${formatMinutesAsTime(termin.start_minute)}–${formatMinutesAsTime(termin.end_minute)}`,
                                  )}
                                >
                                  Löschen
                                </button>
                              </div>
                            </div>
                          )
                        })}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {moveTermin && (
        <div className="modal-backdrop" role="dialog" aria-modal="true">
          <form className="modal-card" onSubmit={handleMove}>
            <h3>Termin verschieben</h3>
            <p className="modal-card__hint">
              Konfliktprüfung: gleicher Tag und überlappende Zeit wird blockiert.
            </p>
            <label>
              Woche
              <input
                type="number"
                min={1}
                value={moveForm.woche}
                onChange={(e) => setMoveForm({ ...moveForm, woche: e.target.value })}
                required
              />
            </label>
            <label>
              Wochentag
              <select
                value={moveForm.wochentag}
                onChange={(e) => setMoveForm({ ...moveForm, wochentag: e.target.value })}
              >
                {WOCHENTAGE.map((d) => (
                  <option key={d.value} value={d.value}>{d.label}</option>
                ))}
              </select>
            </label>
            <label>
              Zeitslot
              <select
                value={moveForm.start_minute}
                onChange={(e) => setMoveForm({ ...moveForm, start_minute: Number(e.target.value) })}
              >
                {SLOT_OPTIONS.map((s) => (
                  <option key={s.start} value={s.start}>{s.label}</option>
                ))}
              </select>
            </label>
            <div className="modal-card__actions">
              <button type="button" className="btn btn-secondary" onClick={() => setMoveTermin(null)} disabled={saving}>
                Abbrechen
              </button>
              <button type="submit" className="btn btn-primary" disabled={saving}>
                {saving ? 'Speichern…' : 'Verschieben'}
              </button>
            </div>
          </form>
        </div>
      )}

      {absageTermin && (
        <div className="modal-backdrop" role="dialog" aria-modal="true">
          <form className="modal-card" onSubmit={handleAbsagen}>
            <h3>Termin absagen</h3>
            <p className="modal-card__hint">
              Der Termin bleibt als abgesagt erhalten und fällt aus Plan/Export heraus.
            </p>
            <label>
              Notiz / Grund (optional)
              <textarea
                rows={3}
                value={absageNotiz}
                onChange={(e) => setAbsageNotiz(e.target.value)}
                placeholder="z. B. Quorum nicht erreichbar"
              />
            </label>
            <div className="modal-card__actions">
              <button type="button" className="btn btn-secondary" onClick={() => setAbsageTermin(null)} disabled={saving}>
                Abbrechen
              </button>
              <button type="submit" className="btn btn-danger" disabled={saving}>
                {saving ? 'Absagen…' : 'Absagen'}
              </button>
            </div>
          </form>
        </div>
      )}

      <style>{`
        .modal-backdrop {
          position: fixed; inset: 0; background: rgba(15, 23, 42, 0.45);
          display: flex; align-items: center; justify-content: center; z-index: 80;
          padding: 1rem;
        }
        .modal-card {
          background: #fff; border-radius: 8px; padding: 1.25rem 1.5rem;
          width: min(420px, 100%); display: flex; flex-direction: column; gap: 0.75rem;
          box-shadow: 0 12px 40px rgba(0,0,0,0.2);
        }
        .modal-card h3 { margin: 0; }
        .modal-card__hint { margin: 0; color: #4b5563; font-size: 0.9rem; }
        .modal-card label { display: flex; flex-direction: column; gap: 0.35rem; font-size: 0.9rem; font-weight: 600; }
        .modal-card input, .modal-card select, .modal-card textarea {
          font-weight: 400; padding: 0.45rem 0.6rem; border: 1px solid #d1d5db; border-radius: 4px;
        }
        .modal-card__actions { display: flex; justify-content: flex-end; gap: 0.5rem; margin-top: 0.25rem; }
      `}</style>
    </>
  )
}
