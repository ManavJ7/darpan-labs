# Darpan Labs SDE — Railway Deployment Checklist

Everything below is ready in code. Follow this list to go live. Fill in the **TODO** fields as you go.

## Decisions locked in
- **Scope**: SDE only (backend + frontend + Celery worker + Postgres + Redis). AI Interviewer stack stays local.
- **Platform**: Railway (all four services in one project).
- **Auth**: Google OAuth + email allowlist (env var `ALLOWED_EMAILS`).
- **Isolation**: Shared-read / owner-write. Any authenticated user can view any study; only the creator can edit/lock/simulate/delete.
- **Data**: `pg_dump` → restore the Dove study + 17 completed simulations from local `darpan` DB. Twin ChromaDB + KG files sync via S3 into Railway volume.

## What's done in code (committed as of this checklist)
- Allowlist gate in `app/services/auth_service.py:get_or_create_user` — rejected emails never create a user row.
- `require_study_owner` helper in `app/auth.py` — 403 if non-owner mutates.
- Auth dep + owner check wired into every mutation endpoint across `studies.py`, `concepts.py`, `research_design.py`, `questionnaire.py`, `simulation.py`, and `app/main.py:POST /studies`.
- `Study.created_by_user_id` FK (nullable) + Alembic migration `c4d5e6f7a8b9_add_study_ownership.py`.
- `GET /studies` supports `?mine=true` filter; response includes `created_by_user_id`.
- CORS wildcard replaced with `CORS_ORIGINS` env var (comma-separated list).
- Frontend `login/page.tsx` dev-login button now gated by `NEXT_PUBLIC_SHOW_DEV_LOGIN=true` and uses `NEXT_PUBLIC_API_URL`.
- `Dockerfile.worker` at repo root — combines AI Interviewer backend + twin-generator + study-design-engine into one container; uses `--pool=solo` (no fork, no SIGSEGV).
- Celery `task_time_limit=1800` + `task_soft_time_limit=1680` — kills stuck tasks at 30 min.
- LiteLLM `timeout=120.0` on every call — prevents the 10-min HTTP retry-storm pattern we saw with P04.
- Dashboard-FS write removed from `twin_tasks.py:544` — validation results now only flow through `validation_reports.report_data` JSONB.

---

## Tomorrow's checklist

### 1) Google Cloud Console — new OAuth 2.0 Web Client
1. Go to https://console.cloud.google.com. Create a new project called "Darpan SDE Prod" (or reuse existing).
2. APIs & Services → OAuth consent screen → External → fill app name, support email, scopes (email, profile, openid).
3. APIs & Services → Credentials → + Create Credentials → OAuth client ID → Web application.
4. Authorized JavaScript origins:
   - `https://<your-app-domain>` (e.g. `https://app.darpanlabs.com`)
   - `http://localhost:3099` (keep for dev)
5. Save. Copy the **Client ID** (ends in `.apps.googleusercontent.com`).
6. **TODO**: Client ID = `_______________________________.apps.googleusercontent.com`

### 2) OpenAI — spending cap
1. https://platform.openai.com/settings/organization/billing/limits
2. Set **hard monthly cap** to $500 (or $1000 if you want more runway).
3. Set soft cap at $300 for an email warning.
4. Reason: gpt-5.4 = ~$60 per 17-twin study. 10 accidental runs = $600. Cap is non-negotiable.

### 3) Domain DNS (if using custom domain)
- At your registrar, add:
  - `app.<yours>.com` → CNAME → `<sde-frontend>.up.railway.app` (Railway will give you this hostname)
  - `api.<yours>.com` → CNAME → `<sde-backend>.up.railway.app`
- Alternative: use Railway's auto-generated `*.up.railway.app` URLs for the beta; swap to custom later.

### 4) Railway — create project + add services
1. `railway login` (CLI) OR use the web dashboard.
2. New Project → "Darpan SDE Prod".
3. Add services (in this order):
   - **Postgres** (template → Postgres). Railway injects `DATABASE_URL` automatically.
   - **Redis** (template → Redis). Railway injects `REDIS_URL`.
   - **Backend** (GitHub repo → `/study-design-engine`, root `/study-design-engine`, Dockerfile `Dockerfile`).
   - **Frontend** (GitHub repo → `/study-design-engine/frontend`, Dockerfile).
   - **Worker** (GitHub repo root, Dockerfile `Dockerfile.worker`). Attach a Volume mounted at `/twin-generator/data` (5 GB should be plenty for the current 1.1 GB).

### 5) Set env vars (Railway dashboard → each service → Variables)

#### Backend (`sde-backend`)
```
DATABASE_URL              (auto-injected by Railway Postgres)
REDIS_URL                 (auto-injected by Railway Redis)
PORT                      (auto-injected — do not set)
GOOGLE_CLIENT_ID          = <client ID from step 1>
JWT_SECRET_KEY            = <run `openssl rand -hex 32` and paste result>
JWT_ALGORITHM             = HS256
JWT_EXPIRATION_HOURS      = 72
ALLOWED_EMAILS            = you@gmail.com,beta1@gmail.com,beta2@gmail.com
OPENAI_API_KEY            = <your OpenAI key>
ANTHROPIC_API_KEY         = <your Anthropic key>
ENVIRONMENT               = production
DEBUG                     = false
CORS_ORIGINS              = https://app.<yours>.com,https://<frontend>.up.railway.app
LLM_DEFAULT_MODEL         = gpt-5.4
```

