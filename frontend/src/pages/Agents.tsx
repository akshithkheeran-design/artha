import clsx from 'clsx'
import { Bot, CheckCircle2, CircleDashed, Loader2, Play, Send, ShieldAlert, Sparkles, User as UserIcon } from 'lucide-react'
import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import NeedBusiness from '../components/NeedBusiness'
import { Chip, Cite, ErrorBox, PageHead, Panel, statusTone } from '../components/ui'
import { api } from '../lib/api'
import { inr } from '../lib/format'
import { useAction, useApi } from '../lib/hooks'
import type { Business, Citation } from '../lib/types'

interface Step { agent: string; name: string; status: string; summary: string; ms?: number }
interface RunOut { steps: Step[]; recommendation: { scheme_id: string; scheme: string; amount: number; also_apply: string[] } | null }
interface ChatOut { reply: string; intent: string; agents_invoked: string[]; citations: Citation[]; redacted: string[]; sanitised_input: string }
type Msg = { who: 'me' | 'ai'; text: string; meta?: ChatOut }

const PROMPTS = ['Which schemes am I eligible for?', 'Why is my score what it is?', 'What documents do I need?',
  'How much will I save vs the moneylender?', 'Where is my application stuck?', 'Who can see my data?', 'What does the agent charge?']

function Pipeline({ b }: { b: Business }) {
  const { data: catalog } = useApi<{ id: string; name: string; desc: string }[]>('/agents/catalog')
  const [shown, setShown] = useState(0)
  const [result, setResult] = useState<RunOut | null>(null)
  const { busy, error, run } = useAction()

  useEffect(() => { setResult(null); setShown(0) }, [b.id])
  useEffect(() => {
    if (!result || shown >= result.steps.length) return
    const t = setTimeout(() => setShown((s) => s + 1), 420)
    return () => clearTimeout(t)
  }, [result, shown])

  const go = () => run(async () => {
    setResult(null)
    setShown(0)
    setResult(await api<RunOut>(`/businesses/${b.id}/agents/run`, { method: 'POST' }))
  })
  const list = result ? result.steps : (catalog ?? []).map((c) => ({ agent: c.id, name: c.name, status: 'idle', summary: c.desc, ms: undefined as number | undefined }))
  const done = result && shown >= result.steps.length

  return (
    <Panel title="Agent pipeline" icon={<Sparkles className="h-3.5 w-3.5" />} hot
      right={<button className="btn-primary !py-1.5 text-xs" onClick={go} disabled={busy || (!!result && !done)}>
        {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />} Run all agents</button>}>
      <ol className="relative space-y-2.5 before:absolute before:bottom-3 before:left-[15px] before:top-3 before:w-px before:bg-edge">
        {list.map((s, i) => {
          const visible = !result || i < shown
          const running = result && i === shown
          return (
            <li key={s.agent + i} className="relative flex gap-3">
              <div className={clsx('z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border bg-panel',
                visible && result ? (s.status === 'ok' ? 'border-neon-green/50 text-neon-green' : 'border-neon-amber/50 text-neon-amber') : 'border-edge text-slate-500')}>
                {running ? <Loader2 className="h-4 w-4 animate-spin text-cyan-300" /> : visible && result ? <CheckCircle2 className="h-4 w-4" /> : <CircleDashed className="h-4 w-4" />}
              </div>
              <div className={clsx('min-w-0 flex-1 rounded-lg border px-3 py-2 transition', visible && result ? 'border-edge bg-abyss/60' : 'border-transparent')}>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-white">{s.name}</span>
                  {result && visible && <Chip tone={statusTone(s.status)}>{s.status}</Chip>}
                  {result && visible && s.ms !== undefined && <span className="ml-auto font-mono text-[10px] text-slate-500">{s.ms} ms</span>}
                </div>
                <div className={clsx('text-xs', result && !visible ? 'text-slate-600' : 'text-slate-400')}>{result && !visible ? 'Waiting…' : s.summary}</div>
              </div>
            </li>
          )
        })}
      </ol>
      <ErrorBox msg={error} />
      {done && result?.recommendation && (
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-neon-magenta/30 bg-neon-magenta/5 p-3">
          <div className="text-sm">
            <div className="label text-neon-magenta">Recommendation · needs your approval</div>
            <div className="mt-1 text-white">{result.recommendation.scheme} for {inr(result.recommendation.amount)}
              {result.recommendation.also_apply.length > 0 && <span className="text-slate-400"> · also consider {result.recommendation.also_apply.join(', ')}</span>}</div>
          </div>
          <Link to={`/applications?draft=${result.recommendation.scheme_id}&amount=${result.recommendation.amount}`} className="btn-magenta !py-1.5 text-xs">Review &amp; draft</Link>
        </div>
      )}
    </Panel>
  )
}

