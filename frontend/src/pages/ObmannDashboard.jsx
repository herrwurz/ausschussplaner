import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api/client'
import '../styles/ObmannDashboard.css'

export default function ObmannDashboard() {
  const navigate = useNavigate()
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

  const user = JSON.parse(localStorage.getItem('user') || '{}')
  const token = localStorage.getItem('token')

  useEffect(() => {
    const checkAuth = () => {
      if (!token || !user.id) {
        navigate('/admin/login')
        return
      }
      if (user.rolle !== 'obmann') {
        navigate('/admin')
        return
      }
      fetchAusschuesse()
      fetchPersonen()
    }
    checkAuth()
  }, [token, user, navigate])

  const fetchAusschuesse = async () => {
    try {
      console.log('🔍 Fetching Obmann Ausschüsse...')
      console.log('Token:', token?.substring(0, 20) + '...')
      const res = await api.get('/obmann/ausschuesse')
      console.log('✅ Ausschüsse loaded:', res.data.length)
      setAusschuesse(res.data)
    } catch (err) {
      console.error('❌ Error:', err)
      console.error('Status:', err.response?.status)
      console.error('Data:', err.response?.data)
      setError(`Ausschüsse laden fehlgeschlagen: ${err.response?.status || err.message}`)
    }
  }

  const fetchPersonen = async () => {
    try {
      setLoading(true)
      console.log('🔍 Fetching Obmann Personen...')
      const res = await api.get('/obmann/personen')
      console.log('✅ Personen loaded:', res.data.length)
      setPersonen(res.data)
    } catch (err) {
      console.error('❌ Error:', err)
      console.error('Status:', err.response?.status)
      console.error('Data:', err.response?.data)
      setError(`Personen laden fehlgeschlagen: ${err.response?.status || err.message}`)
    } finally {
      setLoading(false)
    }
  }

  const fetchPersonVerfuegbarkeit = async (personId) => {
    try {
      console.log(`🔍 Fetching Verfügbarkeit für Person ${personId}...`)
      const res = await api.get(`/obmann/personen/${personId}/verfuegbarkeit`)
      console.log('✅ Verfügbarkeit loaded')
      setPersonVerfuegbarkeit(res.data)
    } catch (err) {
      console.error('❌ Error:', err)
      console.error('Status:', err.response?.status)
      console.error('Data:', err.response?.data)
      setError(`Verfügbarkeit laden fehlgeschlagen: ${err.response?.status || err.message}`)
    }
  }

  const handleCalculate = async (ausschussId, ausschussName) => {
    try {
      setCalculating(ausschussId)
      setError('')
      console.log(`🔍 Berechne Termine für ${ausschussName}...`)

      const res = await api.post(`/obmann/calculate/${ausschussId}`, {}, {
        headers: { Authorization: `Bearer ${token}` },
      })

      console.log('✅ Berechnung erfolgreich')
      setResults(prev => ({
        ...prev,
        [ausschussId]: res.data.results
      }))
      setSuccess(`✅ Termine für "${ausschussName}" berechnet!`)
      setTimeout(() => setSuccess(''), 5000)
    } catch (err) {
      console.error('❌ Error:', err)
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

  if (loading) return (
    <div className="obmann-loading">
      <h2>⏳ Wird geladen...</h2>
    </div>
  )

  return (
    <div className="obmann-container">
      {/* Header */}
      <header className="obmann-header">
        <div>
          <h1>Obmann-Dashboard</h1>
          <p className="obmann-header-subtitle">👤 {user.vorname} {user.nachname}</p>
        </div>
        <button onClick={handleLogout} className="obmann-logout-btn">
          🚪 Logout
        </button>
      </header>

      <div className="obmann-content">
        {error && (
          <div className="obmann-alert obmann-alert-error">
            <span>{error}</span>
            <button onClick={() => setError('')} className="obmann-alert-close">✕</button>
          </div>
        )}

        {success && (
          <div className="obmann-alert obmann-alert-success">
            <span>{success}</span>
            <button onClick={() => setSuccess('')} className="obmann-alert-close">✕</button>
          </div>
        )}

        {/* Tabs */}
        <div className="obmann-tabs">
          <button
            onClick={() => setActiveTab('ausschuesse')}
            className={`obmann-tab-btn ${activeTab === 'ausschuesse' ? 'active' : ''}`}
          >
            📋 Meine Ausschüsse ({ausschuesse.length})
          </button>
          <button
            onClick={() => setActiveTab('personen')}
            className={`obmann-tab-btn ${activeTab === 'personen' ? 'active' : ''}`}
          >
            👥 Meine Personen ({personen.length})
          </button>
        </div>

        {/* Ausschüsse Tab */}
        {activeTab === 'ausschuesse' && (
          <>
            <div className="obmann-section-header">
              <h2>Meine Ausschüsse</h2>
            </div>

            {ausschuesse.length === 0 ? (
              <p className="obmann-empty-state">Sie sind Obmann in keinem Ausschuss.</p>
            ) : (
              <div className="obmann-card-grid">
                {ausschuesse.map((ausschuss) => (
                  <div key={ausschuss.id} className="obmann-card">
                    <h3 className="obmann-card-title">{ausschuss.name}</h3>
                    <p className="obmann-card-meta">
                      Typ: {ausschuss.typ === 'standard' ? '📋 Standard' : ausschuss.typ}
                    </p>
                    <p className="obmann-card-meta">
                      Status: {ausschuss.aktiv ? '✅ Aktiv' : '⚠️ Inaktiv'}
                    </p>

                    <button
                      onClick={() => handleCalculate(ausschuss.id, ausschuss.name)}
                      disabled={calculating === ausschuss.id}
                      className="obmann-card-button"
                    >
                      {calculating === ausschuss.id ? '⏳ Berechnet...' : '📊 Termine berechnen'}
                    </button>

                    {results[ausschuss.id] && (
                      <div className="obmann-results">
                        <p className="obmann-results-title">✅ Berechnung abgeschlossen</p>
                        <pre className="obmann-results-content">
                          {JSON.stringify(results[ausschuss.id], null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </>
        )}

        {/* Personen Tab */}
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
                    <p className="obmann-card-meta">📧 {person.email}</p>
                    <p className="obmann-card-meta">🏛️ {person.gremium}</p>
                    <p className="obmann-card-meta">
                      Status: {person.aktiv ? '✅ Aktiv' : '⚠️ Inaktiv'}
                    </p>

                    <button
                      onClick={() => {
                        setSelectedPerson(person)
                        fetchPersonVerfuegbarkeit(person.id)
                      }}
                      className={`obmann-card-button ${
                        selectedPerson?.id === person.id ? 'active' : 'secondary'
                      }`}
                    >
                      {selectedPerson?.id === person.id ? '✅ Verfügbarkeit zeigen' : '📅 Verfügbarkeit anzeigen'}
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* Verfügbarkeit Details */}
            {personVerfuegbarkeit && (
              <div className="obmann-verfuegbarkeit-section">
                <h3 className="obmann-verfuegbarkeit-title">
                  📅 Verfügbarkeit: {personVerfuegbarkeit.name}
                </h3>
                <div className="obmann-verfuegbarkeit-grid">
                  {Object.entries(personVerfuegbarkeit.verfuegbarkeiten).map(([day, slots]) => (
                    <div key={day} className="obmann-verfuegbarkeit-day">
                      <h4 className="obmann-verfuegbarkeit-day-title">
                        {day === 'monday' ? 'Montag' :
                         day === 'tuesday' ? 'Dienstag' :
                         day === 'wednesday' ? 'Mittwoch' :
                         day === 'thursday' ? 'Donnerstag' :
                         day === 'friday' ? 'Freitag' : day}
                      </h4>
                      <div>
                        {slots.map((slot, idx) => (
                          <div
                            key={idx}
                            className={`obmann-verfuegbarkeit-slot ${
                              slot.verfuegbar ? 'available' : 'unavailable'
                            }`}
                          >
                            {slot.stunde}:00 - {slot.verfuegbar ? '✅ Verfügbar' : '❌ Nicht verfügbar'}
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
