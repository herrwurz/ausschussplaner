import { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import api from '../api/client'
import '../styles/AdminPanel.css'
import '../styles/BenutzerTab.css'
import PeriodenManagement from './PeriodenManagement'
import AusschuessProPeriode from './AusschuessProPeriode'
import MitgliedschaftenManagement from './MitgliedschaftenManagement'
import Terminberechnung from './Terminberechnung'
import FixierteTermine from './FixierteTermine'
import Sitzungsregeln from './Sitzungsregeln'

export default function AdminPanel() {
  const navigate = useNavigate()
  const location = useLocation()
  const [activeTab, setActiveTab] = useState('personen')
  const user = JSON.parse(localStorage.getItem('user') || '{}')
  const isSuperAdmin = user.rolle === 'super_admin'

  useEffect(() => {
    // Set tab based on URL path
    if (location.pathname.includes('perioden')) {
      setActiveTab('perioden')
    } else if (location.pathname.includes('ausschuesse')) {
      setActiveTab('ausschuesse')
    } else if (location.pathname.includes('mitgliedschaften')) {
      setActiveTab('mitgliedschaften')
    } else if (location.pathname.includes('termine-berechnung')) {
      setActiveTab('termine-berechnung')
    } else if (location.pathname.includes('fixierte-termine')) {
      setActiveTab('fixierte-termine')
    } else {
      setActiveTab('personen')
    }
  }, [location.pathname])

  useEffect(() => {
    const token = localStorage.getItem('token')
    const user = localStorage.getItem('user')
    console.log('AdminPanel useEffect: token=', !!token, 'user=', !!user)
    console.log('localStorage keys:', Object.keys(localStorage))

    if (!token || !user) {
      console.log('AdminPanel: Redirecting to login (no token or user)')
      navigate('/admin/login', { replace: true })
    }
  }, [])

  const handleLogout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    localStorage.removeItem('adminAuth')
    navigate('/admin/login')
  }

  return (
    <div className="admin-container">
      <header className="admin-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h1>Admin Panel - AusschussPlaner</h1>
          <button className="btn btn-secondary" onClick={handleLogout} style={{ fontSize: '0.9rem' }}>
            Logout
          </button>
        </div>
      </header>

      <div className="admin-tabs">
        {isSuperAdmin && (
          <button
            className={`tab-btn ${activeTab === 'benutzer' ? 'active' : ''}`}
            onClick={() => setActiveTab('benutzer')}
          >
            🔐 Benutzer
          </button>
        )}
        <button
          className={`tab-btn ${activeTab === 'personen' ? 'active' : ''}`}
          onClick={() => setActiveTab('personen')}
        >
          👥 Personen
        </button>
        <button
          className={`tab-btn ${activeTab === 'perioden' ? 'active' : ''}`}
          onClick={() => setActiveTab('perioden')}
        >
          📅 Perioden
        </button>
        <button
          className={`tab-btn ${activeTab === 'ausschuesse' ? 'active' : ''}`}
          onClick={() => setActiveTab('ausschuesse')}
        >
          📋 Ausschüsse
        </button>
        <button
          className={`tab-btn ${activeTab === 'mitgliedschaften' ? 'active' : ''}`}
          onClick={() => setActiveTab('mitgliedschaften')}
        >
          🎭 Mitgliedschaften
        </button>
        <button
          className={`tab-btn ${activeTab === 'termine-berechnung' ? 'active' : ''}`}
          onClick={() => setActiveTab('termine-berechnung')}
        >
          📊 Berechnung
        </button>
        <button
          className={`tab-btn ${activeTab === 'fixierte-termine' ? 'active' : ''}`}
          onClick={() => setActiveTab('fixierte-termine')}
        >
          📅 Fixierte Termine
        </button>
        {isSuperAdmin && (
          <button
            className={`tab-btn ${activeTab === 'sitzungsregeln' ? 'active' : ''}`}
            onClick={() => setActiveTab('sitzungsregeln')}
          >
            ⚙️ Sitzungsregeln
          </button>
        )}
      </div>

      <div className="admin-content">
        {isSuperAdmin && activeTab === 'benutzer' && <BenutzerTab />}
        {activeTab === 'personen' && <PersonenTab />}
        {activeTab === 'perioden' && <PeriodenManagement />}
        {activeTab === 'ausschuesse' && <AusschuessProPeriode />}
        {activeTab === 'mitgliedschaften' && <MitgliedschaftenManagement />}
        {activeTab === 'termine-berechnung' && <Terminberechnung />}
        {activeTab === 'fixierte-termine' && <FixierteTermine />}
        {isSuperAdmin && activeTab === 'sitzungsregeln' && <Sitzungsregeln />}
      </div>
    </div>
  )
}

