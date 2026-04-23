# Dove Validation Dashboard Integration — Design Spec

**Date:** 2026-04-23
**Status:** Draft
**Scope:** Integrate the existing `validation-dashboard/dove-dashboard` app into the try.darpanlabs.ai deployment as a static viewer, launched from the Dove study's results page.

## Problem

A React/Vite dashboard at `validation-dashboard/dove-dashboard/` renders the comparison between real Dove participant responses and twin responses (radar charts, heatmaps, tier rankings, per-twin accuracy). It is not available from try.darpanlabs.ai. Three gaps:

1. The dashboard is not deployed on Railway — only `sde-api`, `sde-frontend`, `postgres`, and `redis` are.
2. The existing launch button in `study-design-engine/frontend/src/components/steps/SimulationView.tsx:116` hardcodes `http://localhost:5173`.
3. That button is gated to `!study?.is_public` (SimulationView.tsx:180), so it is hidden for the public Dove demo study (`is_public = true`).

## Non-Goals

- No live validation runs (no Celery worker, no `twin.run_validation_report` execution).
- No per-study validation — button appears only for the Dove study.
- No dynamic study ID passed to the dashboard — Dove JSON is already baked into the Vite build.
- No authentication on the dashboard itself — same public-visibility model as the existing Dove results page.
- No refactor of the dashboard app, its analysis pipeline, or its JSON data files.

## Architecture

Three changes, each independent:

### 1. Deploy `dove-dashboard` as a new Railway service

- **Service name:** `sde-validation` in the existing `darpan-try` Railway project.
- **Root directory:** `validation-dashboard/dove-dashboard`.
- **Runtime:** Node 20 container.
- **Build:** `npm ci && npm run build` (runs `tsc -b && vite build`).
- **Serve:** `npx serve dist -s -l tcp://0.0.0.0:$PORT` (already the `start` script in `package.json:11`).
- **Public URL:** custom domain `validation.try.darpanlabs.ai` (new DNS CNAME to Railway).
- **New file:** `validation-dashboard/dove-dashboard/Dockerfile` — multi-stage (builder installs deps + builds, runner copies `dist` and runs `serve`).

No env vars, no API, no database. The app imports four JSON files directly at build time (`src/data/*.json`, ~584 KB total).

### 2. Rewire the launch button

- **New env var:** `NEXT_PUBLIC_VALIDATION_URL` baked into the `sde-frontend` Railway service at build time. Value in prod: `https://validation.try.darpanlabs.ai`. Value in `.env.local.example`: `http://localhost:5173` so local dev still works.
- **Code change:** `study-design-engine/frontend/src/components/steps/SimulationView.tsx` — replace the hardcoded `window.open("http://localhost:5173", "_blank")` with `window.open(process.env.NEXT_PUBLIC_VALIDATION_URL, "_blank")`.
- **Gating change:** remove the `!study?.is_public` condition from the button's visibility check so the Dove public demo shows it. Keep `brand_name?.toLowerCase() === "dove"` and `completedResults.length > 0`.

### 3. Add the button to the Dove results page

- **Target file:** `study-design-engine/frontend/src/app/study/[studyId]/results/page.tsx`.
- **Button label:** "View Validation Dashboard" (or same label as the existing button for consistency).
- **Visibility:** same gating — Dove-branded study, results present.
- **Action:** `window.open(process.env.NEXT_PUBLIC_VALIDATION_URL, "_blank")`.
- **Remove the old button** from `SimulationView.tsx` (option A from brainstorming). The step-5 wizard location is redundant once the results page owns it.

## Data Flow

```
Visitor → try.darpanlabs.ai/study/<dove-id>/results
              │
              └── clicks "View Validation Dashboard"
                       │
                       └── new tab → validation.try.darpanlabs.ai
                                            │
                                            └── static HTML/JS/JSON (Vite build)
```

No API calls at any point. No cross-service dependencies once deployed.

## Components Affected

| File | Change |
|------|--------|
| `validation-dashboard/dove-dashboard/Dockerfile` | New — Node 20 multi-stage build + serve |
| `validation-dashboard/dove-dashboard/.dockerignore` | New — exclude `node_modules`, `dist`, `.env*` |
| `study-design-engine/frontend/src/components/steps/SimulationView.tsx` | Remove the validation button block (lines ~177–219) |
| `study-design-engine/frontend/src/app/study/[studyId]/results/page.tsx` | Add button for Dove studies |
| `study-design-engine/frontend/.env.local.example` | Add `NEXT_PUBLIC_VALIDATION_URL=http://localhost:5173` |
| `study-design-engine/DEPLOY.md` | Document the new `sde-validation` service and env var |
| Railway project (manual) | Create `sde-validation` service, set root dir, add custom domain, add `NEXT_PUBLIC_VALIDATION_URL` to `sde-frontend` |
| DNS (manual) | CNAME `validation.try.darpanlabs.ai` → Railway |

## Error Handling

- If `NEXT_PUBLIC_VALIDATION_URL` is unset at build time, the button's `window.open` call receives `undefined` and opens `about:blank`. Guard the button render so it hides when the env var is missing — avoids a broken UX on misconfigured environments.
- No runtime errors to handle inside the dashboard itself — it's a static bundle.

## Testing

- **Local dev:** run both `sde-frontend` (`npm run dev` on 3000) and `dove-dashboard` (`npm run dev` on 5173). Set `NEXT_PUBLIC_VALIDATION_URL=http://localhost:5173`. Load the Dove study's results page, click the button, verify it opens the dashboard.
- **Dockerfile:** build the `dove-dashboard` image locally, run it, curl the root route, confirm it returns the built `index.html`.
- **Prod smoke:** after Railway deploy, hit `https://validation.try.darpanlabs.ai` and confirm the four tabs render with Dove data. Then hit the Dove results page on `try.darpanlabs.ai` logged out and confirm the button appears and opens the dashboard in a new tab.

## Rollback

- Revert the frontend code changes; re-deploy `sde-frontend`. The `sde-validation` service can stay up (it's read-only and idle-cheap) or be paused in Railway.

## Open Decisions Deferred to Implementation

- Exact placement of the button on the results page (top-right action bar vs. inline with existing buttons) — decide during implementation based on the page's current layout.
- Button styling — match the existing results page's button patterns.
