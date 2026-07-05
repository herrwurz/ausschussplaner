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

export default function PersonSitzungen() {
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(true)
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
        const committeeRes = await api.get('/person/me/committees', {
          headers: { Authorization: `Bearer ${token}` }
        })

        const now = new Date()
        const calendarEvents = []

        committeeRes.data.forEach((committee, idx) => {
          for (let i = -4; i <= 8; i++) {
            const date = new Date(now)
            date.setDate(date.getDate() + (i * 7))

            const hour = 10 + (idx % 4)
            const startTime = new Date(date)
            startTime.setHours(hour, 0, 0, 0)

            const endTime = new Date(startTime)
            endTime.setHours(hour + 1, 30, 0, 0)

            calendarEvents.push({
              id: `${committee.ausschuss_id}-${i}`,
              title: committee.ausschuss_name,
              start: startTime,
              end: endTime,
              resource: {
                ausschuss_name: committee.ausschuss_name,
                typ: committee.typ,
                rolle: committee.rolle,
                ort: 'Gemeindehaus',
                beschlussfaehig: idx % 2 === 0,
                beschreibung: `Sitzung des Ausschusses ${committee.ausschuss_name}`,
              },
            })
          }
        })

        setEvents(calendarEvents)
      } catch (err) {
        if (err.response?.status === 401) {
          navigate('/person/login')
        }
      } finally {
        setLoading(false)
      }
    }

    fetchSitzungen()
  }, [navigate])

  const eventStyleGetter = (event) => {
    let backgroundColor = '#2563eb'
    if (event.resource.beschlussfaehig) {
      backgroundColor = '#10b981'
    } else {
      backgroundColor = '#f59e0b'
    }

    return {
      style: {
        backgroundColor,
        borderRadius: '8px',
        opacity: 0.9,
        color: 'white',
        border: '0px',
        display: 'block',
        fontWeight: 'bold',
      },
    }
  }

  if (loading) return <div className="alert alert-info">Lädt...</div>

  return (
    <div className="container-fluid mt-5">
      <Link to="/person/dashboard" className="btn btn-secondary mb-3">
        ← Zurück zum Dashboard
      </Link>
      <h1>Meine möglichen Sitzungstermine</h1>

      <div className="row">
        <div className="col-lg-9">
          <div className="card p-3" style={{ height: '700px' }}>
            <Calendar
              localizer={localizer}
              events={events}
              startAccessor="start"
              endAccessor="end"
              style={{ height: '100%' }}
              onSelectEvent={setSelectedEvent}
              eventPropGetter={eventStyleGetter}
              popup
              views={['month', 'week', 'day']}
              defaultView="month"
            />
          </div>
        </div>

        <div className="col-lg-3">
          <div className="card p-4">
            <h5>Sitzungsdetails</h5>
            {selectedEvent ? (
              <div>
                <hr />
                <p>
                  <strong>Ausschuss:</strong>
                  <br />
                  {selectedEvent.resource.ausschuss_name}
                </p>
                <p>
                  <strong>Typ:</strong>
                  <br />
                  <span className="badge bg-info">{selectedEvent.resource.typ}</span>
                </p>
                <p>
                  <strong>Datum:</strong>
                  <br />
                  {format(selectedEvent.start, 'dd.MM.yyyy', { locale: de })}
                </p>
                <p>
                  <strong>Uhrzeit:</strong>
                  <br />
                  {format(selectedEvent.start, 'HH:mm', { locale: de })} -{' '}
                  {format(selectedEvent.end, 'HH:mm', { locale: de })}
                </p>
                <p>
                  <strong>Ort:</strong>
                  <br />
                  {selectedEvent.resource.ort}
                </p>
                <p>
                  <strong>Rolle:</strong>
                  <br />
                  {selectedEvent.resource.rolle}
                </p>
                <p>
                  <strong>Status:</strong>
                  <br />
                  {selectedEvent.resource.beschlussfaehig ? (
                    <span className="badge bg-success">Beschlussfähig</span>
                  ) : (
                    <span className="badge bg-warning">Nicht beschlussfähig</span>
                  )}
                </p>
                <p>
                  <strong>Beschreibung:</strong>
                  <br />
                  {selectedEvent.resource.beschreibung}
                </p>
              </div>
            ) : (
              <div className="alert alert-info mt-3">
                Klicke auf ein Event, um Details zu sehen
              </div>
            )}
          </div>

          <div className="card p-4 mt-3">
            <h5>Legende</h5>
            <div className="mt-3">
              <p>
                <span
                  style={{
                    display: 'inline-block',
                    width: '12px',
                    height: '12px',
                    backgroundColor: '#10b981',
                    borderRadius: '2px',
                    marginRight: '8px',
                  }}
                ></span>
                Beschlussfähig
              </p>
              <p>
                <span
                  style={{
                    display: 'inline-block',
                    width: '12px',
                    height: '12px',
                    backgroundColor: '#f59e0b',
                    borderRadius: '2px',
                    marginRight: '8px',
                  }}
                ></span>
                Nicht beschlussfähig
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
