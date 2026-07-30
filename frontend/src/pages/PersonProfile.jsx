import { useEffect, useState } from 'react'
import api from '../api/client'
import PageHeader from '../components/PageHeader'

export default function PersonProfile() {
  const [profile, setProfile] = useState(null)
  const [form, setForm] = useState({})
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const res = await api.get('/person/me')
        setProfile(res.data)
        setForm(res.data)
      } catch {
        /* Auth via PersonPortalLayout */
      }
    }
    fetchProfile()
  }, [])

  const handleSave = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      await api.put('/person/me', form)
      setMessage('Profil aktualisiert!')
      setTimeout(() => setMessage(''), 3000)
    } catch {
      setMessage('Fehler beim Speichern')
    } finally {
      setSaving(false)
    }
  }

  if (!profile) return <div className="alert alert-info">Lädt...</div>

  return (
    <div>
      <PageHeader title="Mein Profil" />
      {message && <div className="alert alert-info">{message}</div>}
      <form onSubmit={handleSave} className="admin-form" style={{ maxWidth: 480 }}>
        <div className="form-group">
          <label>Vorname</label>
          <input
            type="text"
            value={form.vorname || ''}
            onChange={(e) => setForm({ ...form, vorname: e.target.value })}
          />
        </div>
        <div className="form-group">
          <label>Nachname</label>
          <input
            type="text"
            value={form.nachname || ''}
            onChange={(e) => setForm({ ...form, nachname: e.target.value })}
          />
        </div>
        <div className="form-group">
          <label>Email (nicht änderbar)</label>
          <input type="email" value={form.email || ''} disabled />
        </div>
        <div className="form-group">
          <label>Partei</label>
          <select
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
        <button type="submit" className="btn btn-primary" disabled={saving}>
          {saving ? 'Speichert...' : 'Speichern'}
        </button>
      </form>
    </div>
  )
}
