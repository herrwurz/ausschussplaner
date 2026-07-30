import { useState, useEffect } from 'react'
import api from '../api/client'

export default function FixierteTermine() {
  const [termine, setTermine] = useState([])
  const [ausschuesse, setAusschuesse] = useState([])
  const [loading, setLoading] = useState(true)
  const [exporting, setExporting] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [perioden, setPerioden] = useState([])
  const [selectedPeriodeId, setSelectedPeriodeId] = useState(null)

  useEffect(() => {
    fetchPerioden()
    fetchAusschuesse()
  }, [])

  const fetchPerioden = async () => {
    try {
      const res = await api.get('/perioden')
      setPerioden(res.data)
      if (res.data.length > 0) {
        setSelectedPeriodeId(res.data[0].id)
      }
    } catch (err) {
      setError('Perioden laden fehlgeschlagen')
    }
  }

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

  const handleDelete = async (vorschlagId, ausschussId, wochentag, zeit) => {
    if (!window.confirm(`Termin löschen? Ausschuss ${ausschussId} ${wochentag} ${zeit}`)) {
      return
    }

    try {
      await api.delete(`/calculate/results/${vorschlagId}`)
      setMessage(`✅ Termin gelöscht`)
      setTimeout(() => setMessage(''), 3000)
      fetchTermine()
    } catch (err) {
      setMessage(`❌ Fehler beim Löschen: ${err.response?.data?.detail || err.message}`)
      console.error(err)
    }
  }

  const handlePdfExport = async () => {
    try {
      setExporting(true)
      setMessage('')
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
      setMessage('✅ PDF heruntergeladen')
      setTimeout(() => setMessage(''), 3000)
    } catch (err) {
      setMessage(`❌ PDF-Export fehlgeschlagen: ${err.response?.data?.detail || err.message}`)
      console.error(err)
    } finally {
      setExporting(false)
    }
  }

  const selectedPeriode = perioden.find(p => p.id === selectedPeriodeId)

  // Gruppiere Termine nach Woche und Tag
  const grupiertNachWoche = {}
  // Verwende alle Termine (auch mit 0/0, da manuell fixierte keine Mitgliederdaten haben)
  const gueltigeTermine = termine

  gueltigeTermine.forEach(termin => {
    if (!grupiertNachWoche[termin.woche]) {
      grupiertNachWoche[termin.woche] = {}
    }
    // Extrahiere Wochentag aus dem Enum oder verwende direkt
    const wochentag = typeof termin.wochentag === 'string'
      ? termin.wochentag.substring(0, 2).toUpperCase()
      : (termin.wochentag.split('.')[1] || 'Mo').substring(0, 2).toUpperCase()

    if (!grupiertNachWoche[termin.woche][wochentag]) {
      grupiertNachWoche[termin.woche][wochentag] = []
    }
    grupiertNachWoche[termin.woche][wochentag].push(termin)
  })

  const formatMinutesAsTime = (minutes) => {
    if (!minutes && minutes !== 0) return '--:--'
    const h = Math.floor(minutes / 60)
    const m = minutes % 60
    return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`
  }

  const tage = ['Mo', 'Di', 'Mi', 'Do', 'Fr']
  const wochen = Object.keys(grupiertNachWoche).sort((a, b) => parseInt(a) - parseInt(b))

  return (
    <>
      {error && <div className="alert alert-danger">{error}</div>}

      <div className="section-header">
        <h2>📆 Fixierte Termine - Kalender</h2>
        <button
          className="btn btn-primary"
          onClick={handlePdfExport}
          disabled={loading || exporting || termine.length === 0}
          title={termine.length === 0 ? 'Keine Termine zum Exportieren' : 'Wochenplan als PDF herunterladen'}
        >
          {exporting ? 'PDF wird erstellt…' : '📄 PDF herunterladen'}
        </button>
      </div>

      {message && (
        <div style={{
          padding: '0.75rem 1rem',
          marginBottom: '1rem',
          borderRadius: '4px',
          background: message.includes('✅') ? '#d1fae5' : '#fee2e2',
          color: message.includes('✅') ? '#065f46' : '#7f1d1d',
          fontSize: '0.9rem',
          border: `1px solid ${message.includes('✅') ? '#a7f3d0' : '#fca5a5'}`,
        }}>
          {message}
        </div>
      )}

      {/* Periode Selector */}
      <div style={{ marginBottom: '1.5rem', padding: '1rem', background: '#f3f4f6', borderRadius: '4px' }}>
        <label style={{ fontWeight: '600', marginBottom: '0.5rem', display: 'block' }}>
          Gemeinderatsperiode:
        </label>
        <select
          value={selectedPeriodeId || ''}
          onChange={(e) => setSelectedPeriodeId(parseInt(e.target.value))}
          style={{
            padding: '0.5rem',
            border: '1px solid #d1d5db',
            borderRadius: '4px',
            fontSize: '0.95rem',
            width: '100%',
            maxWidth: '400px',
          }}
        >
          {perioden.map((periode) => (
            <option key={periode.id} value={periode.id}>
              {periode.name} ({periode.start_jahr}–{periode.end_jahr})
            </option>
          ))}
        </select>
      </div>

      {loading ? (
        <p>Lädt...</p>
      ) : termine.length === 0 ? (
        <div className="alert alert-info">
          <p>Keine fixierten Termine vorhanden. Gehen Sie zum "Termine" Tab und fixieren Sie Termine aus dem Kalender.</p>
        </div>
      ) : (
        <div style={{ display: 'grid', gap: '2rem' }}>
          {wochen.map((woche) => (
            <div key={woche} style={{
              border: '1px solid #e5e7eb',
              borderRadius: '8px',
              padding: '1.5rem',
              background: '#f9fafb',
            }}>
              <h4 style={{ marginBottom: '1rem', marginTop: 0 }}>Woche {woche}</h4>
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(5, 1fr)',
                gap: '1rem',
              }}>
                {['MO', 'DI', 'MI', 'DO', 'FR'].map((tag) => (
                  <div key={tag} style={{
                    border: '1px solid #d1d5db',
                    borderRadius: '6px',
                    padding: '1rem',
                    background: 'white',
                    minHeight: '200px',
                  }}>
                    <h5 style={{ marginTop: 0, marginBottom: '1rem', color: '#1e3a8a' }}>
                      {tag}
                    </h5>
                    {!grupiertNachWoche[woche]?.[tag] || grupiertNachWoche[woche][tag].length === 0 ? (
                      <p style={{ color: '#999', fontSize: '0.85rem' }}>Keine Termine</p>
                    ) : (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                        {grupiertNachWoche[woche][tag].map((termin) => {
                          const ausschuss = ausschuesse.find(a => a.id === termin.ausschuss_id)
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
                              display: 'flex',
                              justifyContent: 'space-between',
                              alignItems: 'center',
                            }}
                          >
                            <div>
                              <div style={{ fontWeight: '600', marginBottom: '0.25rem' }}>
                                {ausschussName}
                              </div>
                              <div style={{ color: '#666', fontSize: '0.8rem' }}>
                                {formatMinutesAsTime(termin.start_minute)}–{formatMinutesAsTime(termin.end_minute)}
                              </div>
                            </div>
                            <button
                              onClick={() => handleDelete(
                                termin.id,
                                termin.ausschuss_id,
                                tag,
                                `${formatMinutesAsTime(termin.start_minute)}–${formatMinutesAsTime(termin.end_minute)}`
                              )}
                              style={{
                                padding: '0.4rem 0.6rem',
                                fontSize: '0.75rem',
                                background: '#ef4444',
                                color: 'white',
                                border: 'none',
                                borderRadius: '3px',
                                cursor: 'pointer',
                                flexShrink: 0,
                              }}
                            >
                              ✕ Löschen
                            </button>
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
    </>
  )
}
