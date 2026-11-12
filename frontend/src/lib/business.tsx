import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import { api } from './api'
import { useAuth } from './auth'
import type { Business } from './types'

interface BizState {
  businesses: Business[]
  current: Business | null
  select: (id: number) => void
  reload: () => Promise<void>
  loading: boolean
}

const Ctx = createContext<BizState | null>(null)

export function BusinessProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  const [businesses, setBusinesses] = useState<Business[]>([])
  const [currentId, setCurrentId] = useState<number | null>(() => Number(localStorage.getItem('artha.business')) || null)
  const [loading, setLoading] = useState(true)

  const reload = useCallback(async () => {
    if (!user || !['entrepreneur', 'agent'].includes(user.role)) {
      setBusinesses([])
      setLoading(false)
      return
    }
    setLoading(true)
    try {
      const list = await api<Business[]>('/businesses')
      setBusinesses(list.filter((b) => !b.shredded))
    } finally {
      setLoading(false)
    }
  }, [user])

  useEffect(() => {
    reload()
  }, [reload])

  const current = businesses.find((b) => b.id === currentId) ?? businesses[0] ?? null
  const select = (id: number) => {
    setCurrentId(id)
    localStorage.setItem('artha.business', String(id))
  }
  return <Ctx.Provider value={{ businesses, current, select, reload, loading }}>{children}</Ctx.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useBusiness() {
  const c = useContext(Ctx)
  if (!c) throw new Error('useBusiness outside provider')
  return c
}
