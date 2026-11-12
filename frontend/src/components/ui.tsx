import clsx from 'clsx'
import { AlertTriangle, CheckCircle2, CircleHelp, ExternalLink, Loader2, X, XCircle } from 'lucide-react'
import { useEffect, type ReactNode } from 'react'
import type { Citation } from '../lib/types'

export function Panel({ title, icon, right, children, className, hot, bodyClass }: {
  title?: ReactNode; icon?: ReactNode; right?: ReactNode; children: ReactNode; className?: string; hot?: boolean; bodyClass?: string
}) {
  return (
    <section className={clsx(hot ? 'panel-hot corner' : 'panel', 'animate-rise', className)}>
      {title && (
        <header className="flex items-center justify-between gap-3 border-b border-edge/70 px-4 py-3">
          <h3 className="flex items-center gap-2 font-display text-[11px] font-bold uppercase tracking-[0.2em] text-cyan-300">
            {icon}
            {title}
          </h3>
          {right}
        </header>
      )}
      <div className={clsx('p-4', bodyClass)}>{children}</div>
    </section>
  )
}

const tones = {
  cyan: 'text-cyan-300 border-cyan-400/30 bg-cyan-400/5',
  green: 'text-neon-green border-neon-green/30 bg-neon-green/5',
  amber: 'text-neon-amber border-neon-amber/30 bg-neon-amber/5',
  red: 'text-neon-red border-neon-red/30 bg-neon-red/5',
  magenta: 'text-neon-magenta border-neon-magenta/30 bg-neon-magenta/5',
  violet: 'text-neon-violet border-neon-violet/30 bg-neon-violet/5',
  slate: 'text-slate-300 border-slate-500/30 bg-slate-500/5',
}
export type Tone = keyof typeof tones

export function Chip({ tone = 'cyan', children, className }: { tone?: Tone; children: ReactNode; className?: string }) {
  return <span className={clsx('chip', tones[tone], className)}>{children}</span>
}

export function Stat({ label, value, sub, tone = 'cyan', icon }: {
  label: string; value: ReactNode; sub?: ReactNode; tone?: Tone; icon?: ReactNode
}) {
  const color = { cyan: 'text-cyan-300', green: 'text-neon-green', amber: 'text-neon-amber', red: 'text-neon-red',
    magenta: 'text-neon-magenta', violet: 'text-neon-violet', slate: 'text-slate-200' }[tone]
  return (
    <div className="panel corner animate-rise p-4">
      <div className="flex items-start justify-between">
        <span className="label">{label}</span>
        <span className={clsx('opacity-80', color)}>{icon}</span>
      </div>
      <div className={clsx('mt-2 font-display text-2xl font-bold', color)}>{value}</div>
      {sub && <div className="mt-1 text-xs text-slate-400">{sub}</div>}
    </div>
  )
}

export function Spinner({ label = 'Loading' }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 p-6 font-mono text-xs text-cyan-300" role="status">
      <Loader2 className="h-4 w-4 animate-spin" /> {label}…
    </div>
  )
}

export function ErrorBox({ msg, onRetry }: { msg: string | null; onRetry?: () => void }) {
  if (!msg) return null
  return (
    <div role="alert" className="flex items-center justify-between gap-3 rounded-lg border border-neon-red/40 bg-neon-red/10 px-3 py-2 text-sm text-neon-red">
      <span className="flex items-center gap-2"><AlertTriangle className="h-4 w-4 shrink-0" />{msg}</span>
      {onRetry && <button className="btn-ghost !py-1 text-xs" onClick={onRetry}>Retry</button>}
    </div>
  )
}

export function Empty({ icon, title, children }: { icon?: ReactNode; title: string; children?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-10 text-center">
      <div className="text-cyan-400/70">{icon}</div>
      <div className="font-display text-sm tracking-wider text-slate-200">{title}</div>
      <div className="max-w-md text-sm text-slate-400">{children}</div>
    </div>
  )
}

export function Bar({ value, tone = 'cyan', className }: { value: number; tone?: Tone; className?: string }) {
  const c = { cyan: 'bg-cyan-400', green: 'bg-neon-green', amber: 'bg-neon-amber', red: 'bg-neon-red', magenta: 'bg-neon-magenta',
    violet: 'bg-neon-violet', slate: 'bg-slate-400' }[tone]
  return (
    <div className={clsx('h-1.5 w-full overflow-hidden rounded-full bg-white/5', className)}>
      <div className={clsx('h-full rounded-full transition-all duration-700', c)} style={{ width: `${Math.max(0, Math.min(1, value)) * 100}%` }} />
    </div>
  )
}

