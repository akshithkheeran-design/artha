import { AlertTriangle, BadgeCheck, Banknote, FileCheck2, Landmark, Radio, ShieldCheck, TrendingDown, Users } from 'lucide-react'
import { CircleMarker, MapContainer, Polygon, Tooltip as MapTip } from 'react-leaflet'

const INDIA: [number, number][] = [[35.5,74.5],[37,75.5],[35.8,78],[34.5,78.8],[32.5,79.3],[30.9,81.2],[28.9,80.2],[27.4,83.5],[26.5,87.9],[27.9,88.2],[28.2,92],[29.4,95.5],[28.2,97.3],[26,95.2],[24.2,94.2],[23.1,93.4],[22.1,92.6],[23.5,91.8],[25.2,92],[25.1,89.8],[22.4,89.1],[21.6,87.2],[19.7,85.6],[18,83.4],[16.3,81.3],[15.5,80.2],[13.3,80.3],[10.3,79.8],[8.1,77.5],[8.9,76.5],[11.2,75.7],[14.5,74.4],[17.6,73.2],[20.5,72.8],[21.3,72.6],[22.3,69.2],[23.6,68.2],[24.5,71.1],[26.8,70.1],[28,71.9],[30.1,73.9],[32.5,74.6],[34,73.9]]
import { Bar as RBar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Bar, Chip, ErrorBox, PageHead, Panel, Spinner, Stat, chartTheme } from '../components/ui'
import { useAuth } from '../lib/auth'
import { inr, pct, title } from '../lib/format'
import { useApi } from '../lib/hooks'

interface Overview {
  kpis: Record<string, number>
  funnel: { stage: string; count: number }[]
  status: { status: string; count: number }[]
  sectors: { sector: string; count: number }[]
  districts: { district: string; state: string; lat: number; lng: number; count: number; eligible: number; sectors: Record<string, number> }[]
  score_distribution: { band: string; count: number }[]
  feed: { ts: string; action: string; role: string; hash: string }[]
}
const BAND_COLORS: Record<string, string> = { A: '#2bff9e', B: '#22e3f5', C: '#ffc93d', D: '#ff8a3d', E: '#ff4d6d' }
const STAKEHOLDERS = [
  { name: 'Bank branches & NBFCs', does: 'See a complete, consented, explainable file — not a stack of photocopies.', icon: Landmark },
  { name: 'DICs & scheme agencies', does: 'Receive PMEGP / scheme files pre-checked against cited rules.', icon: BadgeCheck },
  { name: 'Business correspondents', does: 'Assist owners only under a scoped consent — fees made transparent.', icon: Users },
  { name: 'SHG federations', does: 'Turn SHG books and group history into NRLM linkage files.', icon: Radio },
]

