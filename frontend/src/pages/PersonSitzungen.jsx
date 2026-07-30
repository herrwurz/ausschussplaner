import { useEffect, useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Calendar, dateFnsLocalizer } from 'react-big-calendar'
import { format, parse, startOfWeek, getDay } from 'date-fns'
import de from 'date-fns/locale/de'
import 'react-big-calendar/lib/css/react-big-calendar.css'
import api from '../api/client'

const locales = { de }
const localizer = dateFnsLocalizer({
  format,
  parse,
  startOfWeek,
  getDay,
  locales,
})

const WOCHENTAG_OFFSET = { MO: 0, DI: 1, MI: 2, DO: 3, FR: 4 }

function mondayOfWeek(refDate) {
  const d = new Date(refDate)
  const day = d.getDay() // 0=So … 6=Sa
  const diff = day === 0 ? -6 : 1 - day
  d.setDate(d.getDate() + diff)
  d.setHours(0, 0, 0, 0)
  return d
}

function vorschlagToEvent(v, ausschussName) {
  const anchor = v.planungs_start_datum
    ? parse(v.planungs_start_datum, 'yyyy-MM-dd', new Date())
    : mondayOfWeek(new Date())
  const offset = WOCHENTAG_OFFSET[(v.wochentag || '').toUpperCase()]
  if (offset === undefined) return null

  const start = new Date(anchor)
  start.setDate(anchor.getDate() + (v.woche - 1) * 7 + offset)
  start.setHours(Math.floor(v.start_minute / 60), v.start_minute % 60, 0, 0)

  const end = new Date(start)
  end.setHours(Math.floor(v.end_minute / 60), v.end_minute % 60, 0, 0)

  return {
    id: v.id,
    title: ausschussName || `Ausschuss #${v.ausschuss_id}`,
    start,
    end,
    resource: {
      ausschuss_name: ausschussName || `Ausschuss #${v.ausschuss_id}`,
      status: v.status,
      quote: v.quote,
      ort: 'Gemeindehaus',
    },
  }
}

export default function PersonSitzungen() {
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedEvent, setSelectedEvent] = useState(null)
  const navigate = useNavigate()

  useEffect(() => {
    const token = localStorage.getItem('personToken')
    if (!token) {
      navigate('/person/login')
      return
    }

    const fetchSitzungen = async () => {
      try {
        setError('')
        const [committeeRes, resultsRes] = await Promise.all([
          api.get('/person/me/committees'),
          api.get('/person/me/sitzungen'),
        ])

        const nameById = Object.fromEntries(
          (committeeRes.data || []).map((c) => [c.ausschuss_id, c.ausschuss_name])
        )

        const calendarEvents = (resultsRes.data || [])
          .map((v) => vorschlagToEvent(v, nameById[v.ausschuss_id]))
          .filter(Boolean)

        setEvents(calendarEvents)
      } catch (err) {
        if (err.response?.status === 401) {
          navigate('/person/login')
          return
        }
        setError('Sitzungen konnten nicht geladen werden')
      } finally {
        setLoading(false)
      }
    }

    fetchSitzungen()
  }, [navigate])

  if (loading) {
    return <div className="container mt-4">Lädt…</div>
  }

  return (
    <div className="container mt-4">
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h2>Meine Sitzungen</h2>
        <Link to="/person/dashboard" className="btn btn-secondary">Zurück</Link>
      </div>

      {error && <div className="alert alert-danger">{error}</div>}

      {events.length === 0 && !error && (
        <div className="alert alert-info">
          Keine fixierten Sitzungstermine für deine Ausschüsse. Der Admin muss Termine zuerst fixieren.
        </div>
      )}

      <div style={{ height: 600 }}>
        <Calendar
          localizer={localizer}
          events={events}
          startAccessor="start"
          endAccessor="end"
          culture="de"
          onSelectEvent={setSelectedEvent}
          messages={{
            today: 'Heute',
            previous: 'Zurück',
            next: 'Weiter',
            month: 'Monat',
            week: 'Woche',
            day: 'Tag',
            agenda: 'Agenda',
            noEventsInRange: 'Keine Termine in diesem Zeitraum',
          }}
        />
      </div>

      {selectedEvent && (
        <div className="card mt-3 p-3">
          <h4>{selectedEvent.resource.ausschuss_name}</h4>
          <p>
            {format(selectedEvent.start, 'EEEE, d. MMMM yyyy HH:mm', { locale: de })}
            {' – '}
            {format(selectedEvent.end, 'HH:mm', { locale: de })}
          </p>
          {selectedEvent.resource.quote != null && (
            <p>Anwesenheitsquote: {selectedEvent.resource.quote}%</p>
          )}
          <button className="btn btn-sm btn-secondary" onClick={() => setSelectedEvent(null)}>
            Schließen
          </button>
        </div>
      )}
    </div>
  )
}
