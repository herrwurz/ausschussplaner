import { useEffect, useState } from 'react'
import api from '../api/client'

// Nur die für die Terminberechnung relevanten Stunden (Engine nutzt volle Stunden)
const HOURS = [7, 16, 17, 18, 19]
const DAYS = ['Mo', 'Di', 'Mi', 'Do', 'Fr']

const hourLabel = (h) => `${String(Math.floor(h)).padStart(2, '0')}:${h % 1 ? '30' : '00'}`
const emptyMatrix = () => {
  const m = {}
  DAYS.forEach((day) => HOURS.forEach((hour) => { m[`${day}-${hour}`] = false }))
  return m
}

export default function Verfuegbarkeiten() {
  const [persons, setPersons] = useState([])
  const [perioden, setPerioden] = useState([])
  const [selectedPerson, setSelectedPerson] = useState('')
  const [selectedPeriode, setSelectedPeriode] = useState('')
  const [availability, setAvailability] = useState({})
  // Einträge außerhalb des Rasters (z.B. halbe Stunden) beim Speichern erhalten
  const [extraItems, setExtraItems] = useState([])
  const [istFallback, setIstFallback] = useState(false)
  const [uebersicht, setUebersicht] = useState(null) // {personId: matrix} für "Alle"
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')

  useEffect(() => {
    const fetchBase = async () => {
      try {
        const [pRes, perRes] = await Promise.all([
          api.get('/persons'),
          api.get('/perioden'),
        ])
        setPersons(pRes.data.filter(p => p.aktiv))
        setPerioden(perRes.data)
        // Erste Periode vorauswählen
        if (perRes.data.length > 0) setSelectedPeriode(String(perRes.data[0].id))
      } catch (error) {
        setMessage('❌ Stammdaten laden fehlgeschlagen')
        console.error('Error:', error)
      } finally {
        setLoading(false)
      }
    }
    fetchBase()
  }, [])

  const periodeParams = () => ({ periode_id: selectedPeriode })

  const itemsToMatrix = (items) => {
    const matrix = emptyMatrix()
    const extras = []
    const dayMap = { MO: 'Mo', DI: 'Di', MI: 'Mi', DO: 'Do', FR: 'Fr' }
    items.forEach((item) => {
      if (!item.verfuegbar) return
      const day = dayMap[item.wochentag] || item.wochentag
      const hour = Number(item.stunde)
      const key = `${day}-${hour}`
      if (key in matrix) matrix[key] = true
      else extras.push(item) // z.B. 16.5 — nicht im Raster, aber nicht verlieren
    })
    return { matrix, extras }
  }

  const ladePerson = async (personId, periodeId) => {
    setMessage('')
    setAvailability({})
    setExtraItems([])
    setIstFallback(false)
    if (!personId || personId === 'alle' || !periodeId) return
    try {
      // effektiv=true: zeigt Standardwerte als Ausgangsbasis, solange die
      // Periode noch keine eigenen Einträge hat
      const res = await api.get(`/persons/${personId}/verfuegbarkeit`, {
        params: { periode_id: periodeId, effektiv: true },
      })
      const { matrix, extras } = itemsToMatrix(res.data)
      setAvailability(matrix)
      setExtraItems(extras)
      // Stammen die Werte aus dem Standard-Fallback? (kein Eintrag trägt die Periode)
      if (res.data.length > 0 && res.data.every(i => i.periode_id === null)) setIstFallback(true)
    } catch (error) {
      setMessage('❌ Verfügbarkeit laden fehlgeschlagen')
      console.error('Error:', error)
    }
  }

  const ladeUebersicht = async (periodeId) => {
    setMessage('')
    setUebersicht(null)
    if (!periodeId) return
    try {
      const results = await Promise.all(
        persons.map((p) =>
          api.get(`/persons/${p.id}/verfuegbarkeit`, {
            params: { periode_id: periodeId, effektiv: true },
          }).then((res) => [p.id, itemsToMatrix(res.data).matrix])
        )
      )
      setUebersicht(Object.fromEntries(results))
    } catch (error) {
      setMessage('❌ Übersicht laden fehlgeschlagen')
      console.error('Error:', error)
    }
  }

  const handlePersonChange = (personId) => {
    setSelectedPerson(personId)
    if (personId === 'alle') ladeUebersicht(selectedPeriode)
    else ladePerson(personId, selectedPeriode)
  }

  const handlePeriodeChange = (periodeId) => {
    setSelectedPeriode(periodeId)
    if (selectedPerson === 'alle') ladeUebersicht(periodeId)
    else if (selectedPerson) ladePerson(selectedPerson, periodeId)
  }

  const toggleAvailability = (day, hour) => {
    const key = `${day}-${hour}`
    setIstFallback(false)
    setAvailability((prev) => ({ ...prev, [key]: !prev[key] }))
  }

  const toggleDay = (day) => {
    const allSet = HOURS.every((hour) => availability[`${day}-${hour}`])
    setIstFallback(false)
    setAvailability((prev) => {
      const next = { ...prev }
      HOURS.forEach((hour) => { next[`${day}-${hour}`] = !allSet })
      return next
    })
  }

  const handleSave = async () => {
    try {
      setSaving(true)
      setMessage('')
      const items = []
      DAYS.forEach((day) => {
        HOURS.forEach((hour) => {
          if (availability[`${day}-${hour}`]) {
            items.push({ wochentag: day, stunde: hour, verfuegbar: true })
          }
        })
      })
      extraItems.forEach((item) => {
        items.push({ wochentag: item.wochentag, stunde: item.stunde, verfuegbar: item.verfuegbar })
      })
      await api.put(`/persons/${selectedPerson}/verfuegbarkeit`, { items }, { params: periodeParams() })
      const periodeName = perioden.find(p => String(p.id) === String(selectedPeriode))?.name || selectedPeriode
      setMessage(`✅ Verfügbarkeiten für Periode ${periodeName} gespeichert`)
      setIstFallback(false)
      setTimeout(() => setMessage(''), 3000)
    } catch (error) {
      setMessage(`❌ Speichern fehlgeschlagen: ${error.response?.data?.detail || error.message}`)
      console.error('Error saving:', error)
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <p>Lade Stammdaten…</p>

  const person = persons.find(p => String(p.id) === String(selectedPerson))

  const downloadErhebungsbogen = async () => {
    try {
      setMessage('')
      const params = {}
      if (selectedPeriode) {
        const p = perioden.find((x) => String(x.id) === String(selectedPeriode))
        if (p) params.periode = `${p.name} (${p.start_jahr}–${p.end_jahr})`
      }
      const res = await api.get('/export/formular/erhebung.pdf', {
        params,
        responseType: 'blob',
      })
      const blob = new Blob([res.data], { type: 'application/pdf' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `erhebungsbogen_${new Date().toISOString().slice(0, 10)}.pdf`
      document.body.appendChild(a)
      a.click()
      a.remove()
      window.URL.revokeObjectURL(url)
      setMessage('✅ Erhebungsbogen heruntergeladen')
      setTimeout(() => setMessage(''), 3000)
    } catch (err) {
      setMessage(`❌ PDF-Download fehlgeschlagen: ${err.message}`)
    }
  }

  return (
    <div>
      <div className="section-header">
        <h2>Verfügbarkeiten</h2>
        <button
          type="button"
          className="btn btn-primary"
          onClick={downloadErhebungsbogen}
          title="Ein Formular: alle Namen | Abwesenheit | Uhrzeiten – zum Verteilen in der GR"
        >
          📄 Erhebungsbogen (GR)
        </button>
      </div>

      {message && (
        <div style={{
          padding: '0.75rem 1rem', marginBottom: '1rem', borderRadius: '4px',
          background: message.includes('✅') ? '#d1fae5' : '#fee2e2',
          color: message.includes('✅') ? '#065f46' : '#7f1d1d',
        }}>
          {message}
        </div>
      )}

      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', marginBottom: '1.5rem' }}>
        <div>
          <label style={{ fontWeight: '600', marginBottom: '0.5rem', display: 'block' }}>Periode:</label>
          <select
            value={selectedPeriode}
            onChange={(e) => handlePeriodeChange(e.target.value)}
            style={{ padding: '0.5rem', border: '1px solid #d1d5db', borderRadius: '4px', fontSize: '0.95rem', minWidth: '220px' }}
          >
            {perioden.length === 0 && <option value="">Keine Periode angelegt</option>}
            {perioden.map((p) => (
              <option key={p.id} value={p.id}>{p.name} ({p.start_jahr}–{p.end_jahr})</option>
            ))}
          </select>
        </div>
        <div>
          <label style={{ fontWeight: '600', marginBottom: '0.5rem', display: 'block' }}>Person:</label>
          <select
            value={selectedPerson}
            onChange={(e) => handlePersonChange(e.target.value)}
            style={{ padding: '0.5rem', border: '1px solid #d1d5db', borderRadius: '4px', fontSize: '0.95rem', minWidth: '220px' }}
          >
            <option value="">– Person wählen –</option>
            <option value="alle">Alle (Übersicht)</option>
            {persons.map((p) => (
              <option key={p.id} value={p.id}>{p.name || `${p.vorname} ${p.nachname}`}</option>
            ))}
          </select>
        </div>
      </div>

      {/* ── Übersicht aller Personen ── */}
      {selectedPerson === 'alle' && (
        uebersicht === null ? <p>Lade Übersicht…</p> : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ borderCollapse: 'collapse', background: 'white', fontSize: '0.8rem' }}>
              <thead>
                <tr>
                  <th rowSpan="2" style={{ padding: '0.35rem 0.6rem', border: '1px solid #d1d5db', background: '#1e3a8a', color: 'white' }}>Person</th>
                  {DAYS.map((day) => (
                    <th key={day} colSpan={HOURS.length} style={{ padding: '0.35rem', border: '1px solid #d1d5db', background: '#1e3a8a', color: 'white' }}>{day}</th>
                  ))}
                </tr>
                <tr>
                  {DAYS.map((day) => HOURS.map((hour) => (
                    <th key={`${day}-${hour}`} style={{ padding: '0.25rem 0.35rem', border: '1px solid #d1d5db', background: '#2563eb', color: 'white', fontWeight: '400' }}>
                      {hour % 1 ? String(Math.floor(hour)) + '½' : hourLabel(hour).slice(0, 2)}
                    </th>
                  )))}
                </tr>
              </thead>
              <tbody>
                {persons.map((p) => (
                  <tr key={p.id}>
                    <td style={{ padding: '0.35rem 0.6rem', border: '1px solid #d1d5db', whiteSpace: 'nowrap', fontWeight: '600' }}>
                      {p.name || `${p.vorname} ${p.nachname}`}
                    </td>
                    {DAYS.map((day) => HOURS.map((hour) => {
                      const ok = uebersicht[p.id]?.[`${day}-${hour}`]
                      return (
                        <td key={`${day}-${hour}`} style={{
                          padding: '0.25rem 0.35rem', border: '1px solid #e5e7eb', textAlign: 'center',
                          background: ok ? '#d1fae5' : '#fee2e2', color: ok ? '#065f46' : '#b91c1c',
                        }}>
                          {ok ? '✓' : '·'}
                        </td>
                      )
                    }))}
                  </tr>
                ))}
              </tbody>
            </table>
            <p style={{ fontSize: '0.85rem', color: '#666', marginTop: '0.5rem' }}>
              Verfügbarkeit aller Personen in der gewählten Periode.
              Nur Lesen — zum Bearbeiten eine Person wählen.
            </p>
          </div>
        )
      )}

      {/* ── Einzelperson bearbeiten ── */}
      {selectedPerson && selectedPerson !== 'alle' && (
        <>
          {istFallback && (
            <div style={{
              padding: '0.75rem 1rem', marginBottom: '1rem', borderRadius: '4px',
              background: '#fef3c7', color: '#92400e', border: '1px solid #fcd34d',
            }}>
              Diese Periode hat noch keine eigenen Einträge — angezeigt werden die
              übernommenen Grundwerte. Beim Speichern werden sie für diese Periode festgeschrieben.
            </div>
          )}

          <table style={{ borderCollapse: 'collapse', background: 'white' }}>
            <thead>
              <tr>
                <th style={{ padding: '0.5rem 1rem', border: '1px solid #d1d5db', background: '#1e3a8a', color: 'white' }}>Tag</th>
                {HOURS.map((hour) => (
                  <th key={hour} style={{ padding: '0.5rem 1rem', border: '1px solid #d1d5db', background: '#1e3a8a', color: 'white' }}>
                    {hourLabel(hour)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {DAYS.map((day) => (
                <tr key={day}>
                  <td
                    onClick={() => toggleDay(day)}
                    title="Klick: ganzen Tag umschalten"
                    style={{ padding: '0.5rem 1rem', border: '1px solid #d1d5db', fontWeight: '600', cursor: 'pointer' }}
                  >
                    {day}
                  </td>
                  {HOURS.map((hour) => (
                    <td
                      key={hour}
                      onClick={() => toggleAvailability(day, hour)}
                      style={{
                        padding: '0.5rem 1rem', border: '1px solid #d1d5db', textAlign: 'center',
                        cursor: 'pointer', userSelect: 'none',
                        background: availability[`${day}-${hour}`] ? '#d1fae5' : '#fee2e2',
                      }}
                    >
                      {availability[`${day}-${hour}`] ? '✓' : '–'}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>

          <p style={{ fontSize: '0.85rem', color: '#666', marginTop: '0.5rem' }}>
            ✓ = verfügbar. Eine Stunde deckt den Zeitraum bis zur nächsten vollen Stunde ab
            (07:00 = Frühsitzung 07:00–08:30, 19:00 = Spätsitzung 19:00–20:30).
            Gespeichert wird für die gewählte Periode.
          </p>

          <button
            className="btn btn-success"
            onClick={handleSave}
            disabled={saving}
            style={{ marginTop: '1rem' }}
          >
            {saving ? '⏳ Speichert…' : `💾 Speichern${person ? ` für ${person.name || person.vorname}` : ''}`}
          </button>
        </>
      )}
    </div>
  )
}
