import { ChevronRight, ShieldCheck } from 'lucide-react'
import { useEffect, useState } from 'react'

const CHECKS = [
  ['TLS channel · HttpOnly / SameSite=Strict session', 'SECURE'],
  ['AES-256-GCM envelope vault · per-owner keys', 'SEALED'],
  ['Consent registry · purpose & scope bound', 'ONLINE'],
  ['Ed25519 hash-chained audit ledger', 'VERIFIED'],
  ['Scheme rulebook · 8 schemes with citations', 'LOADED'],
  ['Risk model calibration & fairness monitors', 'ARMED'],
  ['8 cooperative AI agents', 'READY'],
]

export default function Boot({ onDone }: { onDone: () => void }) {
  const [n, setN] = useState(0)
  const [health, setHealth] = useState<boolean | null>(null)

  useEffect(() => {
    fetch('/api/health', { cache: 'no-store' }).then((r) => setHealth(r.ok)).catch(() => setHealth(false))
    const t = setInterval(() => setN((x) => (x >= CHECKS.length ? x : x + 1)), 260)
    return () => clearInterval(t)
  }, [])
  const done = n >= CHECKS.length

  return (
    <div className="grid-bg fixed inset-0 z-[2000] flex items-center justify-center overflow-hidden bg-void p-4">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-40 animate-scan bg-gradient-to-b from-transparent via-cyan-400/10 to-transparent" />
      <div className="pointer-events-none absolute h-[620px] w-[620px] animate-spinSlow rounded-full border border-dashed border-cyan-400/10" />
      <div className="pointer-events-none absolute h-[460px] w-[460px] animate-spinSlow rounded-full border border-neon-magenta/10 [animation-direction:reverse]" />
      <div className="panel-hot corner relative w-full max-w-xl p-7">
        <div className="flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-400 to-neon-magenta text-void">
            <ShieldCheck className="h-7 w-7" />
          </div>
          <div>
            <div className="h-display text-3xl font-black text-white">ARTHA</div>
            <div className="label text-cyan-300">Agentic Credit Command · Secure boot</div>
          </div>
        </div>
        <div className="mt-6 space-y-2 font-mono text-xs">
          {CHECKS.map(([label, ok], i) => (
            <div key={label} className={`flex items-center justify-between transition-opacity duration-300 ${i < n ? 'opacity-100' : 'opacity-0'}`}>
              <span className="text-slate-300"><span className="text-cyan-400">▸</span> {label}</span>
              <span className="text-neon-green">[{ok}]</span>
            </div>
          ))}
          <div className={`flex items-center justify-between pt-1 transition-opacity ${done ? 'opacity-100' : 'opacity-0'}`}>
            <span className="text-slate-300"><span className="text-cyan-400">▸</span> API heartbeat</span>
            <span className={health ? 'text-neon-green' : health === false ? 'text-neon-red' : 'text-neon-amber'}>
              [{health ? 'OK' : health === false ? 'OFFLINE' : '…'}]
            </span>
          </div>
        </div>
        <div className="mt-5 h-1 overflow-hidden rounded bg-white/5">
          <div className="h-full bg-gradient-to-r from-cyan-400 to-neon-magenta transition-all duration-300" style={{ width: `${(n / CHECKS.length) * 100}%` }} />
        </div>
        <p className="mt-5 text-sm text-slate-400">
          Helping tailors, fabricators, dairy units and SHG enterprises reach the formal credit and government schemes meant for them —
          with <span className="text-cyan-300">your consent</span>, <span className="text-cyan-300">cited eligibility</span> and
          <span className="text-cyan-300"> explainable, fair</span> risk assessment.
        </p>
        <button className="btn-primary mt-6 w-full" disabled={!done} onClick={onDone} autoFocus>
          Enter Command Center <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}
