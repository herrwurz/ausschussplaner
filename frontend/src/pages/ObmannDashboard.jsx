import { useState, useEffect, useRef } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api from '../api/client'
import ObmannLayout from '../components/ObmannLayout'
import '../styles/ObmannDashboard.css'

function readUser() {
  try {
    return JSON.parse(localStorage.getItem('user') || '{}')
  } catch {
    return {}
  }
}

function hourLabel(h) {
  const hour = Number(h)
  const hh = String(Math.floor(hour)).padStart(2, '0')
  const mm = hour % 1 ? '30' : '00'
  return `${hh}:${mm}`
}

const DAY_FULL = { Mo: 'Montag', Di: 'Dienstag', Mi: 'Mittwoch', Do: 'Donnerstag', Fr: 'Freitag' }
const DAY_ORDER = ['Mo', 'Di', 'Mi', 'Do', 'Fr']
const HOURS = [7, 16, 17, 18, 19]

function statusLabel(status) {
  const map = {
    top: '100 %',
    beschlussfähig: 'Beschlussfähig',
    alternativ: 'Alternativ',
    obmann_da: 'Nur Obmann',
    nicht_beschlussfähig: 'Nicht beschlussfähig',
  }
  return map[status] || status
}

function BerechnungErgebnis({ result }) {
  const vorschlaege = result?.vorschlaege || []
  if (!vorschlaege.length) {
    return (
      <div className="obmann-results">
        <p className="obmann-results-title">Keine Terminvorschläge gefunden</p>
        {result?.empfehlung_text && (
          <p className="obmann-card-meta">{result.empfehlung_text}</p>
        )}
      </div>
    )
  }

  return (
    <div className="obmann-results">
      <p className="obmann-results-title">
        {vorschlaege.length} Terminvorschlag{vorschlaege.length === 1 ? '' : 'e'}
      </p>
      {result?.empfehlung_text && (
        <p className="obmann-card-meta" style={{ marginBottom: '0.75rem' }}>
          {result.empfehlung_text}
        </p>
      )}
      <div className="table-responsive">
        <table className="admin-table" style={{ fontSize: '0.85rem' }}>
          <thead>
            <tr>
              <th>Woche</th>
              <th>Tag</th>
              <th>Zeit</th>
              <th>Quote</th>
              <th>Status</th>
              <th>Anwesend</th>
            </tr>
          </thead>
          <tbody>
            {vorschlaege.map((v, idx) => (
              <tr key={`${v.woche}-${v.wochentag}-${v.start}-${idx}`}>
                <td>{v.woche}</td>
                <td>{DAY_FULL[v.wochentag] || v.wochentag}</td>
                <td>{v.start}–{v.ende}</td>
                <td>{v.quote} %</td>
                <td>{statusLabel(v.status)}</td>
                <td>{v.anwesend}/{v.mitglieder}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function VerfuegbarkeitMatrix({ data }) {
  const byDay = data?.verfuegbarkeiten || {}
  const available = new Set()
  DAY_ORDER.forEach((day) => {
    ;(byDay[day] || []).forEach((s) => {
      if (s.verfuegbar) available.add(`${day}-${Number(s.stunde)}`)
    })
  })
  const hasAny = available.size > 0

  if (!hasAny) {
    return (
      <p className="obmann-empty-state">
        Für {data?.name || 'diese Person'} sind keine Standard-Verfügbarkeiten hinterlegt.
      </p>
    )
  }

  return (
    <div className="table-responsive">
      <table className="admin-table" style={{ maxWidth: 520, textAlign: 'center' }}>
        <thead>
          <tr>
            <th>Tag</th>
            {HOURS.map((h) => (
              <th key={h}>{hourLabel(h)}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {DAY_ORDER.map((day) => (
            <tr key={day}>
              <td style={{ textAlign: 'left', fontWeight: 600 }}>{DAY_FULL[day]}</td>
              {HOURS.map((h) => {
                const on = available.has(`${day}-${h}`)
                return (
                  <td key={h}>
                    <span className={`obmann-verfuegbarkeit-slot ${on ? 'available' : 'unavailable'}`}>
                      {on ? '✓' : '–'}
                    </span>
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function ObmannDashboard() {
  const navigate = useNavigate()
  const userRef = useRef(readUser())
  const user = userRef.current

  const [ausschuesse, setAusschuesse] = useState([])
  const [personen, setPersonen] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [calculating, setCalculating] = useState(null)
  const [results, setResults] = useState({})
  const [activeTab, setActiveTab] = useState('ausschuesse')
  const [selectedPerson, setSelectedPerson] = useState(null)
  const [personVerfuegbarkeit, setPersonVerfuegbarkeit] = useState(null)
  const [verfuegbarkeitLoading, setVerfuegbarkeitLoading] = useState(false)

  useEffect(() => {
    const token = localStorage.getItem('token')
    const current = userRef.current

    if (!token || !current.id) {
      navigate('/admin/login', { replace: true })
      return undefined
    }
    if (current.rolle !== 'obmann' && current.rolle !== 'super_admin') {
      navigate('/admin/panel', { replace: true })
      return undefined
    }

    const controller = new AbortController()

    const load = async () => {
      try {
        const [ausRes, perRes] = await Promise.all([
          api.get('/obmann/ausschuesse', { signal: controller.signal }),
          api.get('/obmann/personen', { signal: controller.signal }),
        ])
        setAusschuesse(ausRes.data || [])
        setPersonen(perRes.data || [])
        setError('')
      } catch (err) {
        if (controller.signal.aborted || err.name === 'CanceledError' || err.code === 'ERR_CANCELED') {
          return
        }
        setError(`Laden fehlgeschlagen: ${err.response?.status || err.message}`)
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false)
        }
      }
    }

    load()
    return () => controller.abort()
    // Nur einmal beim Mount laden — keine deps, die Re-Fetches auslösen
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const fetchPersonVerfuegbarkeit = async (personId) => {
    setVerfuegbarkeitLoading(true)
    setPersonVerfuegbarkeit(null)
    setError('')
    try {
      const res = await api.get(`/obmann/personen/${personId}/verfuegbarkeit`)
      setPersonVerfuegbarkeit(res.data)
    } catch (err) {
      setError(
        `Verfügbarkeit laden fehlgeschlagen: ${err.response?.data?.detail || err.response?.status || err.message}`,
      )
    } finally {
      setVerfuegbarkeitLoading(false)
    }
  }

  const handleCalculate = async (ausschussId, ausschussName) => {
    try {
      setCalculating(ausschussId)
      setError('')
      const res = await api.post(`/obmann/calculate/${ausschussId}`)
      setResults((prev) => ({ ...prev, [ausschussId]: res.data }))
      setSuccess(`Termine für "${ausschussName}" berechnet`)
      setTimeout(() => setSuccess(''), 5000)
    } catch (err) {
      setError(`Berechnung fehlgeschlagen: ${err.response?.data?.detail || err.message}`)
    } finally {
      setCalculating(null)
    }
  }

  const handleLogout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    navigate('/admin/login')
  }

  const isSuperAdmin = user.rolle === 'super_admin'

  return (
    <ObmannLayout user={user} onLogout={handleLogout} showAdminLink={isSuperAdmin}>
      {isSuperAdmin && (
        <div style={{ marginBottom: '1rem' }}>
          <Link to="/admin/panel" className="btn btn-secondary">
            ← Zurück zum Admin-Panel
          </Link>
        </div>
      )}

      {loading && (
        <div className="obmann-loading">
          <h2>Wird geladen...</h2>
        </div>
      )}

      {!loading && error && (
        <div className="obmann-alert obmann-alert-error">
          <span>{error}</span>
          <button type="button" onClick={() => setError('')} className="obmann-alert-close">✕</button>
        </div>
      )}

      {!loading && success && (
        <div className="obmann-alert obmann-alert-success">
          <span>{success}</span>
          <button type="button" onClick={() => setSuccess('')} className="obmann-alert-close">✕</button>
        </div>
      )}

      {!loading && (
        <>
          <div className="obmann-tabs">
            <button
              type="button"
              onClick={() => setActiveTab('ausschuesse')}
              className={`obmann-tab-btn ${activeTab === 'ausschuesse' ? 'active' : ''}`}
            >
              Meine Ausschüsse ({ausschuesse.length})
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('personen')}
              className={`obmann-tab-btn ${activeTab === 'personen' ? 'active' : ''}`}
            >
              Meine Personen ({personen.length})
            </button>
          </div>

          {activeTab === 'ausschuesse' && (
            <>
              <div className="obmann-section-header">
                <h2>Meine Ausschüsse</h2>
              </div>

              {ausschuesse.length === 0 ? (
                <p className="obmann-empty-state">
                  Keine Ausschüsse zugewiesen. Voraussetzung: Benutzer-E-Mail entspricht einer Person,
                  die in Mitgliedschaften als Obmann / Obmann-Stv. eingetragen ist.
                </p>
              ) : (
                <div className="obmann-card-grid">
                  {ausschuesse.map((ausschuss) => (
                    <div key={ausschuss.id} className="obmann-card">
                      <h3 className="obmann-card-title">{ausschuss.name}</h3>
                      <p className="obmann-card-meta">
                        Typ: {ausschuss.typ === 'standard' ? 'Standard' : ausschuss.typ}
                      </p>
                      <p className="obmann-card-meta">
                        Status: {ausschuss.aktiv ? 'Aktiv' : 'Inaktiv'}
                      </p>

                      <button
                        type="button"
                        onClick={() => handleCalculate(ausschuss.id, ausschuss.name)}
                        disabled={calculating === ausschuss.id}
                        className="obmann-card-button"
                      >
                        {calculating === ausschuss.id ? 'Berechnet...' : 'Termine berechnen'}
                      </button>

                      {results[ausschuss.id] && (
                        <BerechnungErgebnis result={results[ausschuss.id]} />
                      )}
                    </div>
                  ))}
                </div>
              )}
            </>
          )}

          {activeTab === 'personen' && (
            <>
              <div className="obmann-section-header">
                <h2>Meine Ausschussmitglieder</h2>
              </div>
              {personen.length === 0 ? (
                <p className="obmann-empty-state">Sie haben keine Ausschussmitglieder.</p>
              ) : (
                <div className="obmann-card-grid">
                  {personen.map((person) => (
                    <div
                      key={person.id}
                      className={`obmann-card ${selectedPerson?.id === person.id ? 'selected' : ''}`}
                    >
                      <h3 className="obmann-card-title">
                        {person.vorname} {person.nachname}
                      </h3>
                      <p className="obmann-card-meta">{person.email}</p>
                      <p className="obmann-card-meta">{person.gremium}</p>
                      <p className="obmann-card-meta">
                        Status: {person.aktiv ? 'Aktiv' : 'Inaktiv'}
                      </p>

                      <button
                        type="button"
                        onClick={() => {
                          setSelectedPerson(person)
                          fetchPersonVerfuegbarkeit(person.id)
                        }}
                        className={`obmann-card-button ${
                          selectedPerson?.id === person.id ? 'active' : 'secondary'
                        }`}
                      >
                        {selectedPerson?.id === person.id ? 'Verfügbarkeit zeigen' : 'Verfügbarkeit anzeigen'}
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {verfuegbarkeitLoading && (
                <p className="obmann-empty-state">Verfügbarkeit wird geladen…</p>
              )}

              {!verfuegbarkeitLoading && personVerfuegbarkeit && (
                <div className="obmann-verfuegbarkeit-section">
                  <h3 className="obmann-verfuegbarkeit-title">
                    Verfügbarkeit: {personVerfuegbarkeit.name}
                  </h3>
                  <VerfuegbarkeitMatrix data={personVerfuegbarkeit} />
                </div>
              )}
            </>
          )}
        </>
      )}
    </ObmannLayout>
  )
}
