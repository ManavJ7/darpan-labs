# Validation Dashboard Modal — Design Spec

**Date:** 2026-04-29
**Status:** Approved
**Scope:** Replace the current "View Validation Dashboard" anchor (`<a target="_blank">`) on the Dove study's results page with an in-page modal overlay that opens an iframe of the validation dashboard. The browser URL stays on `/study/<id>/results` for the entire interaction.

## Problem

Today, clicking the "View Validation Dashboard" button on the Dove results page opens `validation.try.darpanlabs.ai` in a new tab. The user wants the dashboard to appear inside the current page — no new tab, no URL change — so the validation view feels like part of the results experience rather than a separate site.

## Non-Goals

- No backend change. The dashboard remains a separately-deployed static Vite app at `validation.try.darpanlabs.ai`.
- No SSO or shared auth context — the dashboard is a public read-only static site, no auth needed.
- No deep-linking into specific dashboard tabs — clicking the button always opens the dashboard's default landing tab.
- No PostMessage-based parent↔iframe communication — the dashboard runs independently.
- No keyboard navigation polish beyond the standard ESC-to-close baseline (Tab focus trap inside the iframe is browser-default behavior; we don't add a custom focus trap).

## Architecture

Three changes, all on the SDE frontend:

### 1. New component `ValidationDashboardModal`

File: `study-design-engine/frontend/src/components/results/ValidationDashboardModal.tsx`.

```ts
type Props = {
  open: boolean;
  onClose: () => void;
  url: string;  // dashboard URL — the parent guarantees this is non-empty
};
```

Renders a `fixed inset-0 z-50` overlay using `framer-motion` (already at `^10.18.0` in the SDE frontend `package.json`). Internal layout:

- Backdrop layer (`bg-black/70`, full viewport, click → `onClose`).
- Modal frame (centered, ~95vw / 95vh, dark surface matching the SDE theme).
- Header row with title "Validation Dashboard", a small "Open in new tab" link (preserves the lost escape hatch), and an X close button.
- Full-bleed `<iframe src={url} />` filling the remaining height.
- Loading spinner overlay shown until the iframe's `onLoad` event fires.

Effects on mount:
- `useEffect` that adds an ESC `keydown` listener calling `onClose`.
- `useEffect` that toggles `document.body.style.overflow = 'hidden'` while open and restores it on close.

### 2. Wire-up on the results page

File: `study-design-engine/frontend/src/app/study/[studyId]/results/page.tsx`.

Changes:
- Add `const [showValidation, setShowValidation] = useState(false);` near the existing `validationUrl` / `showValidationButton` flags.
- Replace the existing `<a href={validationUrl} target="_blank" rel="noopener noreferrer" ...>View Validation Dashboard</a>` with a `<button type="button" onClick={() => setShowValidation(true)} ...>` of identical visual style. Keep the `BarChart3` icon and "View Validation Dashboard" label. Keep the same gating (`showValidationButton`).
- At the bottom of the page's JSX tree, render `<ValidationDashboardModal open={showValidation} onClose={() => setShowValidation(false)} url={validationUrl!} />`.

### 3. Iframe-embedding verification

The dashboard is served by `npx serve dist -s` on Railway. By default, `serve` does not emit `X-Frame-Options` or `Content-Security-Policy: frame-ancestors`, so iframe embedding is permitted by browsers. The implementation plan's verification step will:

1. Curl `https://validation.try.darpanlabs.ai` and inspect response headers for `X-Frame-Options` or `Content-Security-Policy`.
2. If neither is present (expected) → no further action.
3. If a restrictive header is present → fix by adding a `serve.json` config to the dashboard's repo that explicitly allows `try.darpanlabs.ai` as a frame ancestor, OR by adding a Railway proxy header rule. The dashboard's Dockerfile would pick up `serve.json` automatically.

Local-dev equivalent: `vite` dev server (`npm run dev`) does not set frame-blocking headers either.

## Components Affected

| File | Change |
|------|--------|
| `study-design-engine/frontend/src/components/results/ValidationDashboardModal.tsx` | New (~120 lines) |
| `study-design-engine/frontend/src/app/study/[studyId]/results/page.tsx` | Replace `<a>` with `<button>`, add `useState`, render the new modal |

No new dependencies. No backend changes. No deployment changes.

## Data Flow

```
User clicks "View Validation Dashboard" button
  → setShowValidation(true)
  → ValidationDashboardModal renders, framer-motion fades in
  → <iframe src={validationUrl}> loads validation.try.darpanlabs.ai
  → Loading spinner hides on iframe.onLoad
  → User interacts with the dashboard inside the iframe
  → User dismisses (X / ESC / backdrop click / "Open in new tab" link click + close)
  → setShowValidation(false)
  → Modal fades out, iframe unmounts (state-driven; React removes the DOM node)
```

The iframe unmounts on close. Reopening triggers a fresh load. This is intentional — the dashboard's static JSON content doesn't need cross-session caching, and unmounting prevents background resource use.

## Error Handling

- **iframe fails to load (network error, CSP block):** the modal still renders with the loading spinner indefinitely. The "Open in new tab" link in the header is the user's escape hatch. We do NOT add a timeout-driven error state in v1 — the loading spinner + escape hatch is sufficient. If iframe load failures become common in practice, a future iteration can hook the iframe's `onError` event.
- **`url` is empty:** the parent's `showValidationButton` gating already filters out the case where `NEXT_PUBLIC_VALIDATION_URL` is unset. The button doesn't render, so the modal never opens with a bad URL. The `Props.url` type stays `string` (non-optional) — passing `validationUrl!` from the parent is safe given the gating.

## Testing

- **Unit tests:** none added. The modal is mostly DOM scaffolding around an iframe; the only logic is the open/close state machine and the body-scroll-lock side effect, both of which are trivial and have no business-logic surface to test.
- **Manual verification:**
  1. Local: run SDE frontend on `:3000`, dove-dashboard on `:5173`, set `NEXT_PUBLIC_VALIDATION_URL=http://localhost:5173`. Open Dove study results page. Click button → modal opens, iframe shows dashboard. ESC, X, backdrop click each dismiss. URL stays on `/study/<id>/results` throughout.
  2. Deployed: same flow against `try.darpanlabs.ai` after the next sde-frontend redeploy.
- **Iframe-header smoke check:** as part of plan verification, `curl -sI https://validation.try.darpanlabs.ai` and confirm absence of restrictive frame headers.

## Trade-offs Acknowledged

- **Lost affordances vs. the `<a target="_blank">` form:** middle-click and right-click → "open in new tab" no longer work directly on the button. Mitigation: the modal header includes an "Open in new tab" link that preserves the escape hatch.
- **Iframe scroll context:** mouse-wheel events scroll the dashboard inside the iframe rather than the underlying results page. This is expected and matches user intent — the modal is the focal interaction while open.
- **Mobile:** the modal is sized at 95vw / 95vh with a small margin. The dashboard's own responsive layout takes over inside the iframe. Acceptable for a v1.

## Branch

Direct commits to `main`, matching prior session policy.
