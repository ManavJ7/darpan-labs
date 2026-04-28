# Validation Dashboard Modal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the new-tab anchor on the Dove study's results page with an in-page modal overlay containing an iframe of the validation dashboard, so the URL stays on `/study/<id>/results` throughout.

**Architecture:** A new self-contained `ValidationDashboardModal` component renders a `framer-motion`-animated full-viewport overlay with an iframe of `process.env.NEXT_PUBLIC_VALIDATION_URL`. The results page swaps its `<a target="_blank">` for a `<button>` + `useState` + the modal. No backend, no deployment, no new dependencies. An iframe-header verification step confirms `serve` doesn't block embedding.

**Tech Stack:** Next.js 16 (App Router), React 19, TypeScript, framer-motion 10, lucide-react, Tailwind CSS, the dashboard at `validation.try.darpanlabs.ai` (Vite static, served by `serve@14.2.6`).

Spec: [docs/superpowers/specs/2026-04-29-validation-dashboard-modal-design.md](../specs/2026-04-29-validation-dashboard-modal-design.md)

---

## File Structure

**Created:**
- `study-design-engine/frontend/src/components/results/ValidationDashboardModal.tsx` — full-viewport modal overlay with framer-motion animation, ESC + backdrop + X close, body-scroll lock, iframe with loading spinner, and "Open in new tab" escape hatch in the header.

**Modified:**
- `study-design-engine/frontend/src/app/study/[studyId]/results/page.tsx` — three small changes: add a `useState` for modal visibility, swap the existing `<a>` for a `<button>` of identical visual style, render the modal component at the bottom of the JSX tree.

**No other files changed.** No test files added (see spec — modal is DOM scaffolding around an iframe, no business logic to test). No backend, no migrations, no env-var changes.

**Branch:** direct commits to `main`, matching prior session policy.

---

## Task 1: Create the `ValidationDashboardModal` component

**Files:**
- Create: `study-design-engine/frontend/src/components/results/ValidationDashboardModal.tsx`

- [ ] **Step 1: Create the component file**

Write `study-design-engine/frontend/src/components/results/ValidationDashboardModal.tsx` with this exact content:

```tsx
"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, ExternalLink, Loader2 } from "lucide-react";

type Props = {
  open: boolean;
  onClose: () => void;
  url: string;
};

export function ValidationDashboardModal({ open, onClose, url }: Props) {
  const [iframeLoaded, setIframeLoaded] = useState(false);

  // ESC to close
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  // Lock body scroll while open
  useEffect(() => {
    if (!open) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, [open]);

  // Reset loading spinner when reopening
  useEffect(() => {
    if (open) setIframeLoaded(false);
  }, [open]);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
          className="fixed inset-0 z-50 flex items-center justify-center"
          aria-modal="true"
          role="dialog"
          aria-label="Validation Dashboard"
        >
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/70"
            onClick={onClose}
          />

          {/* Modal frame */}
          <motion.div
            initial={{ scale: 0.98, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.98, opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="relative w-[95vw] h-[95vh] bg-darpan-surface border border-darpan-border rounded-xl overflow-hidden flex flex-col"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-2.5 border-b border-darpan-border shrink-0">
              <h2 className="text-sm font-semibold text-white">
                Validation Dashboard
              </h2>
              <div className="flex items-center gap-2">
                <a
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1.5 text-xs text-white/50 hover:text-white/80 transition-colors"
                  aria-label="Open in new tab"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                  Open in new tab
                </a>
                <button
                  type="button"
                  onClick={onClose}
                  className="w-7 h-7 rounded-md flex items-center justify-center text-white/50 hover:text-white hover:bg-darpan-border/50 transition-colors"
                  aria-label="Close"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Iframe area */}
            <div className="relative flex-1 bg-black">
              {!iframeLoaded && (
                <div className="absolute inset-0 flex items-center justify-center">
                  <Loader2 className="w-6 h-6 text-white/30 animate-spin" />
                </div>
              )}
              <iframe
                src={url}
                title="Validation Dashboard"
                className="w-full h-full border-0"
                onLoad={() => setIframeLoaded(true)}
              />
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
```

