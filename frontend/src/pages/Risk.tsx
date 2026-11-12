import clsx from 'clsx'
import { ArrowDownRight, ArrowUpRight, Gauge, Lightbulb, Scale, ShieldCheck } from 'lucide-react'
import { Link } from 'react-router-dom'
import NeedBusiness from '../components/NeedBusiness'
import { Chip, Empty, ErrorBox, PageHead, Panel, Ring, Spinner } from '../components/ui'
import { pct } from '../lib/format'
import { useApi } from '../lib/hooks'
import type { Business, Risk as R } from '../lib/types'

const BAND: Record<string, { c: string; t: string }> = {
  A: { c: '#2bff9e', t: 'Strong' }, B: { c: '#22e3f5', t: 'Good' }, C: { c: '#ffc93d', t: 'Fair' }, D: { c: '#ff8a3d', t: 'Building' }, E: { c: '#ff4d6d', t: 'Not yet' },
}

function View({ b }: { b: Business }) {
  const { data, error, loading, reload } = useApi<R>(`/businesses/${b.id}/risk`, [b.id])
  if (loading && !data) return <Spinner label="Risk Assessor computing" />
  if (error) return <ErrorBox msg={error} onRetry={reload} />
  if (!data) return null
  if (!data.available)
    return <Panel><Empty icon={<Gauge className="h-10 w-10" />} title="Score needs cash-flow data">{data.reason ?? 'Link your UPI statement first.'} <Link className="link" to="/cashflow">Go to Cash-flow →</Link></Empty></Panel>
  const band = BAND[data.band]
  const maxImpact = Math.max(...data.factors.map((f) => Math.abs(f.impact)), 0.01)
  return (
    <div className="space-y-5">
      <div className="grid gap-5 lg:grid-cols-[1fr_2fr]">
        <Panel hot title="Credit-readiness" icon={<Gauge className="h-3.5 w-3.5" />}>
          <div className="flex flex-col items-center gap-3">
            <Ring value={(data.score - 300) / 600} size={170} label={data.score} sub={`band ${data.band} · ${band.t}`} color={band.c} />
            <div className="grid w-full grid-cols-2 gap-2 text-center font-mono text-xs">
              <div className="rounded border border-edge p-2"><div className="text-slate-500">PD (12m)</div><div className="text-white">{pct(data.pd, 1)}</div></div>
              <div className="rounded border border-edge p-2"><div className="text-slate-500">90% interval</div><div className="text-white">{pct(data.pd_interval_90[0], 1)}–{pct(data.pd_interval_90[1], 1)}</div></div>
              <div className="rounded border border-edge p-2"><div className="text-slate-500">Confidence</div><div className="text-white">{data.confidence}</div></div>
              <div className="rounded border border-edge p-2"><div className="text-slate-500">Status</div><div className={data.credit_ready ? 'text-neon-green' : 'text-neon-amber'}>{data.credit_ready ? 'Credit-ready' : 'Building'}</div></div>
            </div>
            <div className="flex flex-wrap justify-center gap-1.5">
              <Chip tone="green"><ShieldCheck className="h-3 w-3" /> gender / caste / region not used</Chip>
              <Chip tone="violet">{data.model_version}</Chip>
            </div>
          </div>
        </Panel>
        <Panel title="Why this score · factor contributions" icon={<Scale className="h-3.5 w-3.5" />}>
          <ul className="space-y-2.5">
            {data.factors.map((f) => {
              const good = f.impact < 0
              return (
                <li key={f.feature} className="grid grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)] items-center gap-3">
                  <div className="min-w-0">
                    <div className="truncate text-sm text-slate-200">{f.label}</div>
                    <div className="font-mono text-[10px] text-slate-500">value {Number.isInteger(f.value) ? f.value : f.value.toFixed(3)}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="relative h-2 flex-1 rounded-full bg-white/5">
                      <div className="absolute inset-y-0 left-1/2 w-px bg-slate-600" />
                      <div className={clsx('absolute inset-y-0 rounded-full', good ? 'right-1/2 bg-neon-green' : 'left-1/2 bg-neon-red')}
                        style={{ width: `${(Math.abs(f.impact) / maxImpact) * 50}%` }} />
                    </div>
                    <span className={clsx('flex w-24 items-center gap-0.5 font-mono text-[10px]', good ? 'text-neon-green' : 'text-neon-red')}>
                      {good ? <ArrowDownRight className="h-3 w-3" /> : <ArrowUpRight className="h-3 w-3" />}{f.direction}
                    </span>
                  </div>
                </li>
              )
            })}
          </ul>
          <p className="mt-3 text-[11px] text-slate-500">Green bars lower the estimated default risk; red bars raise it. Contributions are exact for this logistic model (coefficient × standardised value).</p>
        </Panel>
      </div>
      <div className="grid gap-5 lg:grid-cols-3">
        <Panel title="Strengths" icon={<ArrowDownRight className="h-3.5 w-3.5" />}>
          <ul className="space-y-1.5 text-sm text-slate-300">{data.strengths.map((s) => <li key={s}>✓ {s}</li>)}</ul>
        </Panel>
        <Panel title="Reason codes (adverse)" icon={<ArrowUpRight className="h-3.5 w-3.5" />}>
          <ul className="space-y-1.5 text-sm text-slate-300">{data.reason_codes.length ? data.reason_codes.map((s) => <li key={s}>• {s}</li>) : <li>None — no factor is materially raising risk.</li>}</ul>
        </Panel>
        <Panel title="How to improve" icon={<Lightbulb className="h-3.5 w-3.5" />}>
          <ul className="space-y-2 text-sm">
            {data.suggestions.map((s) => (
              <li key={s.feature} className="rounded-lg border border-edge p-2.5">
                <div className="text-slate-200">{s.action}</div>
                <div className="mt-1 font-mono text-[11px] text-neon-green">→ score {s.new_score} (PD {pct(s.new_pd, 1)})</div>
              </li>
            ))}
            {!data.suggestions.length && <li className="text-slate-400">You're already near the top band.</li>}
          </ul>
        </Panel>
      </div>
      <Panel>
        <p className="text-sm text-slate-400">{data.note} <Link to="/model" className="link">Read the model card &amp; fairness audit →</Link></p>
      </Panel>
    </div>
  )
}

export default function Risk() {
  return (
    <div>
      <PageHead kicker="Risk Assessor agent" title="Credit readiness, explained">
        A calibrated, fairness-audited estimate from your cash-flows — decision support for the lender, a to-do list for you. Never an automatic rejection.
      </PageHead>
      <NeedBusiness>{(b) => <View b={b} />}</NeedBusiness>
    </div>
  )
}
