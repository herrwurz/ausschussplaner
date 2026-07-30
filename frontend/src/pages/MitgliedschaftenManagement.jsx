import { useState, useEffect } from 'react'
import api from '../api/client'
import { usePeriod } from '../contexts/PeriodContext'
import PageHeader from '../components/PageHeader'

export default function MitgliedschaftenManagement() {
  const { selectedPeriodeId, selectedPeriode } = usePeriod()
  const [personen, setPersonen] = useState([])
  const [ausschuesse, setAusschuesse] = useState([])
  const [mitgliedschaften, setMitgliedschaften] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [editingPersonId, setEditingPersonId] = useState(null)
  const [editingAusschussId, setEditingAusschussId] = useState(null)
  const [editingRolle, setEditingRolle] = useState('')

  const rollen = [
    { value: 'Obmann', label: 'Obmann' },
    { value: 'Obmann Stellvertreter', label: 'Obmann-Stellvertreter' },
    { value: 'Mitglied', label: 'Mitglied' },
  ]

  useEffect(() => {
    if (selectedPeriodeId) {
      fetchData()
    }
  }, [selectedPeriodeId])

  const fetchData = async () => {
    try {
      setLoading(true)
      // Lade Personen
      const perRes = await api.get('/persons')
      setPersonen(perRes.data.filter(p => p.aktiv))

      // Lade Ausschüsse dieser Periode
      const ausRes = await api.get('/committees', { params: { periode_id: selectedPeriodeId } })
      setAusschuesse(ausRes.data)

      // Lade Mitgliedschaften
      const mitRes = await api.get('/committees', { params: { periode_id: selectedPeriodeId } })
      const allMitgliedschaften = []
      for (const ausschuss of mitRes.data) {
        for (const mitglied of ausschuss.mitglieder || []) {
          allMitgliedschaften.push({
            person_id: mitglied.person_id,
            ausschuss_id: ausschuss.id,
            rolle: mitglied.rolle,
            person_name: mitglied.name,
            ausschuss_name: ausschuss.name,
          })
        }
      }
      setMitgliedschaften(allMitgliedschaften)
    } catch (err) {
      setError('Daten laden fehlgeschlagen')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const getMitgliedschaft = (personId, ausschussId) => {
    return mitgliedschaften.find(
      m => m.person_id === personId && m.ausschuss_id === ausschussId
    )
  }

  const handleAddMitgliedschaft = async (personId, ausschussId) => {
    try {
      // Finde den Ausschuss und seine Mitglieder
      const ausschuss = ausschuesse.find(a => a.id === ausschussId)
      if (!ausschuss) return

      // Erstelle neue Mitgliedschaft
      const neuerMitglied = {
        person_id: personId,
        rolle: 'Mitglied',
      }

      // Update Ausschuss mit neuem Mitglied
      const newMitglieder = [...(ausschuss.mitglieder || []), neuerMitglied]
      await api.patch(`/committees/${ausschussId}`, {
        mitglieder: newMitglieder,
      })

      // Reload
      fetchData()
    } catch (err) {
      setError('Fehler beim Hinzufügen')
      console.error(err)
    }
  }

  const handleRemoveMitgliedschaft = async (personId, ausschussId) => {
    try {
      const ausschuss = ausschuesse.find(a => a.id === ausschussId)
      if (!ausschuss) return

      // Entferne Mitglied
      const newMitglieder = (ausschuss.mitglieder || []).filter(
        m => m.person_id !== personId
      )
      await api.patch(`/committees/${ausschussId}`, {
        mitglieder: newMitglieder,
      })

      fetchData()
    } catch (err) {
      setError('Fehler beim Entfernen')
      console.error(err)
    }
  }

  const handleChangeRolle = async (personId, ausschussId, newRolle) => {
    try {
      const ausschuss = ausschuesse.find(a => a.id === ausschussId)
      if (!ausschuss) return

      // Update Rolle
      const newMitglieder = (ausschuss.mitglieder || []).map(m =>
        m.person_id === personId ? { ...m, rolle: newRolle } : m
      )
      await api.patch(`/committees/${ausschussId}`, {
        mitglieder: newMitglieder,
      })

      fetchData()
    } catch (err) {
      setError('Fehler beim Ändern der Rolle')
      console.error(err)
    }
  }

  return (
    <>
      {error && <div className="alert alert-danger">{error}</div>}

      <PageHeader
        title="Mitgliedschaften pro Periode"
        description={selectedPeriode ? `${selectedPeriode.name} (${selectedPeriode.start_jahr}–${selectedPeriode.end_jahr})` : 'Periode in der Topbar wählen'}
      />

      {loading ? (
        <p>Lädt...</p>
      ) : personen.length === 0 || ausschuesse.length === 0 ? (
        <div className="alert alert-info">
          <p>
            {personen.length === 0
              ? 'Keine aktiven Personen vorhanden'
              : 'Keine Ausschüsse in dieser Periode'}
          </p>
        </div>
      ) : (
        <div className="table-responsive">
          <table className="admin-table" style={{ fontSize: '0.9rem' }}>
            <thead>
              <tr>
                <th>Person</th>
                {ausschuesse.map((a) => (
                  <th key={a.id} style={{ textAlign: 'center', maxWidth: '120px' }}>
                    {a.name}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {personen.map((person) => (
                <tr key={person.id}>
                  <td style={{ fontWeight: '500', minWidth: '150px' }}>
                    {person.vorname} {person.nachname}
                  </td>
                  {ausschuesse.map((ausschuss) => {
                    const mitgliedschaft = getMitgliedschaft(person.id, ausschuss.id)
                    return (
                      <td key={ausschuss.id} style={{ textAlign: 'center' }}>
                        {mitgliedschaft ? (
                          <div style={{ display: 'flex', gap: '0.25rem', justifyContent: 'center' }}>
                            <select
                              value={mitgliedschaft.rolle}
                              onChange={(e) =>
                                handleChangeRolle(person.id, ausschuss.id, e.target.value)
                              }
                              style={{
                                padding: '0.25rem 0.5rem',
                                fontSize: '0.8rem',
                                borderRadius: '3px',
                                border: '1px solid #2563eb',
                              }}
                            >
                              {rollen.map((rolle) => (
                                <option key={rolle.value} value={rolle.value}>
                                  {rolle.label}
                                </option>
                              ))}
                            </select>
                            <button
                              onClick={() =>
                                handleRemoveMitgliedschaft(person.id, ausschuss.id)
                              }
                              style={{
                                padding: '0.25rem 0.5rem',
                                fontSize: '0.8rem',
                                borderRadius: '3px',
                                background: '#ef4444',
                                color: 'white',
                                border: 'none',
                                cursor: 'pointer',
                              }}
                            >
                              ✕
                            </button>
                          </div>
                        ) : (
                          <button
                            onClick={() =>
                              handleAddMitgliedschaft(person.id, ausschuss.id)
                            }
                            style={{
                              padding: '0.25rem 0.75rem',
                              fontSize: '0.8rem',
                              borderRadius: '3px',
                              background: '#10b981',
                              color: 'white',
                              border: 'none',
                              cursor: 'pointer',
                            }}
                          >
                            + Hinzufügen
                          </button>
                        )}
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p style={{ marginTop: '1.5rem', fontSize: '0.85rem', color: '#666' }}>
        Wählen Sie eine Periode und weisen Sie Personen zu Ausschüssen zu. Wechseln Sie zwischen den
        Rollen (Obmann, Obmann-Stellvertreter, Mitglied) oder entfernen Sie eine Person.
      </p>
    </>
  )
}
