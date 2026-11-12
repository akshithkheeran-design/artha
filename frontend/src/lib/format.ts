export const inr = (n: number | null | undefined) => {
  if (n === null || n === undefined || Number.isNaN(n)) return '—'
  const a = Math.abs(n)
  if (a >= 1e7) return `₹${(n / 1e7).toFixed(2)} Cr`
  if (a >= 1e5) return `₹${(n / 1e5).toFixed(2)} L`
  return `₹${Math.round(n).toLocaleString('en-IN')}`
}
export const inrFull = (n: number) => `₹${Math.round(n).toLocaleString('en-IN')}`
export const pct = (n: number | null | undefined, d = 0) => (n === null || n === undefined ? '—' : `${(n * 100).toFixed(d)}%`)
export const title = (s: string) => s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
export const dt = (s: string) => {
  const d = new Date(s.endsWith('Z') || s.includes('+') ? s : `${s}Z`)
  return d.toLocaleString('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
}
export const day = (s: string) => {
  const d = new Date(s.endsWith('Z') || s.includes('+') ? s : `${s}Z`)
  return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
}
export const short = (h: string | null | undefined, n = 10) => (h ? `${h.slice(0, n)}…` : '—')
