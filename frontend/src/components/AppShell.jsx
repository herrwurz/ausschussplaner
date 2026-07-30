import { useEffect, useState } from 'react'
import { NavLink } from 'react-router-dom'
import { usePeriod } from '../contexts/PeriodContext'
import '../styles/AppShell.css'

/**
 * Gemeinsame App-Shell: Sidebar + Topbar (+ optional Perioden-Switcher).
 */
export default function AppShell({
  brandTitle = 'AusschussPlaner',
  brandSubtitle = 'Portal',
  navGroups = [],
  activeId,
  pageTitle,
  crumbPrefix,
  user = {},
  userRoleLabel,
  onLogout,
  showPeriodSwitcher = false,
  children,
}) {
  const [mobileOpen, setMobileOpen] = useState(false)
  const { perioden, selectedPeriodeId, setSelectedPeriodeId, loading: periodenLoading } = usePeriod()

  useEffect(() => {
    setMobileOpen(false)
  }, [activeId])

  useEffect(() => {
    if (!mobileOpen) return undefined
    const onKey = (e) => {
      if (e.key === 'Escape') setMobileOpen(false)
    }
    document.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
    }
  }, [mobileOpen])

  const displayName = [user.vorname, user.nachname].filter(Boolean).join(' ')
    || user.name
    || user.email
    || brandSubtitle

  return (
    <div className={`app-shell${mobileOpen ? ' app-shell--nav-open' : ''}`}>
      <aside className="app-shell__sidebar" aria-label="Hauptnavigation">
        <div className="app-shell__brand">
          <span className="app-shell__mark" aria-hidden="true" />
          <div>
            <div className="app-shell__brand-title">{brandTitle}</div>
            <div className="app-shell__brand-subtitle">{brandSubtitle}</div>
          </div>
        </div>

        <nav className="app-shell__nav">
          {navGroups.map((group) => {
            if (!group.items?.length) return null
            return (
              <div key={group.id} className="app-shell-nav-group">
                {group.label && (
                  <div className="app-shell-nav-group__label">{group.label}</div>
                )}
                <ul className="app-shell-nav-group__list">
                  {group.items.map((item) => (
                    <li key={item.id}>
                      <NavLink
                        to={item.path}
                        end={item.end}
                        className={({ isActive }) =>
                          `app-shell-nav-link${isActive || activeId === item.id ? ' active' : ''}`
                        }
                        onClick={() => setMobileOpen(false)}
                      >
                        {item.label}
                      </NavLink>
                    </li>
                  ))}
                </ul>
              </div>
            )
          })}
        </nav>
      </aside>

      {mobileOpen && (
        <button
          type="button"
          className="app-shell__backdrop"
          aria-label="Navigation schließen"
          onClick={() => setMobileOpen(false)}
        />
      )}

      <div className="app-shell__main">
        <header className="app-shell__topbar">
          <div className="app-shell__topbar-left">
            <button
              type="button"
              className="app-shell__menu"
              aria-label="Navigation öffnen"
              aria-expanded={mobileOpen}
              onClick={() => setMobileOpen((open) => !open)}
            >
              <span />
              <span />
              <span />
            </button>
            <div>
              <h1 className="app-shell__title">{pageTitle}</h1>
              {crumbPrefix && (
                <p className="app-shell__crumb">{crumbPrefix} · {pageTitle}</p>
              )}
            </div>
          </div>

          <div className="app-shell__topbar-right">
            {showPeriodSwitcher && (
              <label className="app-shell__periode">
                <span className="app-shell__periode-label">Periode</span>
                <select
                  value={selectedPeriodeId ?? ''}
                  onChange={(e) => setSelectedPeriodeId(e.target.value)}
                  disabled={periodenLoading || perioden.length === 0}
                  aria-label="Gemeinderatsperiode wählen"
                >
                  {perioden.length === 0 && (
                    <option value="">Keine Periode</option>
                  )}
                  {perioden.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} ({p.start_jahr}–{p.end_jahr})
                    </option>
                  ))}
                </select>
              </label>
            )}

            <div className="app-shell__user" title={user.email || ''}>
              <span className="app-shell__avatar" aria-hidden="true">
                {(displayName[0] || '?').toUpperCase()}
              </span>
              <span className="app-shell__user-meta">
                <span className="app-shell__user-name">{displayName}</span>
                {userRoleLabel && (
                  <span className="app-shell__user-role">{userRoleLabel}</span>
                )}
              </span>
            </div>
            <button
              type="button"
              className="btn btn-secondary app-shell__logout"
              onClick={onLogout}
            >
              Logout
            </button>
          </div>
        </header>

        <div className="app-shell__page">
          {children}
        </div>
      </div>
    </div>
  )
}
