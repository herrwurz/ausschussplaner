import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api/client'
import '../styles/Login.css'

export default function Login() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleLogin = async (e) => {
    e.preventDefault()
    try {
      setLoading(true)
      setError('')

      const response = await api.post('/api/auth/login', {
        email,
        password,
      })

      // Speichere Token
      localStorage.setItem('token', response.data.access_token)
      localStorage.setItem('user', JSON.stringify(response.data.user))

      // Redirect basierend auf Rolle
      const { rolle } = response.data.user
      if (rolle === 'super_admin' || rolle === 'benutzer') {
        navigate('/admin')
      } else if (rolle === 'obmann') {
        navigate('/obmann')
      } else {
        navigate('/dashboard')
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Login fehlgeschlagen')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-header">
          <h1>AusschussPlaner</h1>
          <p>Terminverwaltung für Gemeinde-Ausschüsse</p>
        </div>

        {error && <div className="alert alert-danger">{error}</div>}

        <form onSubmit={handleLogin}>
          <div className="form-group">
            <label htmlFor="email">Email:</label>
            <input
              type="email"
              id="email"
              placeholder="admin@ausschussplaner.local"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              disabled={loading}
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Passwort:</label>
            <input
              type="password"
              id="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              disabled={loading}
            />
          </div>

          <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
            {loading ? 'Logging in...' : 'Einloggen'}
          </button>
        </form>

        <div className="login-footer">
          <p className="text-muted">
            Demo-Credentials: admin@ausschussplaner.local / admin123
          </p>
        </div>
      </div>
    </div>
  )
}
