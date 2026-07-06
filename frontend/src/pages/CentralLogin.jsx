import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import '../styles/Login.css'

export default function CentralLogin() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const navigate = useNavigate()

  const handleLogin = async (e) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)

    try {
      // Demo: Auto-login basierend auf Email-Präfix
      if (email === 'admin' || email === 'admin123') {
        // Admin Login
        localStorage.setItem('userType', 'admin')
        localStorage.setItem('adminId', '1')
        localStorage.setItem('username', 'admin')
        window.location.href = '/admin/login'
        return
      }

      // Person Login - akzeptiere beliebiges Email mit test-Passwort
      if (password === 'test123' || password === 'admin123') {
        const token = 'demo-token-' + Math.random().toString(36).substr(2, 9)
        localStorage.setItem('userType', 'person')
        localStorage.setItem('token', token)
        localStorage.setItem('user_id', '1')
        localStorage.setItem('name', email.split('@')[0])
        localStorage.setItem('email', email)
        navigate('/person/dashboard')
        return
      }

      setError('Demo-Login: Nutze "admin" als Email oder beliebige Email mit Passwort "test123"')
    } catch (err) {
      setError('Fehler. Versuch es erneut.')
      console.error(err)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="login-page">
      <div className="login-container">
        <div className="login-card">
          <div className="login-header">
            <h1>🏛️ Ausschussplaner</h1>
            <p>Verwaltungsportal</p>
          </div>

          {error && (
            <div className="error-message">
              {error}
            </div>
          )}

          <form onSubmit={handleLogin}>
            <div className="form-group">
              <label>Email oder Benutzername</label>
              <input
                type="text"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@example.com oder admin"
                required
                disabled={isLoading}
              />
            </div>

            <div className="form-group">
              <label>Passwort</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                disabled={isLoading}
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="login-button"
            >
              {isLoading ? 'Wird angemeldet...' : 'Anmelden'}
            </button>
          </form>

          <div className="login-footer">
            <p>Demo-Zugänge:</p>
            <small>Admin: Email="admin" + beliebiges Passwort</small>
            <small>Person: beliebige Email + Passwort="test123"</small>
          </div>
        </div>
      </div>
    </div>
  )
}
