import { CloudDownload, FileUp, Info, Lock, TrendingUp, Wallet } from 'lucide-react'
import { useRef, useState } from 'react'
import { Area, AreaChart, Bar as RBar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import NeedBusiness from '../components/NeedBusiness'
import { Chip, Empty, ErrorBox, PageHead, Panel, Spinner, Stat, chartTheme } from '../components/ui'
import { api } from '../lib/api'
import { dt, inr, inrFull, short, title } from '../lib/format'
import { useAction, useApi } from '../lib/hooks'
import type { Business, Cashflow as CF } from '../lib/types'

const SAMPLE = 'date,amount,type,counterparty,note\n2026-01-03,1450,CR,customer-a@upi,blouse stitching\n2026-01-04,5200,DR,supplier@upi,fabric\n'

function Ingest({ b, onDone, compact }: { b: Business; onDone: () => void; compact?: boolean }) {
  const file = useRef<HTMLInputElement>(null)
  const { busy, error, run } = useAction()
  const [msg, setMsg] = useState<string | null>(null)
  const upload = (f: File) => run(async () => {
    const form = new FormData()
    form.append('file', f)
    const r = await api<{ rows: number }>(`/businesses/${b.id}/cashflow/upload`, { method: 'POST', form })
    setMsg(`${r.rows} transactions encrypted and analysed.`)
    onDone()
  })
  const fetchAA = () => run(async () => {
    const r = await api<{ rows: number }>(`/businesses/${b.id}/cashflow/fetch`, { method: 'POST' })
    setMsg(`${r.rows} transactions pulled via Account Aggregator (simulated) and encrypted.`)
    onDone()
  })
  return (
    <div className={compact ? 'flex flex-wrap items-center gap-2' : 'space-y-3'}>
      <div className="flex flex-wrap gap-2">
        <button className="btn-primary" disabled={busy} onClick={fetchAA}><CloudDownload className="h-4 w-4" /> Fetch via Account Aggregator</button>
        <button className="btn-ghost" disabled={busy} onClick={() => file.current?.click()}><FileUp className="h-4 w-4" /> Upload UPI CSV</button>
        <input ref={file} type="file" accept=".csv,text/csv" className="hidden"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) upload(f); e.target.value = '' }} />
      </div>
      {!compact && (
        <p className="text-xs text-slate-500">CSV columns: <span className="font-mono">date, amount, type (CR/DR), counterparty, note</span> — max 2 MB.
          Counterparty UPI IDs are replaced by keyed hashes before storage. <a className="link" download="upi_sample.csv"
            href={`data:text/csv;charset=utf-8,${encodeURIComponent(SAMPLE)}`}>Sample CSV</a></p>
      )}
      <ErrorBox msg={error} />
      {msg && <div className="text-xs text-neon-green">{msg}</div>}
    </div>
  )
}

