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

      <ol className="admin-home__steps">
        {STEPS.map((step) => (
          <li key={step.n} className="admin-home__step">
            <div className="admin-home__step-num" aria-hidden="true">{step.n}</div>
            <div className="admin-home__step-body">
              <h2 className="admin-home__step-title">{step.title}</h2>
              <p className="admin-home__step-text">{step.text}</p>
              {step.hint && <p className="admin-home__step-hint">{step.hint}</p>}
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => navigate(step.path)}
              >
                {step.cta}
              </button>
            </div>
          </li>
        ))}
      </ol>
    </div>
  )
}
