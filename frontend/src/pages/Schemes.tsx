import clsx from 'clsx'
import { ChevronDown, FileText, Landmark, ShieldCheck } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import NeedBusiness from '../components/NeedBusiness'
import { Bar, CheckIcon, Chip, Cite, ErrorBox, PageHead, Panel, Spinner, Stat, statusTone } from '../components/ui'
import { inr, title } from '../lib/format'
import { useApi } from '../lib/hooks'
import type { Business, SchemeResult } from '../lib/types'

function SchemeCard({ s, open, toggle }: { s: SchemeResult; open: boolean; toggle: () => void }) {
  const tone = statusTone(s.status)
  return (
    <div className={clsx('panel animate-rise overflow-hidden', s.status === 'eligible' && 'border-neon-green/30')}>
      <button className="flex w-full flex-wrap items-center gap-3 p-4 text-left" onClick={toggle} aria-expanded={open}>
        <Landmark className={clsx('h-5 w-5', s.status === 'eligible' ? 'text-neon-green' : s.status === 'likely' ? 'text-neon-amber' : 'text-slate-500')} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-display text-sm font-bold tracking-wider text-white">{s.short}</span>
            <Chip tone={tone}>{s.status}</Chip>
            {s.note && <Chip tone="slate">{s.note}</Chip>}
          </div>
          <div className="truncate text-xs text-slate-400">{s.name} · {s.agency}</div>
        </div>
        <div className="w-32">
          <div className="mb-1 flex justify-between font-mono text-[10px] text-slate-400"><span>match</span><span>{Math.round(s.match * 100)}%</span></div>
          <Bar value={s.match} tone={tone} />
        </div>
        <div className="w-28 text-right">
          <div className="label">Indicative</div>
          <div className="font-mono text-sm text-cyan-300">{s.indicative_amount ? inr(s.indicative_amount) : '—'}</div>
        </div>
        <ChevronDown className={clsx('h-4 w-4 text-slate-400 transition', open && 'rotate-180')} />
      </button>
      {open && (
        <div className="space-y-4 border-t border-edge/70 p-4">
          <p className="text-sm text-slate-300">{s.benefit} <span className="text-slate-500">· {s.typical_rate}</span></p>
          <div>
            <div className="label mb-2">Rule-by-rule check · every claim cited</div>
            <ul className="space-y-2">
              {s.checks.map((c, i) => (
                <li key={i} className="rounded-lg border border-edge/70 bg-abyss/50 p-3">
                  <div className="flex items-start gap-2">
                    <CheckIcon status={c.status} />
                    <div className="min-w-0 flex-1">
                      <div className="text-sm text-slate-100">{c.rule}</div>
                      <div className="mt-0.5 text-xs text-slate-400">{c.detail}</div>
                      <div className="mt-1.5"><Cite c={c.citation} /></div>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="label">Sources</span>
            {s.citations.map((c) => <Cite key={c.url + c.section} c={c} />)}
          </div>
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-cyan-400/20 bg-cyan-400/5 p-3">
            <div className="text-sm"><span className="label mr-2">Next step</span>{s.next_step}</div>
            <div className="flex gap-2">
              <Link to="/documents" className="btn-ghost !py-1.5 text-xs"><FileText className="h-3.5 w-3.5" /> {s.documents.length} documents</Link>
              {s.status !== 'ineligible' && <Link to={`/applications?draft=${s.scheme_id}`} className="btn-primary !py-1.5 text-xs">Draft application</Link>}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function View({ b }: { b: Business }) {
  const { data, error, loading, reload } = useApi<SchemeResult[]>(`/businesses/${b.id}/eligibility`, [b.id])
  const [open, setOpen] = useState<string | null>(null)
  if (loading && !data) return <Spinner label="Scheme Navigator checking rules" />
  if (error) return <ErrorBox msg={error} onRetry={reload} />
  if (!data) return null
  const eligible = data.filter((s) => s.status === 'eligible')
  const likely = data.filter((s) => s.status === 'likely')
  const unknowns = data.flatMap((s) => s.checks.filter((c) => c.status === 'unknown').map((c) => c.rule))
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Eligible now" value={eligible.length} sub={eligible.map((s) => s.short).join(', ') || '—'} tone="green" />
        <Stat label="Likely (need info)" value={likely.length} sub={`${new Set(unknowns).size} questions to answer`} tone="amber" />
        <Stat label="Schemes checked" value={data.length} sub="Central schemes · official rules" />
        <Stat label="Best indicative amount" value={inr(Math.max(0, ...eligible.map((s) => s.indicative_amount ?? 0)))} sub={`Need: ${inr(b.loan_need)} for ${title(b.loan_purpose)}`} tone="magenta" />
      </div>
      <Panel>
        <div className="flex items-start gap-3 text-sm text-slate-300">
          <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-neon-green" />
          <p>Eligibility is computed by deterministic rules — not guessed by a language model. Each rule links to the clause on the official
            scheme portal it comes from, with the date it was last verified. Gender and social category are used <b>only</b> where a scheme
            itself targets them (e.g. Stand-Up India), never in the risk score.</p>
        </div>
      </Panel>
      <div className="space-y-3">
        {[...data].sort((a, z) => z.match - a.match).map((s) => (
          <SchemeCard key={s.scheme_id} s={s} open={open === s.scheme_id} toggle={() => setOpen(open === s.scheme_id ? null : s.scheme_id)} />
        ))}
      </div>
    </div>
  )
}

export default function Schemes() {
  return (
    <div>
      <PageHead kicker="Scheme Navigator agent" title="Schemes you qualify for">
        MSMEs miss 70–80% of the schemes they are eligible for. Here is every central scheme checked against your profile — with the source for each claim.
      </PageHead>
      <NeedBusiness>{(b) => <View b={b} />}</NeedBusiness>
    </div>
  )
}
