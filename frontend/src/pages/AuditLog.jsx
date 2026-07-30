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
    const d = new Date(iso)
    if (Number.isNaN(d.getTime())) return String(iso)
    return d.toLocaleString('de-AT', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return String(iso)
  }
}

function formatApiError(err) {
  const detail = err?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail.map((e) => e?.msg || JSON.stringify(e)).join('; ')
  }
  if (detail && typeof detail === 'object') return JSON.stringify(detail)
  return err?.message || 'Audit-Log laden fehlgeschlagen'
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
        const data = Array.isArray(res.data) ? res.data : []
        if (!cancelled) setRows(data)
      } catch (err) {
        if (!cancelled) {
          setRows([])
          setError(formatApiError(err))
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [filter])

  return (
    <div className="audit-log">
      <PageHeader
        title="Änderungsprotokoll"
        description="Wer hat wann Termine, Personen oder Stammdaten geändert."
      />

      <div className="audit-log__filters">
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

      {error && (
        <div className="alert alert-danger" role="alert">
          {error}
        </div>
      )}

      {loading && <p className="audit-log__status">Lädt…</p>}

      {!loading && !error && rows.length === 0 && (
        <div className="alert alert-info" role="status">
          Noch keine Einträge. Sobald Termine fixiert oder Personen geändert werden, erscheinen sie hier.
        </div>
      )}

      {!loading && rows.length > 0 && (
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
                <tr key={r.id ?? `${r.action}-${r.created_at}`}>
                  <td style={{ whiteSpace: 'nowrap' }}>{formatWhen(r.created_at)}</td>
                  <td>{r.user_email || '—'}</td>
                  <td>{r.action_label || r.action || '—'}</td>
                  <td>{r.detail || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
