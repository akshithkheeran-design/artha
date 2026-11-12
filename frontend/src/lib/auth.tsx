import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import { api } from './api'
import type { User } from './types'

interface AuthState {
  user: User | null
  ready: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, display_name: string) => Promise<void>
  logout: () => Promise<void>
}

const Ctx = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    api<{ user: User }>('/auth/me')
      .then((r) => setUser(r.user))
      .catch(() => setUser(null))
      .finally(() => setReady(true))
    const onUnauth = () => setUser(null)
    window.addEventListener('artha:unauthorized', onUnauth)
    return () => window.removeEventListener('artha:unauthorized', onUnauth)
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const r = await api<{ user: User }>('/auth/login', { method: 'POST', body: { email, password } })
    setUser(r.user)
  }, [])
  const register = useCallback(async (email: string, password: string, display_name: string) => {
    const r = await api<{ user: User }>('/auth/register', { method: 'POST', body: { email, password, display_name } })
    setUser(r.user)
  }, [])
  const logout = useCallback(async () => {
    try {
      await api('/auth/logout', { method: 'POST' })
    } finally {
      setUser(null)
      localStorage.removeItem('artha.business')
    }
  }, [])

  return <Ctx.Provider value={{ user, ready, login, register, logout }}>{children}</Ctx.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const c = useContext(Ctx)
  if (!c) throw new Error('useAuth outside provider')
  return c
}