export function Ring({ value, size = 120, label, sub, color = '#22e3f5' }: {
  value: number; size?: number; label: ReactNode; sub?: ReactNode; color?: string
}) {
  const r = size / 2 - 9
  const c = 2 * Math.PI * r
  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} stroke="rgba(255,255,255,.06)" strokeWidth={8} fill="none" />
        <circle cx={size / 2} cy={size / 2} r={r} stroke={color} strokeWidth={8} fill="none" strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={c * (1 - Math.max(0, Math.min(1, value)))}
          style={{ filter: `drop-shadow(0 0 6px ${color})`, transition: 'stroke-dashoffset 1s ease' }} />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <div className="font-display text-2xl font-bold" style={{ color }}>{label}</div>
        {sub && <div className="label mt-0.5">{sub}</div>}
      </div>
    </div>
  )
}

export function CheckIcon({ status }: { status: string }) {
  if (status === 'pass') return <CheckCircle2 className="h-4 w-4 shrink-0 text-neon-green" aria-label="pass" />
  if (status === 'fail') return <XCircle className="h-4 w-4 shrink-0 text-neon-red" aria-label="fail" />
  return <CircleHelp className="h-4 w-4 shrink-0 text-neon-amber" aria-label="unknown" />
}

export function Cite({ c }: { c: Citation }) {
  return (
    <a href={c.url} target="_blank" rel="noopener noreferrer nofollow"
      className="inline-flex items-center gap-1 rounded border border-neon-violet/30 bg-neon-violet/5 px-1.5 py-0.5 font-mono text-[10px] text-neon-violet hover:bg-neon-violet/15"
      title={`${c.title} — ${c.section} (verified ${c.verified_on})`}>
      <ExternalLink className="h-3 w-3" /> {c.title}{c.section ? ` · ${c.section}` : ''}
    </a>
  )
}

export function Modal({ open, onClose, title, children, wide }: {
  open: boolean; onClose: () => void; title: ReactNode; children: ReactNode; wide?: boolean
}) {
  useEffect(() => {
    if (!open) return
    const k = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', k)
    return () => window.removeEventListener('keydown', k)
  }, [open, onClose])
  if (!open) return null
  return (
    <div className="fixed inset-0 z-[1000] flex items-center justify-center bg-void/80 p-4 backdrop-blur-sm" onClick={onClose}>
      <div role="dialog" aria-modal="true" className={clsx('panel-hot corner max-h-[90vh] w-full overflow-y-auto', wide ? 'max-w-4xl' : 'max-w-lg')}
        onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b border-edge px-5 py-3">
          <h3 className="font-display text-sm font-bold uppercase tracking-[0.18em] text-cyan-300">{title}</h3>
          <button className="text-slate-400 hover:text-white" onClick={onClose} aria-label="Close"><X className="h-5 w-5" /></button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  )
}

export function PageHead({ kicker, title, children, right }: { kicker: string; title: string; children?: ReactNode; right?: ReactNode }) {
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
      <div>
        <div className="label text-cyan-400/80">{kicker}</div>
        <h1 className="h-display mt-1 text-2xl font-bold text-white md:text-3xl">{title}</h1>
        {children && <p className="mt-1.5 max-w-3xl text-sm text-slate-400">{children}</p>}
      </div>
      {right}
    </div>
  )
}

export function Field({ label, children, hint }: { label: string; children: ReactNode; hint?: ReactNode }) {
  return (
    <label className="block">
      <span className="label mb-1.5 block">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-[11px] text-slate-500">{hint}</span>}
    </label>
  )
}

export const statusTone = (s: string): Tone =>
  ({ eligible: 'green', likely: 'amber', ineligible: 'red', active: 'green', revoked: 'red', expired: 'slate',
     sanctioned: 'green', rejected: 'red', withdrawn: 'slate', submitted: 'cyan', under_review: 'violet',
     docs_requested: 'amber', awaiting_owner_approval: 'magenta', draft: 'slate', uploaded: 'green', fetched: 'green',
     fetchable: 'cyan', auto: 'violet', after_sanction: 'slate', missing: 'red', ok: 'green', warn: 'amber',
     blocked: 'red', skipped: 'slate' } as Record<string, Tone>)[s] ?? 'slate'

export const chartTheme = {
  grid: 'rgba(148,163,184,.08)',
  axis: { fontSize: 10, fill: '#64748b', fontFamily: 'JetBrains Mono' },
  tooltip: { background: '#0b1628', border: '1px solid #16263f', borderRadius: 8, fontSize: 12, color: '#e2e8f0' },
}