export default function CommandCenter() {
  const { user } = useAuth()
  const { data, error, loading, reload } = useApi<Overview>('/analytics/overview')
  if (loading && !data) return <Spinner label="Linking agents" />
  if (error) return <ErrorBox msg={error} onRetry={reload} />
  if (!data) return null
  const k = data.kpis
  const maxFunnel = Math.max(...data.funnel.map((f) => f.count), 1)

  return (
    <div className="space-y-5">
      <PageHead kicker={`Welcome, ${user?.display_name}`} title="Command Center"
        right={<Chip tone="green"><ShieldCheck className="h-3 w-3" /> Aggregates only · no personal data</Chip>}>
        Live view of how viable small businesses move from invisible to bankable — schemes matched with citations, consented cash-flow
        files, owner-approved applications and stalled files that need a nudge.
      </PageHead>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Businesses onboarded" value={k.businesses} sub={`${k.consents_active} active consents`} icon={<Users className="h-5 w-5" />} />
        <Stat label="Schemes matched" value={k.schemes_matched} sub={`${k.avg_schemes_per_business} per business · all cited`} tone="green" icon={<Landmark className="h-5 w-5" />} />
        <Stat label="Documents per file" value={`${k.avg_documents} vs ${k.traditional_documents}`} sub="Auto-fetched via DigiLocker / AA" tone="violet" icon={<FileCheck2 className="h-5 w-5" />} />
        <Stat label="Middleman fees avoided" value={inr(k.middleman_fees_avoided)} sub={`Est. at 12.5% of ${k.applications} files`} tone="magenta" icon={<Banknote className="h-5 w-5" />} />
        <Stat label="Credit-ready share" value={pct(k.credit_ready_share)} sub={`Avg score ${k.avg_score} / 900`} tone="cyan" icon={<BadgeCheck className="h-5 w-5" />} />
        <Stat label="Interest saved / yr" value={inr(k.annual_interest_saving)} sub="Moneylender debt → scheme loans" tone="green" icon={<TrendingDown className="h-5 w-5" />} />
        <Stat label="Stalled files" value={k.stalled} sub="Past their SLA — nudges sent" tone={k.stalled ? 'amber' : 'green'} icon={<AlertTriangle className="h-5 w-5" />} />
        <Stat label="Sanctioned" value={inr(k.sanctioned_amount)} sub={`Avg file completeness ${pct(k.avg_completeness)}`} tone="green" icon={<Banknote className="h-5 w-5" />} />
      </div>

      <div className="grid gap-5 xl:grid-cols-[1.6fr_1fr]">
        <Panel title="Enterprise map · scheme coverage" icon={<Radio className="h-3.5 w-3.5" />} bodyClass="p-0"
          right={<span className="label">{data.districts.length} districts</span>}>
          <div className="h-[380px] overflow-hidden rounded-b-xl">
            <MapContainer center={[22, 81]} zoom={4.2} zoomSnap={0.2} scrollWheelZoom={false} className="h-full w-full" attributionControl={false}>
              <Polygon positions={INDIA} pathOptions={{ color: '#22e3f5', weight: 1.2, opacity: 0.7, fillColor: '#22e3f5', fillOpacity: 0.06, dashArray: '3 4' }} interactive={false} />
              {data.districts.map((d) => (
                <CircleMarker key={d.district} center={[d.lat, d.lng]} radius={7 + d.eligible * 2.2}
                  pathOptions={{ color: d.eligible ? '#22e3f5' : '#ff3df2', fillColor: d.eligible ? '#22e3f5' : '#ff3df2', fillOpacity: 0.35, weight: 1.5 }}>
                  <MapTip>
                    <div className="text-xs">
                      <b>{d.district}</b>, {d.state}<br />
                      {d.count} business{d.count > 1 ? 'es' : ''} · {d.eligible} scheme matches<br />
                      {Object.keys(d.sectors).map(title).join(', ')}
                    </div>
                  </MapTip>
                </CircleMarker>
              ))}
            </MapContainer>
          </div>
        </Panel>

        <Panel title="Journey funnel" icon={<TrendingDown className="h-3.5 w-3.5" />}>
          <div className="space-y-3">
            {data.funnel.map((f, i) => (
              <div key={f.stage}>
                <div className="mb-1 flex justify-between text-xs">
                  <span className="text-slate-300">{i + 1}. {title(f.stage)}</span>
                  <span className="font-mono text-cyan-300">{f.count}</span>
                </div>
                <Bar value={f.count / maxFunnel} tone={i === data.funnel.length - 1 ? 'green' : i === 4 ? 'magenta' : 'cyan'} />
              </div>
            ))}
          </div>
          <p className="mt-4 rounded-lg border border-neon-magenta/20 bg-neon-magenta/5 p-3 text-xs text-slate-300">
            <b className="text-neon-magenta">Hard gate:</b> nothing moves from “applied” to a lender until the owner reviews the file and approves it with their password.
          </p>
        </Panel>
      </div>

      <div className="grid gap-5 lg:grid-cols-3">
        <Panel title="Credit-readiness bands" icon={<BadgeCheck className="h-3.5 w-3.5" />}>
          <div className="h-48">
            <ResponsiveContainer>
              <BarChart data={data.score_distribution}>
                <XAxis dataKey="band" tick={chartTheme.axis} axisLine={false} tickLine={false} />
                <YAxis tick={chartTheme.axis} axisLine={false} tickLine={false} allowDecimals={false} width={24} />
                <Tooltip contentStyle={chartTheme.tooltip} cursor={{ fill: 'rgba(34,227,245,.05)' }} />
                <RBar dataKey="count" radius={[4, 4, 0, 0]}>
                  {data.score_distribution.map((d) => <Cell key={d.band} fill={BAND_COLORS[d.band]} />)}
                </RBar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <p className="text-xs text-slate-500">Bands are decision support — no borrower is auto-rejected by the model.</p>
        </Panel>
        <Panel title="Application status" icon={<FileCheck2 className="h-3.5 w-3.5" />}>
          <div className="space-y-2">
            {data.status.map((s) => (
              <div key={s.status} className="flex items-center justify-between rounded-lg border border-edge/70 px-3 py-2 text-sm">
                <span>{title(s.status)}</span><span className="font-mono text-cyan-300">{s.count}</span>
              </div>
            ))}
          </div>
          <div className="mt-3 label">Sectors</div>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {data.sectors.map((s) => <Chip key={s.sector} tone="violet">{title(s.sector)} · {s.count}</Chip>)}
          </div>
        </Panel>
        <Panel title="Live audit feed" icon={<Radio className="h-3.5 w-3.5 animate-pulseDot" />}>
          <ul className="max-h-64 space-y-1.5 overflow-y-auto pr-1 font-mono text-[11px]">
            {data.feed.map((f) => (
              <li key={f.hash} className="flex items-center gap-2 border-b border-edge/40 pb-1.5">
                <span className="text-slate-500">{new Date(f.ts).toLocaleTimeString('en-IN', { hour12: false })}</span>
                <span className="truncate text-slate-200">{f.action}</span>
                <span className="ml-auto text-neon-violet">{f.hash}</span>
              </li>
            ))}
          </ul>
        </Panel>
      </div>

      <Panel title="Who else is in the picture" icon={<Users className="h-3.5 w-3.5" />}>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {STAKEHOLDERS.map((s) => (
            <div key={s.name} className="rounded-lg border border-edge p-3">
              <s.icon className="h-5 w-5 text-cyan-400" />
              <div className="mt-2 text-sm font-semibold text-white">{s.name}</div>
              <div className="mt-1 text-xs text-slate-400">{s.does}</div>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  )
}
