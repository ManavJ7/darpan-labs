# Deploying the `/try` Site to Railway

Single source of truth for getting `try.darpanlabs.ai` live. Follow top to bottom. You will do the clicking on Railway and Namecheap; I (Claude) have already written and pushed the code.

---

## What gets deployed

Three services in one Railway project:

| Service | Repo path | Purpose |
|---|---|---|
| `sde-api` | `study-design-engine/` | FastAPI backend (port 8001 → Railway `$PORT`) |
| `sde-frontend` | `study-design-engine/frontend/` | Next.js 16 UI (port 3000 → Railway `$PORT`) |
| `sde-validation` | `validation-dashboard/dove-dashboard/` | Static Dove validation dashboard (Vite build served via `serve`) |
| `postgres` | (Railway managed) | Shared DB for users + studies + twins |
| `redis` | (Railway managed) | Celery broker + rate-limit counters |

The Celery worker for twin simulations is **deferred** — v1 of the /try site lets visitors design new studies and explore the seeded Dove results, but runs no new simulations. Adding the worker later is a single extra service, see the last section.

---

## 1. Create the Railway project

1. Log in at [railway.app](https://railway.app) with `manavrajeshjain@gmail.com`.
2. Make sure you're on the **Hobby** plan (Account Settings → Billing).
3. Click **New Project** → **Empty Project**. Name it `darpan-try`.

## 2. Add the managed databases

In the project canvas:

1. Click **+ New** → **Database** → **Add PostgreSQL**. Wait 30s for it to provision.
2. Click **+ New** → **Database** → **Add Redis**. Wait 30s.

Both services auto-generate `DATABASE_URL` and `REDIS_URL` env vars that other services in the project can reference.

## 3. Add the backend service

1. Click **+ New** → **GitHub Repo** → connect GitHub → pick `ManavJ7/darpan-labs`.
2. Railway will start detecting the repo. Before it builds:
   - Click the new service → **Settings** → **Source** → set **Root Directory** to `study-design-engine`. Railway will pick up `study-design-engine/Dockerfile`.
   - In **Settings** → **Networking**, enable **Public Networking** (generates a `*.up.railway.app` URL). We'll attach the custom domain later.
3. **Variables** tab — add all of these. For the two `${{ ... }}` references, Railway auto-completes them:

   | Key | Value |
   |---|---|
   | `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` |
   | `REDIS_URL` | `${{Redis.REDIS_URL}}` |
   | `OPENAI_API_KEY` | paste the same key from your local `.env` |
   | `ANTHROPIC_API_KEY` | (optional, leave empty if not using Claude) |
   | `JWT_SECRET_KEY` | run `openssl rand -hex 32` on your machine, paste output |
   | `ENVIRONMENT` | `production` |
   | `DEBUG` | `false` |
   | `SHARED_LOGIN_USERNAME` | `darpantry` |
   | `SHARED_LOGIN_PASSWORD` | `bezosisbad` |
   | `CORS_ORIGINS` | `https://try.darpanlabs.ai,https://try.darpanlabs.com` |
   | `GOOGLE_CLIENT_ID` | (leave blank — Google login is dormant) |
   | `ALLOWED_EMAILS` | (leave blank) |

4. Click **Deploy**. Watch the build log — it should pull `python:3.11-slim`, install requirements, run `alembic upgrade head`, seed the `darpantry` user, then start uvicorn.
5. Once green, copy the public URL (something like `sde-api-production-abcd.up.railway.app`). We'll need it in step 4.

## 4. Add the frontend service

1. **+ New** → **GitHub Repo** → same repo.
2. **Settings** → **Source** → **Root Directory** = `study-design-engine/frontend`.
3. **Settings** → **Networking** → enable **Public Networking**.
4. **Variables** tab:

   | Key | Value |
   |---|---|
   | `NEXT_PUBLIC_API_URL` | `https://api.try.darpanlabs.ai` (the custom domain you'll set in step 5, **not** the `.up.railway.app` URL — it's baked into the JS bundle at build time) |
   | `NEXT_PUBLIC_VALIDATION_URL` | `https://validation.try.darpanlabs.ai` (same build-time bake — set this before the first frontend deploy) |

5. Click **Deploy**. The build will do `npm ci → npm run build → node server.js`. Takes ~2 min the first time.

## 4b. Add the validation dashboard service

1. **+ New** → **GitHub Repo** → same repo.
2. **Settings** → **Source** → **Root Directory** = `validation-dashboard/dove-dashboard`. Railway will pick up `validation-dashboard/dove-dashboard/Dockerfile`.
3. **Settings** → **Networking** → enable **Public Networking**.
4. No environment variables needed — the dashboard is pure static (Dove JSON baked at build time).
5. Click **Deploy**. Build does `npm ci → npm run build → serve dist`. Takes ~1 min.
6. Once green, copy the public URL (e.g. `sde-validation-production-xxxx.up.railway.app`). Skip ahead to section 5 to wire up the custom domain `validation.try.darpanlabs.ai` the same way you did for the API and frontend.

## 5. Custom domains

### 5a. On Railway
1. Click the **backend** service → **Settings** → **Networking** → **Custom Domains** → **Add Domain**.
   - Enter `api.try.darpanlabs.ai`.
   - Railway shows a CNAME target like `xxx.up.railway.app`. **Copy it.**
2. Click the **frontend** service → **Settings** → **Networking** → **Custom Domains** → **Add Domain**.
   - Enter `try.darpanlabs.ai`.
   - Railway shows a different CNAME target. **Copy it.**
3. Click the **sde-validation** service → **Settings** → **Networking** → **Custom Domains** → **Add Domain**.
   - Enter `validation.try.darpanlabs.ai`.
   - Railway shows a third CNAME target. **Copy it.**

### 5b. On Namecheap
1. Log into Namecheap → **Domain List** → click **Manage** next to `darpanlabs.ai`.
2. **Advanced DNS** tab → **Add New Record** (twice):

   | Type | Host | Value | TTL |
   |---|---|---|---|
   | CNAME | `try` | `<frontend CNAME from Railway>` | Automatic |
   | CNAME | `api.try` | `<backend CNAME from Railway>` | Automatic |
   | CNAME | `validation.try` | `<validation CNAME from Railway>` | Automatic |

3. Save.
4. Repeat for `darpanlabs.com` if you want the same URLs working on the `.com` (optional — or set up a 301 redirect).
5. Wait 5–30 min for DNS to propagate. Railway will auto-issue SSL certs once it sees the CNAMEs.

### 5c. Verify
- `https://api.try.darpanlabs.ai/health` → returns `{"status":"healthy",...}`
- `https://try.darpanlabs.ai` → loads the landing page, shows the two Dove demo studies
- `https://validation.try.darpanlabs.ai` → loads the Dove validation dashboard with radar charts, heatmaps, and tier rankings

## 6. Rebuild the frontend (because of the API URL)

The frontend bakes `NEXT_PUBLIC_API_URL` at build time. You entered the custom domain in step 4 before the domain existed — that's fine for the env var, but if the frontend was built before the backend domain was reachable, the first build may have baked a failed lookup. Just click **Redeploy** on the frontend service now that `api.try.darpanlabs.ai` resolves.

## 7. Smoke-test the live site

1. Open `https://try.darpanlabs.ai` in an incognito window. You should see:
   - The landing page with "AI-powered research, run in minutes"
   - A "Try It Out" button top-right
   - The two Dove demo studies listed at the bottom (labeled `DEMO`)
2. Click a demo study → it opens in read-only mode (wizard view with the pre-seeded data).
3. Click "Try It Out" → login form appears. Enter `darpantry` / `bezosisbad`. Login succeeds, you bounce back to the landing page now with the create-study form.
4. Try to create a new study: enter a question, click Run. The study wizard opens.

---

## Adding the twin-simulation worker (later)

When you're ready to let users simulate new studies:

1. **+ New** → **GitHub Repo** → same repo.
2. **Settings** → **Source** → **Root Directory** = `ai-interviewer/backend`.
3. **Settings** → **Service** → **Custom Start Command** = `celery -A app.celery_app worker --loglevel=info --concurrency=1`.
4. **Variables**: same `DATABASE_URL`, `REDIS_URL`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` as the backend.
5. **Settings** → **Volume** → mount a 2 GB volume at `/app/twin-data`. Upload the 1.1 GB `twin-generator/data/output/` contents to it via `railway run --service ai-interviewer-worker rsync -avh twin-generator/data/output/ /app/twin-data/` (from your laptop).
6. Update the worker env to point at that path. (Minor code change; flag me when you get here.)

Cost adds ~$10/month.

---

## Rotating the shared password

1. Railway dashboard → backend service → **Variables** → change `SHARED_LOGIN_PASSWORD`.
2. Click **Deploy** (Railway restarts the container; the Dockerfile CMD re-runs the seed script on boot, updating the password hash in the DB).
3. Existing JWTs remain valid until they expire (72 hours). To force-logout everyone immediately, also rotate `JWT_SECRET_KEY`.

---

## Gotchas I already dealt with

- **Python 3.9 locally**: setup.py requires 3.11+. I pinned the backend Dockerfile at `python:3.11-slim`, so Railway ignores what's on your laptop.
- **bcrypt + passlib compatibility**: a known passlib bug with newer bcrypt. I swapped to bcrypt directly.
- **Google OAuth dormant, not deleted**: backend endpoint still exists but returns 401 with no `GOOGLE_CLIENT_ID` — safe to leave.
- **`.env` files**: root `.gitignore` now covers all nested `.env` files. Verified nothing secret is committed.
