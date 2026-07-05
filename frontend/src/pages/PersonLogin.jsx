import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api/client'

export default function PersonLogin() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const res = await api.post('/person/login', null, {
        params: { email, password }
      })
      const { access_token } = res.data
      localStorage.setItem('personToken', access_token)
      localStorage.setItem('personEmail', email)
      navigate('/person/dashboard')
    } catch (err) {
      setError(err.response?.data?.detail || 'Login fehlgeschlagen')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <h1 style={styles.title}>AusschussPlaner</h1>
        <h2 style={styles.subtitle}>Person Portal</h2>

        {error && <div style={styles.error}>{error}</div>}

        <form onSubmit={handleSubmit}>
          <div style={styles.formGroup}>
            <label>Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              disabled={loading}
            />
          </div>

          <div style={styles.formGroup}>
            <label>Passwort</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              disabled={loading}
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            style={styles.button}
          >
            {loading ? 'Anmelden...' : 'Anmelden'}
          </button>
        </form>

        <p style={styles.info}>
          Passwort vergessen? Kontaktiere den Administrator.
        </p>
      </div>
    </div>
  )
}

const styles = {
  container: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: '100vh',
    background: 'linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%)',
  },
  card: {
    background: 'white',
    borderRadius: 'var(--radius-lg)',
    boxShadow: 'var(--shadow-xl)',
    padding: 'var(--padding-xl)',
    width: '100%',
    maxWidth: '400px',
  },
  title: {
    textAlign: 'center',
    color: 'var(--color-primary-700)',
    marginBottom: 'var(--margin-sm)',
    fontSize: '2rem',
  },
  subtitle: {
    textAlign: 'center',
    color: '#666',
    marginBottom: '30px',
    fontSize: '1rem',
    fontWeight: '400',
  },
  error: {
    background: '#f8d7da',
    color: '#721c24',
    padding: '12px',
    borderRadius: '4px',
    marginBottom: '20px',
    border: '1px solid #f5c6cb',
  },
  formGroup: {
    marginBottom: '20px',
  },
  button: {
    width: '100%',
    padding: '12px',
    background: '#2563eb',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    fontSize: '1rem',
    cursor: 'pointer',
    transition: 'background 0.3s',
  },
  info: {
    textAlign: 'center',
    marginTop: '20px',
    color: '#999',
    fontSize: '0.9rem',
  },
}