// ─────────────────────────────────────────
// Personen Management Tab
// ─────────────────────────────────────────
function PersonenTab() {
  const [persons, setPersons] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [formData, setFormData] = useState({
    vorname: '',
    nachname: '',
    email: '',
    gremium: '',
    partai: '',
    aktiv: true,
  })

  useEffect(() => {
    fetchPersons()
  }, [])

  const fetchPersons = async () => {
    try {
      setLoading(true)
      console.log('🔍 Fetching persons...')
      console.log('Token:', localStorage.getItem('token')?.substring(0, 30) + '...')

      const res = await api.get('/persons')
      console.log('✅ Persons loaded:', res.data.length)
      setPersons(res.data)
    } catch (err) {
      console.error('❌ Error loading persons:', err)
      console.error('Status:', err.response?.status)
      console.error('URL:', err.config?.url)
      setError(`Personen laden fehlgeschlagen: ${err.response?.status || err.message}`)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    try {
      if (editingId) {
        await api.patch(`/persons/${editingId}`, formData)
      } else {
        await api.post('/persons', formData)
      }
      setShowForm(false)
      setEditingId(null)
      setFormData({ vorname: '', nachname: '', email: '', gremium: '', partai: '', aktiv: true })
      fetchPersons()
    } catch (err) {
      setError(err.response?.data?.detail || 'Fehler beim Speichern')
    }
  }

  const handleEdit = (person) => {
    setFormData(person)
    setEditingId(person.id)
    setShowForm(true)
  }

  const handleDelete = async (id) => {
    if (!window.confirm('Wirklich löschen?')) return
    try {
      await api.delete(`/persons/${id}`)
      fetchPersons()
    } catch (err) {
      setError('Löschen fehlgeschlagen')
    }
  }

  const handleCancel = () => {
    setShowForm(false)
    setEditingId(null)
    setFormData({ vorname: '', nachname: '', email: '', gremium: '', partai: '', aktiv: true })
  }

  return (
    <>
      {error && <div className="alert alert-danger">{error}</div>}

      <div className="section-header">
        <h2>Personen-Verwaltung</h2>
        <button className="btn btn-primary" onClick={() => setShowForm(true)}>
          + Neue Person
        </button>
      </div>

      {showForm && (
        <form className="admin-form" onSubmit={handleSubmit}>
          <h3>{editingId ? 'Person bearbeiten' : 'Neue Person'}</h3>
          <div className="form-grid">
            <input
              type="text"
              placeholder="Vorname"
              value={formData.vorname}
              onChange={(e) => setFormData({ ...formData, vorname: e.target.value })}
              required
            />
            <input
              type="text"
              placeholder="Nachname"
              value={formData.nachname}
              onChange={(e) => setFormData({ ...formData, nachname: e.target.value })}
              required
            />
            <input
              type="email"
              placeholder="Email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              required
            />
            <input
              type="text"
              placeholder="Gremium (z.B. Stadtrat)"
              value={formData.gremium}
              onChange={(e) => setFormData({ ...formData, gremium: e.target.value })}
            />
            <input
              type="text"
              placeholder="Partei (z.B. ÖVP, SPÖ)"
              value={formData.partai}
              onChange={(e) => setFormData({ ...formData, partai: e.target.value })}
            />
          </div>
          <div className="form-check">
            <input
              type="checkbox"
              id="aktiv"
              checked={formData.aktiv}
              onChange={(e) => setFormData({ ...formData, aktiv: e.target.checked })}
            />
            <label htmlFor="aktiv">Aktiv</label>
          </div>
          <div className="form-buttons">
            <button type="submit" className="btn btn-success">
              {editingId ? 'Aktualisieren' : 'Erstellen'}
            </button>
            <button type="button" className="btn btn-secondary" onClick={handleCancel}>
              Abbrechen
            </button>
          </div>
        </form>
      )}

      {loading ? (
        <p>Lädt...</p>
      ) : (
        <div className="table-responsive">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Vorname</th>
                <th>Nachname</th>
                <th>Email</th>
                <th>Gremium</th>
                <th>Partei</th>
                <th>Status</th>
                <th>Aktionen</th>
              </tr>
            </thead>
            <tbody>
              {persons.map((person) => (
                <tr key={person.id}>
                  <td>{person.vorname}</td>
                  <td>{person.nachname}</td>
                  <td>{person.email}</td>
                  <td>{person.gremium}</td>
                  <td>{person.partai || '-'}</td>
                  <td>{person.aktiv ? '✅ Aktiv' : '❌ Inaktiv'}</td>
                  <td className="actions">
                    <button className="btn btn-sm btn-warning" onClick={() => handleEdit(person)}>
                      Edit
                    </button>
                    <button className="btn btn-sm btn-danger" onClick={() => handleDelete(person.id)}>
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}

// ─────────────────────────────────────────
// Benutzer Management Tab - Fluent 2
// ─────────────────────────────────────────
function BenutzerTab() {
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [formData, setFormData] = useState({
    email: '',
    vorname: '',
    nachname: '',
    rolle: 'benutzer',
  })

  useEffect(() => {
    fetchUsers()
  }, [])

  const fetchUsers = async () => {
    try {
      setLoading(true)
      const res = await api.get('/users')
      setUsers(res.data)
    } catch (err) {
      setError(`Benutzer laden fehlgeschlagen: ${err.response?.status || err.message}`)
    } finally {
      setLoading(false)
    }
  }

  const handleCreateUser = async (e) => {
    e.preventDefault()
    try {
      setError('')
      const res = await api.post('/users', formData)
      setSuccess(`✅ Benutzer "${res.data.vorname} ${res.data.nachname}" erstellt!\nTemporäres Passwort: ${res.data.temp_password}`)
      setFormData({ email: '', vorname: '', nachname: '', rolle: 'benutzer' })
      setShowForm(false)
      setTimeout(() => setSuccess(''), 5000)
      fetchUsers()
    } catch (err) {
      setError(`❌ Fehler: ${err.response?.data?.detail || err.message}`)
    }
  }

  const handleDeleteUser = async (userId) => {
    if (!window.confirm('Benutzer wirklich löschen?')) return
    try {
      setError('')
      await api.delete(`/users/${userId}`)
      setSuccess('✅ Benutzer gelöscht')
      setTimeout(() => setSuccess(''), 3000)
      fetchUsers()
    } catch (err) {
      setError(`❌ Fehler beim Löschen: ${err.response?.data?.detail || err.message}`)
    }
  }

  const handleResetPassword = async (userId, userName) => {
    try {
      setError('')
      const res = await api.post(`/users/${userId}/reset-password`)
      setSuccess(`✅ Passwort für "${userName}" zurückgesetzt!\nNeues Passwort: ${res.data.temp_password}`)
      setTimeout(() => setSuccess(''), 6000)
    } catch (err) {
      setError(`❌ Fehler: ${err.response?.data?.detail || err.message}`)
    }
  }

  if (loading) return <div className="benutzer-tab">⏳ Lädt...</div>

  return (
    <div className="benutzer-tab">
      {error && (
        <div className="message-box message-box-error">
          <div className="message-box-content">{error}</div>
          <button className="message-box-close" onClick={() => setError('')}>✕</button>
        </div>
      )}

      {success && (
        <div className="message-box message-box-success">
          <div className="message-box-content">{success}</div>
          <button className="message-box-close" onClick={() => setSuccess('')}>✕</button>
        </div>
      )}

      <div className="benutzer-actions">
        <button
          className="btn btn-primary"
          onClick={() => setShowForm(!showForm)}
        >
          {showForm ? '✕ Abbrechen' : '+ Neuer Benutzer'}
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleCreateUser} className="benutzer-form">
          <div className="form-group">
            <label>Email:</label>
            <input
              type="email"
              required
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
            />
          </div>
          <div className="form-group">
            <label>Vorname:</label>
            <input
              type="text"
              required
              value={formData.vorname}
              onChange={(e) => setFormData({ ...formData, vorname: e.target.value })}
            />
          </div>
          <div className="form-group">
            <label>Nachname:</label>
            <input
              type="text"
              required
              value={formData.nachname}
              onChange={(e) => setFormData({ ...formData, nachname: e.target.value })}
            />
          </div>
          <div className="form-group">
            <label>Rolle:</label>
            <select
              value={formData.rolle}
              onChange={(e) => setFormData({ ...formData, rolle: e.target.value })}
            >
              <option value="benutzer">Benutzer</option>
              <option value="obmann">Obmann</option>
              <option value="super_admin">Super Admin</option>
            </select>
          </div>
          <div className="form-actions">
            <button type="submit" className="btn btn-primary">Erstellen</button>
          </div>
        </form>
      )}

      <table className="benutzer-table">
        <thead>
          <tr>
            <th>Email</th>
            <th>Name</th>
            <th>Rolle</th>
            <th>Status</th>
            <th>Aktionen</th>
          </tr>
        </thead>
        <tbody>
          {users.map((user) => (
            <tr key={user.id}>
              <td>{user.email}</td>
              <td>{user.vorname} {user.nachname}</td>
              <td>
                <span className={`role-badge role-${user.rolle}`}>
                  {user.rolle === 'super_admin' ? '👑 Super Admin' : user.rolle === 'obmann' ? '👔 Obmann' : '👤 Benutzer'}
                </span>
              </td>
              <td>
                <span className={`status-badge status-${user.aktiv ? 'active' : 'inactive'}`}>
                  {user.aktiv ? '✅ Aktiv' : '⚠️ Inaktiv'}
                </span>
              </td>
              <td>
                <div className="table-actions">
                  <button
                    className="btn btn-sm"
                    onClick={() => handleResetPassword(user.id, `${user.vorname} ${user.nachname}`)}
                    title="Passwort zurücksetzen"
                  >
                    🔑 Reset
                  </button>
                  {user.rolle !== 'super_admin' && (
                    <button
                      className="btn btn-sm btn-danger"
                      onClick={() => handleDeleteUser(user.id)}
                      title="Benutzer löschen"
                    >
                      🗑️ Löschen
                    </button>
                  )}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
