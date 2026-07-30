import axios from 'axios'

// Relativ: Dev nutzt den Vite-Proxy (vite.config.js), Prod läuft same-origin
const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

function isPersonRoute() {
  return window.location.pathname.startsWith('/person')
}

// Passendes Token je Kontext (Admin vs. Person-Portal)
api.interceptors.request.use((config) => {
  if (isPersonRoute()) {
    const personToken = localStorage.getItem('personToken')
    if (personToken) {
      config.headers.Authorization = `Bearer ${personToken}`
    }
  } else {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
  }
  return config
}, (error) => Promise.reject(error))

// 401: Login-Endpoints nicht umleiten; sonst kontextabhängig
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status
    const url = error.config?.url || ''
    const isLoginCall = url.includes('/login') || url.includes('/auth/login') || url.includes('/person/login')

    if (status === 401 && !isLoginCall) {
      if (isPersonRoute()) {
        localStorage.removeItem('personToken')
        if (!window.location.pathname.includes('/person/login')) {
          window.location.href = '/person/login'
        }
      } else {
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        if (!window.location.pathname.includes('/admin/login')) {
          window.location.href = '/admin/login'
        }
      }
    }
    return Promise.reject(error)
  }
)

export default api
