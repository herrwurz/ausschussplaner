import { useEffect, useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import api from '../api/client'

export default function PersonPassword() {
  const [form, setForm] = useState({ old_password: '', new_password: '', confirm_password: '' })
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    const token = localStorage.getItem('personToken')
    if (!token) {
      navigate('/person/login')
    }
  }, [navigate])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setMessage('')

    if (form.new_password !== form.confirm_password) {
      setError('Passwörter stimmen nicht überein!')
      return
    }

    if (form.new_password.length < 8) {
      setError('Passwort muss mindestens 8 Zeichen lang sein!')
      return
    }

    setSaving(true)
    const token = localStorage.getItem('personToken')

    try {
      await api.put(
        '/person/me/password',
        {
          old_password: form.old_password,
          new_password: form.new_password,
        },
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      )
      setMessage('Passwort erfolgreich geändert!')
      setForm({ old_password: '', new_password: '', confirm_password: '' })
      setTimeout(() => navigate('/person/dashboard'), 2000)
    } catch (err) {
      if (err.response?.status === 401) {
        setError('Aktuelles Passwort ist falsch!')
      } else {
        setError('Fehler beim Ändern des Passworts')
      }
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="container mt-5">
      <Link to="/person/dashboard" className="btn btn-secondary mb-3">
        ← Zurück zum Dashboard
      </Link>
      <div className="row">
        <div className="col-md-6">
          <h1>Passwort ändern</h1>

          {error && <div className="alert alert-danger">{error}</div>}
          {message && <div className="alert alert-success">{message}</div>}

          <form onSubmit={handleSubmit} className="card p-4">
            <div className="mb-3">
              <label className="form-label">Aktuelles Passwort</label>
              <input
                type="password"
                className="form-control"
                value={form.old_password}
                onChange={(e) => setForm({ ...form, old_password: e.target.value })}
                required
              />
            </div>

            <div className="mb-3">
              <label className="form-label">Neues Passwort</label>
              <input
                type="password"
                className="form-control"
                value={form.new_password}
                onChange={(e) => setForm({ ...form, new_password: e.target.value })}
                placeholder="Mindestens 8 Zeichen"
                required
              />
            </div>

            <div className="mb-3">
              <label className="form-label">Passwort wiederholen</label>
              <input
                type="password"
                className="form-control"
                value={form.confirm_password}
                onChange={(e) => setForm({ ...form, confirm_password: e.target.value })}
                required
              />
            </div>

            <button
              type="submit"
              className="btn btn-primary w-100"
              disabled={saving}
            >
              {saving ? 'Speichert...' : 'Passwort ändern'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
