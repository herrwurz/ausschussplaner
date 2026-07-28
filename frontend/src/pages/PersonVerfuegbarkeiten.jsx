import { useEffect, useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import api from '../api/client'

// Gleiches Raster wie Admin / Engine (Mo–Fr, relevante volle Stunden)
const HOURS = [7, 16, 17, 18, 19]
const DAYS = ['Mo', 'Di', 'Mi', 'Do', 'Fr']
const hourLabel = (h) => `${String(h).padStart(2, '0')}:00`

const emptyMatrix = () => {
  const m = {}
  DAYS.forEach((day) => HOURS.forEach((hour) => { m[`${day}-${hour}`] = false }))
  return m
}

export default function PersonVerfuegbarkeiten() {
  const [availability, setAvailability] = useState(emptyMatrix())
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    const token = localStorage.getItem('personToken')
    if (!token) {
      navigate('/person/login')
      return
    }

    const fetchAvailability = async () => {
      try {
        const res = await api.get('/person/me/verfuegbarkeiten')
        const matrix = emptyMatrix()
        ;(res.data || []).forEach((v) => {
          const key = `${v.wochentag}-${v.stunde}`
          if (key in matrix && v.verfuegbar) matrix[key] = true
        })
        setAvailability(matrix)
      } catch (err) {
        if (err.response?.status === 401) {
          navigate('/person/login')
        }
      } finally {
        setLoading(false)
      }
    }
    fetchAvailability()
  }, [navigate])

  const toggleAvailability = (day, hour) => {
    const key = `${day}-${hour}`
    setAvailability((prev) => ({
      ...prev,
      [key]: !prev[key],
    }))
  }

  const handleSave = async () => {
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

    try {
      await api.put('/person/me/verfuegbarkeiten', { items })
      setMessage('Verfügbarkeiten gespeichert!')
      setTimeout(() => setMessage(''), 3000)
    } catch (err) {
      setMessage(err.response?.data?.detail || 'Fehler beim Speichern')
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <div className="alert alert-info">Lädt...</div>

  return (
    <div className="container mt-4">
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h2>Meine Verfügbarkeiten</h2>
        <Link to="/person/dashboard" className="btn btn-secondary">Zurück</Link>
      </div>

      <p className="text-muted" style={{ fontSize: '0.9rem' }}>
        Standardverfügbarkeit Mo–Fr für die Sitzungszeiten (07:00 sowie 16:00–19:00).
        Perioden-spezifische Overrides setzt der Admin.
      </p>

      {message && (
        <div className={`alert ${message.includes('Fehler') ? 'alert-danger' : 'alert-success'}`}>
          {message}
        </div>
      )}

      <div className="table-responsive">
        <table className="table table-bordered text-center">
          <thead>
            <tr>
              <th></th>
              {HOURS.map((h) => (
                <th key={h}>{hourLabel(h)}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {DAYS.map((day) => (
              <tr key={day}>
                <th>{day}</th>
                {HOURS.map((hour) => {
                  const key = `${day}-${hour}`
                  const on = !!availability[key]
                  return (
                    <td key={key}>
                      <button
                        type="button"
                        className={`btn btn-sm ${on ? 'btn-success' : 'btn-outline-secondary'}`}
                        onClick={() => toggleAvailability(day, hour)}
                        aria-pressed={on}
                      >
                        {on ? '✓' : '–'}
                      </button>
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
        {saving ? 'Speichert…' : 'Speichern'}
      </button>
    </div>
  )
}
