import { ClipboardPen, MessagesSquare } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Bar as RBar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Chip, ErrorBox, Field as F, PageHead, Panel, Spinner, Stat, chartTheme } from '../components/ui'
import { api } from '../lib/api'
import { inrFull, title } from '../lib/format'
import { useAction, useApi } from '../lib/hooks'

type Count = { label: string; count: number }
interface Insights { respondents: number; by_type: Record<string, number>; avg_agent_fee_pct: number | null; avg_documents_last_loan: number | null; avg_cost_per_incomplete_file: number | null; [k: string]: unknown }
const QUESTIONS: { key: string; q: string }[] = [
  { key: 'schemes_heard', q: '1 · Which schemes has this business heard of?' }, { key: 'heard_from', q: '1b · …and from whom?' },
  { key: 'stalled_at', q: '2 · Where did the last loan attempt stall?' }, { key: 'agent_services', q: '3 · What does the agent actually do?' },
  { key: 'informal_records', q: '4 · What informal records exist?' }, { key: 'willing_to_share', q: '4b · Would the owner share them?' },
  { key: 'branch_needs', q: '5 · What does a branch manager need to see?' }, { key: 'dropout_reason', q: '6 · Why do eligible applicants drop out?' },
]
const list = (s: string) => s.split(',').map((x) => x.trim().toLowerCase().replace(/\s+/g, '_')).filter(Boolean).slice(0, 10)

