import { useCallback, useEffect, useRef, useState } from 'react'
import { api, isStaticDemo } from './api'

export function useApi<T>(path: string | null, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(!!path)
  const seq = useRef(0)

  const load = useCallback(async () => {
    if (!path) return
    const id = ++seq.current
    setLoading(true)
    try {
      const d = await api<T>(path)
      if (id === seq.current) {
        setData(d)
        setError(null)
      }
    } catch (e) {
      if (id === seq.current) setError((e as Error).message)
    } finally {
      if (id === seq.current) setLoading(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, ...deps])

  useEffect(() => {
    load()
  }, [load])

  return { data, error, loading, reload: load, setData }
}

export function useAction() {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const run = useCallback(async <R,>(fn: () => Promise<R>): Promise<R | undefined> => {
    setBusy(true)
    setError(null)
    try {
      return await fn()
    } catch (e) {
      setError((e as Error).message)
      return undefined
    } finally {
      setBusy(false)
    }
  }, [])
  return { busy, error, run, setError }
}

export function useStaticDemo() {
  const [demo, setDemo] = useState(false)
  useEffect(() => {
    isStaticDemo().then(setDemo)
  }, [])
  return demo
}
