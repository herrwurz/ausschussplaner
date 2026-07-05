import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import './styles/App.css'
import CentralLogin from './pages/CentralLogin'
import PersonLogin from './pages/PersonLogin'
import PersonSetPassword from './pages/PersonSetPassword'
import PersonDashboard from './pages/PersonDashboard'
import PersonProfile from './pages/PersonProfile'
import PersonPassword from './pages/PersonPassword'
import PersonVerfuegbarkeiten from './pages/PersonVerfuegbarkeiten'
import PersonAbsences from './pages/PersonAbsences'
import PersonCommittees from './pages/PersonCommittees'
import PersonSitzungen from './pages/PersonSitzungen'
import TestDashboard from './pages/TestDashboard'
import AdminLogin from './pages/AdminLogin'
import AdminPanel from './pages/AdminPanel'
import ObmannDashboard from './pages/ObmannDashboard'
import ProtectedRoute from './components/ProtectedRoute'

function AppLayout() {
  return (
    <div className="app-layout">
      <main className="content">
        <Routes>
          {/* Central Login - used by both Admin and Person */}
          <Route path="/login" element={<CentralLogin />} />

          {/* Admin Panel - React-based admin UI (nur für Admins) */}
          <Route path="/admin" element={<Navigate to="/admin/login" replace />} />
          <Route path="/admin/login" element={<AdminLogin />} />
          <Route path="/admin/panel" element={
            <ProtectedRoute requiredRole="admin">
              <AdminPanel />
            </ProtectedRoute>
          } />
          <Route path="/admin/personen" element={
            <ProtectedRoute requiredRole="admin">
              <AdminPanel />
            </ProtectedRoute>
          } />
          <Route path="/admin/perioden" element={
            <ProtectedRoute requiredRole="admin">
              <AdminPanel />
            </ProtectedRoute>
          } />
          <Route path="/admin/ausschuesse" element={
            <ProtectedRoute requiredRole="admin">
              <AdminPanel />
            </ProtectedRoute>
          } />

          {/* Obmann Dashboard (nur für Obmänner) */}
          <Route path="/obmann" element={<Navigate to="/obmann/dashboard" replace />} />
          <Route path="/obmann/dashboard" element={
            <ProtectedRoute requiredRole="obmann">
              <ObmannDashboard />
            </ProtectedRoute>
          } />

          {/* Test Dashboard - View all data from API */}
          <Route path="/test" element={<TestDashboard />} />


          {/* Person Portal Routes */}
          <Route path="/person" element={<Navigate to="/person/login" replace />} />
          <Route path="/person/login" element={<PersonLogin />} />
          <Route path="/person/set-password" element={<PersonSetPassword />} />
          <Route path="/person/dashboard" element={<PersonDashboard />} />
          <Route path="/person/profile" element={<PersonProfile />} />
          <Route path="/person/password" element={<PersonPassword />} />
          <Route path="/person/verfuegbarkeiten" element={<PersonVerfuegbarkeiten />} />
          <Route path="/person/absences" element={<PersonAbsences />} />
          <Route path="/person/committees" element={<PersonCommittees />} />
          <Route path="/person/sitzungen" element={<PersonSitzungen />} />

          {/* Default redirect to admin login */}
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
