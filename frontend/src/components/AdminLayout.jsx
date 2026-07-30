import AppShell from './AppShell'

const NAV_GROUPS = [
  {
    id: 'start',
    label: 'Übersicht',
    items: [
      { id: 'start', label: 'Start', path: '/admin/panel' },
    ],
  },
  {
    id: 'stammdaten',
    label: 'Stammdaten',
    items: [
      { id: 'personen', label: 'Personen', path: '/admin/personen' },
      { id: 'perioden', label: 'Perioden', path: '/admin/perioden' },
      { id: 'ausschuesse', label: 'Ausschüsse', path: '/admin/ausschuesse' },
      { id: 'mitgliedschaften', label: 'Mitgliedschaften', path: '/admin/mitgliedschaften' },
    ],
  },
  {
    id: 'planung',
    label: 'Planung',
    items: [
      { id: 'termine-berechnung', label: 'Berechnung', path: '/admin/termine-berechnung' },
      { id: 'fixierte-termine', label: 'Fixierte Termine', path: '/admin/fixierte-termine' },
      { id: 'abwesenheiten', label: 'Abwesenheiten', path: '/admin/abwesenheiten' },
      { id: 'verfuegbarkeiten', label: 'Verfügbarkeiten', path: '/admin/verfuegbarkeiten' },
    ],
  },
  {
    id: 'system',
    label: 'System',
    items: [
      { id: 'audit', label: 'Änderungsprotokoll', path: '/admin/audit' },
      { id: 'sitzungsregeln', label: 'Sitzungsregeln', path: '/admin/sitzungsregeln', superAdminOnly: true },
      { id: 'benutzer', label: 'Benutzer', path: '/admin/benutzer', superAdminOnly: true },
      { id: 'obmann-dashboard', label: 'Obmann-Dashboard', path: '/obmann/dashboard', superAdminOnly: true },
    ],
  },
]

const PAGE_TITLES = {
  start: 'Start',
  personen: 'Personen',
  perioden: 'Perioden',
  ausschuesse: 'Ausschüsse',
  mitgliedschaften: 'Mitgliedschaften',
  'termine-berechnung': 'Berechnung',
  'fixierte-termine': 'Fixierte Termine',
  abwesenheiten: 'Abwesenheiten',
  verfuegbarkeiten: 'Verfügbarkeiten',
  audit: 'Änderungsprotokoll',
  sitzungsregeln: 'Sitzungsregeln',
  benutzer: 'Benutzer',
}

export default function AdminLayout({
  activeTab,
  isSuperAdmin = false,
  user = {},
  onLogout,
  children,
}) {
  const navGroups = NAV_GROUPS.map((group) => ({
    ...group,
    items: group.items.filter((item) => !item.superAdminOnly || isSuperAdmin),
  })).filter((group) => group.items.length > 0)

  return (
    <AppShell
      brandSubtitle="Administration"
      navGroups={navGroups}
      activeId={activeTab}
      pageTitle={PAGE_TITLES[activeTab] || 'Admin'}
      crumbPrefix="Admin"
      user={user}
      userRoleLabel={
        isSuperAdmin
          ? 'Super Admin'
          : user.rolle === 'sekretariat'
            ? 'Sekretariat'
            : user.rolle === 'benutzer'
              ? 'Benutzer'
              : undefined
      }
      onLogout={onLogout}
      showPeriodSwitcher
    >
      {children}
    </AppShell>
  )
}
