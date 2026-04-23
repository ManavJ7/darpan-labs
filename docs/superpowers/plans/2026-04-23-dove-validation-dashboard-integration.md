# Dove Validation Dashboard Integration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy the existing `validation-dashboard/dove-dashboard` Vite app as a standalone Railway service, and replace the hardcoded `localhost:5173` launcher with a public-friendly button on the Dove study's results page.

**Architecture:** The dashboard is a pure static Vite bundle (no API, ~584 KB of baked JSON). We add a Dockerfile so Railway can build/serve it as a 4th service at `validation.try.darpanlabs.ai`. In the SDE frontend, we introduce a `NEXT_PUBLIC_VALIDATION_URL` build-time env var, delete the old validation-trigger block from the wizard's step 5, and add a simple "View Validation Dashboard" button to the Dove results page header that opens that URL in a new tab. No Celery worker. No per-study dynamic behaviour. Dove-only.

**Tech Stack:** Node 20 (Alpine), Vite 7, React 19, Next.js 16 (standalone), Railway, Docker, TypeScript.

Spec: [docs/superpowers/specs/2026-04-23-dove-validation-dashboard-integration-design.md](../specs/2026-04-23-dove-validation-dashboard-integration-design.md)

---

## File Structure

**Created:**
- `validation-dashboard/dove-dashboard/Dockerfile` — multi-stage Node 20 build → `serve dist`
- `validation-dashboard/dove-dashboard/.dockerignore` — exclude `node_modules`, `dist`, local env files
- `study-design-engine/frontend/.env.example` — add `NEXT_PUBLIC_VALIDATION_URL` line (file exists, appending)

**Modified:**
- `study-design-engine/frontend/Dockerfile` — add `NEXT_PUBLIC_VALIDATION_URL` build arg so Next.js can bake it into the bundle
- `study-design-engine/frontend/src/components/steps/SimulationView.tsx` — delete the `Validation Dashboard` block (lines 177–219) and related `handleOpenDashboard`, `validationStatus`, and unused API imports
- `study-design-engine/frontend/src/app/study/[studyId]/results/page.tsx` — add a "View Validation Dashboard" button in the page header, visible only when `brand_name === "dove"`, results exist, and the env var is set
- `DEPLOY.md` — document the new `sde-validation` service and the new `NEXT_PUBLIC_VALIDATION_URL` variable

**No test files created.** This is infrastructure + UI wiring — no new business logic. Verification is via `docker build`, `npm run build`, and manual smoke tests against the running UI. Each task has an explicit verification step.

---

## Task 1: Dockerfile for the dove-dashboard Vite app

**Files:**
- Create: `validation-dashboard/dove-dashboard/Dockerfile`
- Create: `validation-dashboard/dove-dashboard/.dockerignore`

- [ ] **Step 1: Create `.dockerignore`**

Write `validation-dashboard/dove-dashboard/.dockerignore`:

```gitignore
node_modules
dist
.env
.env.*
npm-debug.log
.DS_Store
.git
.gitignore
README.md
```

- [ ] **Step 2: Create the Dockerfile**

Write `validation-dashboard/dove-dashboard/Dockerfile`:

```dockerfile
# Dove Validation Dashboard — static Vite app served by `serve`
FROM node:20-alpine AS base

# --- Dependencies stage ---
FROM base AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci

# --- Build stage ---
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# --- Production stage ---
FROM base AS runner
WORKDIR /app
ENV NODE_ENV=production

# Install only `serve` in the runtime image — no source, no dev deps
RUN npm install --global serve@14

COPY --from=builder /app/dist ./dist

EXPOSE 3000

# Railway injects $PORT dynamically; serve it with SPA fallback (-s).
CMD ["sh", "-c", "serve dist -s -l tcp://0.0.0.0:${PORT:-3000}"]
```

- [ ] **Step 3: Verify the image builds**

Run from the repo root:

```bash
docker build -t dove-dashboard:dev validation-dashboard/dove-dashboard
```

Expected: build succeeds. Final layer runs `npm install --global serve@14` and leaves `dist/` in place. If `npm ci` fails because `package-lock.json` is absent, run `cd validation-dashboard/dove-dashboard && npm install` locally once, commit the lockfile, and retry.

