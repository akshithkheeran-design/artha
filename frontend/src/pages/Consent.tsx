import { Download, Eye, KeyRound, Lock, ShieldOff, Trash2, UserCheck } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import NeedBusiness from '../components/NeedBusiness'
import { Chip, ErrorBox, Field, Modal, PageHead, Panel, Spinner, statusTone } from '../components/ui'
import { api } from '../lib/api'
import { useAuth } from '../lib/auth'
import { useBusiness } from '../lib/business'
import { day, dt, short, title } from '../lib/format'
import { useAction, useApi } from '../lib/hooks'
import type { Business, Consent as C, ConsentCatalog } from '../lib/types'

interface Access { id: number; ts: string; action: string; actor_role: string; actor: string; details: Record<string, unknown> }

function Grant({ b, cat, onDone }: { b: Business; cat: ConsentCatalog; onDone: () => void }) {
  const [type, setType] = useState('agent')
  const orgs = type === 'platform' ? [cat.platform_org] : type === 'agent' ? cat.agents : cat.lenders.filter((l) => l.type === type).map((l) => l.org)
  const [org, setOrg] = useState('')
  const [purpose, setPurpose] = useState('assisted_onboarding')
  const [scopes, setScopes] = useState<string[]>(['profile', 'eligibility'])
  const [days, setDays] = useState(60)
  const { busy, error, run } = useAction()
  const submit = (e: FormEvent) => {
    e.preventDefault()
    run(async () => {
      await api(`/businesses/${b.id}/consents`, { method: 'POST', body: { grantee_type: type, grantee_org: org || orgs[0], purpose, scopes, days } })
      onDone()
    })
  }
  return (
    <form onSubmit={submit} className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Who">
          <select className="input" value={type} onChange={(e) => { setType(e.target.value); setOrg('') }}>
            <option value="platform">ARTHA analysis agents</option><option value="agent">Business correspondent</option>
            <option value="lender">Bank / NBFC</option><option value="dic">DIC / scheme agency</option>
          </select>
        </Field>
        <Field label="Organisation">
          <select className="input" value={org || orgs[0] || ''} onChange={(e) => setOrg(e.target.value)}>
            {orgs.map((o) => <option key={o} value={o}>{o}</option>)}
          </select>
        </Field>
      </div>
      <Field label="Purpose">
        <select className="input" value={purpose} onChange={(e) => setPurpose(e.target.value)}>
          {Object.entries(cat.purposes).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
      </Field>
      <div>
        <div className="label mb-2">What they may see</div>
        <div className="grid gap-1.5 sm:grid-cols-2">
          {Object.entries(cat.scopes).map(([k, v]) => (
            <label key={k} className="flex items-start gap-2 text-sm text-slate-300">
              <input type="checkbox" className="mt-1 accent-cyan-400" checked={scopes.includes(k)}
                onChange={() => setScopes((s) => (s.includes(k) ? s.filter((x) => x !== k) : [...s, k]))} /> {v}
            </label>
          ))}
        </div>
      </div>
      <Field label={`Expires after ${days} days`}><input type="range" min={1} max={365} value={days} onChange={(e) => setDays(Number(e.target.value))} className="w-full accent-cyan-400" /></Field>
      <ErrorBox msg={error} />
      <button className="btn-primary w-full" disabled={busy || !scopes.length}><UserCheck className="h-4 w-4" /> Sign &amp; grant consent</button>
    </form>
  )
}

function Privacy() {
  const { logout } = useAuth()
  const { reload } = useBusiness()
  const [open, setOpen] = useState(false)
  const [pw, setPw] = useState('')
  const [text, setText] = useState('')
  const { busy, error, run } = useAction()
  const exportData = () => run(async () => {
    const d = await api('/me/export')
    const url = URL.createObjectURL(new Blob([JSON.stringify(d, null, 2)], { type: 'application/json' }))
    const a = document.createElement('a')
    a.href = url
    a.download = 'artha-my-data.json'
    a.click()
    setTimeout(() => URL.revokeObjectURL(url), 2000)
  })
  const erase = (e: FormEvent) => {
    e.preventDefault()
    run(async () => { await api('/me/erase', { method: 'POST', body: { password: pw, confirm_text: text } }); await reload(); await logout() })
  }
  return (
    <Panel title="Your data rights" icon={<Lock className="h-3.5 w-3.5" />}>
      <div className="grid gap-3 md:grid-cols-2">
        <div className="rounded-lg border border-edge p-3">
          <div className="text-sm font-semibold text-white">Download everything</div>
          <p className="mt-1 text-xs text-slate-400">A machine-readable copy of your profile, consents and document list.</p>
          <button className="btn-ghost mt-3 text-xs" onClick={exportData} disabled={busy}><Download className="h-3.5 w-3.5" /> Export my data</button>
        </div>
        <div className="rounded-lg border border-neon-red/30 p-3">
          <div className="text-sm font-semibold text-white">Erase my data</div>
          <p className="mt-1 text-xs text-slate-400">Destroys your encryption key (crypto-shredding). Every copy of your data becomes unreadable — permanently.</p>
          <button className="btn-danger mt-3 text-xs" onClick={() => setOpen(true)}><Trash2 className="h-3.5 w-3.5" /> Erase…</button>
        </div>
      </div>
      <ErrorBox msg={error} />
      <Modal open={open} onClose={() => setOpen(false)} title="Erase all my data">
        <form onSubmit={erase} className="space-y-3">
          <p className="text-sm text-slate-300">All consents are revoked, open applications withdrawn and your key destroyed. The audit ledger keeps only non-personal entries. This cannot be undone.</p>
          <Field label='Type "ERASE"'><input className="input" value={text} onChange={(e) => setText(e.target.value)} /></Field>
          <Field label="Password"><input className="input" type="password" value={pw} onChange={(e) => setPw(e.target.value)} autoComplete="current-password" /></Field>
          <ErrorBox msg={error} />
          <button className="btn-danger w-full" disabled={busy || text !== 'ERASE' || !pw}>Permanently erase</button>
        </form>
      </Modal>
    </Panel>
  )
}

function View({ b }: { b: Business }) {
  const { data, error, loading, reload } = useApi<C[]>(`/businesses/${b.id}/consents`, [b.id])
  const { data: cat } = useApi<ConsentCatalog>('/consent/catalog')
  const { data: log, reload: reloadLog } = useApi<Access[]>(`/businesses/${b.id}/access-log`, [b.id])
  const [granting, setGranting] = useState(false)
  const { busy, error: rErr, run } = useAction()
  const revoke = (c: C) => confirm(`Revoke ${c.grantee_org}'s access? They lose access immediately.`) &&
    run(async () => { await api(`/consents/${c.id}/revoke`, { method: 'POST' }); await reload(); await reloadLog() })
  if (loading && !data) return <Spinner />
  if (error) return <ErrorBox msg={error} onRetry={reload} />
  const active = (data ?? []).filter((c) => c.status === 'active')
  return (
    <div className="space-y-5">
      <Panel title={`Consents · ${active.length} active`} icon={<KeyRound className="h-3.5 w-3.5" />}
        right={<button className="btn-primary !py-1.5 text-xs" onClick={() => setGranting(true)}><UserCheck className="h-3.5 w-3.5" /> Grant access</button>}>
        <ErrorBox msg={rErr} />
        <div className="grid gap-3 md:grid-cols-2">
          {(data ?? []).map((c) => (
            <div key={c.id} className={`rounded-lg border p-3 ${c.status === 'active' ? 'border-edge bg-abyss/50' : 'border-edge/50 opacity-60'}`}>
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="text-sm font-semibold text-white">{c.grantee_org}</div>
                  <div className="text-xs text-slate-400">{c.purpose_text}</div>
                </div>
                <Chip tone={statusTone(c.status)}>{c.status}</Chip>
              </div>
              <div className="mt-2 flex flex-wrap gap-1">{c.scopes.map((s) => <Chip key={s} tone="violet">{title(s)}</Chip>)}</div>
              <div className="mt-2 flex items-center justify-between font-mono text-[10px] text-slate-500">
                <span>{c.status === 'revoked' && c.revoked_at ? `revoked ${day(c.revoked_at)}` : `until ${day(c.expires_at)}`} · sig {short(c.signature, 10)}</span>
                {c.status === 'active' && <button className="btn-danger !px-2 !py-0.5 text-[11px]" disabled={busy} onClick={() => revoke(c)}><ShieldOff className="h-3 w-3" /> Revoke</button>}
              </div>
            </div>
          ))}
        </div>
      </Panel>
      <Panel title="Who looked at my data" icon={<Eye className="h-3.5 w-3.5" />}>
        <div className="max-h-80 overflow-y-auto">
          <table className="w-full text-sm">
            <tbody>
              {(log ?? []).map((l) => (
                <tr key={l.id} className="table-row">
                  <td className="py-2 font-mono text-[11px] text-slate-500">{dt(l.ts)}</td>
                  <td className="text-slate-200">{l.actor}</td>
                  <td><Chip tone={l.actor_role === 'entrepreneur' ? 'cyan' : 'magenta'}>{l.actor_role}</Chip></td>
                  <td className="font-mono text-xs text-slate-300">{l.action}{l.details?.scope ? ` · ${String(l.details.scope)}` : ''}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
      <Privacy />
      {cat && <Modal open={granting} onClose={() => setGranting(false)} title="Grant consent"><Grant b={b} cat={cat} onDone={() => { setGranting(false); reload(); reloadLog() }} /></Modal>}
    </div>
  )
}

export default function ConsentPage() {
  return (
    <div>
      <PageHead kicker="Consent Guardian" title="Consent & Privacy">
        Your data is used only with your consent — for a stated purpose, a chosen scope and a fixed time. Revoke any time; access stops instantly.
      </PageHead>
      <NeedBusiness>{(b) => <View b={b} />}</NeedBusiness>
    </div>
  )
}