- [ ] **Step 2: Type-check just this file**

Run from repo root:

```bash
cd study-design-engine/frontend && npx tsc --noEmit 2>&1 | grep "ValidationDashboardModal" ; echo "exit:$?"
cd ../..
```

Expected: no matches (grep exits 1 — confirms zero errors mentioning the new file). Pre-existing errors in unrelated files (`printSurvey.test.ts`, `SurveyQuestionPreview.test.tsx`, `TerritoryScorecard.tsx`, `QuestionnaireView.tsx`) are known and outside scope.

If you see any error mentioning `ValidationDashboardModal.tsx`, STOP and report BLOCKED with the error.

- [ ] **Step 3: Commit**

```bash
git add study-design-engine/frontend/src/components/results/ValidationDashboardModal.tsx
git commit -m "sde-frontend: add ValidationDashboardModal component"
```

Confirm 1 file: `git show --stat HEAD | head -5`.

---

## Task 2: Wire the modal into the Dove results page

**Files:**
- Modify: `study-design-engine/frontend/src/app/study/[studyId]/results/page.tsx`

This task makes three precise edits, all matching `old_string` content currently in the file.

- [ ] **Step 1: Add the modal import**

In `study-design-engine/frontend/src/app/study/[studyId]/results/page.tsx`, find the import at line 15:

```tsx
import { CompareDecide } from "@/components/results/CompareDecide";
```

Use Edit. `old_string`:

```tsx
import { CompareDecide } from "@/components/results/CompareDecide";
```

`new_string`:

```tsx
import { CompareDecide } from "@/components/results/CompareDecide";
import { ValidationDashboardModal } from "@/components/results/ValidationDashboardModal";
```

(Keeps the import block clean and grouped with other `@/components/results/*` imports.)

- [ ] **Step 2: Add the modal-visibility state**

Find the line near 302 (right after the `showValidationButton` flag, before the `return (`):

```tsx
  const showValidationButton =
    hasResults &&
    !!validationUrl &&
    study?.brand_name?.toLowerCase() === "dove";

  return (
```

Use Edit. `old_string`:

```tsx
  const showValidationButton =
    hasResults &&
    !!validationUrl &&
    study?.brand_name?.toLowerCase() === "dove";

  return (
```

`new_string`:

```tsx
  const showValidationButton =
    hasResults &&
    !!validationUrl &&
    study?.brand_name?.toLowerCase() === "dove";

  const [showValidation, setShowValidation] = useState(false);

  return (
```

- [ ] **Step 3: Replace the anchor with a button**

Find the exact existing block (around lines 363-372):

```tsx
            {showValidationButton && (
              <a
                href={validationUrl!}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 rounded-md bg-cyan-600 px-4 py-2 text-sm font-semibold text-white hover:bg-cyan-500 transition-colors shrink-0"
              >
                <BarChart3 className="w-4 h-4" />
                View Validation Dashboard
              </a>
            )}
```

Use Edit. `old_string` is the block above. `new_string`:

```tsx
            {showValidationButton && (
              <button
                type="button"
                onClick={() => setShowValidation(true)}
                className="flex items-center gap-2 rounded-md bg-cyan-600 px-4 py-2 text-sm font-semibold text-white hover:bg-cyan-500 transition-colors shrink-0"
              >
                <BarChart3 className="w-4 h-4" />
                View Validation Dashboard
              </button>
            )}
```

- [ ] **Step 4: Render the modal at the bottom of the JSX tree**

The component's outermost return is a `<div className="min-h-screen flex">` that wraps the Sidebar + the main content `div`. We render the modal as a sibling at the very end, just before the closing `</div>` of the root.

Find the file's last few lines. The final `return` block ends with two closing `</div>` tags before `);` and `}`. The exact tail looks like:

```tsx
          )}
        </main>
      </div>
    </div>
  );
}
```

Use Edit. `old_string`:

```tsx
          )}
        </main>
      </div>
    </div>
  );
}
```

`new_string`:

