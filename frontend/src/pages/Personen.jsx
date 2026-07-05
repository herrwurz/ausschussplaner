import { useEffect, useState } from 'react'
import api from '../api/client'

export default function Personen() {
  const [persons, setPersons] = useState([])
  const [loading, setLoading] = useState(true)
  const [form, setForm] = useState({ vorname: '', nachname: '', email: '', partei: '', gremium: '' })
  const [editingId, setEditingId] = useState(null)
  const [editForm, setEditForm] = useState({ vorname: '', nachname: '', email: '', partei: '', gremium: '' })

  const fetchPersons = async () => {
    try {
      const res = await api.get('/persons')
      setPersons(res.data)
    } catch (error) {
      console.error('Error:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchPersons()
  }, [])

  const handleCreate = async (e) => {
    e.preventDefault()
    try {
      await api.post('/persons', form)
      setForm({ vorname: '', nachname: '', email: '', partei: '', gremium: '' })
      fetchPersons()
    } catch (error) {
      console.error('Error creating person:', error)
    }
  }

  const handleEdit = (person) => {
    setEditingId(person.id)
    setEditForm({
      vorname: person.vorname,
      nachname: person.nachname,
      email: person.email,
      partei: person.partei || '',
      gremium: person.gremium || ''
    })
  }

  const handleSaveEdit = async (e) => {
    e.preventDefault()
    try {
      await api.patch(`/persons/${editingId}`, editForm)
      setEditingId(null)
      setEditForm({ vorname: '', nachname: '', email: '', partei: '', gremium: '' })
      fetchPersons()
    } catch (error) {
      console.error('Error updating person:', error)
    }
  }

  const handleDelete = async (id) => {
    if (!confirm('Person löschen?')) return
    try {
      await api.delete(`/persons/${id}`)
      fetchPersons()
    } catch (error) {
      console.error('Error:', error)
    }
  }

  return (
    <div>
      <h1>Personen</h1>
      <form onSubmit={handleCreate} className="card p-3 mb-4">
        <div className="row">
          <div className="col-md-3">
            <input
              type="text"
              className="form-control"
              placeholder="Vorname"
              value={form.vorname}
              onChange={(e) => setForm({ ...form, vorname: e.target.value })}
              required
            />
          </div>
          <div className="col-md-3">
            <input
              type="text"
              className="form-control"
              placeholder="Nachname"
              value={form.nachname}
              onChange={(e) => setForm({ ...form, nachname: e.target.value })}
              required
            />
          </div>
          <div className="col-md-2">
            <input
              type="email"
              className="form-control"
              placeholder="Email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
            />
          </div>
          <div className="col-md-2">
            <select
              className="form-control"
              value={form.partei || ''}
              onChange={(e) => setForm({ ...form, partei: e.target.value || '' })}
            >
              <option value="">Partei</option>
              <option value="SPÖ">SPÖ</option>
              <option value="ÖVP">ÖVP</option>
              <option value="Die Grünen">Grüne</option>
              <option value="FPÖ">FPÖ</option>
              <option value="NEOS">NEOS</option>
              <option value="KPÖ">KPÖ</option>
            </select>
          </div>
          <div className="col-md-2">
            <button type="submit" className="btn btn-primary w-100">Hinzufügen</button>
          </div>
        </div>
      </form>

      {loading ? (
        <div className="alert alert-info">Lädt...</div>
      ) : (
        <table className="table table-striped">
          <thead>
            <tr>
              <th>Vorname</th>
              <th>Nachname</th>
              <th>Email</th>
              <th>Partei</th>
              <th>Gremium</th>
              <th>Aktionen</th>
            </tr>
          </thead>
          <tbody>
            {persons.map((p) => (
              <tr key={p.id}>
                <td>{p.vorname}</td>
                <td>{p.nachname}</td>
                <td>{p.email}</td>
                <td><span className="badge bg-info">{p.partei || '—'}</span></td>
                <td>{p.gremium}</td>
                <td>
                  <button
                    className="btn btn-sm btn-warning me-2"
                    onClick={() => handleEdit(p)}
                  >
                    Bearbeiten
                  </button>
                  <button
                    className="btn btn-sm btn-danger"
                    onClick={() => handleDelete(p.id)}
                  >
                    Löschen
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {/* Edit Modal */}
      {editingId && (
        <div className="modal d-block" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">Person bearbeiten</h5>
                <button
                  type="button"
                  className="btn-close"
                  onClick={() => setEditingId(null)}
                ></button>
              </div>
              <form onSubmit={handleSaveEdit}>
                <div className="modal-body">
                  <div className="mb-3">
                    <label className="form-label">Vorname</label>
                    <input
                      type="text"
                      className="form-control"
                      value={editForm.vorname}
                      onChange={(e) => setEditForm({ ...editForm, vorname: e.target.value })}
                      required
                    />
                  </div>
                  <div className="mb-3">
                    <label className="form-label">Nachname</label>
                    <input
                      type="text"
                      className="form-control"
                      value={editForm.nachname}
                      onChange={(e) => setEditForm({ ...editForm, nachname: e.target.value })}
                      required
                    />
                  </div>
                  <div className="mb-3">
                    <label className="form-label">Email</label>
                    <input
                      type="email"
                      className="form-control"
                      value={editForm.email}
                      onChange={(e) => setEditForm({ ...editForm, email: e.target.value })}
                    />
                  </div>
                  <div className="mb-3">
                    <label className="form-label">Partei</label>
                    <select
                      className="form-control"
                      value={editForm.partei || ''}
                      onChange={(e) => setEditForm({ ...editForm, partei: e.target.value || '' })}
                    >
                      <option value="">Keine</option>
                      <option value="SPÖ">SPÖ</option>
                      <option value="ÖVP">ÖVP</option>
                      <option value="Die Grünen">Grüne</option>
                      <option value="FPÖ">FPÖ</option>
                      <option value="NEOS">NEOS</option>
                      <option value="KPÖ">KPÖ</option>
                    </select>
                  </div>
                  <div className="mb-3">
                    <label className="form-label">Gremium</label>
                    <input
                      type="text"
                      className="form-control"
                      value={editForm.gremium || ''}
                      onChange={(e) => setEditForm({ ...editForm, gremium: e.target.value })}
                      placeholder="z.B. Gemeinderat"
                    />
                  </div>
                </div>
                <div className="modal-footer">
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() => setEditingId(null)}
                  >
                    Abbrechen
                  </button>
                  <button type="submit" className="btn btn-primary">
                    Speichern
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
