import { Link2, ScrollText, ShieldCheck, ShieldX } from 'lucide-react'
import { Chip, ErrorBox, PageHead, Panel, Spinner } from '../components/ui'
import { dt, short } from '../lib/format'
import { useApi } from '../lib/hooks'
import type { AuditEntry } from '../lib/types'

interface Verify { valid: boolean; entries: number; head: string; public_key_ed25519: string; algorithm: string; broken_at?: number }

export default function Audit() {
  const { data, error, loading, reload } = useApi<AuditEntry[]>('/audit?limit=200')
  const { data: v, reload: reverify } = useApi<Verify>('/audit/verify')
  return (
    <div className="space-y-5">
      <PageHead kicker="Audit Sentinel" title="Tamper-evident audit trail"
        right={<button className="btn-ghost" onClick={() => { reload(); reverify() }}><ShieldCheck className="h-4 w-4" /> Re-verify chain</button>}>
        Every consent, data access, agent run and decision is hash-chained and signed. Entries record what happened — never the personal data itself.
      </PageHead>
      {v && (
        <Panel hot>
          <div className="flex flex-wrap items-center gap-4">
            {v.valid ? <ShieldCheck className="h-10 w-10 text-neon-green" /> : <ShieldX className="h-10 w-10 text-neon-red" />}
            <div>
              <div className={`font-display text-lg font-bold ${v.valid ? 'text-neon-green' : 'text-neon-red'}`}>{v.valid ? 'CHAIN INTACT' : `CHAIN BROKEN${v.broken_at ? ` AT #${v.broken_at}` : ''}`}</div>
              <div className="text-xs text-slate-400">{v.entries} entries · {v.algorithm}</div>
            </div>
            <div className="ml-auto space-y-1 font-mono text-[10px] text-slate-400">
              <div>head {short(v.head, 40)}</div>
              <div>ed25519 pub {v.public_key_ed25519}</div>
            </div>
          </div>
        </Panel>
      )}
      <Panel title="Ledger" icon={<ScrollText className="h-3.5 w-3.5" />}>
        {loading && !data ? <Spinner /> : error ? <ErrorBox msg={error} onRetry={reload} /> : (
          <div className="max-h-[560px] overflow-auto">
            <table className="w-full min-w-[760px] text-xs">
              <thead className="sticky top-0 bg-panel"><tr className="label text-left"><th className="py-2 font-normal">#</th><th className="font-normal">Time</th><th className="font-normal">Role</th><th className="font-normal">Action</th><th className="font-normal">Details</th><th className="font-normal">Hash ← prev</th></tr></thead>
              <tbody>
                {(data ?? []).map((e) => (
                  <tr key={e.id} className="table-row">
                    <td className="py-2 font-mono text-slate-500">{e.id}</td>
                    <td className="font-mono text-slate-400">{dt(e.ts)}</td>
                    <td><Chip tone={e.actor_role === 'entrepreneur' ? 'cyan' : e.actor_role === 'system' ? 'slate' : 'magenta'}>{e.actor_role}</Chip></td>
                    <td className="font-mono text-slate-200">{e.action}</td>
                    <td className="max-w-[260px] truncate font-mono text-slate-500" title={JSON.stringify(e.details)}>{JSON.stringify(e.details)}</td>
                    <td className="font-mono text-neon-violet"><span className="inline-flex items-center gap-1">{short(e.hash, 8)} <Link2 className="h-3 w-3 text-slate-600" /> <span className="text-slate-500">{short(e.prev_hash, 8)}</span></span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </div>
  )
}