function Chat({ b }: { b: Business }) {
  const [msgs, setMsgs] = useState<Msg[]>([{ who: 'ai', text: `Namaste! I'm the ARTHA orchestrator for ${b.name}. Ask me anything about schemes, your score, documents or your applications. I never store your identifiers — they're redacted before I read them.` }])
  const [text, setText] = useState('')
  const { busy, error, run } = useAction()
  const end = useRef<HTMLDivElement>(null)
  useEffect(() => end.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }), [msgs])

  const send = (q: string) => {
    if (!q.trim()) return
    setMsgs((m) => [...m, { who: 'me', text: q }])
    setText('')
    run(async () => {
      const r = await api<ChatOut>('/agents/chat', { method: 'POST', body: { business_id: b.id, message: q } })
      setMsgs((m) => [...m.slice(0, -1), { who: 'me', text: r.sanitised_input }, { who: 'ai', text: r.reply, meta: r }])
    })
  }
  const submit = (e: FormEvent) => { e.preventDefault(); send(text) }

  return (
    <Panel title="Ask the agents" icon={<Bot className="h-3.5 w-3.5" />} className="flex flex-col" bodyClass="flex flex-1 flex-col">
      <div className="h-[420px] space-y-3 overflow-y-auto pr-1" aria-live="polite">
        {msgs.map((m, i) => (
          <div key={i} className={clsx('flex gap-2', m.who === 'me' && 'flex-row-reverse')}>
            <div className={clsx('flex h-7 w-7 shrink-0 items-center justify-center rounded-full', m.who === 'me' ? 'bg-neon-magenta/20 text-neon-magenta' : 'bg-cyan-400/15 text-cyan-300')}>
              {m.who === 'me' ? <UserIcon className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
            </div>
            <div className={clsx('max-w-[85%] rounded-xl px-3 py-2 text-sm', m.who === 'me' ? 'bg-neon-magenta/10 text-slate-100' : 'border border-edge bg-abyss/70 text-slate-200')}>
              <div className="whitespace-pre-line">{m.text}</div>
              {m.meta && (
                <div className="mt-2 space-y-1.5">
                  {m.meta.citations.length > 0 && <div className="flex flex-wrap gap-1">{m.meta.citations.slice(0, 4).map((c) => <Cite key={c.url + c.section} c={c} />)}</div>}
                  <div className="flex flex-wrap gap-1">
                    {m.meta.agents_invoked.map((a) => <Chip key={a} tone="slate">{a}</Chip>)}
                    {m.meta.redacted.length > 0 && <Chip tone="amber"><ShieldAlert className="h-3 w-3" /> redacted: {m.meta.redacted.join(', ')}</Chip>}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
        {busy && <div className="flex items-center gap-2 font-mono text-xs text-cyan-300"><Loader2 className="h-3.5 w-3.5 animate-spin" /> agents thinking…</div>}
        <div ref={end} />
      </div>
      <div className="mt-3 flex flex-wrap gap-1.5">
        {PROMPTS.map((p) => <button key={p} className="rounded-full border border-edge px-2.5 py-1 text-[11px] text-slate-400 hover:border-cyan-400/40 hover:text-cyan-300" onClick={() => send(p)} disabled={busy}>{p}</button>)}
      </div>
      <ErrorBox msg={error} />
      <form onSubmit={submit} className="mt-3 flex gap-2">
        <input className="input" value={text} onChange={(e) => setText(e.target.value)} maxLength={1000} placeholder="Type a question (PAN, phone, Aadhaar are auto-redacted)…" aria-label="Message" />
        <button className="btn-primary" disabled={busy || !text.trim()} aria-label="Send"><Send className="h-4 w-4" /></button>
      </form>
    </Panel>
  )
}

export default function Agents() {
  return (
    <div>
      <PageHead kicker="Orchestrator · 8 agents" title="AI Agent Console">
        Agents do the bank-mitra’s legwork — for free, under your consent, with every step sealed in the audit ledger. They draft; you decide.
      </PageHead>
      <NeedBusiness>{(b) => (
        <div className="grid gap-5 xl:grid-cols-2">
          <Pipeline b={b} />
          <Chat key={b.id} b={b} />
        </div>
      )}</NeedBusiness>
    </div>
  )
}
