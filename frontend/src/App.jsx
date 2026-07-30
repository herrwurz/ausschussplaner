import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import './styles/App.css'
import './styles/AdminPanel.css'
import { PeriodProvider } from './contexts/PeriodContext'
import PersonLogin from './pages/PersonLogin'
import PersonSetPassword from './pages/PersonSetPassword'
import PersonDashboard from './pages/PersonDashboard'
import PersonProfile from './pages/PersonProfile'
import PersonPassword from './pages/PersonPassword'
import PersonVerfuegbarkeiten from './pages/PersonVerfuegbarkeiten'
import PersonAbsences from './pages/PersonAbsences'
import PersonCommittees from './pages/PersonCommittees'
import PersonSitzungen from './pages/PersonSitzungen'
import AdminLogin from './pages/AdminLogin'
import AdminPanel from './pages/AdminPanel'
import ObmannDashboard from './pages/ObmannDashboard'
import ProtectedRoute from './components/ProtectedRoute'
import PersonPortalLayout from './components/PersonPortalLayout'

function AdminPanelRoute() {
  return (
    <ProtectedRoute requiredRole="admin">
      <PeriodProvider>
        <AdminPanel />
      </PeriodProvider>
    </ProtectedRoute>
  )
}

function AppLayout() {
  return (
    <div className="app-layout">
      <main className="content">
        <Routes>
          <Route path="/admin" element={<Navigate to="/admin/login" replace />} />
          <Route path="/admin/login" element={<AdminLogin />} />
          <Route path="/admin/panel" element={<AdminPanelRoute />} />
          <Route path="/admin/benutzer" element={<AdminPanelRoute />} />
          <Route path="/admin/personen" element={<AdminPanelRoute />} />
          <Route path="/admin/perioden" element={<AdminPanelRoute />} />
          <Route path="/admin/ausschuesse" element={<AdminPanelRoute />} />
          <Route path="/admin/mitgliedschaften" element={<AdminPanelRoute />} />
          <Route path="/admin/termine-berechnung" element={<AdminPanelRoute />} />
          <Route path="/admin/fixierte-termine" element={<AdminPanelRoute />} />
          <Route path="/admin/abwesenheiten" element={<AdminPanelRoute />} />
          <Route path="/admin/verfuegbarkeiten" element={<AdminPanelRoute />} />
          <Route path="/admin/sitzungsregeln" element={<AdminPanelRoute />} />

          <Route path="/obmann" element={<Navigate to="/obmann/dashboard" replace />} />
          <Route path="/obmann/dashboard" element={
            <ProtectedRoute requiredRole="obmann">
              <ObmannDashboard />
            </ProtectedRoute>
          } />

          <Route path="/person" element={<Navigate to="/person/login" replace />} />
          <Route path="/person/login" element={<PersonLogin />} />
          <Route path="/person/set-password" element={<PersonSetPassword />} />
          <Route element={<PersonPortalLayout />}>
            <Route path="/person/dashboard" element={<PersonDashboard />} />
            <Route path="/person/profile" element={<PersonProfile />} />
            <Route path="/person/password" element={<PersonPassword />} />
            <Route path="/person/verfuegbarkeiten" element={<PersonVerfuegbarkeiten />} />
            <Route path="/person/absences" element={<PersonAbsences />} />
            <Route path="/person/committees" element={<PersonCommittees />} />
            <Route path="/person/sitzungen" element={<PersonSitzungen />} />
          </Route>

          <Route path="/login" element={<Navigate to="/admin/login" replace />} />
          <Route path="/" element={<Navigate to="/admin/login" replace />} />
        </Routes>
      </main>
    </div>
  )
}

export default function App() {
  return (
    <Router>
      <AppLayout />
    </Router>
  )
}
