import clsx from 'clsx'
import { AlertTriangle, CheckCircle2, ClipboardList, FilePlus2, Fingerprint, Hourglass, Lock, Send, Undo2 } from 'lucide-react'
import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Bar, Chip, Empty, ErrorBox, Field, Modal, PageHead, Panel, Spinner, Stat, statusTone } from '../components/ui'
import { api } from '../lib/api'
import { useAuth } from '../lib/auth'
import { useBusiness } from '../lib/business'
import { dt, inr, pct, short, title } from '../lib/format'
import { useAction, useApi } from '../lib/hooks'
import type { Application, SchemeResult } from '../lib/types'

interface Meta { reason_codes: Record<string, string>; lenders: { org: string; type: string; kind: string }[]; share_default: string[] }
const SCOPE_LABEL: Record<string, string> = {
  profile: 'Business profile (masked IDs)', cashflow_summary: 'Cash-flow summary', risk_report: 'Credit-readiness report',
  eligibility: 'Eligibility + citations', documents: 'Documents', upi_transactions: 'Raw UPI lines',
}

function DraftForm({ onDone }: { onDone: (a: Application) => void }) {
  const { current } = useBusiness()
  const [params] = useSearchParams()
  const { data: elig } = useApi<SchemeResult[]>(current ? `/businesses/${current.id}/eligibility` : null, [current?.id])
  const { data: meta } = useApi<Meta>('/applications-meta')
  const [scheme, setScheme] = useState(params.get('draft') ?? '')
  const [lender, setLender] = useState('')
  const [amount, setAmount] = useState(Number(params.get('amount')) || 0)
  const { busy, error, run } = useAction()
  const options = (elig ?? []).filter((s) => s.status !== 'ineligible')
  useEffect(() => {
    if (!scheme && options[0]) setScheme(options[0].scheme_id)
  }, [options, scheme])
  useEffect(() => {
    const s = options.find((o) => o.scheme_id === scheme)
    if (s && !params.get('amount')) setAmount(s.indicative_amount ?? current?.loan_need ?? 100000)
  }, [scheme]) // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!meta) return
    const want = scheme === 'pmegp' ? 'dic' : 'lender'
    setLender(meta.lenders.find((l) => l.type === want)?.org ?? meta.lenders[0]?.org ?? '')
  }, [meta, scheme])
  if (!current) return <Empty title="Select a business first" />
  const submit = (e: FormEvent) => {
    e.preventDefault()
    run(async () => onDone(await api<Application>(`/businesses/${current.id}/applications`, { method: 'POST', body: { scheme_id: scheme, lender_org: lender, amount } })))
  }
  return (
    <form onSubmit={submit} className="space-y-4">
      <p className="text-sm text-slate-400">The Application Drafter builds a masked, encrypted file for <b className="text-white">{current.name}</b>. Nothing is sent until the owner approves it.</p>
      <Field label="Scheme">
        <select className="input" value={scheme} onChange={(e) => setScheme(e.target.value)} required>
          {options.map((s) => <option key={s.scheme_id} value={s.scheme_id}>{s.short} — {s.status}</option>)}
        </select>
      </Field>
      <Field label="Lender / agency">
        <select className="input" value={lender} onChange={(e) => setLender(e.target.value)} required>
          {meta?.lenders.map((l) => <option key={l.org} value={l.org}>{l.org} ({l.kind})</option>)}
        </select>
      </Field>
      <Field label="Amount (₹)" hint={inr(amount)}>
        <input className="input" type="number" min={1000} max={100000000} step={1000} value={amount} onChange={(e) => setAmount(Number(e.target.value))} required />
      </Field>
      <ErrorBox msg={error} />
      <button className="btn-primary w-full" disabled={busy || !scheme || !lender}><FilePlus2 className="h-4 w-4" /> Draft application</button>
    </form>
  )
}