- [ ] **Step 4: Verify the container serves the dashboard**

Run:

```bash
docker run --rm -p 5555:3000 -e PORT=3000 dove-dashboard:dev
```

In another terminal:

```bash
curl -sI http://localhost:5555/ | head -1
curl -s http://localhost:5555/ | grep -o '<title>[^<]*</title>'
```

Expected: `HTTP/1.1 200 OK` and `<title>` tag containing the dashboard title. Ctrl-C the container when done.

- [ ] **Step 5: Commit**

```bash
git add validation-dashboard/dove-dashboard/Dockerfile validation-dashboard/dove-dashboard/.dockerignore
git commit -m "validation-dashboard: Dockerfile for Railway static deployment"
```

---

## Task 2: Build-arg plumbing for `NEXT_PUBLIC_VALIDATION_URL`

**Files:**
- Modify: `study-design-engine/frontend/Dockerfile` (after `NEXT_PUBLIC_API_URL` lines)
- Modify: `study-design-engine/frontend/.env.example` (append new variable)

- [ ] **Step 1: Update the frontend Dockerfile to accept the new build arg**

Edit `study-design-engine/frontend/Dockerfile`. After the existing `NEXT_PUBLIC_API_URL` lines (lines 17–18), add a matching pair for the new variable. Resulting block should look like:

```dockerfile
# Build args for Next.js (baked at build time)
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

ARG NEXT_PUBLIC_VALIDATION_URL
ENV NEXT_PUBLIC_VALIDATION_URL=$NEXT_PUBLIC_VALIDATION_URL
```

Everything else in the Dockerfile stays untouched.

- [ ] **Step 2: Update `.env.example`**

Edit `study-design-engine/frontend/.env.example`. After the existing `NEXT_PUBLIC_GOOGLE_CLIENT_ID=` line, add:

```env

# URL of the Dove validation dashboard (separate Railway service).
# In local dev, run `cd validation-dashboard/dove-dashboard && npm run dev` and use http://localhost:5173.
# In production, set to https://validation.try.darpanlabs.ai.
NEXT_PUBLIC_VALIDATION_URL=http://localhost:5173
```

- [ ] **Step 3: Verify the frontend still builds**

Run:

```bash
cd study-design-engine/frontend && npm run build
```

Expected: build completes. `next build` output should include the standalone server. Warnings are fine; errors are not. Return to repo root afterward: `cd ../..`.

- [ ] **Step 4: Commit**

```bash
git add study-design-engine/frontend/Dockerfile study-design-engine/frontend/.env.example
git commit -m "sde-frontend: plumb NEXT_PUBLIC_VALIDATION_URL build arg"
```

---

## Task 3: Remove the old validation block from `SimulationView.tsx`

**Files:**
- Modify: `study-design-engine/frontend/src/components/steps/SimulationView.tsx`

This block is being removed entirely (not moved). The new button lives on the results page (Task 4).

- [ ] **Step 1: Delete the JSX block for the Validation Dashboard**

Edit `study-design-engine/frontend/src/components/steps/SimulationView.tsx`. Remove lines 177–219 (the `{/* Validation Dashboard — only for the Dove study ... */}` block, from the opening comment through the closing `)}`). The surrounding structure before and after (the Results Dashboard card on line 153 and the `Tab: Available Twins` section starting around line 221) must remain intact.

Use Edit with `old_string` being the exact 43-line block starting at `      {/* Validation Dashboard — only for the Dove study (has real participant` and ending at `      )}` and `new_string` being an empty string (no blank line needed — the surrounding comments already whitespace-separate the sections).

- [ ] **Step 2: Delete the `handleOpenDashboard` function**

In the same file, remove lines 104–127 (the entire `const handleOpenDashboard = async (mode: "synthesis" | "comparison") => { ... };` function declaration, including trailing blank line if any). The function becomes unused once the JSX above is gone.

- [ ] **Step 3: Delete the `validationStatus` state**

In the same file, remove line 30:

```tsx
  const [validationStatus, setValidationStatus] = useState<string | null>(null);
```

- [ ] **Step 4: Remove unused imports**

In the same file, the imports from `@/lib/studyApi` on lines 7–17 import `createValidationReport`, `getValidationReport`, and `type ValidationReportDetail` — all three become unused after Steps 1–3.

