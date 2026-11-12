// Static demo mode: used only when no ARTHA backend is reachable (e.g. a frontend-only Netlify deploy).
// Serves a snapshot of the seeded synthetic data and simulates key actions in memory. No real data.
import { ApiError } from './api'

type Err = { __status: number; detail: string }
type Persona = { get: Record<string, unknown>; post: Record<string, unknown> }
type Snap = { password: string; personas: Record<string, Persona> }
type Rec = Record<string, unknown>

const KEY = 'artha.demo.user'
const READONLY = 'This action needs the live ARTHA backend — this site is running as a read-only static demo.'
let snapP: Promise<Snap> | null = null
const load = () => (snapP ??= import('../demo/snapshot.json').then((m) => m.default as unknown as Snap))
const overrides: Record<string, Record<string, unknown>> = {}
const isErr = (v: unknown): v is Err => !!v && typeof v === 'object' && '__status' in (v as Rec)
const now = () => new Date().toISOString()
const hex = (n: number) => Array.from(crypto.getRandomValues(new Uint8Array(n)), (b) => b.toString(16).padStart(2, '0')).join('')

function moneyTrail(q: URLSearchParams, base: Rec) {
  const n = (k: string, d: number) => (q.has(k) ? Number(q.get(k)) : d)
  const files = n('files_per_month', 120), inc_s = n('incomplete_share', 0.45), hrs = n('followup_hours', 6)
  const cost = n('officer_cost_per_hour', 650), drop_s = n('dropout_share', 0.35), loan = n('avg_loan', 300000)
  const nim = n('net_interest_margin', 0.035), acq = n('acquisition_cost', 2500), days = n('extra_days', 38)
  const inc = files * inc_s, staff = inc * hrs * cost, dropouts = inc * drop_s
  const lost = dropouts * loan * nim, sunk = dropouts * acq
  const perFile = hrs * cost + drop_s * (loan * nim + acq)
  const w = (base.with_artha ?? {}) as Rec
  const measured = Number(w.files_observed) ? Number(w.measured_incomplete_share) : inc_s
  const wInc = files * measured
  const wTotal = wInc * hrs * 0.3 * cost + wInc * drop_s * 0.5 * (loan * nim + acq)
  const total = staff + lost + sunk
  const r = Math.round
  return {
    assumptions_note: base.assumptions_note,
    lender: { incomplete_files: r(inc * 10) / 10, staff_cost: r(staff), dropouts: r(dropouts * 10) / 10, lost_margin: r(lost), sunk_acquisition: r(sunk),
      cost_per_incomplete_file: r(perFile), monthly_total: r(total), annual_total: r(total * 12), capital_idle_days: days },
    with_artha: { measured_incomplete_share: Math.round(measured * 1000) / 1000, monthly_total: r(wTotal), monthly_saving: r(total - wTotal),
      docs_requests_observed: w.docs_requests_observed ?? 0, files_observed: w.files_observed ?? 0 },
    borrower: { loan, moneylender_interest: r(loan * 0.3), scheme_interest: r(loan * 0.11), agent_fee: r(loan * 0.125), annual_saving: r(loan * 0.19 + loan * 0.125) },
  }
}

