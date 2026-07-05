import { useEffect, useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import api from '../api/client'

const HOURS = Array.from({ length: 13 }, (_, i) => 7 + i)
const DAYS = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']

export default function PersonVerfuegbarkeiten() {
  const [availability, setAvailability] = useState({})
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
        const res = await api.get('/person/me/verfuegbarkeiten', {
          headers: { Authorization: `Bearer ${token}` }
        })
        const items = {}
        res.data.forEach((v) => {
          items[`${v.wochentag}-${v.stunde}`] = v.verfuegbar
        })
        setAvailability(items)
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
    const token = localStorage.getItem('personToken')

    const items = []
    DAYS.forEach((day) => {
      HOURS.forEach((hour) => {
        const key = `${day}-${hour}`
        items.push({
          wochentag: day,
          stunde: hour,
          verfuegbar: availability[key] || false,
        })
      })
    })

    try {
      await api.put('/person/me/verfuegbarkeiten', { items }, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setMessage('Verfügbarkeiten gespeichert!')
      setTimeout(() => setMessage(''), 3000)
    } catch (err) {
      setMessage('Fehler beim Speichern')
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <div className="alert alert-info">Lädt...</div>

  return (
    <div className="container mt-5">
      <Link to="/person/dashboard" className="btn btn-secondary mb-3">
        ← Zurück zum Dashboard
      </Link>
      <h1>Meine Verfügbarkeiten</h1>

      {message && <div className="alert alert-info">{message}</div>}

      <div className="card p-3 mb-4">
        <div className="table-responsive">
          <table className="table table-sm table-bordered">
            <thead>
              <tr>
                <th>Stunde</th>
                {DAYS.map((day) => (
                  <th key={day} className="text-center">{day}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {HOURS.map((hour) => (
                <tr key={hour}>
                  <td><strong>{hour}:00</strong></td>
                  {DAYS.map((day) => (
                    <td
                      key={`${day}-${hour}`}
                      className="text-center p-2"
                      style={{
                        cursor: 'pointer',
                        backgroundColor: availability[`${day}-${hour}`] ? '#d4edda' : '#f8f9fa',
                      }}
                      onClick={() => toggleAvailability(day, hour)}
                    >
                      <input
                        type="checkbox"
                        checked={availability[`${day}-${hour}`] || false}
                        readOnly
                      />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <button
          className="btn btn-primary"
          onClick={handleSave}
          disabled={saving}
        >
          {saving ? 'Speichert...' : 'Speichern'}
        </button>
      </div>
    </div>
  )
}
