import { useEffect, useState } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import api from '../api/client'

export default function PersonSetPassword() {
  const [searchParams] = useSearchParams()
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const navigate = useNavigate()

  const token = searchParams.get('token')

  useEffect(() => {
    if (!token) {
      setError('Kein Token gefunden. Der Link ist ungültig.')
    }
  }, [token])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')

    if (password !== confirmPassword) {
      setError('Passwörter stimmen nicht überein')
      return
    }

    if (password.length < 8) {
      setError('Passwort muss mindestens 8 Zeichen lang sein')
      return
    }

    setLoading(true)
    try {
      const response = await api.post('/person/set-password', null, {
        params: {
          token,
          new_password: password,
        },
      })
      setSuccess(true)
      setTimeout(() => navigate('/person/login'), 2000)
    } catch (err) {
      if (err.response?.status === 404) {
        setError('Token ist ungültig oder abgelaufen')
      } else if (err.response?.status === 410) {
        setError('Token ist abgelaufen (48h)')
      } else {
        setError(err.response?.data?.detail || 'Fehler beim Passwort setzen')
      }
    } finally {
      setLoading(false)
    }
  }

  if (!token) {
    return (
      <div className="container mt-5">
        <div className="col-md-6 mx-auto">
          <div className="alert alert-danger">{error}</div>
          <a href="/person/login" className="btn btn-secondary">Zurück zum Login</a>
        </div>
      </div>
    )
  }

  if (success) {
    return (
      <div className="container mt-5">
        <div className="col-md-6 mx-auto">
          <div className="alert alert-success">
            <h4>✅ Passwort gesetzt!</h4>
            <p>Du wirst zum Login weitergeleitet...</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="container mt-5">
      <div className="col-md-6 mx-auto">
        <h1>Passwort setzen</h1>

        {error && <div className="alert alert-danger">{error}</div>}

        <form onSubmit={handleSubmit} className="card p-4">
          <div className="mb-3">
            <label className="form-label">Passwort</label>
            <input
              type="password"
              className="form-control"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength="8"
            />
            <small className="form-text text-muted">Mindestens 8 Zeichen</small>
          </div>

          <div className="mb-3">
            <label className="form-label">Passwort wiederholen</label>
            <input
              type="password"
              className="form-control"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              minLength="8"
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary w-100"
            disabled={loading}
          >
            {loading ? 'Speichert...' : 'Passwort setzen'}
          </button>
        </form>

        <p className="mt-3 text-center text-muted">
          <small>Der Link ist 48 Stunden lang gültig.</small>
        </p>
      </div>
    </div>
  )
}
