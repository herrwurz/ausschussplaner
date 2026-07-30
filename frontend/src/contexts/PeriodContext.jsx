import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import api from '../api/client'

const STORAGE_KEY = 'selectedPeriodeId'

const PeriodContext = createContext({
  perioden: [],
  selectedPeriodeId: null,
  selectedPeriode: null,
  setSelectedPeriodeId: () => {},
  loading: false,
  refreshPerioden: async () => {},
})

function pickDefaultId(perioden, storedId) {
  if (!perioden?.length) return null
  const stored = perioden.find((p) => String(p.id) === String(storedId))
  if (stored) return stored.id
  const aktiv = perioden.find((p) => p.aktiv)
  return (aktiv || perioden[0]).id
}

function canFetchPerioden() {
  if (typeof window === 'undefined') return false
  if (window.location.pathname.startsWith('/person')) return false
  return Boolean(localStorage.getItem('token'))
}

export function PeriodProvider({ children, enabled = true }) {
  const [perioden, setPerioden] = useState([])
  const [selectedPeriodeId, setSelectedPeriodeIdState] = useState(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      return raw ? Number(raw) || raw : null
    } catch {
      return null
    }
  })
  const [loading, setLoading] = useState(Boolean(enabled))

  const refreshPerioden = useCallback(async () => {
    if (!enabled || !canFetchPerioden()) {
      setLoading(false)
      return
    }
    try {
      setLoading(true)
      const res = await api.get('/perioden')
      const list = res.data || []
      setPerioden(list)
      setSelectedPeriodeIdState((current) => {
        const next = pickDefaultId(list, current ?? localStorage.getItem(STORAGE_KEY))
        if (next != null) localStorage.setItem(STORAGE_KEY, String(next))
        return next
      })
    } catch {
      setPerioden([])
    } finally {
      setLoading(false)
    }
  }, [enabled])

  useEffect(() => {
    refreshPerioden()
  }, [refreshPerioden])

  const setSelectedPeriodeId = useCallback((id) => {
    const next = id === '' || id == null ? null : (Number(id) || id)
    setSelectedPeriodeIdState(next)
    if (next != null) localStorage.setItem(STORAGE_KEY, String(next))
    else localStorage.removeItem(STORAGE_KEY)
  }, [])

  const selectedPeriode = useMemo(
    () => perioden.find((p) => String(p.id) === String(selectedPeriodeId)) || null,
    [perioden, selectedPeriodeId],
  )

  const value = useMemo(
    () => ({
      perioden,
      selectedPeriodeId,
      selectedPeriode,
      setSelectedPeriodeId,
      loading,
      refreshPerioden,
    }),
    [perioden, selectedPeriodeId, selectedPeriode, setSelectedPeriodeId, loading, refreshPerioden],
  )

  return (
    <PeriodContext.Provider value={value}>
      {children}
    </PeriodContext.Provider>
  )
}

export function usePeriod() {
  return useContext(PeriodContext)
}