Replace the import block:

Old:

```tsx
import {
  listAvailableTwins,
  simulateTwins,
  listTwinSimulationResults,
  createValidationReport,
  getValidationReport,
  type AvailableTwin,
  type TwinSimulationResult,
  type SimulationJobItem,
  type ValidationReportDetail,
} from "@/lib/studyApi";
```

New:

```tsx
import {
  listAvailableTwins,
  simulateTwins,
  listTwinSimulationResults,
  type AvailableTwin,
  type TwinSimulationResult,
  type SimulationJobItem,
} from "@/lib/studyApi";
```

(If `ValidationReportDetail` or the two API functions are referenced elsewhere in the file beyond what we deleted, the TypeScript compiler will flag it in the next step — revert that specific removal if so. Do NOT delete those exports from `@/lib/studyApi` itself; other consumers or admin tooling may still use them.)

- [ ] **Step 5: Type-check the frontend**

Run:

```bash
cd study-design-engine/frontend && npx tsc --noEmit
```

Expected: zero errors. If `createValidationReport`/`getValidationReport`/`ValidationReportDetail` were referenced elsewhere in the file, add them back to the import list. Return to repo root.

- [ ] **Step 6: Run the frontend build as a smoke check**

```bash
cd study-design-engine/frontend && npm run build && cd ../..
```

Expected: build completes. No unused-import warnings for the removed symbols.

- [ ] **Step 7: Commit**

```bash
git add study-design-engine/frontend/src/components/steps/SimulationView.tsx
git commit -m "sde-frontend: remove inline validation dashboard launcher"
```

---

## Task 4: Add the "View Validation Dashboard" button to the results page

**Files:**
- Modify: `study-design-engine/frontend/src/app/study/[studyId]/results/page.tsx`

Button placement: the existing results page has a header row (lines 343–357) containing a back-arrow link, the title "Results Dashboard", and a subtitle. We add a right-aligned action button on the same row, visible only when the study is Dove, results exist, and `NEXT_PUBLIC_VALIDATION_URL` is set.

- [ ] **Step 1: Import the `BarChart3` icon**

Edit `study-design-engine/frontend/src/app/study/[studyId]/results/page.tsx`. Update the `lucide-react` import on line 7 from:

```tsx
import { ArrowLeft, Loader2 } from "lucide-react";
```

to:

```tsx
import { ArrowLeft, Loader2, BarChart3 } from "lucide-react";
```

- [ ] **Step 2: Add a computed flag for validation-dashboard visibility**

In the same file, inside the `ResultsDashboardPage` component, immediately after the line that defines `hasResults` (around line 296: `const hasResults = completedCount > 0 && sections.length > 0 && concepts.length > 0;`), add:

```tsx
  const validationUrl = process.env.NEXT_PUBLIC_VALIDATION_URL;
  const showValidationButton =
    hasResults &&
    !!validationUrl &&
    study?.brand_name?.toLowerCase() === "dove";
```

This keeps the gating logic in one place. `process.env.NEXT_PUBLIC_VALIDATION_URL` is inlined at build time by Next.js — at runtime the expression becomes a string literal or `undefined`.

- [ ] **Step 3: Add the button to the header row**

In the same file, modify the header block at lines 343–357. The existing block wraps the back-arrow and title in a single `<div className="flex items-center gap-4 mb-8">`. Change it so the back-arrow + title form a left group and the button floats right.

Replace:

```tsx
          {/* Header */}
          <div className="flex items-center gap-4 mb-8">
            <Link
              href={`/study/${studyId}`}
              className="w-8 h-8 rounded-lg bg-darpan-surface border border-darpan-border flex items-center justify-center text-white/40 hover:text-white/70 hover:border-darpan-border-active transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
            </Link>
            <div>
              <h1 className="text-xl font-bold">Results Dashboard</h1>
              <p className="text-sm text-white/35 mt-0.5">
                {completedCount} twin simulation{completedCount !== 1 ? "s" : ""} &middot;{" "}
                {concepts.length} concept{concepts.length !== 1 ? "s" : ""}
              </p>
            </div>
          </div>
```

With:

