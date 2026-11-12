import clsx from 'clsx'
import {
  Activity, Bot, Building2, Calculator, ClipboardList, FileStack, Fingerprint, Gauge, KeyRound, Landmark, LogOut,
  Menu, Radar, Scale, ScrollText, ShieldCheck, Wallet, X,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../lib/auth'
import { useStaticDemo } from '../lib/hooks'
import { useBusiness } from '../lib/business'
import type { Role } from '../lib/types'
import { Chip } from './ui'

type Item = { to: string; label: string; icon: typeof Radar; roles?: Role[] }
const OWN: Role[] = ['entrepreneur', 'agent']
const NAV: { group: string; items: Item[] }[] = [
  { group: 'Command', items: [
    { to: '/', label: 'Command Center', icon: Radar },
    { to: '/agents', label: 'AI Agent Console', icon: Bot, roles: OWN },
  ] },
  { group: 'My Business', items: [
    { to: '/schemes', label: 'Scheme Navigator', icon: Landmark, roles: OWN },
    { to: '/cashflow', label: 'Cash-flow Intel', icon: Wallet, roles: OWN },
    { to: '/risk', label: 'Credit Readiness', icon: Gauge, roles: OWN },
    { to: '/documents', label: 'Document Vault', icon: FileStack, roles: OWN },
    { to: '/applications', label: 'Applications', icon: ClipboardList, roles: ['entrepreneur', 'agent', 'lender', 'dic'] },
    { to: '/consent', label: 'Consent & Privacy', icon: KeyRound, roles: ['entrepreneur'] },
    { to: '/onboard', label: 'Add Business', icon: Building2, roles: ['entrepreneur'] },
  ] },
  { group: 'Ecosystem', items: [
    { to: '/money', label: 'Following the Money', icon: Calculator },
    { to: '/field', label: 'Field Research', icon: Activity },
  ] },
  { group: 'Governance', items: [
    { to: '/model', label: 'Model & Fairness', icon: Scale },
    { to: '/audit', label: 'Audit Trail', icon: ScrollText },
  ] },
]

const ROLE_LABEL: Record<Role, string> = {
  entrepreneur: 'Entrepreneur', agent: 'Business Correspondent', lender: 'Bank / NBFC', dic: 'DIC / Scheme agency', auditor: 'Auditor',
}

function Clock() {
  const [t, setT] = useState(new Date())
  useEffect(() => {
    const i = setInterval(() => setT(new Date()), 1000)
    return () => clearInterval(i)
  }, [])
  return <span className="font-mono text-xs text-slate-400">{t.toLocaleTimeString('en-IN', { hour12: false, timeZone: 'Asia/Kolkata' })} IST</span>
}

export default function Layout() {
  const demo = useStaticDemo()
  const { user, logout } = useAuth()
  const { businesses, current, select } = useBusiness()
  const [open, setOpen] = useState(false)
  const loc = useLocation()
  useEffect(() => {
    setOpen(false)
  }, [loc.pathname])
  if (!user) return null

  return (
    <div className="flex min-h-full">
      <aside className={clsx(
        'fixed inset-y-0 left-0 z-[900] flex w-64 flex-col border-r border-edge bg-abyss/95 backdrop-blur-xl transition-transform lg:translate-x-0',
        open ? 'translate-x-0' : '-translate-x-full')}>
        <div className="flex items-center gap-3 border-b border-edge px-5 py-4">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-cyan-400 to-neon-magenta font-display text-lg font-black text-void">A</div>
          <div>
            <div className="h-display text-lg font-black leading-none text-white">ARTHA</div>
            <div className="label mt-1 !text-[9px] text-cyan-400/80">Agentic Credit Command</div>
          </div>
          <button className="ml-auto text-slate-400 lg:hidden" onClick={() => setOpen(false)} aria-label="Close menu"><X className="h-5 w-5" /></button>
        </div>
        <nav className="flex-1 space-y-5 overflow-y-auto px-3 py-4">
          {NAV.map((g) => {
            const items = g.items.filter((i) => !i.roles || i.roles.includes(user.role))
            if (!items.length) return null
            return (
              <div key={g.group}>
                <div className="label mb-2 px-2 !text-[9px]">{g.group}</div>
                {items.map((i) => (
                  <NavLink key={i.to} to={i.to} end={i.to === '/'}
                    className={({ isActive }) => clsx(
                      'group mb-0.5 flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition',
                      isActive ? 'bg-cyan-400/10 text-cyan-300 shadow-[inset_2px_0_0_#22e3f5]' : 'text-slate-400 hover:bg-white/[0.03] hover:text-slate-100')}>
                    <i.icon className="h-4 w-4" />
                    {i.label}
                  </NavLink>
                ))}
              </div>
            )
          })}
        </nav>
        <div className="m-3 rounded-lg border border-neon-green/20 bg-neon-green/[0.04] p-3 font-mono text-[10px] leading-relaxed text-slate-400">
          <div className="mb-1 flex items-center gap-1.5 text-neon-green"><ShieldCheck className="h-3.5 w-3.5" /> DATA PROTECTION ACTIVE</div>
          <div>Vault · AES-256-GCM</div>
          <div>Ledger · SHA-256 + Ed25519</div>
          <div>Access · consent-gated</div>
        </div>
      </aside>
      {open && <div className="fixed inset-0 z-[800] bg-void/70 lg:hidden" onClick={() => setOpen(false)} />}

      <div className="flex min-w-0 flex-1 flex-col lg:pl-64">
        <header className="sticky top-0 z-[700] flex flex-wrap items-center gap-3 border-b border-edge bg-void/80 px-4 py-2.5 backdrop-blur-xl md:px-6">
          <button className="text-slate-300 lg:hidden" onClick={() => setOpen(true)} aria-label="Open menu"><Menu className="h-5 w-5" /></button>
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 animate-pulseDot rounded-full bg-neon-green" />
            <span className="label hidden sm:inline">{demo ? 'Static demo · synthetic data' : 'Systems nominal'}</span>
          </div>
          <Clock />
          {businesses.length > 0 && (
            <label className="ml-auto flex items-center gap-2">
              <span className="label hidden md:inline">Business</span>
              <select className="input !w-auto max-w-[220px] !py-1.5" value={current?.id ?? ''} onChange={(e) => select(Number(e.target.value))}>
                {businesses.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
              </select>
            </label>
          )}
          <div className={clsx('flex items-center gap-3', businesses.length === 0 && 'ml-auto')}>
            <div className="hidden text-right md:block">
              <div className="text-sm font-medium text-slate-100">{user.display_name}</div>
              <div className="font-mono text-[10px] text-slate-500">{user.org ?? user.email}</div>
            </div>
            <Chip tone={user.role === 'entrepreneur' ? 'cyan' : user.role === 'auditor' ? 'violet' : 'magenta'}>
              <Fingerprint className="h-3 w-3" /> {ROLE_LABEL[user.role]}
            </Chip>
            <button className="btn-ghost !px-2.5 !py-1.5" onClick={logout} aria-label="Sign out" title="Sign out"><LogOut className="h-4 w-4" /></button>
          </div>
        </header>
        <main className="grid-bg flex-1 px-4 py-6 md:px-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
