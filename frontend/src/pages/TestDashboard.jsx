import { useEffect, useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'

const API = ''
const PARTEIEN = ['ÖVP', 'SPÖ', 'Grüne', 'FPÖ', 'NEOS', 'KPÖ']

export default function TestDashboard() {
  const [data, setData] = useState({ persons: [], committees: [], periods: [], absences: [], yearplans: [] })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [activeTab, setActiveTab] = useState('personen')
  const navigate = useNavigate()

  // Form states - CREATE
  const [newPerson, setNewPerson] = useState({ vorname: '', nachname: '', email: '', partei: '', gremium: '' })
  const [newCommittee, setNewCommittee] = useState({ name: '', typ: 'ausschuss' })
  const [newAbsence, setNewAbsence] = useState({ person_id: '', von: '', bis: '', art: 'URLAUB', bemerkung: '' })
  const [newYearplan, setNewYearplan] = useState({ name: '', periode_id: '' })

  // Form states - EDIT
  const [editPerson, setEditPerson] = useState(null)
  const [editCommittee, setEditCommittee] = useState(null)
  const [editAbsence, setEditAbsence] = useState(null)
  const [editYearplan, setEditYearplan] = useState(null)

  useEffect(() => { fetchAllData() }, [])

  const fetchAllData = async () => {
    try {
      setLoading(true)
      const [p, c, pr, a, y] = await Promise.all([
        fetch(`${API}/api/persons`).then(r => r.json()).catch(() => []),
        fetch(`${API}/api/committees`).then(r => r.json()).catch(() => []),
        fetch(`${API}/api/periode`).then(r => r.json()).catch(() => []),
        fetch(`${API}/api/absences`).then(r => r.json()).catch(() => []),
        fetch(`${API}/api/jahresplan`).then(r => r.json()).catch(() => [])
      ])
      setData({ persons: p, committees: c, periods: pr, absences: a, yearplans: y })
      setError('')
    } catch (err) {
      setError(`Fehler: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  // PERSONEN - CREATE
  const addPerson = async () => {
    if (!newPerson.vorname || !newPerson.nachname || !newPerson.email) {
      setError('Vorname, Nachname und Email erforderlich')
      return
    }
    try {
      const res = await fetch(`${API}/api/persons`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newPerson)
      })
      if (res.ok) {
        setNewPerson({ vorname: '', nachname: '', email: '', partei: '', gremium: '' })
        fetchAllData()
      } else setError('Fehler beim Hinzufügen')
    } catch (err) { setError(err.message) }
  }

  // PERSONEN - UPDATE
  const updatePerson = async () => {
    if (!editPerson.vorname || !editPerson.nachname) {
      setError('Vorname und Nachname erforderlich')
      return
    }
    try {
      const res = await fetch(`${API}/api/persons/${editPerson.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editPerson)
      })
      if (res.ok) {
        setEditPerson(null)
        fetchAllData()
      } else setError('Fehler beim Update')
    } catch (err) { setError(err.message) }
  }

  // PERSONEN - DELETE
  const deletePerson = async (id) => {
    if (!window.confirm('Wirklich löschen?')) return
    try {
      const res = await fetch(`${API}/api/persons/${id}`, { method: 'DELETE' })
      if (res.ok) fetchAllData()
      else setError('Fehler beim Löschen')
    } catch (err) { setError(err.message) }
  }

  // AUSSCHÜSSE - CREATE
  const addCommittee = async () => {
    if (!newCommittee.name) {
      setError('Name erforderlich')
      return
    }
    try {
      const res = await fetch(`${API}/api/committees`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newCommittee)
      })
      if (res.ok) {
        setNewCommittee({ name: '', typ: 'STANDARD' })
        fetchAllData()
      } else setError('Fehler')
    } catch (err) { setError(err.message) }
  }

  // AUSSCHÜSSE - UPDATE
  const updateCommittee = async () => {
    if (!editCommittee.name) {
      setError('Name erforderlich')
      return
    }
    try {
      const res = await fetch(`${API}/api/committees/${editCommittee.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editCommittee)
      })
      if (res.ok) {
        setEditCommittee(null)
        fetchAllData()
      } else setError('Fehler beim Update')
    } catch (err) { setError(err.message) }
  }

  // AUSSCHÜSSE - DELETE
  const deleteCommittee = async (id) => {
    if (!window.confirm('Löschen?')) return
    try {
      const res = await fetch(`${API}/api/committees/${id}`, { method: 'DELETE' })
      if (res.ok) fetchAllData()
    } catch (err) { setError(err.message) }
  }

  // ABWESENHEITEN - CREATE
  const addAbsence = async () => {
    if (!newAbsence.person_id || !newAbsence.von || !newAbsence.bis) {
      setError('Person, Von und Bis erforderlich')
      return
    }
    try {
      const res = await fetch(`${API}/api/absences`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newAbsence)
      })
      if (res.ok) {
        setNewAbsence({ person_id: '', von: '', bis: '', art: 'URLAUB', bemerkung: '' })
        fetchAllData()
      } else setError('Fehler')
    } catch (err) { setError(err.message) }
  }

  // ABWESENHEITEN - UPDATE
  const updateAbsence = async () => {
    if (!editAbsence.person_id || !editAbsence.von || !editAbsence.bis) {
      setError('Pflichtfelder erforderlich')
      return
    }
    try {
      const res = await fetch(`${API}/api/absences/${editAbsence.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editAbsence)
      })
      if (res.ok) {
        setEditAbsence(null)
        fetchAllData()
      } else setError('Fehler beim Update')
    } catch (err) { setError(err.message) }
  }

  // ABWESENHEITEN - DELETE
  const deleteAbsence = async (id) => {
    if (!window.confirm('Löschen?')) return
    try {
      const res = await fetch(`${API}/api/absences/${id}`, { method: 'DELETE' })
      if (res.ok) fetchAllData()
    } catch (err) { setError(err.message) }
  }

  // JAHRESPLÄNE - CREATE
  const addYearplan = async () => {
    if (!newYearplan.name || !newYearplan.periode_id) {
      setError('Name und Periode erforderlich')
      return
    }
    try {
      const res = await fetch(`${API}/api/jahresplan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newYearplan)
      })
      if (res.ok) {
        setNewYearplan({ name: '', periode_id: '' })
        fetchAllData()
      } else setError('Fehler')
    } catch (err) { setError(err.message) }
  }

  // JAHRESPLÄNE - UPDATE
  const updateYearplan = async () => {
    if (!editYearplan.name || !editYearplan.periode_id) {
      setError('Name und Periode erforderlich')
      return
    }
    try {
      const res = await fetch(`${API}/api/jahresplan/${editYearplan.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editYearplan)
      })
      if (res.ok) {
        setEditYearplan(null)
        fetchAllData()
      } else setError('Fehler beim Update')
    } catch (err) { setError(err.message) }
  }

  // JAHRESPLÄNE - DELETE
  const deleteYearplan = async (id) => {
    if (!window.confirm('Löschen?')) return
    try {
      const res = await fetch(`${API}/api/jahresplan/${id}`, { method: 'DELETE' })
      if (res.ok) fetchAllData()
    } catch (err) { setError(err.message) }
  }

  if (loading) return <div style={{ padding: '20px' }}>Laden...</div>

  const inputStyle = { padding: '8px', border: '1px solid #d1d5db', borderRadius: '4px', marginRight: '5px' }
  const buttonStyle = { padding: '8px 15px', background: '#2563eb', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', marginRight: '5px' }
  const dangerButtonStyle = { ...buttonStyle, background: '#dc2626' }
  const tabStyle = (name) => ({ padding: '10px 20px', background: activeTab === name ? '#1e3a8a' : '#d1d5db', color: activeTab === name ? 'white' : 'black', border: 'none', cursor: 'pointer', borderRadius: '4px', marginRight: '5px' })
  const tableStyle = { width: '100%', borderCollapse: 'collapse', marginTop: '10px' }
  const thStyle = { background: '#1e3a8a', color: 'white', padding: '10px', textAlign: 'left', borderBottom: '2px solid #d1d5db' }
  const tdStyle = { padding: '10px', borderBottom: '1px solid #d1d5db' }

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '20px', fontFamily: 'sans-serif' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '30px' }}>
        <h1>🧪 Test-Dashboard (Übergangslösung)</h1>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button onClick={() => { localStorage.clear(); navigate('/login') }} style={dangerButtonStyle}>Logout</button>
        </div>
      </div>

      {error && <div style={{ background: '#fee2e2', color: '#dc2626', padding: '15px', borderRadius: '6px', marginBottom: '20px' }}>{error}</div>}

      {/* TABS */}
      <div style={{ marginBottom: '20px' }}>
        {['personen', 'ausschuesse', 'abwesenheiten', 'jahrespläne'].map(tab => (
          <button key={tab} onClick={() => setActiveTab(tab)} style={tabStyle(tab)}>
            {tab.toUpperCase()}
          </button>
        ))}
      </div>

      {/* PERSONEN */}
      {activeTab === 'personen' && (
        <div style={{ background: '#f9fafb', padding: '20px', borderRadius: '8px' }}>
          <h2>👤 Personen ({data.persons.length})</h2>

          {/* CREATE */}
          <div style={{ background: 'white', padding: '15px', borderRadius: '6px', marginBottom: '20px', border: '1px solid #d1d5db' }}>
            <h4>Neue Person</h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '8px', marginBottom: '10px' }}>
              <input type="text" placeholder="Vorname" value={newPerson.vorname} onChange={(e) => setNewPerson({ ...newPerson, vorname: e.target.value })} style={inputStyle} />
              <input type="text" placeholder="Nachname" value={newPerson.nachname} onChange={(e) => setNewPerson({ ...newPerson, nachname: e.target.value })} style={inputStyle} />
              <input type="email" placeholder="Email" value={newPerson.email} onChange={(e) => setNewPerson({ ...newPerson, email: e.target.value })} style={inputStyle} />
              <select value={newPerson.partei} onChange={(e) => setNewPerson({ ...newPerson, partei: e.target.value })} style={inputStyle}>
                <option value="">-- Partei --</option>
                {PARTEIEN.map(p => <option key={p} value={p}>{p}</option>)}
              </select>
              <input type="text" placeholder="Gremium" value={newPerson.gremium} onChange={(e) => setNewPerson({ ...newPerson, gremium: e.target.value })} style={inputStyle} />
              <button onClick={addPerson} style={buttonStyle}>Hinzufügen</button>
            </div>
          </div>

          {/* EDIT */}
          {editPerson && (
            <div style={{ background: '#fffbeb', padding: '15px', borderRadius: '6px', marginBottom: '20px', border: '1px solid #fbbf24' }}>
              <h4>Person bearbeiten</h4>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '8px', marginBottom: '10px' }}>
                <input type="text" placeholder="Vorname" value={editPerson.vorname} onChange={(e) => setEditPerson({ ...editPerson, vorname: e.target.value })} style={inputStyle} />
                <input type="text" placeholder="Nachname" value={editPerson.nachname} onChange={(e) => setEditPerson({ ...editPerson, nachname: e.target.value })} style={inputStyle} />
                <input type="email" placeholder="Email" value={editPerson.email} onChange={(e) => setEditPerson({ ...editPerson, email: e.target.value })} style={inputStyle} />
                <select value={editPerson.partei || ''} onChange={(e) => setEditPerson({ ...editPerson, partei: e.target.value })} style={inputStyle}>
                  <option value="">-- Partei --</option>
                  {PARTEIEN.map(p => <option key={p} value={p}>{p}</option>)}
                </select>
                <input type="text" placeholder="Gremium" value={editPerson.gremium || ''} onChange={(e) => setEditPerson({ ...editPerson, gremium: e.target.value })} style={inputStyle} />
                <button onClick={updatePerson} style={buttonStyle}>Speichern</button>
                <button onClick={() => setEditPerson(null)} style={{ ...buttonStyle, background: '#6b7280' }}>Abbrechen</button>
              </div>
            </div>
          )}

          {/* TABLE */}
          <table style={tableStyle}>
            <thead>
              <tr><th style={thStyle}>ID</th><th style={thStyle}>Name</th><th style={thStyle}>Email</th><th style={thStyle}>Partei</th><th style={thStyle}>Gremium</th><th style={thStyle}>Actions</th></tr>
            </thead>
            <tbody>
              {data.persons.map(p => (
                <tr key={p.id}>
                  <td style={tdStyle}>{p.id}</td>
                  <td style={tdStyle}>{p.vorname} {p.nachname}</td>
                  <td style={tdStyle}>{p.email}</td>
                  <td style={tdStyle}>{p.partei || '-'}</td>
                  <td style={tdStyle}>{p.gremium || '-'}</td>
                  <td style={tdStyle}>
                    <button onClick={() => setEditPerson(p)} style={{ ...buttonStyle, background: '#f97316' }}>Edit</button>
                    <button onClick={() => deletePerson(p.id)} style={dangerButtonStyle}>Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* AUSSCHÜSSE */}
      {activeTab === 'ausschuesse' && (
        <div style={{ background: '#f9fafb', padding: '20px', borderRadius: '8px' }}>
          <h2>🏢 Ausschüsse ({data.committees.length})</h2>

          {/* CREATE */}
          <div style={{ background: 'white', padding: '15px', borderRadius: '6px', marginBottom: '20px', border: '1px solid #d1d5db' }}>
            <h4>Neuer Ausschuss</h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '8px', marginBottom: '10px' }}>
              <input type="text" placeholder="Name" value={newCommittee.name} onChange={(e) => setNewCommittee({ ...newCommittee, name: e.target.value })} style={inputStyle} />
              <select value={newCommittee.typ} onChange={(e) => setNewCommittee({ ...newCommittee, typ: e.target.value })} style={inputStyle}>
                <option value="ausschuss">Ausschuss</option><option value="stadtratsitzung">Stadtratsitzung</option><option value="gemeinderatsitzung">Gemeinderatsitzung</option><option value="sonstige">Sonstige</option>
              </select>
              <button onClick={addCommittee} style={buttonStyle}>Hinzufügen</button>
            </div>
          </div>

          {/* EDIT */}
          {editCommittee && (
            <div style={{ background: '#fffbeb', padding: '15px', borderRadius: '6px', marginBottom: '20px', border: '1px solid #fbbf24' }}>
              <h4>Ausschuss bearbeiten</h4>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '8px', marginBottom: '10px' }}>
                <input type="text" placeholder="Name" value={editCommittee.name} onChange={(e) => setEditCommittee({ ...editCommittee, name: e.target.value })} style={inputStyle} />
                <select value={editCommittee.typ} onChange={(e) => setEditCommittee({ ...editCommittee, typ: e.target.value })} style={inputStyle}>
                  <option value="ausschuss">Ausschuss</option><option value="stadtratsitzung">Stadtratsitzung</option><option value="gemeinderatsitzung">Gemeinderatsitzung</option><option value="sonstige">Sonstige</option>
                </select>
                <button onClick={updateCommittee} style={buttonStyle}>Speichern</button>
                <button onClick={() => setEditCommittee(null)} style={{ ...buttonStyle, background: '#6b7280' }}>Abbrechen</button>
              </div>
            </div>
          )}

          {/* TABLE */}
          <table style={tableStyle}>
            <thead>
              <tr><th style={thStyle}>ID</th><th style={thStyle}>Name</th><th style={thStyle}>Typ</th><th style={thStyle}>Actions</th></tr>
            </thead>
            <tbody>
              {data.committees.map(c => (
                <tr key={c.id}>
                  <td style={tdStyle}>{c.id}</td>
                  <td style={tdStyle}>{c.name}</td>
                  <td style={tdStyle}>{c.typ}</td>
                  <td style={tdStyle}>
                    <button onClick={() => setEditCommittee(c)} style={{ ...buttonStyle, background: '#f97316' }}>Edit</button>
                    <button onClick={() => deleteCommittee(c.id)} style={dangerButtonStyle}>Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* ABWESENHEITEN */}
      {activeTab === 'abwesenheiten' && (
        <div style={{ background: '#f9fafb', padding: '20px', borderRadius: '8px' }}>
          <h2>🚫 Abwesenheiten ({data.absences.length})</h2>

          {/* CREATE */}
          <div style={{ background: 'white', padding: '15px', borderRadius: '6px', marginBottom: '20px', border: '1px solid #d1d5db' }}>
            <h4>Neue Abwesenheit</h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '8px', marginBottom: '10px' }}>
              <select value={newAbsence.person_id} onChange={(e) => setNewAbsence({ ...newAbsence, person_id: e.target.value })} style={inputStyle}>
                <option value="">Person</option>
                {data.persons.map(p => <option key={p.id} value={p.id}>{p.vorname} {p.nachname}</option>)}
              </select>
              <input type="date" value={newAbsence.von} onChange={(e) => setNewAbsence({ ...newAbsence, von: e.target.value })} style={inputStyle} />
              <input type="date" value={newAbsence.bis} onChange={(e) => setNewAbsence({ ...newAbsence, bis: e.target.value })} style={inputStyle} />
              <select value={newAbsence.art} onChange={(e) => setNewAbsence({ ...newAbsence, art: e.target.value })} style={inputStyle}>
                <option value="URLAUB">URLAUB</option><option value="KRANKHEIT">KRANKHEIT</option><option value="DIENSTREISE">DIENSTREISE</option>
              </select>
              <button onClick={addAbsence} style={buttonStyle}>Hinzufügen</button>
            </div>
          </div>

          {/* EDIT */}
          {editAbsence && (
            <div style={{ background: '#fffbeb', padding: '15px', borderRadius: '6px', marginBottom: '20px', border: '1px solid #fbbf24' }}>
              <h4>Abwesenheit bearbeiten</h4>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '8px', marginBottom: '10px' }}>
                <select value={editAbsence.person_id} onChange={(e) => setEditAbsence({ ...editAbsence, person_id: e.target.value })} style={inputStyle}>
                  <option value="">Person</option>
                  {data.persons.map(p => <option key={p.id} value={p.id}>{p.vorname} {p.nachname}</option>)}
                </select>
                <input type="date" value={editAbsence.von} onChange={(e) => setEditAbsence({ ...editAbsence, von: e.target.value })} style={inputStyle} />
                <input type="date" value={editAbsence.bis} onChange={(e) => setEditAbsence({ ...editAbsence, bis: e.target.value })} style={inputStyle} />
                <select value={editAbsence.art} onChange={(e) => setEditAbsence({ ...editAbsence, art: e.target.value })} style={inputStyle}>
                  <option value="URLAUB">URLAUB</option><option value="KRANKHEIT">KRANKHEIT</option><option value="DIENSTREISE">DIENSTREISE</option>
                </select>
                <button onClick={updateAbsence} style={buttonStyle}>Speichern</button>
                <button onClick={() => setEditAbsence(null)} style={{ ...buttonStyle, background: '#6b7280' }}>Abbrechen</button>
              </div>
            </div>
          )}

          {/* TABLE */}
          <table style={tableStyle}>
            <thead>
              <tr><th style={thStyle}>ID</th><th style={thStyle}>Person</th><th style={thStyle}>Von</th><th style={thStyle}>Bis</th><th style={thStyle}>Art</th><th style={thStyle}>Actions</th></tr>
            </thead>
            <tbody>
              {data.absences.map(a => {
                const person = data.persons.find(p => p.id === a.person_id)
                return (
                  <tr key={a.id}>
                    <td style={tdStyle}>{a.id}</td>
                    <td style={tdStyle}>{person ? `${person.vorname} ${person.nachname}` : 'Unbekannt'}</td>
                    <td style={tdStyle}>{a.von}</td>
                    <td style={tdStyle}>{a.bis}</td>
                    <td style={tdStyle}>{a.art}</td>
                    <td style={tdStyle}>
                      <button onClick={() => setEditAbsence(a)} style={{ ...buttonStyle, background: '#f97316' }}>Edit</button>
                      <button onClick={() => deleteAbsence(a.id)} style={dangerButtonStyle}>Delete</button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* JAHRESPLÄNE */}
      {activeTab === 'jahrespläne' && (
        <div style={{ background: '#f9fafb', padding: '20px', borderRadius: '8px' }}>
          <h2>📊 Jahrespläne ({data.yearplans.length})</h2>

          {/* CREATE */}
          <div style={{ background: 'white', padding: '15px', borderRadius: '6px', marginBottom: '20px', border: '1px solid #d1d5db' }}>
            <h4>Neuer Jahresplan</h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '8px', marginBottom: '10px' }}>
              <input type="text" placeholder="Name" value={newYearplan.name} onChange={(e) => setNewYearplan({ ...newYearplan, name: e.target.value })} style={inputStyle} />
              <select value={newYearplan.periode_id} onChange={(e) => setNewYearplan({ ...newYearplan, periode_id: e.target.value })} style={inputStyle}>
                <option value="">Periode wählen</option>
                {data.periods.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
              <button onClick={addYearplan} style={buttonStyle}>Hinzufügen</button>
            </div>
          </div>

          {/* EDIT */}
          {editYearplan && (
            <div style={{ background: '#fffbeb', padding: '15px', borderRadius: '6px', marginBottom: '20px', border: '1px solid #fbbf24' }}>
              <h4>Jahresplan bearbeiten</h4>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '8px', marginBottom: '10px' }}>
                <input type="text" placeholder="Name" value={editYearplan.name} onChange={(e) => setEditYearplan({ ...editYearplan, name: e.target.value })} style={inputStyle} />
                <select value={editYearplan.periode_id} onChange={(e) => setEditYearplan({ ...editYearplan, periode_id: e.target.value })} style={inputStyle}>
                  <option value="">Periode wählen</option>
                  {data.periods.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                </select>
                <button onClick={updateYearplan} style={buttonStyle}>Speichern</button>
                <button onClick={() => setEditYearplan(null)} style={{ ...buttonStyle, background: '#6b7280' }}>Abbrechen</button>
              </div>
            </div>
          )}

          {/* TABLE */}
          <table style={tableStyle}>
            <thead>
              <tr><th style={thStyle}>ID</th><th style={thStyle}>Name</th><th style={thStyle}>Periode</th><th style={thStyle}>Actions</th></tr>
            </thead>
            <tbody>
              {data.yearplans.map(yp => {
                const period = data.periods.find(p => p.id === yp.periode_id)
                return (
                  <tr key={yp.id}>
                    <td style={tdStyle}>{yp.id}</td>
                    <td style={tdStyle}>{yp.name}</td>
                    <td style={tdStyle}>{period ? period.name : 'Unbekannt'}</td>
                    <td style={tdStyle}>
                      <button onClick={() => setEditYearplan(yp)} style={{ ...buttonStyle, background: '#f97316' }}>Edit</button>
                      <button onClick={() => deleteYearplan(yp.id)} style={dangerButtonStyle}>Delete</button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
