export type Role = 'entrepreneur' | 'agent' | 'lender' | 'dic' | 'auditor'
export interface User { id: number; email: string; role: Role; display_name: string; org: string | null }

export interface Profile {
  owner_name?: string; phone?: string; pan?: string; aadhaar_last4?: string; udyam_number?: string
  gender?: string; social_category?: string; age?: number; education?: string
  is_new_unit?: boolean; is_first_venture?: boolean; prior_default?: boolean; is_shg?: boolean
  shg_months_active?: number; shg_books_maintained?: boolean; artisan_trade?: string | null
  street_vendor?: boolean; has_itr?: boolean; has_audited_statements?: boolean
  [k: string]: unknown
}
export interface Business {
  id: number; name: string; sector: string; activity_type: string; state: string; district: string; region: string
  area: string; lat: number; lng: number; years_in_operation: number; employees: number; loan_need: number
  loan_purpose: string; shredded: boolean; profile?: Profile | null
}
export interface Citation { title: string; url: string; section: string; verified_on: string }
export interface Check { rule: string; status: 'pass' | 'fail' | 'unknown'; detail: string; citation: Citation }
export interface SchemeResult {
  scheme_id: string; name: string; short: string; agency: string; status: 'eligible' | 'likely' | 'ineligible'
  match: number; indicative_amount: number | null; note?: string; benefit: string; typical_rate: string
  checks: Check[]; citations: Citation[]; documents: string[]; next_step: string
}
export interface Factor { feature: string; label: string; value: number; impact: number; direction: string }
export interface Risk {
  available: boolean; reason?: string; model_version: string; pd: number; pd_interval_90: [number, number]; score: number
  band: string; credit_ready: boolean; confidence: string; factors: Factor[]; reason_codes: string[]; strengths: string[]
  suggestions: { action: string; feature: string; new_pd: number; new_score: number }[]
  protected_attributes_used: boolean; note: string; features: Record<string, number>
}
export interface DocItem {
  doc_type: string; label: string; status: string; required_by: string[]; auto_source: string | null; document_id: number | null
}
export interface DocChecklist {
  schemes: string[]; items: DocItem[]
  stats: { traditional: number; required: number; ready: number; auto_fetchable: number; owner_must_upload: number; completeness: number }
}
export interface CashSummary {
  avg_monthly_inflow: number; avg_monthly_outflow: number; transactions: number; months: number
  stressed_monthly_surplus: number; sustainable_emi: number; suggested_loan_36m: number
  informal_monthly_repayment: number; informal_principal_estimate: number; annual_interest_saving: number
  informal_rate_assumed: number; scheme_rate_assumed: number
}
export interface Cashflow {
  available: boolean; reason?: string
  dataset: { id: number; source: string; rows: number; uploaded_at: string; sha256: string }
  features: Record<string, number>
  monthly: { month: string; inflow: number; outflow: number; obligations: number; payers: number }[]
  summary: CashSummary; categories: { category: string; amount: number }[]; insights: string[]
}
export interface Consent {
  id: number; grantee_type: string; grantee_org: string; purpose: string; purpose_text: string; scopes: string[]
  status: string; granted_at: string; expires_at: string; revoked_at: string | null; artefact_hash: string; signature: string
}
export interface ConsentCatalog {
  purposes: Record<string, string>; scopes: Record<string, string>; platform_org: string; agents: string[]
  lenders: { org: string; type: string; kind: string }[]
}
export interface TimelineEvent { status: string; note: string; actor: string; at: string }
export interface Application {
  id: number; ref: string; business_id: number; business_name: string; district: string; sector: string
  scheme_id: string; scheme: string; lender_org: string; amount: number; status: string; completeness: number
  created_at: string; updated_at: string; approved_at: string | null; snapshot_hash: string | null
  approval_signature: string | null; decision_reason: string | null; decision_reason_text: string | null
  timeline: TimelineEvent[]; stall: { days_in_status: number; limit: number; stalled: boolean; nudge: string } | null
  consent_id: number | null
  snapshot?: {
    amount: number; applicant: Record<string, string | number>; cashflow?: Partial<CashSummary> | null
    completeness: number; documents: DocItem[]; risk?: Partial<Risk> | null; eligibility?: Partial<SchemeResult> | null
    [k: string]: unknown
  } | null
}
export interface AuditEntry {
  id: number; ts: string; actor_role: string; action: string; business_id: number | null
  details: Record<string, unknown>; prev_hash: string; hash: string; signature: string
}
export interface AgentStep { id?: string; name: string; status: string; summary: string; detail?: unknown; ms?: number }
