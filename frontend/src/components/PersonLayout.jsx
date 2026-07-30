import AppShell from './AppShell'

const NAV_GROUPS = [
  {
    id: 'main',
    label: 'Mein Bereich',
    items: [
      { id: 'dashboard', label: 'Übersicht', path: '/person/dashboard' },
      { id: 'verfuegbarkeiten', label: 'Verfügbarkeiten', path: '/person/verfuegbarkeiten' },
      { id: 'absences', label: 'Abwesenheiten', path: '/person/absences' },
      { id: 'sitzungen', label: 'Sitzungen', path: '/person/sitzungen' },
      { id: 'committees', label: 'Ausschüsse', path: '/person/committees' },
    ],
  },
  {
    id: 'konto',
    label: 'Konto',
    items: [
      { id: 'profile', label: 'Profil', path: '/person/profile' },
      { id: 'password', label: 'Passwort', path: '/person/password' },
    ],
  },
]

const PAGE_TITLES = {
  dashboard: 'Übersicht',
  verfuegbarkeiten: 'Verfügbarkeiten',
  absences: 'Abwesenheiten',
  sitzungen: 'Sitzungen',
  committees: 'Ausschüsse',
  profile: 'Profil',
  password: 'Passwort',
}

export default function PersonLayout({ activeId, user = {}, onLogout, children }) {
  return (
    <AppShell
      brandSubtitle="Personenportal"
      navGroups={NAV_GROUPS}
      activeId={activeId}
      pageTitle={PAGE_TITLES[activeId] || 'Portal'}
      crumbPrefix="Person"
      user={user}
      userRoleLabel="Person"
      onLogout={onLogout}
    >
      {children}
    </AppShell>
  )
}