export async function demoApi(path: string, method: string, body: unknown): Promise<unknown> {
  const s = await load()
  await new Promise((r) => setTimeout(r, 150))
  const [p, qs = ''] = path.split('?')
  if (p === '/health') return { ok: true, mode: 'static-demo' }
  if (p === '/auth/login') {
    const { email = '', password = '' } = (body ?? {}) as { email?: string; password?: string }
    const e = email.trim().toLowerCase()
    if (!s.personas[e] || password !== s.password) throw new ApiError(401, 'Invalid email or password. In the static demo, pick a demo persona below.')
    sessionStorage.setItem(KEY, e)
    return s.personas[e].get['/auth/me']
  }
  if (p === '/auth/register') throw new ApiError(400, 'Creating accounts needs the live backend. Use a demo persona.')
  if (p === '/auth/logout') { sessionStorage.removeItem(KEY); return { ok: true } }

  const who = sessionStorage.getItem(KEY) ?? ''
  const P = s.personas[who]
  if (!P) throw new ApiError(401, 'Not signed in')
  const st = (overrides[who] ??= {})
  const get = (k: string): unknown => (k in st ? st[k] : k in P.get ? structuredClone(P.get[k]) : undefined)
  const set = (k: string, v: unknown) => { st[k] = v }
  const ok = (v: unknown) => { if (v === undefined) throw new ApiError(404, READONLY); if (isErr(v)) throw new ApiError(v.__status, v.detail); return v }

  if (method === 'GET') {
    if (p === '/analytics/money-trail') return moneyTrail(new URLSearchParams(qs), (get(p) ?? {}) as Rec)
    return ok(get(path))
  }
  let m: RegExpMatchArray | null
  if ((m = p.match(/^\/businesses\/(\d+)\/(agents\/run|cashflow\/fetch)$/))) return ok(structuredClone(P.post[p]))
  if (p === '/agents/chat') {
    const { business_id, message } = body as { business_id: number; message: string }
    const hit = P.post[`chat:${business_id}:${message}`]
    if (hit) return ok(structuredClone(hit))
    return { reply: 'Static demo: the live agents are offline here, so only the suggested questions have answers. Deploy the backend (see README) for free-form chat.',
      intent: 'demo', agents_invoked: [], citations: [], redacted: [], sanitised_input: message }
  }
  if ((m = p.match(/^\/applications\/(\d+)\/(approve|decision|withdraw)$/))) {
    const k = `/applications/${m[1]}`
    const a = ok(get(k)) as Rec
    const b = (body ?? {}) as Rec
    const actor = String((P.get['/auth/me'] as { user?: Rec })?.user?.display_name ?? 'You')
    if (m[2] === 'approve') {
      if (b.password !== s.password) throw new ApiError(403, 'Password incorrect')
      if (!b.confirm) throw new ApiError(400, 'Explicit confirmation required')
      Object.assign(a, { status: 'submitted', approved_at: now(), snapshot_hash: hex(32), approval_signature: hex(64) })
    } else if (m[2] === 'withdraw') a.status = 'withdrawn'
    else {
      if (b.action === 'rejected' && !b.reason_code) throw new ApiError(400, 'Reason code required')
      Object.assign(a, { status: b.action, decision_reason: b.reason_code ?? null,
        decision_reason_text: b.reason_code ? ((get('/applications-meta') as Rec)?.reason_codes as Rec)?.[String(b.reason_code)] ?? null : null })
    }
    a.updated_at = now()
    a.timeline = [...((a.timeline as Rec[]) ?? []), { status: a.status, at: now(), actor, note: String(b.note ?? '') }]
    a.stall = { stalled: false }
    set(k, a)
    const list = get('/applications') as Rec[] | undefined
    if (Array.isArray(list)) set('/applications', list.map((x) => (x.id === a.id ? { ...x, status: a.status, updated_at: a.updated_at, stall: a.stall } : x)))
    return a
  }
  if ((m = p.match(/^\/consents\/(\d+)\/revoke$/))) {
    const id = Number(m[1])
    for (const k of [...Object.keys(P.get), ...Object.keys(st)].filter((x) => /^\/businesses\/\d+\/consents$/.test(x))) {
      const list = get(k) as Rec[]
      const c = Array.isArray(list) && list.find((x) => x.id === id)
      if (c) { Object.assign(c, { status: 'revoked', revoked_at: now() }); set(k, list); return c }
    }
    throw new ApiError(404, 'Consent not found')
  }
  if ((m = p.match(/^\/businesses\/(\d+)\/consents$/))) {
    const b = body as Rec
    const cat = (get('/consent/catalog') ?? {}) as { purposes?: Rec }
    const list = (ok(get(p)) as Rec[]) ?? []
    const c = { id: Date.now(), business_id: Number(m[1]), grantee_type: b.grantee_type, grantee_org: b.grantee_org, purpose: b.purpose,
      purpose_text: cat.purposes?.[String(b.purpose)] ?? b.purpose, scopes: b.scopes, status: 'active', granted_at: now(),
      expires_at: new Date(Date.now() + Number(b.days ?? 30) * 864e5).toISOString(), revoked_at: null, signature: hex(64) }
    set(p, [c, ...list])
    return c
  }
  if (p === '/field/interviews') return { id: Date.now(), redacted: [] }
  throw new ApiError(400, READONLY)
}
