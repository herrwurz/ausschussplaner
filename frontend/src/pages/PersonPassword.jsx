import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api/client'
import PageHeader from '../components/PageHeader'

export default function PersonPassword() {
  const [form, setForm] = useState({ old_password: '', new_password: '', confirm_password: '' })
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const navigate = useNavigate()

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
    try {
      await api.put('/person/me/password', {
        old_password: form.old_password,
        new_password: form.new_password,
      })
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
    <div>
      <PageHeader title="Passwort ändern" />
      {error && <div className="alert alert-danger">{error}</div>}
      {message && <div className="alert alert-success">{message}</div>}
      <form onSubmit={handleSubmit} className="admin-form" style={{ maxWidth: 480 }}>
        <div className="form-group">
          <label>Aktuelles Passwort</label>
          <input
            type="password"
            value={form.old_password}
            onChange={(e) => setForm({ ...form, old_password: e.target.value })}
            required
          />
        </div>
        <div className="form-group">
          <label>Neues Passwort</label>
          <input
            type="password"
            value={form.new_password}
            onChange={(e) => setForm({ ...form, new_password: e.target.value })}
            required
          />
        </div>
        <div className="form-group">
          <label>Neues Passwort bestätigen</label>
          <input
            type="password"
            value={form.confirm_password}
            onChange={(e) => setForm({ ...form, confirm_password: e.target.value })}
            required
          />
        </div>
        <button type="submit" className="btn btn-primary" disabled={saving}>
          {saving ? 'Speichert...' : 'Passwort ändern'}
        </button>
      </form>
    </div>
  )
}