function Approve({ a, onDone }: { a: Application; onDone: (a: Application) => void }) {
  const { data: meta } = useApi<Meta>('/applications-meta')
  const [scopes, setScopes] = useState<string[]>(['profile', 'cashflow_summary', 'risk_report', 'eligibility', 'documents'])
  const [days, setDays] = useState(90)
  const [pw, setPw] = useState('')
  const [ok, setOk] = useState(false)
  const { busy, error, run } = useAction()
  const toggle = (s: string) => setScopes((x) => (x.includes(s) ? x.filter((y) => y !== s) : [...x, s]))
  const submit = (e: FormEvent) => {
    e.preventDefault()
    run(async () => onDone(await api<Application>(`/applications/${a.id}/approve`, { method: 'POST', body: { password: pw, confirm: ok, scopes, days } })))
  }
  return (
    <form onSubmit={submit} className="space-y-4 rounded-lg border border-neon-magenta/30 bg-neon-magenta/5 p-4">
      <div className="flex items-center gap-2 font-display text-xs font-bold uppercase tracking-widest text-neon-magenta"><Fingerprint className="h-4 w-4" /> Owner approval</div>
      <div>
        <div className="label mb-2">Share with {a.lender_org} only</div>
        <div className="grid gap-1.5 sm:grid-cols-2">
          {Object.keys(SCOPE_LABEL).filter((s) => s !== 'upi_transactions').map((s) => (
            <label key={s} className="flex items-center gap-2 text-sm text-slate-300">
              <input type="checkbox" className="accent-cyan-400" checked={scopes.includes(s)} onChange={() => toggle(s)} /> {SCOPE_LABEL[s]}
            </label>
          ))}
        </div>
        <p className="mt-1 text-[11px] text-slate-500">Raw UPI lines are never shared with lenders. {meta ? '' : ''}</p>
      </div>
      <Field label={`Consent valid for ${days} days`}>
        <input type="range" min={7} max={365} value={days} onChange={(e) => setDays(Number(e.target.value))} className="w-full accent-cyan-400" />
      </Field>
      <label className="flex items-start gap-2 text-sm text-slate-200">
        <input type="checkbox" className="mt-1 accent-neon-magenta" checked={ok} onChange={(e) => setOk(e.target.checked)} />
        I have reviewed this application. I approve sending it to {a.lender_org} and allow them to see the selected data until consent expires or I revoke it.
      </label>
      <Field label="Confirm with your password">
        <input className="input" type="password" value={pw} onChange={(e) => setPw(e.target.value)} autoComplete="current-password" required />
      </Field>
      <ErrorBox msg={error} />
      <button className="btn-magenta w-full" disabled={busy || !ok || !pw || !scopes.length}><Send className="h-4 w-4" /> Approve &amp; submit</button>
    </form>
  )
}

function Decide({ a, onDone }: { a: Application; onDone: (a: Application) => void }) {
  const { data: meta } = useApi<Meta>('/applications-meta')
  const [action, setAction] = useState('under_review')
  const [reason, setReason] = useState('')
  const [note, setNote] = useState('')
  const { busy, error, run } = useAction()
  const submit = (e: FormEvent) => {
    e.preventDefault()
    run(async () => onDone(await api<Application>(`/applications/${a.id}/decision`, { method: 'POST', body: { action, reason_code: reason || null, note } })))
  }
  return (
    <form onSubmit={submit} className="space-y-3 rounded-lg border border-cyan-400/30 bg-cyan-400/5 p-4">
      <div className="label text-cyan-300">Lender decision</div>
      <div className="grid grid-cols-2 gap-2">
        {['under_review', 'docs_requested', 'sanctioned', 'rejected'].map((s) => (
          <button type="button" key={s} onClick={() => setAction(s)} className={clsx('rounded-lg border px-2 py-1.5 text-xs', action === s ? 'border-cyan-400/60 bg-cyan-400/10 text-cyan-300' : 'border-edge text-slate-400')}>{title(s)}</button>
        ))}
      </div>
      {action === 'rejected' && (
        <Field label="Reason code (required — shared with the owner)">
          <select className="input" value={reason} onChange={(e) => setReason(e.target.value)} required>
            <option value="">Select…</option>
            {meta && Object.entries(meta.reason_codes).map(([k, v]) => <option key={k} value={k}>{k} · {v}</option>)}
          </select>
        </Field>
      )}
      <Field label="Note to owner"><input className="input" value={note} onChange={(e) => setNote(e.target.value)} maxLength={300} /></Field>
      <ErrorBox msg={error} />
      <button className="btn-primary w-full" disabled={busy}>Record decision</button>
    </form>
  )
}

