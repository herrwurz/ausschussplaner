import AppShell from './AppShell'

export default function ObmannLayout({
  activeId = 'dashboard',
  user = {},
  onLogout,
  showAdminLink = false,
  children,
}) {
  const navGroups = [
    {
      id: 'main',
      label: 'Obmann',
      items: [
        { id: 'dashboard', label: 'Dashboard', path: '/obmann/dashboard' },
        ...(showAdminLink
          ? [{ id: 'admin', label: '← Admin-Panel', path: '/admin/panel' }]
          : []),
      ],
    },
  ]

  return (
    <AppShell
      brandSubtitle="Obmann"
      navGroups={navGroups}
      activeId={activeId}
      pageTitle="Dashboard"
      crumbPrefix="Obmann"
      user={user}
      userRoleLabel={user.rolle === 'super_admin' ? 'Super Admin' : 'Obmann'}
      onLogout={onLogout}
      showPeriodSwitcher={false}
    >
      {children}
    </AppShell>
  )
}