#### Frontend (`sde-frontend`)
```
NEXT_PUBLIC_API_URL       = https://api.<yours>.com
NEXT_PUBLIC_GOOGLE_CLIENT_ID = <same client ID from step 1>
# Optional: hide the Dev Login button in prod. The backend also 404s /dev-login
# when ENVIRONMENT=production, so this is purely cosmetic.
NEXT_PUBLIC_HIDE_DEV_LOGIN = true
```

#### Worker (`sde-worker`)
```
DATABASE_URL              (auto)
REDIS_URL                 (auto)
OPENAI_API_KEY            = <same>
ANTHROPIC_API_KEY         = <same>
TWIN_DATA_DIR             = /twin-generator/data
LLM_DEFAULT_MODEL         = gpt-5.4
ENVIRONMENT               = production
OBJC_DISABLE_INITIALIZE_FORK_SAFETY = YES  (harmless on Linux, kept for macOS parity)
```

### 6) Deploy + run migrations
1. Push to GitHub. Railway auto-deploys backend + frontend + worker.
2. Backend's Dockerfile doesn't auto-run Alembic — run it once manually:
   ```
   railway run --service sde-backend alembic upgrade head
   ```
3. Verify: `psql $RAILWAY_DATABASE_URL -c "SELECT column_name FROM information_schema.columns WHERE table_name='studies' AND column_name='created_by_user_id';"` — should return one row.

### 7) Restore the Dove study data
```bash
# On local machine:
pg_dump -Fc darpan \
  -f darpan.dump \
  --exclude-table=users \
  --exclude-table=alembic_version

# Upload via Railway CLI (or use a one-shot job pod):
railway run --service sde-backend \
  pg_restore -d "$DATABASE_URL" \
  --no-owner --no-privileges \
  /tmp/darpan.dump
```
Excluding `users` so the prod DB starts with an empty users table; on your first Google sign-in (with your email in `ALLOWED_EMAILS`), your user row is created. Then backfill:
```sql
UPDATE studies
SET created_by_user_id = (SELECT id FROM users WHERE email = 'YOUR_EMAIL@gmail.com')
WHERE created_by_user_id IS NULL;
```

### 8) Populate twin volume
Twin data (~1.1 GB) must be copied to the `/twin-generator/data` volume on `sde-worker`. Two paths:

**Simpler — one-shot upload via worker shell**:
```bash
# tar it up locally
cd twin-generator
tar czf /tmp/twin-data.tar.gz data/

# Railway doesn't let you scp into a volume directly; shell into worker and pull:
railway shell --service sde-worker
# inside the container — point at a publicly hosted tar if easier, or use S3:
aws s3 cp s3://<your-bucket>/twin-data.tar.gz .
tar xzf twin-data.tar.gz -C /
```

**S3 path (repeatable)**:
1. Create S3 bucket `darpan-twin-data-prod` (private). Upload `twin-generator/data/` contents.
2. Add `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` to the worker env.
3. Worker Dockerfile stays unchanged — sync on boot via a tiny wrapper script (optional; for now a one-time manual `aws s3 sync` from `railway run` is fine).

### 9) First-time verification
1. `curl https://api.<yours>.com/health` → `{"status":"healthy"}`
2. Open `https://app.<yours>.com/login` → Google sign-in with `ALLOWED_EMAILS`-listed email → lands on dashboard.
3. Sign-in with a NON-listed email → should see 403 toast + **no user row created** (`SELECT COUNT(*) FROM users` stays at 1).
4. Open the Dove study, click a territory → results dashboard renders with real ISS scores (remember the in-progress re-run completes around 05:48 local — check that first!).
5. As a second allowlisted user, try to edit Dove's study brief → 403 (owner check working).
6. As owner, re-run simulation → worker picks it up, status progresses running → completed inside ~70 min.

### 10) Post-launch ops hygiene
- Set up Railway **spend alerts** at $30/mo, $50/mo, $80/mo.
- Pin OpenAI dashboard + Railway dashboard to your home screen — check daily during the first week.
- Rotate `JWT_SECRET_KEY` on a quarterly schedule (users will need to re-login).

---

## What I did NOT automate (because you chose to)
- Google OAuth client creation (step 1) — needs your Google account.
- OpenAI spending cap (step 2) — needs your billing dashboard.
- DNS (step 3) — your registrar.
- Railway account creation and paying for plan (step 4).
- pasting the OAuth Client ID, JWT secret, and allowlist into env vars (step 5).

Everything else — code, migrations, dockerfiles, auth logic, allowlist enforcement, rank-based verdict, validation-retry loop, scale-enforced prompts — is in the repo and ready to deploy.
