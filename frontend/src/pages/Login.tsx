import { ArrowRight, BadgeIndianRupee, FileWarning, Lock, ShieldCheck, Users, UserRound } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { ErrorBox, Field } from '../components/ui'
import { useAuth } from '../lib/auth'
import { useAction } from '../lib/hooks'

const DEMO_PW = 'Artha@Demo2026'
const PERSONAS = [
  { email: 'lakshmi@artha.demo', name: 'Lakshmi S.', role: 'Tailor · Tiruppur', tag: 'Entrepreneur' },
  { email: 'meena@artha.demo', name: 'Meena Behera', role: 'SHG food unit · Khordha', tag: 'Entrepreneur' },
  { email: 'ravi@artha.demo', name: 'Ravi Patil', role: 'Fabricator · Pune', tag: 'Entrepreneur' },
  { email: 'bc@artha.demo', name: 'Suresh', role: 'Business correspondent', tag: 'Agent' },
  { email: 'manager@artha.demo', name: 'R. Krishnan', role: 'Branch manager', tag: 'Lender' },
  { email: 'dic@artha.demo', name: 'A. Das', role: 'District Industries Centre', tag: 'DIC' },
  { email: 'auditor@artha.demo', name: 'Fairness Office', role: 'Model risk & audit', tag: 'Auditor' },
]
const PAIN = [
  { k: '70–80%', v: 'of eligible schemes missed by MSMEs', icon: BadgeIndianRupee },
  { k: '15–20', v: 'documents per loan file, months of follow-up', icon: FileWarning },
  { k: '10–15%', v: 'taken by middlemen', icon: Users },
  { k: '24–36%', v: 'moneylender interest when files stall', icon: Lock },
]

export default function Login() {
  const { login, register } = useAuth()
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const { busy, error, run, setError } = useAction()

  const submit = (e: FormEvent) => {
    e.preventDefault()
    run(() => (mode === 'login' ? login(email.trim(), password) : register(email.trim(), password, name.trim())))
  }
  const pick = (em: string) => {
    setMode('login')
    setEmail(em)
    setPassword(DEMO_PW)
    setError(null)
  }

  return (
    <div className="grid-bg min-h-full">
      <div className="mx-auto grid max-w-7xl gap-8 px-4 py-10 lg:grid-cols-[1.25fr_1fr] lg:py-16">
        <div className="animate-rise">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-400 to-neon-magenta font-display text-xl font-black text-void">A</div>
            <div>
              <div className="h-display text-2xl font-black text-white">ARTHA</div>
              <div className="label text-cyan-400/80">Problem statement 3.2 · Agentic AI</div>
            </div>
          </div>
          <h1 className="h-display mt-8 text-3xl font-black leading-tight text-white md:text-5xl">
            Viable small businesses,<br />
            <span className="bg-gradient-to-r from-cyan-300 via-cyan-400 to-neon-magenta bg-clip-text text-transparent">finally bankable.</span>
          </h1>
          <p className="mt-5 max-w-xl text-slate-300">
            Eight cooperating AI agents turn steady UPI flows into a credit file a bank recognises, find every scheme an owner qualifies
            for — each claim cited to its official source — and file the application only after the entrepreneur approves it.
          </p>
          <div className="mt-8 grid gap-3 sm:grid-cols-2">
            {PAIN.map((p) => (
              <div key={p.k} className="panel corner flex items-center gap-4 p-4">
                <p.icon className="h-6 w-6 shrink-0 text-neon-magenta" />
                <div>
                  <div className="font-display text-xl font-bold text-white">{p.k}</div>
                  <div className="text-xs text-slate-400">{p.v}</div>
                </div>
              </div>
            ))}
          </div>
          <div className="mt-6 flex flex-wrap gap-2 font-mono text-[10px] uppercase tracking-wider text-slate-400">
            {['Consent-gated data', 'Per-owner AES-256 keys', 'Cited eligibility', 'Calibrated & fair scoring', 'Owner approves every file'].map((t) => (
              <span key={t} className="rounded-full border border-edge px-2.5 py-1"><ShieldCheck className="mr-1 inline h-3 w-3 text-neon-green" />{t}</span>
            ))}
          </div>
        </div>

        <div className="space-y-4">
          <form onSubmit={submit} className="panel-hot corner animate-rise space-y-4 p-6" autoComplete="on">
            <div className="flex rounded-lg border border-edge p-1">
              {(['login', 'register'] as const).map((m) => (
                <button type="button" key={m} onClick={() => { setMode(m); setError(null) }}
                  className={`flex-1 rounded-md py-1.5 text-sm transition ${mode === m ? 'bg-cyan-400/15 text-cyan-300' : 'text-slate-400 hover:text-white'}`}>
                  {m === 'login' ? 'Sign in' : 'Create account'}
                </button>
              ))}
            </div>
            {mode === 'register' && (
              <Field label="Your name">
                <input className="input" value={name} onChange={(e) => setName(e.target.value)} required minLength={2} maxLength={80} autoComplete="name" />
              </Field>
            )}
            <Field label="Email">
              <input className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="username" maxLength={120} />
            </Field>
            <Field label="Password" hint={mode === 'register' ? '10+ characters with upper-case, lower-case and a digit. Stored only as an Argon2 hash.' : undefined}>
              <input className="input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required
                minLength={mode === 'register' ? 10 : 1} maxLength={128} autoComplete={mode === 'login' ? 'current-password' : 'new-password'} />
            </Field>
            <ErrorBox msg={error} />
            <button className="btn-primary w-full" disabled={busy}>
              {busy ? 'Verifying…' : mode === 'login' ? 'Sign in securely' : 'Create entrepreneur account'} <ArrowRight className="h-4 w-4" />
            </button>
            <p className="text-center text-[11px] text-slate-500">Sessions expire after 30 minutes. 5 wrong passwords lock the account for 15 minutes.</p>
          </form>

          <div className="panel animate-rise p-4">
            <div className="label mb-3">Demo personas · synthetic data only</div>
            <div className="grid gap-2 sm:grid-cols-2">
              {PERSONAS.map((p) => (
                <button key={p.email} type="button" onClick={() => pick(p.email)}
                  className={`flex items-center gap-3 rounded-lg border px-3 py-2 text-left transition hover:border-cyan-400/40 hover:bg-cyan-400/5 ${email === p.email ? 'border-cyan-400/50 bg-cyan-400/10' : 'border-edge'}`}>
                  <UserRound className="h-4 w-4 shrink-0 text-cyan-400" />
                  <div className="min-w-0">
                    <div className="truncate text-sm text-slate-100">{p.name} <span className="font-mono text-[9px] text-neon-magenta">{p.tag}</span></div>
                    <div className="truncate text-[11px] text-slate-500">{p.role}</div>
                  </div>
                </button>
              ))}
            </div>
            <p className="mt-3 text-[11px] text-slate-500">Click a persona to fill the form, then sign in. Demo password: <span className="font-mono text-slate-300">{DEMO_PW}</span></p>
          </div>
        </div>
      </div>
    </div>
  )
}
