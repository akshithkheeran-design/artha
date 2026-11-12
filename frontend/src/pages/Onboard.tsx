import { Building2, Mic, Sparkles } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { Chip, ErrorBox, Field, PageHead, Panel } from '../components/ui'
import { api } from '../lib/api'
import { useBusiness } from '../lib/business'
import { title } from '../lib/format'
import { useAction } from '../lib/hooks'
import type { Business } from '../lib/types'

interface IntakeOut { extracted: Record<string, string | number | boolean>; follow_up_questions: string[]; confidence: number; redacted: string[] }
const EMPTY = { name: '', sector: 'tailoring', activity_type: 'manufacturing', state: '', district: '', area: 'rural', years_in_operation: 1, employees: 1, loan_need: 200000, loan_purpose: 'working_capital' }
const P0 = { owner_name: '', gender: 'undisclosed', social_category: 'undisclosed', is_shg: false, is_new_unit: false, prior_default: false, has_itr: false }

export default function Onboard() {
  const nav = useNavigate()
  const { reload, select } = useBusiness()
  const [story, setStory] = useState('')
  const [f, setF] = useState(EMPTY)
  const [p, setP] = useState(P0)
  const [intake, setIntake] = useState<IntakeOut | null>(null)
  const { busy, error, run } = useAction()
  const set = (k: string, v: string | number) => setF((x) => ({ ...x, [k]: v }))

  const parse = () => run(async () => {
    const r = await api<IntakeOut>('/agents/intake', { method: 'POST', body: { text: story } })
    setIntake(r)
    const e = r.extracted
    setF((x) => ({ ...x, ...Object.fromEntries(Object.entries(e).filter(([k]) => k in EMPTY)) }) as typeof EMPTY)
    setP((x) => ({ ...x, ...(e.gender ? { gender: String(e.gender) } : {}), ...(e.social_category ? { social_category: String(e.social_category) } : {}),
      ...(e.is_shg !== undefined ? { is_shg: !!e.is_shg } : {}), ...(e.is_new_unit !== undefined ? { is_new_unit: !!e.is_new_unit } : {}) }))
  })
  const submit = (e: FormEvent) => {
    e.preventDefault()
    run(async () => {
      const profile = Object.fromEntries(Object.entries(p).filter(([, v]) => v !== ''))
      const b = await api<Business>('/businesses', { method: 'POST', body: { ...f, profile } })
      await reload()
      select(b.id)
      nav('/consent')
    })
  }
  return (
    <div className="space-y-5">
      <PageHead kicker="Intake Agent" title="Add your business">Tell us about your work in your own words — the Intake Agent fills the form. Identifiers you type are redacted before analysis.</PageHead>
      <Panel hot title="Describe your business" icon={<Mic className="h-3.5 w-3.5" />}>
        <textarea className="input min-h-[90px]" maxLength={2000} value={story} onChange={(e) => setStory(e.target.value)}
          placeholder="e.g. I am a woman tailor in Tiruppur, Tamil Nadu running for 5 years with 3 workers. I get about ₹60,000 a month on UPI and need ₹3 lakh for new machines." />
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <button className="btn-primary" disabled={busy || story.trim().length < 3} onClick={parse}><Sparkles className="h-4 w-4" /> Extract details</button>
          {intake && <Chip tone="green">confidence {Math.round(intake.confidence * 100)}%</Chip>}
          {intake?.redacted.map((r) => <Chip key={r} tone="amber">redacted {r}</Chip>)}
        </div>
        {intake && intake.follow_up_questions.length > 0 && <ul className="mt-3 space-y-1 text-sm text-neon-amber">{intake.follow_up_questions.map((q) => <li key={q}>? {q}</li>)}</ul>}
      </Panel>
      <form onSubmit={submit}>
        <Panel title="Business profile" icon={<Building2 className="h-3.5 w-3.5" />}>
          <div className="grid gap-4 md:grid-cols-3">
            <Field label="Business name"><input className="input" required minLength={2} maxLength={120} value={f.name} onChange={(e) => set('name', e.target.value)} /></Field>
            <Field label="Owner name"><input className="input" maxLength={80} value={p.owner_name} onChange={(e) => setP({ ...p, owner_name: e.target.value })} /></Field>
            <Field label="Sector"><select className="input" value={f.sector} onChange={(e) => set('sector', e.target.value)}>{['tailoring', 'fabrication', 'dairy', 'food_processing', 'handicraft', 'retail', 'services', 'other'].map((s) => <option key={s} value={s}>{title(s)}</option>)}</select></Field>
            <Field label="Activity"><select className="input" value={f.activity_type} onChange={(e) => set('activity_type', e.target.value)}>{['manufacturing', 'services', 'trading', 'agri_allied'].map((s) => <option key={s} value={s}>{title(s)}</option>)}</select></Field>
            <Field label="State"><input className="input" required minLength={2} value={f.state} onChange={(e) => set('state', e.target.value)} /></Field>
            <Field label="District"><input className="input" required minLength={2} value={f.district} onChange={(e) => set('district', e.target.value)} /></Field>
            <Field label="Area"><select className="input" value={f.area} onChange={(e) => set('area', e.target.value)}><option value="rural">Rural</option><option value="urban">Urban</option></select></Field>
            <Field label="Years running"><input className="input" type="number" min={0} max={80} step={0.5} value={f.years_in_operation} onChange={(e) => set('years_in_operation', Number(e.target.value))} /></Field>
            <Field label="Workers"><input className="input" type="number" min={0} max={500} value={f.employees} onChange={(e) => set('employees', Number(e.target.value))} /></Field>
            <Field label="Loan needed (₹)"><input className="input" type="number" min={0} step={1000} value={f.loan_need} onChange={(e) => set('loan_need', Number(e.target.value))} /></Field>
            <Field label="Purpose"><select className="input" value={f.loan_purpose} onChange={(e) => set('loan_purpose', e.target.value)}>{['working_capital', 'machinery', 'expansion', 'new_unit', 'livestock'].map((s) => <option key={s} value={s}>{title(s)}</option>)}</select></Field>
            <Field label="Gender" hint="Used only for schemes that target it — never in the risk score."><select className="input" value={p.gender} onChange={(e) => setP({ ...p, gender: e.target.value })}>{['undisclosed', 'female', 'male', 'transgender'].map((s) => <option key={s} value={s}>{title(s)}</option>)}</select></Field>
            <Field label="Social category" hint="Optional · e.g. Stand-Up India / PMEGP"><select className="input" value={p.social_category} onChange={(e) => setP({ ...p, social_category: e.target.value })}>{['undisclosed', 'general', 'sc', 'st', 'obc', 'minority'].map((s) => <option key={s} value={s}>{s.toUpperCase()}</option>)}</select></Field>
          </div>
          <div className="mt-4 flex flex-wrap gap-4 text-sm text-slate-300">
            {([['is_shg', 'Run by an SHG'], ['is_new_unit', 'New (greenfield) unit'], ['has_itr', 'Have filed ITR'], ['prior_default', 'Have defaulted on a loan before']] as const).map(([k, l]) => (
              <label key={k} className="flex items-center gap-2"><input type="checkbox" className="accent-cyan-400" checked={p[k]} onChange={(e) => setP({ ...p, [k]: e.target.checked })} /> {l}</label>
            ))}
          </div>
          <ErrorBox msg={error} />
          <button className="btn-primary mt-4" disabled={busy}>Save — encrypted with your personal key</button>
        </Panel>
      </form>
    </div>
  )
}