```tsx
          )}
        </main>
      </div>

      <ValidationDashboardModal
        open={showValidation}
        onClose={() => setShowValidation(false)}
        url={validationUrl ?? ""}
      />
    </div>
  );
}
```

(The modal is a sibling of the main content div, both inside the root `<div className="min-h-screen flex">`. The `url={validationUrl ?? ""}` fallback is defensive — `showValidationButton` already gates on `!!validationUrl`, so the modal can't open without a real URL, but the fallback satisfies TypeScript without a non-null assertion.)

- [ ] **Step 5: Type-check the modified file**

```bash
cd study-design-engine/frontend && npx tsc --noEmit 2>&1 | grep "results/page.tsx" ; echo "exit:$?"
cd ../..
```

Expected: no matches (grep exits 1).

If you see any error mentioning `results/page.tsx`, STOP and report BLOCKED.

- [ ] **Step 6: Commit**

```bash
git add study-design-engine/frontend/src/app/study/[studyId]/results/page.tsx
git commit -m "sde-frontend: open validation dashboard in modal instead of new tab"
```

Confirm 1 file changed: `git show --stat HEAD | head -5`.

---

## Task 3: Iframe-header verification + (conditional) `serve.json`

**Files:**
- Possibly create: `validation-dashboard/dove-dashboard/serve.json`
- Possibly modify: `validation-dashboard/dove-dashboard/Dockerfile`

Most likely no files change in this task — the `serve` defaults already permit iframe embedding. The task exists so we PROVE that's the case, and have a fix ready if a future serve update changes defaults.

- [ ] **Step 1: Inspect headers from the local dev server**

Run the dashboard's Vite dev server in the background and inspect headers:

```bash
cd validation-dashboard/dove-dashboard && npm run dev &
DASHBOARD_PID=$!
sleep 4
curl -sI http://localhost:5173/ | grep -iE "x-frame-options|content-security-policy|frame-ancestors" ; echo "vite_headers_exit:$?"
kill $DASHBOARD_PID 2>/dev/null
cd ../..
```

Expected: zero matches (grep exits 1) — Vite dev server emits no frame-blocking headers.

If matches appear, report them. The browser-side test (Step 3) is more authoritative because the production server is `serve`, not Vite.

- [ ] **Step 2: Inspect headers from a Docker-built `serve` instance**

The production-equivalent test:

```bash
docker build -t dove-dashboard:modal-check validation-dashboard/dove-dashboard
docker run --rm -d --name dove-modal-check -p 5558:3000 -e PORT=3000 dove-dashboard:modal-check
sleep 2
curl -sI http://localhost:5558/ | grep -iE "x-frame-options|content-security-policy|frame-ancestors" ; echo "serve_headers_exit:$?"
docker stop dove-modal-check
```

Expected: zero matches (grep exits 1). The `serve` package at version 14.2.6 does not emit `X-Frame-Options` or `Content-Security-Policy: frame-ancestors` by default, so iframes embedding the dashboard from any origin will load.

- [ ] **Step 3: Browser smoke test (manual)**

Run both services side-by-side. Two terminals:

Terminal 1 — dashboard:
```bash
cd validation-dashboard/dove-dashboard && npm run dev
```

Terminal 2 — SDE frontend:
```bash
cd study-design-engine/frontend
# Ensure .env.local has NEXT_PUBLIC_VALIDATION_URL=http://localhost:5173
npm run dev
```

Plus the SDE backend (`uvicorn app.main:app --reload --port 8001`) so the results page can fetch study data.

In a browser:
1. Log in (dev-login or `darpantry`/`bezosisbad`), open the seeded Dove study.
2. Navigate to `/study/<dove-id>/results`.
3. Click the "View Validation Dashboard" button.
4. Confirm the modal animates in over the page (URL bar still shows `/study/<id>/results`).
5. Confirm the iframe loads the dashboard with all four tabs / charts / etc.
6. Press ESC → modal closes. URL still unchanged.
7. Reopen with the button → click the backdrop (outside the white frame) → modal closes.
8. Reopen → click the X button in the modal header → modal closes.
9. Reopen → click "Open in new tab" link in the header → confirms a new tab opens to the dashboard URL. Modal stays open behind it (user can close manually).
10. Open browser dev tools → Console tab → confirm no `Refused to display ... in a frame` errors.

If step 4 fails (iframe shows a blank page or "refused to connect" error) AND step 1/2 returned no headers, the issue is something else (CORS-via-rendering, CSP from a parent meta tag, etc.) — report BLOCKED with browser console screenshot. If step 1 or 2 surfaced a header, see Step 4.

- [ ] **Step 4 (conditional): Add `serve.json` if a restrictive header was found**

Skip this step if Steps 1-3 all passed.

If `serve` was found to emit `X-Frame-Options: SAMEORIGIN` or similar, fix it by adding a serve config. Create `validation-dashboard/dove-dashboard/serve.json` with:

```json
{
  "headers": [
    {
      "source": "**/*",
      "headers": [
        {
          "key": "Content-Security-Policy",
          "value": "frame-ancestors 'self' https://try.darpanlabs.ai https://try.darpanlabs.com http://localhost:3000"
        }
      ]
    }
  ]
}
```

Then update the Dockerfile to copy `serve.json` into the runner stage. In `validation-dashboard/dove-dashboard/Dockerfile`, find:

```dockerfile
COPY --from=builder /app/dist ./dist
```

`old_string` = the line above; `new_string`:

```dockerfile
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/serve.json ./serve.json
```

`serve` automatically picks up `serve.json` from the current directory at boot. `frame-ancestors` is the modern CSP-based replacement for `X-Frame-Options`; it explicitly allows the SDE frontend's origins to embed the dashboard.

Rebuild the image and re-run Step 2 to confirm the new CSP header is correct (it should now appear in the curl output, listing the allowed origins).

Commit:

```bash
git add validation-dashboard/dove-dashboard/serve.json validation-dashboard/dove-dashboard/Dockerfile
git commit -m "validation-dashboard: allow iframe embedding from try.darpanlabs.ai"
```

- [ ] **Step 5: Hand back**

Report:
- Output of Step 1 (Vite headers)
- Output of Step 2 (serve headers)
- Result of Step 3 (modal works / fails — and if fails, the dev-tools console output)
- Whether Step 4 was needed (and if so, the new commit SHA)

---

## Task 4: Final verification

No commit. Sanity-check the work end-to-end before declaring done.

- [ ] **Step 1: Footprint check**

```bash
git diff --stat 490f3c2..HEAD
```

Expected: 2 files (the modal + the results page), with possibly a 3rd if Task 3 Step 4 fired (`serve.json` + Dockerfile).

- [ ] **Step 2: No-references-to-old-anchor check**

```bash
grep -nE "<a[^>]*target=\"_blank\"[^>]*validationUrl" study-design-engine/frontend/src/
```

Expected: zero matches in the results page. (The modal's "Open in new tab" link is `target="_blank"` but uses the prop `url` directly — it should also be matched by this grep.)

Refine to confirm the new pattern exists:

```bash
grep -n "ValidationDashboardModal" study-design-engine/frontend/src/app/study/\[studyId\]/results/page.tsx
```

Expected: 2 matches (the import + the JSX usage).

- [ ] **Step 3: Confirm commit chain**

```bash
git log --oneline -6
```

Expected, top to bottom:
1. `sde-frontend: open validation dashboard in modal instead of new tab` (Task 2)
2. `sde-frontend: add ValidationDashboardModal component` (Task 1)
3. (optional) `validation-dashboard: allow iframe embedding from try.darpanlabs.ai` (Task 3 Step 4, if needed)
4. `docs: design spec for validation dashboard modal on Dove results page` (`490f3c2`)

If you see the optional commit between Tasks 1 and 2, that's also fine — order matters less than presence.

- [ ] **Step 4: Hand back to controller**

Report:
- Final commit SHAs
- Footprint summary
- Whether Step 3 of Task 3 (browser smoke) passed
- Anything skipped or unresolved
