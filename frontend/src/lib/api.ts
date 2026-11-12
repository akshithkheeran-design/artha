export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

function csrfToken(): string {
  const m = document.cookie.split('; ').find((c) => c.startsWith('artha_csrf='))
  return m ? decodeURIComponent(m.split('=')[1]) : ''
}

type Opts = { method?: string; body?: unknown; form?: FormData; signal?: AbortSignal }

async function request(path: string, { method = 'GET', body, form, signal }: Opts = {}): Promise<Response> {
  const headers: Record<string, string> = {}
  if (method !== 'GET') headers['x-csrf-token'] = csrfToken()
  if (body !== undefined) headers['content-type'] = 'application/json'
  const res = await fetch(`/api${path}`, {
    method,
    headers,
    credentials: 'same-origin',
    cache: 'no-store',
    signal,
    body: form ?? (body !== undefined ? JSON.stringify(body) : undefined),
  })
  if (!res.ok) {
    let msg = res.statusText || 'Request failed'
    try {
      const j = await res.json()
      if (typeof j.detail === 'string') msg = j.detail
    } catch {
      /* non-JSON error */
    }
    if (res.status === 401 && !path.startsWith('/auth/')) window.dispatchEvent(new Event('artha:unauthorized'))
    throw new ApiError(res.status, msg)
  }
  return res
}

let demoCheck: Promise<boolean> | null = null
export function isStaticDemo(): Promise<boolean> {
  if (import.meta.env.VITE_STATIC_DEMO === '1') return Promise.resolve(true)
  return (demoCheck ??= fetch('/api/health', { cache: 'no-store' })
    .then((r) => !(r.ok && (r.headers.get('content-type') ?? '').includes('application/json')))
    .catch(() => true))
}

export async function api<T>(path: string, opts?: Opts): Promise<T> {
  if (await isStaticDemo()) {
    const { demoApi } = await import('./demo')
    if (opts?.form) throw new ApiError(400, 'Uploads need the live ARTHA backend — this site is running as a read-only static demo.')
    return (await demoApi(path, opts?.method ?? 'GET', opts?.body)) as T
  }
  const res = await request(path, opts)
  return (await res.json()) as T
}

export async function downloadBlob(path: string, filename: string) {
  if (await isStaticDemo()) throw new ApiError(400, 'Encrypted document download needs the live ARTHA backend.')
  const res = await request(path)
  const url = URL.createObjectURL(await res.blob())
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.rel = 'noopener'
  a.click()
  setTimeout(() => URL.revokeObjectURL(url), 2000)
}
