import { useEffect, useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import api from '../api/client'

export default function PersonProfile() {
  const [profile, setProfile] = useState(null)
  const [form, setForm] = useState({})
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    const token = localStorage.getItem('personToken')
    if (!token) {
      navigate('/person/login')
      return
    }

    const fetchProfile = async () => {
      try {
        const res = await api.get('/person/me', {
          headers: { Authorization: `Bearer ${token}` }
        })
        setProfile(res.data)
        setForm(res.data)
      } catch (err) {
        if (err.response?.status === 401) {
          navigate('/person/login')
        }
      }
    }
    fetchProfile()
  }, [navigate])

  const handleSave = async (e) => {
    e.preventDefault()
    setSaving(true)
    const token = localStorage.getItem('personToken')

    try {
      await api.put('/person/me', form, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setMessage('Profil aktualisiert!')
      setTimeout(() => setMessage(''), 3000)
    } catch (err) {
      setMessage('Fehler beim Speichern')
    } finally {
      setSaving(false)
    }
  }

  if (!profile) return <div className="alert alert-info">Lädt...</div>

  return (
    <div className="container mt-5">
      <Link to="/person/dashboard" className="btn btn-secondary mb-3">
        ← Zurück zum Dashboard
      </Link>
      <div className="row">
        <div className="col-md-6">
          <h1>Mein Profil</h1>

          {message && <div className="alert alert-info">{message}</div>}

          <form onSubmit={handleSave} className="card p-4">
            <div className="mb-3">
              <label className="form-label">Vorname</label>
              <input
                type="text"
                className="form-control"
                value={form.vorname || ''}
                onChange={(e) => setForm({ ...form, vorname: e.target.value })}
              />
            </div>

            <div className="mb-3">
              <label className="form-label">Nachname</label>
              <input
                type="text"
                className="form-control"
                value={form.nachname || ''}
                onChange={(e) => setForm({ ...form, nachname: e.target.value })}
              />
            </div>

            <div className="mb-3">
              <label className="form-label">Email (nicht änderbar)</label>
              <input
                type="email"
                className="form-control"
                value={form.email || ''}
                disabled
              />
            </div>

            <div className="mb-3">
              <label className="form-label">Partei</label>
              <select
                className="form-control"
                value={form.partei || ''}
                onChange={(e) => setForm({ ...form, partei: e.target.value || null })}
              >
                <option value="">-- Keine Angabe --</option>
                <option value="SPÖ">SPÖ</option>
                <option value="ÖVP">ÖVP</option>
                <option value="Die Grünen">Die Grünen</option>
                <option value="FPÖ">FPÖ</option>
                <option value="NEOS">NEOS</option>
                <option value="KPÖ">KPÖ</option>
              </select>
            </div>

            <button
              type="submit"
              className="btn btn-primary w-100"
              disabled={saving}
            >
              {saving ? 'Speichert...' : 'Speichern'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