function Detail({ id, onChange }: { id: number; onChange: () => void }) {
  const { user } = useAuth()
  const { data: a, error, loading, setData } = useApi<Application>(`/applications/${id}`, [id])
  const { busy, error: wErr, run } = useAction()
  if (loading && !a) return <Spinner />
  if (error) return <ErrorBox msg={error} />
  if (!a) return null
  const done = (x: Application) => { setData(x); onChange() }
  const snap = a.snapshot
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-mono text-sm text-cyan-300">{a.ref}</span>
        <Chip tone={statusTone(a.status)}>{title(a.status)}</Chip>
        <span className="text-sm text-slate-300">{a.scheme} · {inr(a.amount)} → {a.lender_org}</span>
      </div>
      {a.stall?.stalled && <div className="flex items-center gap-2 rounded-lg border border-neon-amber/40 bg-neon-amber/10 p-3 text-sm text-neon-amber"><AlertTriangle className="h-4 w-4" /> Stalled {a.stall.days_in_status} days (SLA {a.stall.limit}). {a.stall.nudge}</div>}
      {a.decision_reason_text && <div className="rounded-lg border border-neon-red/40 bg-neon-red/10 p-3 text-sm text-neon-red">Reason {a.decision_reason}: {a.decision_reason_text}</div>}
      <div className="grid gap-5 md:grid-cols-2">
        <div>
          <div className="label mb-2">Timeline</div>
          <ol className="space-y-2 border-l border-edge pl-4">
            {a.timeline.map((t, i) => (
              <li key={i} className="relative">
                <span className="absolute -left-[21px] top-1.5 h-2.5 w-2.5 rounded-full bg-cyan-400 shadow-glow" />
                <div className="text-sm text-slate-100">{title(t.status)} <span className="text-xs text-slate-500">· {t.actor}</span></div>
                <div className="font-mono text-[10px] text-slate-500">{dt(t.at)}</div>
                {t.note && <div className="text-xs text-slate-400">{t.note}</div>}
              </li>
            ))}
          </ol>
          {a.snapshot_hash && (
            <div className="mt-4 space-y-1 rounded-lg border border-edge p-3 font-mono text-[10px] text-slate-400">
              <div className="flex items-center gap-1 text-neon-green"><Lock className="h-3 w-3" /> Signed snapshot</div>
              <div>sha256 {short(a.snapshot_hash, 32)}</div>
              <div>ed25519 {short(a.approval_signature, 32)}</div>
            </div>
          )}
        </div>
        <div className="space-y-3">
          {snap ? (
            <>
              <div className="label">What the lender sees · identifiers masked</div>
              <dl className="grid grid-cols-2 gap-x-3 gap-y-1.5 rounded-lg border border-edge p-3 text-xs">
                {Object.entries(snap.applicant ?? {}).slice(0, 12).map(([k, v]) => (
                  <div key={k} className="contents"><dt className="text-slate-500">{title(k)}</dt><dd className="truncate font-mono text-slate-200">{String(v)}</dd></div>
                ))}
              </dl>
              {snap.cashflow && <div className="grid grid-cols-3 gap-2 text-center font-mono text-[11px]">
                <div className="rounded border border-edge p-2"><div className="text-slate-500">Inflow/mo</div>{inr(snap.cashflow.avg_monthly_inflow)}</div>
                <div className="rounded border border-edge p-2"><div className="text-slate-500">EMI cap</div>{inr(snap.cashflow.sustainable_emi)}</div>
                <div className="rounded border border-edge p-2"><div className="text-slate-500">Score</div>{snap.risk?.score ?? '—'} {snap.risk?.band}</div>
              </div>}
              <div>
                <div className="mb-1 flex justify-between text-xs"><span className="label">File completeness</span><span className="font-mono">{pct(a.completeness)}</span></div>
                <Bar value={a.completeness} tone={a.completeness > 0.9 ? 'green' : 'amber'} />
              </div>
            </>
          ) : <div className="rounded-lg border border-edge p-3 text-sm text-slate-400">Snapshot not available (consent revoked or data erased).</div>}
          {user?.role === 'entrepreneur' && a.status === 'awaiting_owner_approval' && <Approve a={a} onDone={done} />}
          {user && ['lender', 'dic'].includes(user.role) && ['submitted', 'under_review', 'docs_requested'].includes(a.status) && <Decide a={a} onDone={done} />}
          {user?.role === 'entrepreneur' && !['sanctioned', 'rejected', 'withdrawn'].includes(a.status) && (
            <button className="btn-danger w-full" disabled={busy} onClick={() => confirm('Withdraw this application? The lender loses access.') &&
              run(async () => done(await api<Application>(`/applications/${a.id}/withdraw`, { method: 'POST' })))}><Undo2 className="h-4 w-4" /> Withdraw</button>
          )}
          <ErrorBox msg={wErr} />
        </div>
      </div>
    </div>
  )
}

