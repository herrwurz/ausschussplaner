import { useNavigate } from 'react-router-dom'
import PageHeader from '../components/PageHeader'
import './AdminStartseite.css'

const STEPS = [
  {
    n: 1,
    title: 'Verfügbarkeiten prüfen',
    text: 'Fehlende oder veraltete Zeiten der Mandatare nachziehen.',
    path: '/admin/verfuegbarkeiten',
    cta: 'Zur Übersicht',
  },
  {
    n: 2,
    title: 'Termine berechnen',
    text: 'Vorschläge für Ausschüsse, Stadtrat oder Gemeinderat erzeugen.',
    path: '/admin/termine-berechnung',
    cta: 'Berechnung starten',
  },
  {
    n: 3,
    title: 'Termine fixieren & pflegen',
    text: 'Auswählen, verschieben oder absagen – mit Konfliktprüfung.',
    path: '/admin/fixierte-termine',
    cta: 'Fixierte Termine',
  },
  {
    n: 4,
    title: 'Einladen',
    text: 'Export als PDF oder Kalenderdatei (.ics) für den Versand.',
    path: '/admin/fixierte-termine',
    cta: 'Zum Export',
    hint: 'Automatischer Mailversand folgt später.',
  },
]

export default function AdminStartseite() {
  const navigate = useNavigate()

  return (
    <div className="admin-home">
      <PageHeader
        title="Planungswoche"
        description="Vier Schritte – vom Abgleich der Verfügbarkeiten bis zum Export."
      />

      <div className="admin-home__tiles" role="list">
        {STEPS.map((step) => (
          <button
            key={step.n}
            type="button"
            role="listitem"
            className="admin-home__tile"
            onClick={() => navigate(step.path)}
          >
            <span className="admin-home__tile-num" aria-hidden="true">{step.n}</span>
            <span className="admin-home__tile-title">{step.title}</span>
            <span className="admin-home__tile-text">{step.text}</span>
            {step.hint && <span className="admin-home__tile-hint">{step.hint}</span>}
            <span className="admin-home__tile-cta">{step.cta}</span>
          </button>
        ))}
      </div>
    </div>
  )
}