```tsx
          {/* Header */}
          <div className="flex items-center gap-4 mb-8">
            <Link
              href={`/study/${studyId}`}
              className="w-8 h-8 rounded-lg bg-darpan-surface border border-darpan-border flex items-center justify-center text-white/40 hover:text-white/70 hover:border-darpan-border-active transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
            </Link>
            <div className="flex-1 min-w-0">
              <h1 className="text-xl font-bold">Results Dashboard</h1>
              <p className="text-sm text-white/35 mt-0.5">
                {completedCount} twin simulation{completedCount !== 1 ? "s" : ""} &middot;{" "}
                {concepts.length} concept{concepts.length !== 1 ? "s" : ""}
              </p>
            </div>
            {showValidationButton && (
              <a
                href={validationUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 rounded-md bg-cyan-600 px-4 py-2 text-sm font-semibold text-white hover:bg-cyan-500 transition shrink-0"
              >
                <BarChart3 className="w-4 h-4" />
                View Validation Dashboard
              </a>
            )}
          </div>
```

Notes:
- `<a target="_blank" rel="noopener noreferrer">` is used instead of `window.open` so the link still works with middle-click / right-click "open in new tab" and is SSR-safe (Next.js renders this page with `"use client"` but the anchor is idiomatic).
- `rel="noopener noreferrer"` is a security baseline for external links — prevents the opened tab from accessing `window.opener`.
- Colour matches the cyan treatment that the removed `SimulationView` block used, so the brand cue stays consistent.

- [ ] **Step 4: Type-check**

```bash
cd study-design-engine/frontend && npx tsc --noEmit && cd ../..
```

Expected: zero errors.

- [ ] **Step 5: Run the frontend build**

```bash
cd study-design-engine/frontend && npm run build && cd ../..
```

Expected: build completes.

- [ ] **Step 6: Manual verification (local)**

Open two terminals.

Terminal 1 — run the dashboard:

```bash
cd validation-dashboard/dove-dashboard && npm install && npm run dev
```

Expected: Vite dev server on `http://localhost:5173`.

Terminal 2 — run the SDE frontend with the env var pointed at it:

```bash
cd study-design-engine/frontend
cp .env.example .env.local  # skip if .env.local already exists
# Ensure .env.local contains: NEXT_PUBLIC_VALIDATION_URL=http://localhost:5173
npm run dev
```

Also run the backend (`cd study-design-engine && uvicorn app.main:app --reload --port 8001`) if it isn't already running — the results page fetches study data from the API.

Then in a browser:
1. Log in (or use the dev-login flow) and open the seeded Dove study.
2. Navigate to `/study/<dove-study-id>/results`.
3. Confirm the "View Validation Dashboard" button appears in the page header, right-aligned.
4. Click it. A new tab opens to `http://localhost:5173` showing the Dove dashboard (radar charts, heatmap, tier rankings, etc.).
5. Navigate to a non-Dove study's results page. Confirm the button is hidden.
6. Stop the SDE frontend, unset `NEXT_PUBLIC_VALIDATION_URL` in `.env.local`, rebuild, restart, reload the Dove results page. Confirm the button is hidden.

- [ ] **Step 7: Commit**

```bash
git add study-design-engine/frontend/src/app/study/[studyId]/results/page.tsx
git commit -m "sde-frontend: add Dove validation dashboard button to results page"
```

---

## Task 5: Document the new Railway service in DEPLOY.md

**Files:**
- Modify: `DEPLOY.md`

- [ ] **Step 1: Update the "What gets deployed" table**

In `DEPLOY.md`, replace the services table at lines 11–16 with:

```markdown
| Service | Repo path | Purpose |
|---|---|---|
| `sde-api` | `study-design-engine/` | FastAPI backend (port 8001 → Railway `$PORT`) |
| `sde-frontend` | `study-design-engine/frontend/` | Next.js 16 UI (port 3000 → Railway `$PORT`) |
| `sde-validation` | `validation-dashboard/dove-dashboard/` | Static Dove validation dashboard (Vite build served via `serve`) |
| `postgres` | (Railway managed) | Shared DB for users + studies + twins |
| `redis` | (Railway managed) | Celery broker + rate-limit counters |
```

- [ ] **Step 2: Add the new variable to the frontend variables table**