function Chart({ data }: { data: Count[] }) {
  if (!data?.length) return <div className="py-6 text-center text-xs text-slate-500">No answers yet</div>
  return (
    <div style={{ height: Math.max(90, data.length * 26) }}>
      <ResponsiveContainer>
        <BarChart data={data.map((d) => ({ ...d, label: title(d.label) }))} layout="vertical" margin={{ left: 8 }}>
          <XAxis type="number" hide allowDecimals={false} />
          <YAxis type="category" dataKey="label" tick={chartTheme.axis} width={120} axisLine={false} tickLine={false} />
          <Tooltip contentStyle={chartTheme.tooltip} cursor={{ fill: 'rgba(34,227,245,.05)' }} />
          <RBar dataKey="count" fill="#22e3f5" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

function Form({ onDone }: { onDone: () => void }) {
  const [v, setV] = useState({ respondent_type: 'entrepreneur', sector: '', state: '', schemes_heard: '', heard_from: '', last_loan_documents: '', stalled_at: '', agent_fee_pct: '', agent_services: '', informal_records: '', willing_to_share: 'conditional', branch_needs: '', dropout_reason: '', cost_per_incomplete_file: '', notes: '' })
  const { busy, error, run } = useAction()
  const [ok, setOk] = useState<string | null>(null)
  const s = (k: keyof typeof v) => (e: { target: { value: string } }) => setV({ ...v, [k]: e.target.value })
  const num = (x: string) => (x === '' ? null : Number(x))
  const submit = (e: FormEvent) => {
    e.preventDefault()
    run(async () => {
      const r = await api<{ redacted: string[] }>('/field/interviews', { method: 'POST', body: {
        respondent_type: v.respondent_type, sector: v.sector, state: v.state, schemes_heard: list(v.schemes_heard), heard_from: v.heard_from || 'none',
        last_loan_documents: num(v.last_loan_documents), stalled_at: v.stalled_at || 'none', agent_fee_pct: num(v.agent_fee_pct),
        agent_services: list(v.agent_services), informal_records: list(v.informal_records), willing_to_share: v.willing_to_share,
        branch_needs: list(v.branch_needs), dropout_reason: v.dropout_reason || 'none', cost_per_incomplete_file: num(v.cost_per_incomplete_file), notes: v.notes } })
      setOk(r.redacted.length ? `Saved. Redacted from notes: ${r.redacted.join(', ')}` : 'Saved anonymously.')
      onDone()
    })
  }
  return (
    <form onSubmit={submit} className="grid gap-3 md:grid-cols-3">
      <F label="Respondent"><select className="input" value={v.respondent_type} onChange={s('respondent_type')}>{['entrepreneur', 'shg', 'bc_agent', 'branch_manager', 'dic_officer'].map((x) => <option key={x} value={x}>{title(x)}</option>)}</select></F>
      <F label="Sector"><input className="input" required pattern="[A-Za-z0-9_ ]+" value={v.sector} onChange={s('sector')} /></F>
      <F label="State"><input className="input" required pattern="[A-Za-z0-9_ ]+" value={v.state} onChange={s('state')} /></F>
      <F label="Q1 Schemes heard of (comma list)"><input className="input" value={v.schemes_heard} onChange={s('schemes_heard')} placeholder="mudra, pmegp" /></F>
      <F label="Q1 Heard from"><input className="input" value={v.heard_from} onChange={s('heard_from')} placeholder="bank_mitra / agent / neighbour" /></F>
      <F label="Q2 Documents asked last time"><input className="input" type="number" min={0} max={60} value={v.last_loan_documents} onChange={s('last_loan_documents')} /></F>
      <F label="Q2 Where it stalled"><input className="input" value={v.stalled_at} onChange={s('stalled_at')} placeholder="documents / collateral / no_response" /></F>
      <F label="Q3 Agent fee (% of loan)"><input className="input" type="number" min={0} max={50} step={0.5} value={v.agent_fee_pct} onChange={s('agent_fee_pct')} /></F>
      <F label="Q3 What the agent did"><input className="input" value={v.agent_services} onChange={s('agent_services')} placeholder="form filling, branch visits" /></F>
      <F label="Q4 Informal records"><input className="input" value={v.informal_records} onChange={s('informal_records')} placeholder="upi, notebook, shg_books" /></F>
      <F label="Q4 Willing to share"><select className="input" value={v.willing_to_share} onChange={s('willing_to_share')}><option value="yes">Yes</option><option value="conditional">Conditional</option><option value="no">No</option></select></F>
      <F label="Q5 Branch manager needs"><input className="input" value={v.branch_needs} onChange={s('branch_needs')} placeholder="12m cash-flow, KYC" /></F>
      <F label="Q6 Drop-out reason"><input className="input" value={v.dropout_reason} onChange={s('dropout_reason')} placeholder="documents / time_lost" /></F>
      <F label="Money · cost per incomplete file (₹)"><input className="input" type="number" min={0} value={v.cost_per_incomplete_file} onChange={s('cost_per_incomplete_file')} /></F>
      <F label="Notes (no names / numbers)"><input className="input" maxLength={600} value={v.notes} onChange={s('notes')} /></F>
      <div className="md:col-span-3"><ErrorBox msg={error} />{ok && <div className="mb-2 text-xs text-neon-green">{ok}</div>}<button className="btn-primary" disabled={busy}><ClipboardPen className="h-4 w-4" /> Save interview</button></div>
    </form>
  )
}

export default function Field() {
  const { data, error, loading, reload } = useApi<Insights>('/field/insights')
  return (
    <div className="space-y-5">
      <PageHead kicker="Questions to take into the field" title="Field Research" right={<Chip tone="amber">Seed answers are illustrative samples</Chip>}>
        Capture structured, anonymised answers to the six field questions from owners, SHGs, agents, branch managers and DIC officers — and watch the patterns emerge.
      </PageHead>
      {loading && !data ? <Spinner /> : error ? <ErrorBox msg={error} onRetry={reload} /> : data && (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Stat label="Respondents" value={data.respondents} sub={Object.entries(data.by_type).map(([k, n]) => `${title(k)} ${n}`).join(' · ')} />
            <Stat label="Avg agent fee" value={data.avg_agent_fee_pct !== null ? `${data.avg_agent_fee_pct}%` : '—'} sub="of loan amount" tone="magenta" />
            <Stat label="Avg docs last loan" value={data.avg_documents_last_loan ?? '—'} sub="asked by lender" tone="amber" />
            <Stat label="Cost / incomplete file" value={data.avg_cost_per_incomplete_file !== null ? inrFull(data.avg_cost_per_incomplete_file) : '—'} sub="reported by branch managers" tone="red" />
          </div>
          <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
            {QUESTIONS.map((q) => <Panel key={q.key} title={q.q} icon={<MessagesSquare className="h-3.5 w-3.5" />}><Chart data={data[q.key] as Count[]} /></Panel>)}
          </div>
        </>
      )}
      <Panel title="Record an interview" icon={<ClipboardPen className="h-3.5 w-3.5" />}><Form onDone={reload} /></Panel>
    </div>
  )
}