export default function Applications() {
  const { user } = useAuth()
  const { current } = useBusiness()
  const [params, setParams] = useSearchParams()
  const { data, error, loading, reload } = useApi<Application[]>('/applications')
  const [openId, setOpenId] = useState<number | null>(null)
  const [drafting, setDrafting] = useState(!!params.get('draft'))
  const [filter, setFilter] = useState('all')
  const isOwnerSide = user?.role === 'entrepreneur' || user?.role === 'agent'
  const list = useMemo(() => (data ?? []).filter((a) => (!isOwnerSide || !current || a.business_id === current.id) && (filter === 'all' || a.status === filter)), [data, filter, current, isOwnerSide])
  const all = (data ?? []).filter((a) => !isOwnerSide || !current || a.business_id === current.id)

  return (
    <div className="space-y-5">
      <PageHead kicker="Application Drafter · tracker" title={isOwnerSide ? 'Applications' : 'Incoming applications'}
        right={isOwnerSide && <button className="btn-primary" onClick={() => setDrafting(true)}><FilePlus2 className="h-4 w-4" /> New application</button>}>
        {isOwnerSide ? 'Agents draft. You approve every file with your password before any lender sees it. Stalled files get nudged automatically.'
          : 'Only owner-approved files appear here, and only the data the owner chose to share. Every view is logged in the owner’s access log.'}
      </PageHead>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Total" value={all.length} icon={<ClipboardList className="h-5 w-5" />} />
        <Stat label="Awaiting owner" value={all.filter((a) => a.status === 'awaiting_owner_approval').length} tone="magenta" icon={<Fingerprint className="h-5 w-5" />} />
        <Stat label="Stalled" value={all.filter((a) => a.stall?.stalled).length} tone="amber" icon={<Hourglass className="h-5 w-5" />} />
        <Stat label="Sanctioned" value={inr(all.filter((a) => a.status === 'sanctioned').reduce((s, a) => s + a.amount, 0))} tone="green" icon={<CheckCircle2 className="h-5 w-5" />} />
      </div>
      <Panel title="Files" icon={<ClipboardList className="h-3.5 w-3.5" />}
        right={<select className="input !w-auto !py-1 text-xs" value={filter} onChange={(e) => setFilter(e.target.value)} aria-label="Filter status">
          {['all', 'awaiting_owner_approval', 'submitted', 'under_review', 'docs_requested', 'sanctioned', 'rejected', 'withdrawn'].map((s) => <option key={s} value={s}>{title(s)}</option>)}
        </select>}>
        {loading && !data ? <Spinner /> : error ? <ErrorBox msg={error} onRetry={reload} /> : list.length === 0 ? <Empty icon={<ClipboardList className="h-10 w-10" />} title="No applications">{isOwnerSide ? 'Run the agents or draft one from the Scheme Navigator.' : 'No owner has approved a file for your organisation yet.'}</Empty> : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-sm">
              <thead><tr className="label text-left"><th className="py-2 font-normal">Ref</th><th className="font-normal">Business</th><th className="font-normal">Scheme</th><th className="font-normal">Amount</th><th className="font-normal">Status</th><th className="font-normal">Complete</th><th className="font-normal">Updated</th></tr></thead>
              <tbody>
                {list.map((a) => (
                  <tr key={a.id} className="table-row cursor-pointer" onClick={() => setOpenId(a.id)}>
                    <td className="py-2.5 font-mono text-xs text-cyan-300">{a.ref}</td>
                    <td><div className="text-slate-100">{a.business_name}</div><div className="text-[11px] text-slate-500">{a.district} · {title(a.sector)}</div></td>
                    <td>{a.scheme}<div className="text-[11px] text-slate-500">{a.lender_org}</div></td>
                    <td className="font-mono">{inr(a.amount)}</td>
                    <td><Chip tone={statusTone(a.status)}>{title(a.status)}</Chip>{a.stall?.stalled && <AlertTriangle className="ml-1 inline h-3.5 w-3.5 text-neon-amber" aria-label="stalled" />}</td>
                    <td className="w-28"><Bar value={a.completeness} tone={a.completeness > 0.9 ? 'green' : 'amber'} /></td>
                    <td className="font-mono text-[11px] text-slate-400">{dt(a.updated_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
      <Modal open={openId !== null} onClose={() => setOpenId(null)} title="Application file" wide>
        {openId !== null && <Detail id={openId} onChange={reload} />}
      </Modal>
      <Modal open={drafting} onClose={() => { setDrafting(false); setParams({}) }} title="Draft application">
        <DraftForm onDone={(a) => { setDrafting(false); setParams({}); reload(); setOpenId(a.id) }} />
      </Modal>
    </div>
  )
}
