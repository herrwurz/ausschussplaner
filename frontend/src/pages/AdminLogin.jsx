import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api/client'
import '../styles/Login.css'

export default function AdminLogin() {
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

      const response = await api.post('/auth/login', {
        email,
        password,
      })

      console.log('AdminLogin: Login successful', {
        email: response.data.user.email,
        rolle: response.data.user.rolle
      })

      // Speichere Token und User
      localStorage.setItem('token', response.data.access_token)
      localStorage.setItem('user', JSON.stringify(response.data.user))
      localStorage.setItem('adminAuth', 'true')  // Legacy compat

      console.log('AdminLogin: Token saved, navigating to /admin/panel')

      // Redirect je nach Rolle
      const rolle = response.data.user.rolle
      if (rolle === 'obmann') {
        navigate('/obmann/dashboard')
      } else {
        navigate('/admin/panel')
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
          <p>Admin-Zugang</p>
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
            Demo: admin@ausschussplaner.local / admin123
          </p>
        </div>
      </div>
    </div>
  )
}
