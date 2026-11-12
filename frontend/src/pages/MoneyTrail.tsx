import { Banknote, Building, Calculator, Clock, Info, UserRound } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Bar as RBar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { ErrorBox, PageHead, Panel, Stat, chartTheme } from '../components/ui'
import { api } from '../lib/api'
import { inr, inrFull, pct } from '../lib/format'

interface Trail {
  assumptions_note: string
  lender: { incomplete_files: number; staff_cost: number; dropouts: number; lost_margin: number; sunk_acquisition: number; cost_per_incomplete_file: number; monthly_total: number; annual_total: number; capital_idle_days: number }
  with_artha: { measured_incomplete_share: number; monthly_total: number; monthly_saving: number; docs_requests_observed: number; files_observed: number }
  borrower: { loan: number; moneylender_interest: number; scheme_interest: number; agent_fee: number; annual_saving: number }
}
const PARAMS = [
  { k: 'files_per_month', label: 'Loan files per branch / month', min: 10, max: 600, step: 10, fmt: (v: number) => `${v}` },
  { k: 'incomplete_share', label: 'Share of files incomplete', min: 0.05, max: 0.9, step: 0.05, fmt: (v: number) => pct(v) },
  { k: 'followup_hours', label: 'Officer hours chasing each incomplete file', min: 0.5, max: 20, step: 0.5, fmt: (v: number) => `${v} h` },
  { k: 'officer_cost_per_hour', label: 'Loaded officer cost / hour', min: 200, max: 2000, step: 50, fmt: (v: number) => inrFull(v) },
  { k: 'dropout_share', label: 'Incomplete files that drop out', min: 0.05, max: 0.8, step: 0.05, fmt: (v: number) => pct(v) },
  { k: 'avg_loan', label: 'Average ticket size', min: 50000, max: 2000000, step: 25000, fmt: (v: number) => inr(v) },
  { k: 'net_interest_margin', label: 'Net interest margin', min: 0.01, max: 0.08, step: 0.005, fmt: (v: number) => pct(v, 1) },
  { k: 'acquisition_cost', label: 'Sourcing cost per file', min: 0, max: 10000, step: 250, fmt: (v: number) => inrFull(v) },
] as const
type Key = (typeof PARAMS)[number]['k']
const DEFAULTS: Record<Key, number> = { files_per_month: 120, incomplete_share: 0.45, followup_hours: 6, officer_cost_per_hour: 650, dropout_share: 0.35, avg_loan: 300000, net_interest_margin: 0.035, acquisition_cost: 2500 }