function View({ b }: { b: Business }) {
  const { data, error, loading, reload } = useApi<CF>(`/businesses/${b.id}/cashflow`, [b.id])
  if (loading && !data) return <Spinner label="Cash-flow Analyst reading statement" />
  if (error) return (
    <Panel><ErrorBox msg={error} onRetry={reload} />
      <p className="mt-3 text-sm text-slate-400">If you revoked the cash-flow consent, grant it again in <a className="link" href="/consent">Consent &amp; Privacy</a>.</p></Panel>)
  if (!data) return null
  if (!data.available)
    return (
      <Panel>
        <Empty icon={<Wallet className="h-10 w-10" />} title="No cash-flow data yet">
          Banks can’t see your steady UPI sales because they don’t show up as ITRs. Link your statement — with your consent — and ARTHA
          turns it into a credit file.
        </Empty>
        <div className="flex justify-center"><Ingest b={b} onDone={reload} /></div>
      </Panel>
    )
  const s = data.summary
  const f = data.features
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Avg monthly inflow" value={inr(s.avg_monthly_inflow)} sub={`${s.transactions} UPI lines · ${s.months} months`} />
        <Stat label="Sustainable EMI" value={inr(s.sustainable_emi)} sub={`Stressed surplus ${inr(s.stressed_monthly_surplus)}/mo`} tone="green" />
        <Stat label="Supportable loan (36m)" value={inr(s.suggested_loan_36m)} sub={`Need ${inr(b.loan_need)}`} tone="magenta" />
        <Stat label="Saving vs moneylender" value={inr(s.annual_interest_saving)} sub={s.informal_monthly_repayment ? `${inrFull(s.informal_monthly_repayment)}/mo informal repayments detected` : 'No informal debt detected'} tone={s.informal_monthly_repayment ? 'amber' : 'green'} />
      </div>
      <div className="grid gap-5 xl:grid-cols-[1.7fr_1fr]">
        <Panel title="Monthly UPI inflow vs outflow" icon={<TrendingUp className="h-3.5 w-3.5" />}>
          <div className="h-72">
            <ResponsiveContainer>
              <AreaChart data={data.monthly}>
                <defs>
                  <linearGradient id="in" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#22e3f5" stopOpacity={0.4} /><stop offset="1" stopColor="#22e3f5" stopOpacity={0} /></linearGradient>
                  <linearGradient id="out" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#ff3df2" stopOpacity={0.3} /><stop offset="1" stopColor="#ff3df2" stopOpacity={0} /></linearGradient>
                </defs>
                <CartesianGrid stroke={chartTheme.grid} vertical={false} />
                <XAxis dataKey="month" tick={chartTheme.axis} axisLine={false} tickLine={false} />
                <YAxis tick={chartTheme.axis} axisLine={false} tickLine={false} tickFormatter={(v) => inr(v)} width={64} />
                <Tooltip contentStyle={chartTheme.tooltip} formatter={(v: number) => inrFull(v)} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Area type="monotone" dataKey="inflow" name="Inflow" stroke="#22e3f5" fill="url(#in)" strokeWidth={2} />
                <Area type="monotone" dataKey="outflow" name="Outflow" stroke="#ff3df2" fill="url(#out)" strokeWidth={2} />
                <Area type="monotone" dataKey="obligations" name="Loan repayments" stroke="#ffc93d" fill="none" strokeDasharray="4 3" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Panel>
        <Panel title="Agent insights" icon={<Info className="h-3.5 w-3.5" />}>
          <ul className="space-y-2 text-sm">
            {data.insights.map((t, i) => (
              <li key={i} className="flex gap-2 rounded-lg border border-edge/70 bg-abyss/50 p-2.5"><span className="text-cyan-400">▸</span><span className="text-slate-300">{t}</span></li>
            ))}
          </ul>
          <div className="mt-4 grid grid-cols-2 gap-2 font-mono text-[11px]">
            {[['Active sales days', `${Math.round(f.active_day_ratio * 100)}%`], ['Unique payers / mo', f.payers_per_month],
              ['Inflow volatility (CV)', f.inflow_cv], ['Top payer share', `${Math.round(f.top_payer_share * 100)}%`],
              ['Surplus ratio', `${Math.round(f.surplus_ratio * 100)}%`], ['Obligation ratio', `${Math.round(f.obligation_ratio * 100)}%`]].map(([k, v]) => (
              <div key={String(k)} className="rounded border border-edge/60 p-2"><div className="text-slate-500">{k}</div><div className="text-cyan-300">{v}</div></div>
            ))}
          </div>
        </Panel>
      </div>
      <div className="grid gap-5 lg:grid-cols-2">
        <Panel title="Where the money goes" icon={<Wallet className="h-3.5 w-3.5" />}>
          <div className="h-60">
            <ResponsiveContainer>
              <BarChart data={data.categories.map((c) => ({ ...c, category: title(c.category) }))} layout="vertical" margin={{ left: 20 }}>
                <XAxis type="number" tick={chartTheme.axis} axisLine={false} tickLine={false} tickFormatter={(v) => inr(v)} />
                <YAxis type="category" dataKey="category" tick={chartTheme.axis} axisLine={false} tickLine={false} width={100} />
                <Tooltip contentStyle={chartTheme.tooltip} formatter={(v: number) => inrFull(v)} cursor={{ fill: 'rgba(34,227,245,.05)' }} />
                <RBar dataKey="amount" fill="#9b7bff" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>
        <Panel title="Data provenance" icon={<Lock className="h-3.5 w-3.5" />}>
          <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
            <dt className="label pt-0.5">Source</dt><dd><Chip tone="violet">{title(data.dataset.source)}</Chip></dd>
            <dt className="label pt-0.5">Ingested</dt><dd className="font-mono text-xs">{dt(data.dataset.uploaded_at)}</dd>
            <dt className="label pt-0.5">Rows</dt><dd className="font-mono text-xs">{data.dataset.rows}</dd>
            <dt className="label pt-0.5">SHA-256</dt><dd className="font-mono text-xs text-neon-violet">{short(data.dataset.sha256, 24)}</dd>
            <dt className="label pt-0.5">Storage</dt><dd className="text-xs text-slate-400">AES-256-GCM under your personal key · counterparties pseudonymised</dd>
          </dl>
          <div className="mt-4 border-t border-edge/70 pt-4"><div className="label mb-2">Refresh data</div><Ingest b={b} onDone={reload} compact /></div>
        </Panel>
      </div>
    </div>
  )
}

export default function Cashflow() {
  return (
    <div>
      <PageHead kicker="Cash-flow Analyst agent" title="Your UPI flows, read like a bank would">
        No ITR or audited statements? Steady digital sales are evidence too. Used only under your active consent.
      </PageHead>
      <NeedBusiness>{(b) => <View b={b} />}</NeedBusiness>
    </div>
  )
}
