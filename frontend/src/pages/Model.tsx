import { AlertTriangle, CheckCircle2, Scale, XCircle } from 'lucide-react'
import { CartesianGrid, Line, ResponsiveContainer, Scatter, ComposedChart, Tooltip, XAxis, YAxis, Legend } from 'recharts'
import { Chip, ErrorBox, PageHead, Panel, Spinner, Stat, chartTheme } from '../components/ui'
import { pct, title } from '../lib/format'
import { useApi } from '../lib/hooks'

interface Group { n: number; approval_rate: number; tpr_good_borrowers: number; mean_predicted_pd: number; observed_default: number; calibration_gap: number }
interface Fair { groups: Record<string, Group>; disparate_impact: number; equal_opportunity_gap: number; max_calibration_gap: number; checks: Record<string, boolean> }
interface Card {
  version: string; algorithm: string; training_data: string; test_size: number
  features: { key: string; label: string; weight: number }[]; excluded_attributes: string[]
  metrics: { auc: number; brier: number; ece: number; base_rate: number }
  reliability: { bin: number; predicted: number; observed: number; count: number }[]
  approve_threshold_pd: number; fairness: Record<string, Fair>; limitations: string[]; monitoring: string
}

export default function Model() {
  const { data: c, error, loading, reload } = useApi<Card>('/model/card')
  if (loading && !c) return <Spinner />
  if (error) return <ErrorBox msg={error} onRetry={reload} />
  if (!c) return null
  return (
    <div className="space-y-5">
      <PageHead kicker="Governance · model card" title="Model & Fairness" right={<Chip tone="violet">{c.version}</Chip>}>
        {c.algorithm}. Trained on {c.training_data}; evaluated on {c.test_size.toLocaleString()} held-out profiles.
      </PageHead>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="AUC (discrimination)" value={c.metrics.auc.toFixed(3)} sub="0.5 = random" />
        <Stat label="Brier score" value={c.metrics.brier.toFixed(4)} sub="Lower is better" tone="violet" />
        <Stat label="Calibration error (ECE)" value={c.metrics.ece.toFixed(4)} sub="Predicted ≈ observed" tone="green" />
        <Stat label="Base default rate" value={pct(c.metrics.base_rate, 1)} sub={`Ready threshold PD ≤ ${pct(c.approve_threshold_pd)}`} tone="amber" />
      </div>
      <div className="grid gap-5 lg:grid-cols-2">
        <Panel title="Reliability · is it calibrated?" icon={<Scale className="h-3.5 w-3.5" />}>
          <div className="h-64">
            <ResponsiveContainer>
              <ComposedChart data={c.reliability}>
                <CartesianGrid stroke={chartTheme.grid} />
                <XAxis dataKey="predicted" type="number" domain={[0, 'dataMax']} tick={chartTheme.axis} tickFormatter={(v) => pct(v)} name="Predicted" />
                <YAxis type="number" domain={[0, 'dataMax']} tick={chartTheme.axis} tickFormatter={(v) => pct(v)} width={40} />
                <Tooltip contentStyle={chartTheme.tooltip} formatter={(v: number) => pct(v, 1)} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Line dataKey="predicted" name="Perfect calibration" stroke="#64748b" strokeDasharray="4 4" dot={false} />
                <Scatter dataKey="observed" name="Observed default" fill="#22e3f5" />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </Panel>
        <Panel title="Inputs & exclusions" icon={<Scale className="h-3.5 w-3.5" />}>
          <ul className="space-y-1.5 text-sm">
            {c.features.map((f) => (
              <li key={f.key} className="flex justify-between gap-3"><span className="text-slate-300">{f.label}</span>
                <span className={`font-mono text-xs ${f.weight < 0 ? 'text-neon-green' : 'text-neon-red'}`}>{f.weight > 0 ? '+' : ''}{f.weight.toFixed(3)}</span></li>
            ))}
          </ul>
          <div className="mt-4 label">Never used as inputs</div>
          <div className="mt-2 flex flex-wrap gap-1.5">{c.excluded_attributes.map((a) => <Chip key={a} tone="red"><XCircle className="h-3 w-3" />{a}</Chip>)}</div>
        </Panel>
      </div>
      <div className="grid gap-5 lg:grid-cols-2">
        {Object.entries(c.fairness).map(([attr, f]) => (
          <Panel key={attr} title={`Fairness across ${attr}`} icon={<Scale className="h-3.5 w-3.5" />}
            right={Object.values(f.checks).every(Boolean) ? <Chip tone="green">all checks pass</Chip> : <Chip tone="red">attention</Chip>}>
            <div className="mb-3 grid grid-cols-3 gap-2 text-center font-mono text-xs">
              <div className="rounded border border-edge p-2"><div className="text-slate-500">Disparate impact</div><div className="text-white">{f.disparate_impact.toFixed(3)}</div></div>
              <div className="rounded border border-edge p-2"><div className="text-slate-500">Equal opp. gap</div><div className="text-white">{f.equal_opportunity_gap.toFixed(3)}</div></div>
              <div className="rounded border border-edge p-2"><div className="text-slate-500">Max calib. gap</div><div className="text-white">{f.max_calibration_gap.toFixed(3)}</div></div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead><tr className="label text-left"><th className="py-1 font-normal">Group</th><th className="font-normal">n</th><th className="font-normal">Ready rate</th><th className="font-normal">TPR</th><th className="font-normal">Pred PD</th><th className="font-normal">Obs default</th></tr></thead>
                <tbody>{Object.entries(f.groups).map(([g, v]) => (
                  <tr key={g} className="table-row font-mono"><td className="py-1.5 font-sans text-slate-200">{title(g)}</td><td>{v.n}</td><td>{pct(v.approval_rate, 1)}</td><td>{pct(v.tpr_good_borrowers, 1)}</td><td>{pct(v.mean_predicted_pd, 1)}</td><td>{pct(v.observed_default, 1)}</td></tr>
                ))}</tbody>
              </table>
            </div>
            <ul className="mt-3 space-y-1 text-xs">{Object.entries(f.checks).map(([k, ok]) => (
              <li key={k} className="flex items-center gap-1.5">{ok ? <CheckCircle2 className="h-3.5 w-3.5 text-neon-green" /> : <XCircle className="h-3.5 w-3.5 text-neon-red" />}<span className="font-mono text-slate-400">{k.replace(/_/g, ' ')}</span></li>
            ))}</ul>
          </Panel>
        ))}
      </div>
      <Panel title="Limitations & monitoring" icon={<AlertTriangle className="h-3.5 w-3.5" />}>
        <ul className="list-disc space-y-1 pl-5 text-sm text-slate-300">{c.limitations.map((l) => <li key={l}>{l}</li>)}</ul>
        <p className="mt-3 text-sm text-slate-400">{c.monitoring}</p>
      </Panel>
    </div>
  )
}
