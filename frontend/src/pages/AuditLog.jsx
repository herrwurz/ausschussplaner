import { useEffect, useState } from 'react'
import api from '../api/client'
import PageHeader from '../components/PageHeader'

const FILTERS = [
  { value: '', label: 'Alle' },
  { value: 'termin.', label: 'Termine' },
  { value: 'person.', label: 'Personen' },
  { value: 'ausschuss.', label: 'Ausschüsse' },
  { value: 'abwesenheit.', label: 'Abwesenheiten' },
  { value: 'benutzer.', label: 'Benutzer' },
]

function formatWhen(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('de-AT', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return iso
  }
}

export default function AuditLog() {
  const [rows, setRows] = useState([])
  const [filter, setFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        setLoading(true)
        setError('')
        const params = { limit: 200 }
        if (filter) params.action = filter
        const res = await api.get('/audit', { params })
        if (!cancelled) setRows(res.data || [])
      } catch (err) {
        if (!cancelled) setError(err.response?.data?.detail || 'Audit-Log laden fehlgeschlagen')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [filter])

  return (
    <>
      <PageHeader
        title="Änderungsprotokoll"
        description="Wer hat wann Termine, Personen oder Stammdaten geändert."
      />

      <div style={{ marginBottom: '1rem', display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
        {FILTERS.map((f) => (
          <button
            key={f.value || 'all'}
            type="button"
            className={`btn btn-sm ${filter === f.value ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setFilter(f.value)}
          >
            {f.label}
          </button>
        ))}
      </div>

      {error && <div className="alert alert-danger">{error}</div>}
      {loading ? (
        <p>Lädt…</p>
      ) : rows.length === 0 ? (
        <div className="alert alert-info">Noch keine Einträge.</div>
      ) : (
        <div className="table-responsive">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Zeit</th>
                <th>Benutzer</th>
                <th>Aktion</th>
                <th>Detail</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id}>
                  <td style={{ whiteSpace: 'nowrap' }}>{formatWhen(r.created_at)}</td>
                  <td>{r.user_email || '—'}</td>
                  <td>{r.action_label || r.action}</td>
                  <td>{r.detail || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}