In the frontend service setup section (step 4), replace the Variables table with:

```markdown
   | Key | Value |
   |---|---|
   | `NEXT_PUBLIC_API_URL` | `https://api.try.darpanlabs.ai` (the custom domain you'll set in step 5, **not** the `.up.railway.app` URL — it's baked into the JS bundle at build time) |
   | `NEXT_PUBLIC_VALIDATION_URL` | `https://validation.try.darpanlabs.ai` (same build-time bake — set this before the first frontend deploy) |
```

- [ ] **Step 3: Add a section for the validation service**

Insert a new section between current section 4 ("Add the frontend service") and section 5 ("Custom domains"). Call it "4b. Add the validation dashboard service". Content:

```markdown
## 4b. Add the validation dashboard service

1. **+ New** → **GitHub Repo** → same repo.
2. **Settings** → **Source** → **Root Directory** = `validation-dashboard/dove-dashboard`. Railway will pick up `validation-dashboard/dove-dashboard/Dockerfile`.
3. **Settings** → **Networking** → enable **Public Networking**.
4. No environment variables needed — the dashboard is pure static (Dove JSON baked at build time).
5. Click **Deploy**. Build does `npm ci → npm run build → serve dist`. Takes ~1 min.
6. Once green, copy the public URL (e.g. `sde-validation-production-xxxx.up.railway.app`). Skip ahead to section 5 to wire up the custom domain `validation.try.darpanlabs.ai` the same way you did for the API and frontend.
```

- [ ] **Step 4: Add the custom-domain entry to section 5a and 5b**

In section 5a, after the two existing Custom Domains instructions, append:

```markdown
3. Click the **sde-validation** service → **Settings** → **Networking** → **Custom Domains** → **Add Domain**.
   - Enter `validation.try.darpanlabs.ai`.
   - Railway shows a third CNAME target. **Copy it.**
```

In section 5b, add a third row to the Namecheap DNS table:

```markdown
   | CNAME | `validation.try` | `<validation CNAME from Railway>` | Automatic |
```

In section 5c verification, append:

```markdown
- `https://validation.try.darpanlabs.ai` → loads the Dove validation dashboard with radar charts, heatmaps, and tier rankings
```

- [ ] **Step 5: Commit**

```bash
git add DEPLOY.md
git commit -m "docs: deploy steps for sde-validation Railway service"
```

---

## Task 6: Final verification + end-to-end smoke

- [ ] **Step 1: Full build sweep**

From repo root:

```bash
docker build -t dove-dashboard:dev validation-dashboard/dove-dashboard
cd study-design-engine/frontend && npm run build && cd ../..
```

Expected: both builds succeed.

- [ ] **Step 2: Local end-to-end smoke**

Run the three services locally the way Railway will run them:

Terminal 1 (dashboard):
```bash
docker run --rm -p 5173:3000 -e PORT=3000 dove-dashboard:dev
```

Terminal 2 (backend):
```bash
cd study-design-engine && uvicorn app.main:app --reload --port 8001
```

Terminal 3 (frontend):
```bash
cd study-design-engine/frontend
# Confirm .env.local has NEXT_PUBLIC_VALIDATION_URL=http://localhost:5173
npm run dev
```

In the browser:
1. Go to `http://localhost:3000`, log in (dev-login or darpantry/bezosisbad), pick the Dove demo study.
2. Click through to `/study/<id>/results`. Verify the "View Validation Dashboard" button is visible in the header.
3. Click the button. Verify a new tab opens at `http://localhost:5173` and the Dove dashboard renders its four tabs with charts.
4. Go back to the study wizard step 5 (Simulation). Verify there is NO longer a "Validation Dashboard" card (only the "Results Dashboard" card with "View Results" is left).
5. Open a non-Dove study (create a test one via the "Try It Out" login if needed). Confirm the validation button does NOT appear on its results page.

- [ ] **Step 3: Final commit and branch summary**

```bash
git log --oneline -10
git status
```

Expected: five commits from this plan (Tasks 1–5 each produced one commit; Task 6 is verification only). Working tree clean.

Report the branch name + commit list back to the user along with the manual Railway + DNS steps to execute next (they were documented in `DEPLOY.md` in Task 5; no further code changes needed).
