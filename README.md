# ARTHA · Agentic Credit Command

Problem statement 3.2: viable small businesses cannot reach formal credit or the schemes meant for them.

Eight cooperating agents (Intake, Consent Guardian, Cash-flow Analyst, Scheme Navigator, Risk Assessor, Document Agent, Application Drafter, Audit Sentinel) turn UPI flows into a lender-ready file, match schemes with citations to official sources, and submit only after the owner approves.

## Data protection
- Per-owner data keys (AES-256-GCM) wrapped by a master key; profiles, cash-flow, documents and application snapshots are encrypted at rest. Erasure destroys the key (crypto-shredding).
- Purpose-, scope- and time-bound consents, Ed25519-signed and revocable; every access by a lender/agent is checked against consent and shown in the owner's access log.
- Owner approval needs an explicit confirmation plus password; lenders only see masked identifiers and the scopes the owner chose.
- Argon2 passwords, HttpOnly + SameSite=Strict session cookie, CSRF token, lockout and rate limits, strict CSP and security headers, upload magic-byte checks, PII redaction of free text.
- Hash-chained, signed audit ledger with no personal data in entries.

## Risk model
Logistic regression on cash-flow features only (gender, caste, religion, region, age excluded). Reports PD with a 90% interval, reason codes and improvements, calibration (ECE/reliability) and fairness by gender and region (disparate impact, equal-opportunity and calibration gaps). Trained on **synthetic data** — retrain and re-audit on real consented repayment data before production use.

## Run locally
```bash
cd frontend && npm ci && npm run build
cd ../backend && pip install -r requirements.txt
uvicorn app.main:app --port 8000      # serves API + built frontend
```
Dev mode: `npm run dev` in `frontend` (proxies `/api` to port 8000). Tests: `cd backend && pytest`.

Demo accounts (synthetic, development only): `lakshmi@artha.demo`, `ravi@artha.demo`, `meena@artha.demo`, `bc@artha.demo`, `manager@artha.demo`, `dic@artha.demo`, `auditor@artha.demo` — password `Artha@Demo2026`.

## Deploy (free, one click)
ARTHA has a Python backend, so a static host alone (Netlify/GitHub Pages) cannot run it.

**Render (recommended — whole app in one service):** render.com → New → Blueprint → pick this repo → Apply. `render.yaml` builds the `Dockerfile`, generates the four secret keys and seeds the demo accounts. The free plan's disk is temporary, so demo data resets on restart.

**Netlify (frontend only):** deploy the backend on Render first, then replace `BACKEND_URL` in `netlify.toml` with its URL and import the repo in Netlify — `netlify.toml` already sets base `frontend`, build command and publish `dist`.

**Any Docker host:** `docker build -t artha . && docker run -p 8000:8000 -e ARTHA_MASTER_KEY=… -e ARTHA_JWT_SECRET=… -e ARTHA_SIGNING_SEED=… -e ARTHA_INDEX_KEY=… -e ARTHA_SEED_DEMO=true artha`

## Production
Set `ARTHA_ENV=production` and provide `ARTHA_MASTER_KEY`, `ARTHA_JWT_SECRET`, `ARTHA_SIGNING_SEED`, `ARTHA_INDEX_KEY` (32+ random characters or base64) from a secrets manager — the app refuses to start without them. Demo seeding is off by default in production; serve behind TLS (secure cookies + HSTS on), and use Postgres via `ARTHA_DATABASE_URL`.
