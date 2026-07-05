import { useState, useEffect } from 'react'
import api from '../api/client'

export default function Terminberechnung() {
  const [perioden, setPerioden] = useState([])
  const [selectedPeriodeId, setSelectedPeriodeId] = useState(null)
  const [ausschuesse, setAusschuesse] = useState([])
  const [selectedAusschussIds, setSelectedAusschussIds] = useState([])
  const [planungswochen, setPlanungswochen] = useState(2)
  const [freitagModus, setFreitagModus] = useState('nein')
  // Sitzungsart trennt Standard-Ausschüsse von Stadtrat-/Gemeinderatssitzungen
  const [sitzungsart, setSitzungsart] = useState('ausschuesse')
  const [startDatum, setStartDatum] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [results, setResults] = useState(null)
  const [showResults, setShowResults] = useState(false)
  const [fixierteTermine, setFixierteTermine] = useState([])
  // 0 = alle Termine anzeigen; 100 würde alles außer Volltreffern wegfiltern
  const [minVerfuegbarkeit, setMinVerfuegbarkeit] = useState(0)
  const [maxAnzahlTermine, setMaxAnzahlTermine] = useState(1)

  useEffect(() => {
    console.log('✅ COMPONENT MOUNTED - minVerfuegbarkeit=' + minVerfuegbarkeit + ', maxAnzahlTermine=' + maxAnzahlTermine)
  }, [])

  useEffect(() => {
    fetchPerioden()
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

  useEffect(() => {
    if (selectedPeriodeId) {
      fetchAusschuesse()
    }
  }, [selectedPeriodeId])

  const fetchAusschuesse = async () => {
    try {
      const res = await api.get('/committees', { params: { periode_id: selectedPeriodeId } })
      setAusschuesse(res.data)
    } catch (err) {
      setError('Ausschüsse laden fehlgeschlagen')
    }
  }

  // Sitzungsart -> AusschussTyp Mapping ("alle" = kein Filter)
  const SITZUNGSART_TYP = { ausschuesse: 'standard', stadtrat: 'stadtrat', gemeinderat: 'gemeinderat' }
  const filterBySitzungsart = (liste, art) =>
    art === 'alle' ? liste : liste.filter(a => a.typ === SITZUNGSART_TYP[art])
  const gefilterteAusschuesse = filterBySitzungsart(ausschuesse, sitzungsart)

  // Bei Wechsel der Sitzungsart (oder neuen Ausschüssen) automatisch alle passenden wählen
  useEffect(() => {
    setSelectedAusschussIds(filterBySitzungsart(ausschuesse, sitzungsart).map(a => a.id))
  }, [ausschuesse, sitzungsart])

  const handleCalculate = async (e) => {
    e.preventDefault()
    try {
      setLoading(true)
      setError('')

      // Lade fixierte Termine VOR der Berechnung
      const fixRes = await api.get('/calculate/results')
      setFixierteTermine(fixRes.data || [])
      console.log('Geladene fixierte Termine:', fixRes.data)

      const payload = {
        ausschuss_ids: selectedAusschussIds.length > 0 ? selectedAusschussIds : null,
        planungswochen,
        freitag_modus: freitagModus,
        max_alternativen: maxAnzahlTermine,
        min_verfuegbarkeit: minVerfuegbarkeit,
        start_datum: startDatum || null,
      }

      console.log('DEBUG PAYLOAD:', payload)
      const res = await api.post('/calculate', payload)
      console.log('DEBUG RESPONSE analysen[0].top_termine count:', res.data.analysen?.[0]?.top_termine?.length)
      setResults(res.data)
      setShowResults(true)
    } catch (err) {
      setError(err.response?.data?.detail || 'Berechnung fehlgeschlagen')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const toggleAusschuss = (id) => {
    if (selectedAusschussIds.includes(id)) {
      setSelectedAusschussIds(selectedAusschussIds.filter(a => a !== id))
    } else {
      setSelectedAusschussIds([...selectedAusschussIds, id])
    }
  }

  const selectedPeriode = perioden.find(p => p.id === selectedPeriodeId)

  const fetchFixierteTermine = async () => {
    try {
      const res = await api.get('/calculate/results')
      setFixierteTermine(res.data || [])
    } catch (err) {
      console.error('Fehler beim Laden fixierter Termine:', err)
    }
  }

  return (
    <>
      {error && <div className="alert alert-danger">{error}</div>}

      {!showResults ? (
        <>
          <div className="section-header">
            <h2>Terminberechnung für Ausschüsse</h2>
          </div>

          <form className="admin-form" onSubmit={handleCalculate}>
            {/* Periode Selector */}
            <div style={{ marginBottom: '1.5rem' }}>
              <label style={{ fontWeight: '600', marginBottom: '0.5rem', display: 'block' }}>
                Periode:
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

            {/* Sitzungsart Selector */}
            <div style={{ marginBottom: '1.5rem' }}>
              <label style={{ fontWeight: '600', marginBottom: '0.5rem', display: 'block' }}>
                Sitzungsart:
              </label>
              <select
                value={sitzungsart}
                onChange={(e) => setSitzungsart(e.target.value)}
                style={{
                  padding: '0.5rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '4px',
                  fontSize: '0.95rem',
                  width: '100%',
                  maxWidth: '400px',
                }}
              >
                <option value="ausschuesse">Ausschüsse</option>
                <option value="stadtrat">Stadtratsitzung</option>
                <option value="gemeinderat">Gemeinderatsitzung</option>
                <option value="alle">Alle (gemeinsam berechnen)</option>
              </select>
              <p style={{ fontSize: '0.85rem', color: '#666', marginTop: '0.25rem' }}>
                Stadtrat- und Gemeinderatssitzungen werden getrennt von den Ausschüssen berechnet
              </p>
            </div>

            {/* Ausschüsse Selector */}
            <div style={{ marginBottom: '1.5rem' }}>
              <label style={{ fontWeight: '600', marginBottom: '0.5rem', display: 'block' }}>
                {sitzungsart === 'ausschuesse' ? 'Ausschüsse:' : 'Gremium:'}
              </label>
              <div style={{
                display: 'flex',
                flexWrap: 'wrap',
                gap: '0.5rem',
                padding: '1rem',
                border: '1px solid #d1d5db',
                borderRadius: '4px',
                background: '#f9fafb',
              }}>
                {gefilterteAusschuesse.length === 0 ? (
                  <p style={{ color: '#999' }}>Keine passenden Gremien in dieser Periode</p>
                ) : (
                  gefilterteAusschuesse.map((a) => (
                    <label key={a.id} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <input
                        type="checkbox"
                        checked={selectedAusschussIds.includes(a.id)}
                        onChange={() => toggleAusschuss(a.id)}
                      />
                      <span>{a.name}</span>
                    </label>
                  ))
                )}
              </div>
              <button
                type="button"
                onClick={() => setSelectedAusschussIds(gefilterteAusschuesse.map(a => a.id))}
                style={{ marginTop: '0.5rem', padding: '0.25rem 0.75rem', fontSize: '0.85rem' }}
                className="btn btn-sm btn-secondary"
              >
                Alle wählen
              </button>
              <button
                type="button"
                onClick={() => setSelectedAusschussIds([])}
                style={{ marginTop: '0.5rem', marginLeft: '0.5rem', padding: '0.25rem 0.75rem', fontSize: '0.85rem' }}
                className="btn btn-sm btn-secondary"
              >
                Keine wählen
              </button>
            </div>

            {/* Planungswochen */}
            <div style={{ marginBottom: '1.5rem' }}>
              <label style={{ fontWeight: '600', marginBottom: '0.5rem', display: 'block' }}>
                Planungswochen:
              </label>
              <input
                type="number"
                min="1"
                max="12"
                value={planungswochen}
                onChange={(e) => setPlanungswochen(parseInt(e.target.value))}
                style={{
                  padding: '0.5rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '4px',
                  fontSize: '0.95rem',
                  width: '100px',
                }}
              />
              <p style={{ fontSize: '0.85rem', color: '#666', marginTop: '0.25rem' }}>
                Anzahl der Wochen für die Terminplanung
              </p>
            </div>

            {/* Freitag-Modus */}
            <div style={{ marginBottom: '1.5rem' }}>
              <label style={{ fontWeight: '600', marginBottom: '0.5rem', display: 'block' }}>
                Freitag-Modus:
              </label>
              <select
                value={freitagModus}
                onChange={(e) => setFreitagModus(e.target.value)}
                style={{
                  padding: '0.5rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '4px',
                  fontSize: '0.95rem',
                }}
              >
                <option value="reserve">Reserve (nur wenn nötig)</option>
                <option value="normal">Normal (mit anderen Tagen)</option>
                <option value="nein">Keine Freitage</option>
              </select>
            </div>

            {/* Start-Datum */}
            <div style={{ marginBottom: '1.5rem' }}>
              <label style={{ fontWeight: '600', marginBottom: '0.5rem', display: 'block' }}>
                Start-Datum (Optional):
              </label>
              <input
                type="date"
                value={startDatum}
                onChange={(e) => setStartDatum(e.target.value)}
                style={{
                  padding: '0.5rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '4px',
                  fontSize: '0.95rem',
                  width: '100%',
                  maxWidth: '250px',
                }}
              />
              <p style={{ fontSize: '0.85rem', color: '#666', marginTop: '0.25rem' }}>
                Montag der ersten Planungswoche (mit Abwesenheits-Check)
              </p>
            </div>

            {/* Min. Verfügbarkeit */}
            <div style={{ marginBottom: '1.5rem' }}>
              <label style={{ fontWeight: '600', marginBottom: '0.5rem', display: 'block' }}>
                Min. Verfügbarkeit (%):
              </label>
              <input
                type="number"
                min="0"
                max="100"
                value={minVerfuegbarkeit}
                onChange={(e) => setMinVerfuegbarkeit(parseInt(e.target.value) || 0)}
                style={{
                  padding: '0.5rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '4px',
                  fontSize: '0.95rem',
                  width: '100px',
                }}
              />
              <p style={{ fontSize: '0.85rem', color: '#666', marginTop: '0.25rem' }}>
                Nur Termine mit mind. dieser Quote anzeigen (0 = alle, 100 = nur 100%)
              </p>
            </div>

            {/* Max. Anzahl Termine */}
            <div style={{ marginBottom: '1.5rem' }}>
              <label style={{ fontWeight: '600', marginBottom: '0.5rem', display: 'block' }}>
                Max. Anzahl Termine:
              </label>
              <input
                type="number"
                min="1"
                max="50"
                value={maxAnzahlTermine}
                onChange={(e) => setMaxAnzahlTermine(parseInt(e.target.value) || 5)}
                style={{
                  padding: '0.5rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '4px',
                  fontSize: '0.95rem',
                  width: '100px',
                }}
              />
              <p style={{ fontSize: '0.85rem', color: '#666', marginTop: '0.25rem' }}>
                Maximale Anzahl von Terminvorschlägen pro Ausschuss
              </p>
            </div>

            <div className="form-buttons">
              <button
                type="submit"
                className="btn btn-success"
                disabled={loading || selectedAusschussIds.length === 0}
              >
                {loading ? '⏳ Berechnung läuft...' : '🧮 Termine berechnen'}
              </button>
            </div>
          </form>
        </>
      ) : (
        <Kalendaransicht
          results={results}
          periode={selectedPeriode}
          onBack={() => setShowResults(false)}
          fixierteTermine={fixierteTermine}
          onTerminFixed={fetchFixierteTermine}
        />
      )}
    </>
  )
}

// ───────────────────────────────────────────
// Kalendaransicht
// ───────────────────────────────────────────
function Kalendaransicht({ results, periode, onBack, fixierteTermine, onTerminFixed }) {
  const [ausschuessMap, setAusschuessMap] = useState({})
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')

  useEffect(() => {
    // Lade Ausschuss-Details für alle Analysen
    const map = {}
    results.analysen.forEach(analyse => {
      map[analyse.ausschuss_id] = analyse.ausschuss_name
    })
    setAusschuessMap(map)
  }, [results])

  const istBereitsFixiert = (termin) => {
    return fixierteTermine.some(f =>
      f.ausschuss_id === termin.ausschuss_id &&
      f.woche === termin.woche &&
      f.wochentag === termin.wochentag &&
      f.start_minute === (parseInt(termin.start.split(':')[0]) * 60 + parseInt(termin.start.split(':')[1])) &&
      f.end_minute === (parseInt(termin.ende.split(':')[0]) * 60 + parseInt(termin.ende.split(':')[1]))
    )
  }

  const handleFixieren = async (termin) => {
    try {
      setLoading(true)
      // Speichere den Termin als Sitzungsvorschlag
      const startMin = parseInt(termin.start.split(':')[0]) * 60 + parseInt(termin.start.split(':')[1])
      const endMin = parseInt(termin.ende.split(':')[0]) * 60 + parseInt(termin.ende.split(':')[1])

      const payload = {
        ausschuss_id: termin.ausschuss_id,
        ausschuss_name: termin.ausschuss,
        woche: termin.woche,
        wochentag: termin.wochentag,
        start_minute: startMin,
        end_minute: endMin,
      }
      console.log('Fixieren Payload:', payload)

      await api.post('/calculate/results', payload)
      setMessage(`✅ ${termin.ausschuss} am ${termin.wochentag} ${termin.start}–${termin.ende} fixiert!`)
      // Aktualisiere fixierte Termine Liste
      if (onTerminFixed) {
        onTerminFixed()
      }
      setTimeout(() => setMessage(''), 3000)
    } catch (err) {
      setMessage(`❌ Fehler beim Fixieren: ${err.response?.data?.detail || err.message}`)
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  // Überprüfe ob Termin mit fixiertem Termin überlappt
  const hatUeberschneidung = (termin) => {
    return fixierteTermine.some(f => {
      // Vergleiche Wochentag (beide zu Großbuchstaben)
      const fWochentag = (f.wochentag.includes('.') ? f.wochentag.split('.')[1] : f.wochentag).toUpperCase()
      const tWochentag = termin.wochentag.toUpperCase()

      if (fWochentag !== tWochentag) {
        return false
      }
      if (f.woche !== termin.woche) {
        return false
      }

      // Überprüfe Zeit-Überschneidung
      const fStart = f.start_minute
      const fEnd = f.end_minute
      const tStart = parseInt(termin.start.split(':')[0]) * 60 + parseInt(termin.start.split(':')[1])
      const tEnd = parseInt(termin.ende.split(':')[0]) * 60 + parseInt(termin.ende.split(':')[1])

      // Überschneidung wenn: tStart < fEnd AND tEnd > fStart
      const overlap = tStart < fEnd && tEnd > fStart
      return overlap
    })
  }

  // Generiere 14-Tage-Kalender aus Ergebnissen
  const generierteKalendarwochen = () => {
    console.log('DEBUG: generierteKalendarwochen aufgerufen')
    console.log('DEBUG: results.analysen count:', results.analysen?.length)
    console.log('DEBUG: Fixierte Termine beim Kalender-Gen:', fixierteTermine)
    if (results.analysen && results.analysen[0]) {
      console.log('DEBUG: First analyse top_termine:', results.analysen[0].top_termine?.length)
    }

    const wochen = []
    const tage = ['Mo', 'Di', 'Mi', 'Do', 'Fr']
    const analysen = results.analysen || []

    for (let w = 1; w <= 2; w++) {
      const woche = {
        woche: w,
        tage: {}
      }
      for (const tag of tage) {
        woche.tage[tag] = []
      }

      for (const analyse of analysen) {
        // Nutze beste_je_tag (global assigned) - aber nur TOP-Termin (erste Option) pro Ausschuss
        const allTermine = analyse.beste_je_tag || []

        // NUR TOP-Termin (erstes Element) im Kalender anzeigen
        const topTermin = allTermine[0]
        if (!topTermin) continue

        console.log(`DEBUG KALENDER: ${analyse.ausschuss_name} - topTermin.woche=${topTermin.woche}, current w=${w}, all best_je_tag count=${allTermine.length}`)

        // Wichtig: Vergleiche Numbers, nicht Strings
        if (Number(topTermin.woche) !== w) continue

        const v = topTermin
        // Normalisiere wochentag: "Mo", "Di", "Mi", "Do", "Fr"
        let wochentag = v.wochentag || ''
        if (wochentag.includes('Mo')) wochentag = 'Mo'
        else if (wochentag.includes('Di')) wochentag = 'Di'
        else if (wochentag.includes('Mi')) wochentag = 'Mi'
        else if (wochentag.includes('Do')) wochentag = 'Do'
        else if (wochentag.includes('Fr')) wochentag = 'Fr'

        const termin = {
          ausschuss: analyse.ausschuss_name,
          ausschuss_id: analyse.ausschuss_id,
          zeit: `${v.start}–${v.ende}`,
          start: v.start,
          ende: v.ende,
          anwesend: v.anwesend,
          total: v.mitglieder,
          quote: v.quote,
          status: v.status,
          empfehlung: v.empfehlung,
          woche: w,
          wochentag: wochentag,
        }

        // Nur zeigen wenn KEINE Überschneidung mit fixiertem Termin
        if (!hatUeberschneidung(termin) && woche.tage[wochentag]) {
          woche.tage[wochentag].push(termin)
        }
      }
      wochen.push(woche)
    }

    console.log('DEBUG: wochen array count:', wochen.length)
    for (let i = 0; i < wochen.length; i++) {
      const w = wochen[i]
      const tageCount = Object.values(w.tage).reduce((sum, tage) => sum + tage.length, 0)
      console.log(`DEBUG: Woche ${w.woche}: ${tageCount} Termine`)
    }

    return wochen
  }

  const wochen = generierteKalendarwochen()

  return (
    <>
      <div className="section-header">
        <h2>📅 14-Tage Terminkalender</h2>
        <button className="btn btn-secondary" onClick={onBack}>
          ← Zurück
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

      <div style={{ marginBottom: '1.5rem' }}>
        <h3>{periode?.name} ({periode?.start_jahr}–{periode?.end_jahr})</h3>
        <p style={{ color: '#666', fontSize: '0.9rem' }}>
          {results.analysen?.length} Ausschüsse berechnet
        </p>
      </div>

      <div style={{ display: 'grid', gap: '2rem' }}>
        {wochen.map((woche) => (
          <div key={woche.woche} style={{
            border: '1px solid #e5e7eb',
            borderRadius: '8px',
            padding: '1.5rem',
            background: '#f9fafb',
          }}>
            <h4 style={{ marginBottom: '1rem' }}>Woche {woche.woche}</h4>
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(5, 1fr)',
              gap: '1rem',
            }}>
              {['Mo', 'Di', 'Mi', 'Do', 'Fr'].map((tag) => (
                <div key={tag} style={{
                  border: '1px solid #d1d5db',
                  borderRadius: '6px',
                  padding: '1rem',
                  background: 'white',
                  minHeight: '150px',
                }}>
                  <h5 style={{ marginBottom: '0.75rem', color: '#1e3a8a' }}>{tag}</h5>
                  {woche.tage[tag].length === 0 ? (
                    <p style={{ color: '#999', fontSize: '0.85rem' }}>Keine Termine</p>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                      {woche.tage[tag]
                        .sort((a, b) => {
                          // Sortiere nach Start-Zeit (z.B. "09:00" vs "14:00")
                          const timeA = a.start.split(':').map(Number)
                          const timeB = b.start.split(':').map(Number)
                          return (timeA[0] * 60 + timeA[1]) - (timeB[0] * 60 + timeB[1])
                        })
                        .map((termin, idx) => (
                        <div key={idx} style={{
                          padding: '0.75rem',
                          background: termin.status === 'top' ? '#f0f4ff' : '#fef3c7',
                          borderRadius: '4px',
                          fontSize: '0.85rem',
                          borderLeft: `3px solid ${termin.status === 'top' ? '#2563eb' : '#f59e0b'}`,
                        }}>
                          <div style={{ fontWeight: '600', marginBottom: '0.25rem' }}>
                            {termin.ausschuss}
                          </div>
                          <div style={{ color: '#666', fontSize: '0.8rem' }}>
                            {termin.zeit}
                          </div>
                          <div style={{ color: '#666', fontSize: '0.8rem', marginTop: '0.25rem' }}>
                            ✓ {termin.anwesend}/{termin.total} ({termin.quote}%)
                          </div>
                          {termin.empfehlung && (
                            <button
                              onClick={() => handleFixieren(termin)}
                              disabled={loading || istBereitsFixiert(termin) || hatUeberschneidung(termin)}
                              title={hatUeberschneidung(termin) ? 'Überschneidung mit fixiertem Termin' : ''}
                              style={{
                                marginTop: '0.5rem',
                                padding: '0.4rem 0.75rem',
                                fontSize: '0.75rem',
                                background: istBereitsFixiert(termin) ? '#9ca3af' : (hatUeberschneidung(termin) ? '#fca5a5' : '#059669'),
                                color: 'white',
                                border: 'none',
                                borderRadius: '3px',
                                cursor: (loading || istBereitsFixiert(termin) || hatUeberschneidung(termin)) ? 'not-allowed' : 'pointer',
                                opacity: (loading || istBereitsFixiert(termin) || hatUeberschneidung(termin)) ? 0.6 : 1,
                                width: '100%',
                                fontWeight: '500',
                              }}
                            >
                              {istBereitsFixiert(termin) ? '✓ Fixiert' : (hatUeberschneidung(termin) ? '⚠️ Besetzt' : (loading ? '⏳...' : '📌 ' + termin.empfehlung))}
                            </button>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Terminvorschläge je Ausschuss */}
      <div style={{ marginTop: '2rem', padding: '1.5rem', background: '#fff7ed', borderRadius: '8px', border: '1px solid #fed7aa' }}>
        <h3 style={{ marginTop: 0, marginBottom: '1.5rem' }}>📋 Alle Terminvorschläge je Ausschuss</h3>
        <div style={{ display: 'grid', gap: '1.5rem' }}>
          {results.analysen?.map(analyse => {
            const allTermine = analyse.beste_je_tag || []
            return (
              <div key={analyse.ausschuss_id} style={{
                border: '1px solid #fbcfe8',
                borderRadius: '6px',
                padding: '1rem',
                background: 'white',
              }}>
                <div style={{ fontWeight: '700', marginBottom: '1rem', color: '#1e3a8a', fontSize: '1.1rem' }}>
                  {analyse.ausschuss_name}
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  {allTermine.length === 0 ? (
                    <p style={{ color: '#999', fontSize: '0.9rem' }}>Keine Terminvorschläge verfügbar</p>
                  ) : (
                    allTermine.map((termin, idx) => (
                      <div key={idx} style={{
                        padding: '0.75rem 1rem',
                        background: idx === 0 ? '#dbeafe' : '#f3f4f6',
                        borderRadius: '4px',
                        borderLeft: `4px solid ${idx === 0 ? '#2563eb' : '#9ca3af'}`,
                        fontSize: '0.9rem',
                      }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.25rem' }}>
                          <span style={{ fontWeight: idx === 0 ? '700' : '600' }}>
                            {idx === 0 ? '⭐ TOP: ' : ''}W{termin.woche} · {termin.wochentag} · {termin.start}–{termin.ende}
                          </span>
                          <span style={{ fontSize: '0.8rem', color: '#666' }}>
                            {termin.anwesend}/{termin.mitglieder} ({termin.quote}%)
                          </span>
                        </div>
                        <div style={{ fontSize: '0.8rem', color: '#666', marginBottom: '0.5rem' }}>
                          Status: <strong>{termin.status}</strong> | {termin.empfehlung || 'Keine'}
                        </div>

                        {/* Validierungsdaten */}
                        {termin.required_availability_hours && termin.required_availability_hours.length > 0 && (
                          <div style={{ fontSize: '0.75rem', color: '#1e40af', marginBottom: '0.5rem' }}>
                            ✓ Erforderliche Stunden: <strong>{termin.required_availability_hours.join(', ')}</strong>
                          </div>
                        )}

                        {termin.anwesende_mitglieder && termin.anwesende_mitglieder.length > 0 && (
                          <div style={{ fontSize: '0.75rem', color: '#059669', marginBottom: '0.5rem' }}>
                            ✓ Anwesend: {termin.anwesende_mitglieder.map(m => `${m.name} (${m.rolle})`).join(', ')}
                          </div>
                        )}

                        {termin.fehlende_mitglieder && termin.fehlende_mitglieder.length > 0 && (
                          <div style={{ fontSize: '0.75rem', color: '#dc2626' }}>
                            ✗ Fehlend: {termin.fehlende_mitglieder.map(m => `${m.name} (${m.rolle})`).join(', ')}
                          </div>
                        )}
                      </div>
                    ))
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>

      <div style={{ marginTop: '2rem', padding: '1rem', background: '#f0f9ff', borderRadius: '6px' }}>
        <h4>Zusammenfassung der Berechnung</h4>

        <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
          <div style={{ flex: 1, minWidth: '120px', padding: '1rem', background: 'white', borderRadius: '6px', textAlign: 'center', border: '1px solid #e5e7eb' }}>
            <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#1e40af' }}>{results.analysen?.length || 0}</div>
            <div style={{ fontSize: '0.85rem', color: '#666', marginTop: '0.5rem' }}>Ausschüsse</div>
          </div>
          <div style={{ flex: 1, minWidth: '120px', padding: '1rem', background: 'white', borderRadius: '6px', textAlign: 'center', border: '1px solid #e5e7eb' }}>
            <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#15803d' }}>
              {results.analysen?.reduce((sum, a) => sum + (a.top_termine?.length || 0), 0)}
            </div>
            <div style={{ fontSize: '0.85rem', color: '#666', marginTop: '0.5rem' }}>Top-Termine</div>
          </div>
          <div style={{ flex: 1, minWidth: '120px', padding: '1rem', background: 'white', borderRadius: '6px', textAlign: 'center', border: '1px solid #e5e7eb' }}>
            <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#b45309' }}>
              {results.analysen?.reduce((sum, a) => sum + (a.alternativen?.length || 0), 0)}
            </div>
            <div style={{ fontSize: '0.85rem', color: '#666', marginTop: '0.5rem' }}>Alternativen</div>
          </div>
          <div style={{ flex: 1, minWidth: '120px', padding: '1rem', background: 'white', borderRadius: '6px', textAlign: 'center', border: '1px solid #e5e7eb' }}>
            <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#7c3aed' }}>{fixierteTermine?.length || 0}</div>
            <div style={{ fontSize: '0.85rem', color: '#666', marginTop: '0.5rem' }}>Fixiert</div>
          </div>
        </div>

        <div style={{ marginTop: '1rem', padding: '0.75rem', background: 'white', borderRadius: '4px', border: '1px solid #bfdbfe' }}>
          <h5 style={{ marginTop: 0 }}>Ausschuss-Details</h5>
          {results.analysen?.map(analyse => (
            <div key={analyse.ausschuss_id} style={{ marginBottom: '0.5rem', paddingBottom: '0.5rem', borderBottom: '1px solid #e5e7eb' }}>
              <div style={{ fontWeight: '600' }}>{analyse.ausschuss_name}</div>
              <div style={{ fontSize: '0.85rem', color: '#666' }}>
                {analyse.top_termine?.length || 0} Top-Termine
                {analyse.alternativen?.length > 0 && ` + ${analyse.alternativen.length} Alternativen`}
                {' '}| {analyse.mitglieder?.length || 0} Mitglieder
                {analyse.beschlussfaehig?.length > 0 && ` | ${analyse.beschlussfaehig.length} beschlussfähige Termine`}
              </div>
              {analyse.empfehlung_text && (
                <div style={{ fontSize: '0.8rem', color: '#059669', marginTop: '0.25rem' }}>
                  💡 {analyse.empfehlung_text}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </>
  )
}