export default function MoneyTrail() {
  const [p, setP] = useState(DEFAULTS)
  const [d, setD] = useState<Trail | null>(null)
  const [err, setErr] = useState<string | null>(null)
  useEffect(() => {
    const t = setTimeout(() => {
      const q = new URLSearchParams(Object.entries(p).map(([k, v]) => [k, String(v)]))
      api<Trail>(`/analytics/money-trail?${q}`).then((x) => { setD(x); setErr(null) }).catch((e) => setErr(e.message))
    }, 200)
    return () => clearTimeout(t)
  }, [p])

  return (
    <div className="space-y-5">
      <PageHead kicker="Following the money" title="What an incomplete file really costs">
        Every incomplete file costs a lender staff time, lost margin and sourcing spend — and costs the borrower months and moneylender interest. Tune the assumptions with numbers from the field.
      </PageHead>
      <ErrorBox msg={err} />
      <div className="grid gap-5 xl:grid-cols-[360px_1fr]">
        <Panel title="Field assumptions" icon={<Calculator className="h-3.5 w-3.5" />}>
          <div className="space-y-4">
            {PARAMS.map((x) => (
              <label key={x.k} className="block">
                <div className="mb-1 flex justify-between text-xs"><span className="text-slate-300">{x.label}</span><span className="font-mono text-cyan-300">{x.fmt(p[x.k])}</span></div>
                <input type="range" className="w-full accent-cyan-400" min={x.min} max={x.max} step={x.step} value={p[x.k]}
                  onChange={(e) => setP({ ...p, [x.k]: Number(e.target.value) })} />
              </label>
            ))}
            <button className="btn-ghost w-full text-xs" onClick={() => setP(DEFAULTS)}>Reset</button>
          </div>
          {d && <p className="mt-4 flex gap-2 text-[11px] text-slate-500"><Info className="h-3.5 w-3.5 shrink-0" />{d.assumptions_note}</p>}
        </Panel>
        {d && (
          <div className="space-y-5">
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
              <Stat label="Cost per incomplete file" value={inr(d.lender.cost_per_incomplete_file)} sub="Staff time + expected lost margin" tone="red" icon={<Building className="h-5 w-5" />} />
              <Stat label="Branch cost / month" value={inr(d.lender.monthly_total)} sub={`${d.lender.incomplete_files} incomplete · ${d.lender.dropouts} drop out`} tone="amber" icon={<Banknote className="h-5 w-5" />} />
              <Stat label="Branch cost / year" value={inr(d.lender.annual_total)} sub={`+${d.lender.capital_idle_days} days capital idle per file`} tone="magenta" icon={<Clock className="h-5 w-5" />} />
              <Stat label="Saving with ARTHA / month" value={inr(d.with_artha.monthly_saving)} sub={`Measured incomplete share ${pct(d.with_artha.measured_incomplete_share)} (${d.with_artha.files_observed} files)`} tone="green" icon={<Calculator className="h-5 w-5" />} />
            </div>
            <Panel title="Lender: monthly cost breakdown" icon={<Building className="h-3.5 w-3.5" />}>
              <div className="h-64">
                <ResponsiveContainer>
                  <BarChart data={[
                    { name: 'Today', staff: d.lender.staff_cost, margin: d.lender.lost_margin, sourcing: d.lender.sunk_acquisition },
                    { name: 'With ARTHA', staff: Math.round(d.with_artha.monthly_total * (d.lender.staff_cost / d.lender.monthly_total || 0)), margin: Math.round(d.with_artha.monthly_total * (d.lender.lost_margin / d.lender.monthly_total || 0)), sourcing: Math.round(d.with_artha.monthly_total * (d.lender.sunk_acquisition / d.lender.monthly_total || 0)) },
                  ]} layout="vertical" margin={{ left: 10 }}>
                    <CartesianGrid stroke={chartTheme.grid} horizontal={false} />
                    <XAxis type="number" tick={chartTheme.axis} tickFormatter={(v) => inr(v)} axisLine={false} tickLine={false} />
                    <YAxis type="category" dataKey="name" tick={chartTheme.axis} axisLine={false} tickLine={false} width={80} />
                    <Tooltip contentStyle={chartTheme.tooltip} formatter={(v: number) => inrFull(v)} cursor={{ fill: 'rgba(34,227,245,.05)' }} />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <RBar dataKey="staff" name="Officer follow-up" stackId="a" fill="#22e3f5" />
                    <RBar dataKey="margin" name="Lost interest margin" stackId="a" fill="#ff3df2" />
                    <RBar dataKey="sourcing" name="Sunk sourcing cost" stackId="a" fill="#ffc93d" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Panel>
            <Panel title={`Borrower: one year on a ${inr(d.borrower.loan)} loan`} icon={<UserRound className="h-3.5 w-3.5" />}>
              <div className="grid gap-3 md:grid-cols-3">
                <div className="rounded-lg border border-neon-red/30 bg-neon-red/5 p-3"><div className="label">Moneylender @ ~30%</div><div className="font-display text-xl text-neon-red">{inr(d.borrower.moneylender_interest)}</div></div>
                <div className="rounded-lg border border-neon-amber/30 bg-neon-amber/5 p-3"><div className="label">Agent fee @ 12.5%</div><div className="font-display text-xl text-neon-amber">{inr(d.borrower.agent_fee)}</div></div>
                <div className="rounded-lg border border-neon-green/30 bg-neon-green/5 p-3"><div className="label">Scheme loan @ ~11%</div><div className="font-display text-xl text-neon-green">{inr(d.borrower.scheme_interest)}</div></div>
              </div>
              <p className="mt-3 text-sm text-slate-300">The owner keeps about <b className="text-neon-green">{inr(d.borrower.annual_saving)}</b> a year — margin that funds the next season’s growth instead of interest.</p>
            </Panel>
          </div>
        )}
      </div>
    </div>
  )
}
