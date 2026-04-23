# Validation Dashboard Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the Aggregate and Individual tabs of the validation dashboard to match the visual language and hero-first hierarchy of the `study-design-engine` Results dashboard. Extended tabs remain untouched.

**Architecture:** Single-page Vite + React 19 app at `validation-dashboard/dove-dashboard`. Data stays in committed JSON files; all new logic is client-side derivation (Spearman ρ, agreement %, headline templates). Ports component chrome (darpan-* tokens, `bg-darpan-surface border-darpan-border rounded-xl`, Space Grotesk + JetBrains Mono, framer-motion fade-ins, lucide-react icons) from Results. Replaces `row1-winners/`, `row2-ranking/`, `row3-heatmap/`, `row4-insights/` with a new `aggregate/` directory organized around a verdict-first evidence pyramid: research question → data-source toggle → hero verdict → concept agreement table → recommendation → collapsible diagnostic → deep insights.

**Tech Stack:** Vite 7, React 19, TypeScript 5.9, Tailwind CSS 4, recharts 3, Zustand 5, + new: framer-motion, lucide-react, vitest (dev only).

**Spec reference:** [docs/superpowers/specs/2026-04-23-validation-dashboard-redesign-design.md](../specs/2026-04-23-validation-dashboard-redesign-design.md)

**Working directory for all shell commands:** `validation-dashboard/dove-dashboard/`

---

## Phase 1 — Foundation (deps, fonts, tokens)

### Task 1: Install new dependencies

**Files:**
- Modify: `validation-dashboard/dove-dashboard/package.json` (via npm)

- [ ] **Step 1: Install framer-motion and lucide-react**

```bash
cd validation-dashboard/dove-dashboard
npm install framer-motion lucide-react
```

- [ ] **Step 2: Install vitest as dev dep**

```bash
npm install -D vitest
```

- [ ] **Step 3: Verify package.json lists the new deps**

Run: `cat package.json | grep -E 'framer-motion|lucide-react|vitest'`
Expected: three matches.

- [ ] **Step 4: Build to confirm nothing broke**

```bash
npm run build
```
Expected: `tsc -b && vite build` succeeds with no errors. If tsc emits errors unrelated to this change, stop and fix them first.

- [ ] **Step 5: Commit**

```bash
git add package.json package-lock.json
git commit -m "validation-dashboard: add framer-motion, lucide-react, vitest"
```

---

### Task 2: Swap primary font to Space Grotesk

**Files:**
- Modify: `validation-dashboard/dove-dashboard/src/index.css:1-24`

- [ ] **Step 1: Update the Google Fonts import and `--font-sans` token**

Replace the first two `@import` lines and the `@theme` block's font declarations. Current (line 1) is:
```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap');
```

New:
```css
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap');
```

Inside `@theme { ... }` change:
```css
  --font-sans: 'Inter', sans-serif;
```
to:
```css
  --font-sans: 'Space Grotesk', system-ui, sans-serif;
```

- [ ] **Step 2: Run dev server and verify**

```bash
npm run dev
```
Open `http://localhost:5173` in a browser. Confirm body text renders in Space Grotesk (slightly more geometric than Inter). Stop the dev server.

- [ ] **Step 3: Commit**

```bash
git add src/index.css
git commit -m "validation-dashboard: swap primary font to Space Grotesk"
```

---

### Task 3: Rename design tokens to `darpan-*`

**Files:**
- Modify: `validation-dashboard/dove-dashboard/src/index.css:4-25`

- [ ] **Step 1: Rewrite the `@theme` block**

Replace the entire `@theme { ... }` block in `src/index.css` with:

```css
@theme {
  --color-darpan-bg: #0A0A0A;
  --color-darpan-surface: #111111;
  --color-darpan-elevated: #1A1A1A;
  --color-darpan-border: #2A2A2A;
  --color-darpan-border-active: #333333;
  --color-darpan-lime: #C8FF00;
  --color-darpan-lime-dim: #9ACC00;
  --color-darpan-cyan: #00D4FF;
  --color-darpan-cyan-dim: #00A8CC;
  --color-darpan-success: #00FF88;
  --color-darpan-warning: #FFB800;
  --color-darpan-error: #FF4444;
  --color-concept-1: #3B82F6;
  --color-concept-2: #10B981;
  --color-concept-3: #F59E0B;
  --color-concept-4: #EF4444;
  --color-concept-5: #8B5CF6;
  --font-sans: 'Space Grotesk', system-ui, sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
}
```

- [ ] **Step 2: Update body and scrollbar rules to reference new names**

In the same file, replace:
```css
body {
  background-color: var(--color-bg);
  ...
}
```
with:
```css
body {
  background-color: var(--color-darpan-bg);
  ...
}
```

And `::-webkit-scrollbar-track { background: var(--color-bg); }` → `var(--color-darpan-bg)`.
And `::-webkit-scrollbar-thumb { background: var(--color-border); }` → `var(--color-darpan-border)`.
And `::-webkit-scrollbar-thumb:hover { background: var(--color-primary); }` → `var(--color-darpan-lime)`.
And `*:focus-visible { outline: 2px solid var(--color-primary); }` → `var(--color-darpan-lime)`.

- [ ] **Step 3: Do not build yet**

The build will fail because every existing component uses the old class names. Next task fixes that in bulk.

---

### Task 4: Bulk-migrate token class names across all components

**Files:**
- Modify: all `.tsx` files under `validation-dashboard/dove-dashboard/src/components/` and `src/App.tsx`

This is a mechanical find/replace sweep. Use `sed`.

- [ ] **Step 1: Replace `bg-*` classes**

```bash
cd validation-dashboard/dove-dashboard
find src -type f \( -name "*.tsx" -o -name "*.ts" \) -exec sed -i '' \
  -e 's/\bbg-bg\b/bg-darpan-bg/g' \
  -e 's/\bbg-surface\b/bg-darpan-surface/g' \
  -e 's/\bbg-card\b/bg-darpan-surface/g' \
  -e 's/\bbg-muted\b/bg-darpan-elevated/g' \
  -e 's/\bbg-primary\b/bg-darpan-lime/g' \
  -e 's/\bbg-secondary\b/bg-darpan-cyan/g' \
  -e 's/\bbg-success\b/bg-darpan-success/g' \
  -e 's/\bbg-warning\b/bg-darpan-warning/g' \
  -e 's/\bbg-destructive\b/bg-darpan-error/g' \
  {} +
```

- [ ] **Step 2: Replace `border-*` classes**

```bash
find src -type f \( -name "*.tsx" -o -name "*.ts" \) -exec sed -i '' \
  -e 's/\bborder-border\b/border-darpan-border/g' \
  -e 's/\bborder-primary\b/border-darpan-lime/g' \
  -e 's/\bborder-secondary\b/border-darpan-cyan/g' \
  -e 's/\bborder-success\b/border-darpan-success/g' \
  -e 's/\bborder-warning\b/border-darpan-warning/g' \
  -e 's/\bborder-destructive\b/border-darpan-error/g' \
  {} +
```

- [ ] **Step 3: Replace `text-*` classes**

```bash
find src -type f \( -name "*.tsx" -o -name "*.ts" \) -exec sed -i '' \
  -e 's/\btext-primary\b/text-darpan-lime/g' \
  -e 's/\btext-secondary\b/text-darpan-cyan/g' \
  -e 's/\btext-success\b/text-darpan-success/g' \
  -e 's/\btext-warning\b/text-darpan-warning/g' \
  -e 's/\btext-destructive\b/text-darpan-error/g' \
  -e 's/\btext-text-secondary\b/text-white\/60/g' \
  -e 's/\btext-text-muted\b/text-white\/40/g' \
  -e 's/\btext-text\b/text-white/g' \
  {} +
```

- [ ] **Step 4: Replace opacity suffix variants** (e.g. `bg-primary/10`, `text-primary/30`)

```bash
find src -type f \( -name "*.tsx" -o -name "*.ts" \) -exec sed -i '' \
  -e 's/\bbg-primary\//bg-darpan-lime\//g' \
  -e 's/\btext-primary\//text-darpan-lime\//g' \
  -e 's/\bborder-primary\//border-darpan-lime\//g' \
  -e 's/\bbg-secondary\//bg-darpan-cyan\//g' \
  -e 's/\btext-secondary\//text-darpan-cyan\//g' \
  -e 's/\bborder-secondary\//border-darpan-cyan\//g' \
  -e 's/\bbg-success\//bg-darpan-success\//g' \
  -e 's/\btext-success\//text-darpan-success\//g' \
  -e 's/\bborder-success\//border-darpan-success\//g' \
  -e 's/\bbg-warning\//bg-darpan-warning\//g' \
  -e 's/\btext-warning\//text-darpan-warning\//g' \
  -e 's/\bborder-warning\//border-darpan-warning\//g' \
  -e 's/\bbg-destructive\//bg-darpan-error\//g' \
  -e 's/\btext-destructive\//text-darpan-error\//g' \
  -e 's/\bborder-destructive\//border-darpan-error\//g' \
  {} +
```

- [ ] **Step 5: Sanity-check no old tokens remain**

```bash
grep -rE '\b(bg-card|bg-bg|bg-muted|border-border|text-primary|text-text-secondary|text-text-muted)\b' src --include="*.tsx" --include="*.ts" || echo "clean"
```
Expected: `clean`.

- [ ] **Step 6: Build**

```bash
npm run build
```
Expected: success. If any errors reference unknown CSS classes, those are leftovers — grep the file and fix by hand.

- [ ] **Step 7: Dev-server visual check**

```bash
npm run dev
```
Open the four tabs — they should all still render with their current layout (we haven't touched layout yet, only token names). Confirm nothing is now invisible (bad text color) or the wrong shade. Stop the server.

- [ ] **Step 8: Commit**

```bash
git add src
git commit -m "validation-dashboard: migrate design tokens to darpan-* namespace"
```

---

## Phase 2 — Pure-logic utilities (TDD)

### Task 5: Wire up vitest

**Files:**
- Modify: `validation-dashboard/dove-dashboard/package.json`
- Modify: `validation-dashboard/dove-dashboard/vite.config.ts`
- Create: `validation-dashboard/dove-dashboard/src/lib/__tests__/.gitkeep`

- [ ] **Step 1: Add a test script to package.json**

Edit `package.json` so the `scripts` block becomes:

```json
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "lint": "eslint .",
    "preview": "vite preview",
    "start": "serve dist -s -l tcp://0.0.0.0:$PORT",
    "test": "vitest run",
    "test:watch": "vitest"
  },
```

- [ ] **Step 2: Add vitest config to vite.config.ts**

Replace the contents of `vite.config.ts` with:

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': '/src',
    },
  },
  test: {
    environment: 'node',
    include: ['src/**/*.test.ts', 'src/**/*.test.tsx'],
  },
})
```

- [ ] **Step 3: Add a triple-slash reference at the top of vite.config.ts so vitest types resolve**

Insert as line 1:

```typescript
/// <reference types="vitest" />
```

- [ ] **Step 4: Confirm vitest runs with zero tests**

```bash
npm test
```
Expected: `No test files found` or similar. Exit code 0.

- [ ] **Step 5: Commit**

```bash
git add package.json package-lock.json vite.config.ts
git commit -m "validation-dashboard: wire up vitest"
```

---

### Task 6: Implement `spearmanRho` in verdict-utils (TDD)

**Files:**
- Create: `validation-dashboard/dove-dashboard/src/lib/verdict-utils.ts`
- Create: `validation-dashboard/dove-dashboard/src/lib/verdict-utils.test.ts`

- [ ] **Step 1: Write the failing test**

Create `src/lib/verdict-utils.test.ts`:

```typescript
import { describe, it, expect } from 'vitest';
import { spearmanRho } from './verdict-utils';

describe('spearmanRho', () => {
  it('returns 1 for identical rankings', () => {
    const a = { A: 80, B: 60, C: 40 };
    const b = { A: 81, B: 61, C: 41 };
    expect(spearmanRho(a, b)).toBeCloseTo(1, 4);
  });

  it('returns -1 for perfectly reversed rankings', () => {
    const a = { A: 80, B: 60, C: 40 };
    const b = { A: 40, B: 60, C: 80 };
    expect(spearmanRho(a, b)).toBeCloseTo(-1, 4);
  });

  it('returns 0 when only one shared key exists', () => {
    const a = { A: 80 };
    const b = { A: 40, B: 60 };
    expect(spearmanRho(a, b)).toBe(0);
  });

  it('handles ties by using mid-ranks', () => {
    const a = { A: 50, B: 50, C: 70 };
    const b = { A: 60, B: 60, C: 80 };
    // A,B tie at rank 2.5 in both; C is rank 1 in both. rho = 1.
    expect(spearmanRho(a, b)).toBeCloseTo(1, 4);
  });

  it('ignores keys that are not in both maps', () => {
    const a = { A: 80, B: 60, C: 40, D: 20 };
    const b = { A: 81, B: 61, C: 41 };
    expect(spearmanRho(a, b)).toBeCloseTo(1, 4);
  });
});
```

- [ ] **Step 2: Run tests — expect failure**

```bash
npm test
```
Expected: All five tests fail with `Cannot find module './verdict-utils'` or similar.

- [ ] **Step 3: Implement spearmanRho**

Create `src/lib/verdict-utils.ts`:

```typescript
type ScoreMap = Record<string, number>;

function midRanks(values: number[]): number[] {
  const indexed = values.map((v, i) => ({ v, i }));
  indexed.sort((a, b) => b.v - a.v); // descending

  const ranks = new Array<number>(values.length);
  let i = 0;
  while (i < indexed.length) {
    let j = i;
    while (j + 1 < indexed.length && indexed[j + 1].v === indexed[i].v) j++;
    const mid = (i + j) / 2 + 1; // 1-based mid-rank
    for (let k = i; k <= j; k++) ranks[indexed[k].i] = mid;
    i = j + 1;
  }
  return ranks;
}

export function spearmanRho(a: ScoreMap, b: ScoreMap): number {
  const shared = Object.keys(a).filter((k) => k in b);
  if (shared.length < 2) return 0;

  const aVals = shared.map((k) => a[k]);
  const bVals = shared.map((k) => b[k]);
  const aRanks = midRanks(aVals);
  const bRanks = midRanks(bVals);

  const n = shared.length;
  const mean = (n + 1) / 2;
  let num = 0, dA = 0, dB = 0;
  for (let i = 0; i < n; i++) {
    const da = aRanks[i] - mean;
    const db = bRanks[i] - mean;
    num += da * db;
    dA += da * da;
    dB += db * db;
  }
  if (dA === 0 || dB === 0) return 0;
  return num / Math.sqrt(dA * dB);
}
```

- [ ] **Step 4: Run tests — expect pass**

```bash
npm test
```
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/lib/verdict-utils.ts src/lib/verdict-utils.test.ts
git commit -m "validation-dashboard: add spearmanRho to verdict-utils"
```

---

### Task 7: Add `overallAgreementPct` and `sharedTierCount`

**Files:**
- Modify: `validation-dashboard/dove-dashboard/src/lib/verdict-utils.ts`
- Modify: `validation-dashboard/dove-dashboard/src/lib/verdict-utils.test.ts`

- [ ] **Step 1: Add tests**

Append to `src/lib/verdict-utils.test.ts`:

```typescript
import { overallAgreementPct, sharedTierCount } from './verdict-utils';

describe('overallAgreementPct', () => {
  it('returns 100 when all composites are identical', () => {
    const a = { A: 70, B: 50 };
    const b = { A: 70, B: 50 };
    expect(overallAgreementPct(a, b)).toBe(100);
  });

  it('subtracts delta/100 per concept and averages', () => {
    const a = { A: 70, B: 50 };
    const b = { A: 60, B: 50 }; // delta 10 and 0 → 0.9 and 1.0 → mean 0.95 → 95
    expect(overallAgreementPct(a, b)).toBe(95);
  });

  it('floors at 0 per concept', () => {
    const a = { A: 0 };
    const b = { A: 200 }; // delta 200 → capped at 0 → 0%
    expect(overallAgreementPct(a, b)).toBe(0);
  });

  it('ignores non-shared keys', () => {
    const a = { A: 70, C: 30 };
    const b = { A: 70, B: 99 };
    expect(overallAgreementPct(a, b)).toBe(100);
  });

  it('returns 0 when no shared keys', () => {
    expect(overallAgreementPct({ A: 70 }, { B: 70 })).toBe(0);
  });
});

describe('sharedTierCount', () => {
  it('counts concepts with identical tier', () => {
    const a = { A: 1, B: 1, C: 2 };
    const b = { A: 1, B: 2, C: 2 };
    expect(sharedTierCount(a, b)).toBe(2);
  });

  it('ignores concepts not in both maps', () => {
    const a = { A: 1, B: 1 };
    const b = { A: 1, C: 1 };
    expect(sharedTierCount(a, b)).toBe(1);
  });
});
```

- [ ] **Step 2: Run tests — expect failure**

```bash
npm test
```
Expected: 2 new describe blocks fail; existing 5 still pass.

- [ ] **Step 3: Implement both functions**

Append to `src/lib/verdict-utils.ts`:

```typescript
export function overallAgreementPct(a: ScoreMap, b: ScoreMap): number {
  const shared = Object.keys(a).filter((k) => k in b);
  if (shared.length === 0) return 0;
  const perConcept = shared.map((k) => Math.max(0, 1 - Math.abs(a[k] - b[k]) / 100));
  const mean = perConcept.reduce((s, v) => s + v, 0) / shared.length;
  return Math.round(mean * 100);
}

type TierMap = Record<string, number>;
export function sharedTierCount(a: TierMap, b: TierMap): number {
  return Object.keys(a).filter((k) => k in b && a[k] === b[k]).length;
}
```

- [ ] **Step 4: Run tests — expect pass**

```bash
npm test
```
Expected: 12 passed total.

- [ ] **Step 5: Commit**

```bash
git add src/lib/verdict-utils.ts src/lib/verdict-utils.test.ts
git commit -m "validation-dashboard: add overallAgreementPct and sharedTierCount"
```

---

### Task 8: Add headline + supporting-sentence composers

**Files:**
- Modify: `validation-dashboard/dove-dashboard/src/lib/verdict-utils.ts`
- Modify: `validation-dashboard/dove-dashboard/src/lib/verdict-utils.test.ts`

- [ ] **Step 1: Add tests**

Append to `src/lib/verdict-utils.test.ts`:

```typescript
import {
  aggregateHeadline,
  aggregateSupporting,
  individualHeadline,
  individualSupporting,
  formatPValue,
} from './verdict-utils';

describe('aggregateHeadline', () => {
  it('returns Confirmed copy', () => {
    expect(aggregateHeadline('Confirmed')).toBe('Twins match customers on this study');
  });
  it('returns Directional copy', () => {
    expect(aggregateHeadline('Directional')).toBe('Twins partly match — read with caution');
  });
  it('returns Divergent copy', () => {
    expect(aggregateHeadline('Divergent')).toBe('Twins do not match — further testing needed');
  });
});

describe('aggregateSupporting', () => {
  it('Confirmed: mentions shared top + friedman + shared tiers', () => {
    const s = aggregateSupporting({
      level: 'Confirmed',
      realTop: 'Deep Nourish',
      twinTop: 'Deep Nourish',
      friedmanP: 0.003,
      friedmanSig: true,
      sharedTiers: 4,
      totalConcepts: 5,
      rankAgreementPairs: 5,
    });
    expect(s).toContain('Deep Nourish');
    expect(s).toContain('Friedman');
    expect(s).toContain('4 of 5');
  });

  it('Divergent: names both tops and tier mismatch count', () => {
    const s = aggregateSupporting({
      level: 'Divergent',
      realTop: 'Deep Nourish',
      twinTop: 'Pure Touch',
      friedmanP: 0.5,
      friedmanSig: false,
      sharedTiers: 1,
      totalConcepts: 5,
      rankAgreementPairs: 2,
    });
    expect(s).toContain('Deep Nourish');
    expect(s).toContain('Pure Touch');
  });
});

describe('individualHeadline', () => {
  it('Good template', () => {
    expect(individualHeadline('Good', 'P04', 'Deep Nourish')).toBe(
      'Twin P04 matches participant P04 on Deep Nourish',
    );
  });
  it('All-concepts variant', () => {
    expect(individualHeadline('Acceptable', 'P04', null)).toBe(
      'Twin P04 vs participant P04 across all concepts',
    );
  });
});

describe('individualSupporting', () => {
  it('names the largest single deviation', () => {
    const s = individualSupporting({
      withinOneCount: 12,
      totalMetrics: 14,
      largestDeviation: { metric: 'believability', real: 2, twin: 4 },
    });
    expect(s).toContain('12');
    expect(s).toContain('14');
    expect(s).toContain('believability');
  });

  it('omits deviation sentence when no metrics', () => {
    const s = individualSupporting({
      withinOneCount: 0,
      totalMetrics: 0,
      largestDeviation: null,
    });
    expect(s).toBe('No metric data available for this pair.');
  });
});

describe('formatPValue', () => {
  it('renders p<0.001 for tiny values', () => {
    expect(formatPValue(0.0002)).toBe('p<0.001');
  });
  it('renders regular values to three decimals', () => {
    expect(formatPValue(0.034)).toBe('p=0.034');
  });
});
```

- [ ] **Step 2: Run tests — expect failure**

```bash
npm test
```
Expected: 5 new describe blocks fail.

- [ ] **Step 3: Implement the composers**

Append to `src/lib/verdict-utils.ts`:

```typescript
export type AgreementLevel = 'Confirmed' | 'Directional' | 'Divergent';
export type QualityTier = 'Good' | 'Acceptable' | 'Poor';

export function formatPValue(p: number): string {
  if (p < 0.001) return 'p<0.001';
  return `p=${p.toFixed(3)}`;
}

export function aggregateHeadline(level: AgreementLevel): string {
  switch (level) {
    case 'Confirmed':   return 'Twins match customers on this study';
    case 'Directional': return 'Twins partly match — read with caution';
    case 'Divergent':   return 'Twins do not match — further testing needed';
  }
}

export interface AggregateSupportingInput {
  level: AgreementLevel;
  realTop: string;
  twinTop: string;
  friedmanP: number;
  friedmanSig: boolean;
  sharedTiers: number;
  totalConcepts: number;
  rankAgreementPairs: number;
}

export function aggregateSupporting(i: AggregateSupportingInput): string {
  const sig = i.friedmanSig ? 'significant' : 'not significant';
  if (i.level === 'Confirmed') {
    return `Twins ranked ${i.realTop} #1, same as customers. Friedman ${formatPValue(i.friedmanP)} (${sig}). ${i.sharedTiers} of ${i.totalConcepts} concepts fall in the same statistical tier.`;
  }
  if (i.level === 'Directional') {
    return `Twins ranked ${i.twinTop} #1; customers ranked ${i.realTop} #1. Overall ordering agrees on ${i.rankAgreementPairs}/${i.totalConcepts} pairs.`;
  }
  return `Twins ranked ${i.twinTop} #1; customers ranked ${i.realTop} #1. ${i.totalConcepts - i.sharedTiers}/${i.totalConcepts} concepts fall in different statistical tiers.`;
}

export function individualHeadline(
  tier: QualityTier,
  participantId: string,
  conceptName: string | null,
): string {
  if (conceptName === null) {
    return `Twin ${participantId} vs participant ${participantId} across all concepts`;
  }
  switch (tier) {
    case 'Good':
      return `Twin ${participantId} matches participant ${participantId} on ${conceptName}`;
    case 'Acceptable':
      return `Twin ${participantId} partly matches participant ${participantId} on ${conceptName}`;
    case 'Poor':
      return `Twin ${participantId} diverges from participant ${participantId} on ${conceptName}`;
  }
}

export interface IndividualSupportingInput {
  withinOneCount: number;
  totalMetrics: number;
  largestDeviation: { metric: string; real: number; twin: number } | null;
}

export function individualSupporting(i: IndividualSupportingInput): string {
  if (i.totalMetrics === 0 || i.largestDeviation === null) {
    return 'No metric data available for this pair.';
  }
  const d = i.largestDeviation;
  return `Within ±1 on ${i.withinOneCount} of ${i.totalMetrics} metrics. Largest deviation on ${d.metric} (twin rated ${d.twin}, real rated ${d.real}).`;
}
```

- [ ] **Step 4: Run tests — expect pass**

```bash
npm test
```
Expected: 20 passed total.

- [ ] **Step 5: Commit**

```bash
git add src/lib/verdict-utils.ts src/lib/verdict-utils.test.ts
git commit -m "validation-dashboard: add headline/supporting-sentence composers"
```

---

## Phase 3 — Aggregate tab

All component files in this phase live under `validation-dashboard/dove-dashboard/src/components/aggregate/`.

### Task 9: Create ResearchQuestionCard

**Files:**
- Create: `src/components/aggregate/ResearchQuestionCard.tsx`

- [ ] **Step 1: Write the component**

```tsx
import { motion } from 'framer-motion';

interface Props {
  question: string;
}

export function ResearchQuestionCard({ question }: Props) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-darpan-surface border border-darpan-border rounded-xl px-5 py-4"
    >
      <p className="text-xs font-medium text-white/30 uppercase tracking-wider mb-1.5">
        Research Question
      </p>
      <p className="text-sm text-white/60 leading-relaxed">{question}</p>
    </motion.div>
  );
}
```

- [ ] **Step 2: Build**

```bash
npm run build
```
Expected: success.

- [ ] **Step 3: Commit**

```bash
git add src/components/aggregate/ResearchQuestionCard.tsx
git commit -m "validation-dashboard: add ResearchQuestionCard"
```

---

### Task 10: Create HeroVerdictCard

**Files:**
- Create: `src/components/aggregate/HeroVerdictCard.tsx`

- [ ] **Step 1: Write the component**

```tsx
import { motion } from 'framer-motion';
import { CheckCircle2, AlertTriangle, XCircle } from 'lucide-react';
import {
  aggregateHeadline,
  aggregateSupporting,
  spearmanRho,
  overallAgreementPct,
  sharedTierCount,
  type AgreementLevel,
} from '../../lib/verdict-utils';
import type { DashboardData } from '../../types';

interface Props {
  data: DashboardData;
}

const LEVEL_CONFIG: Record<AgreementLevel, { color: string; Icon: typeof CheckCircle2 }> = {
  Confirmed:   { color: '#00FF88', Icon: CheckCircle2 },
  Directional: { color: '#FFB800', Icon: AlertTriangle },
  Divergent:   { color: '#FF4444', Icon: XCircle },
};

export function HeroVerdictCard({ data }: Props) {
  const level = data.agreement.level as AgreementLevel;
  const cfg = LEVEL_CONFIG[level];

  const agreementPct = overallAgreementPct(data.real.composites, data.twin.composites);
  const rho = spearmanRho(data.real.composites, data.twin.composites);
  const shared = sharedTierCount(data.real.tiers, data.twin.tiers);
  const total = Object.keys(data.real.tiers).length;

  const rankAgreement = (() => {
    const names = Object.keys(data.real.composites).filter((n) => n in data.twin.composites);
    const sortedReal = [...names].sort((a, b) => data.real.composites[b] - data.real.composites[a]);
    const sortedTwin = [...names].sort((a, b) => data.twin.composites[b] - data.twin.composites[a]);
    let pairs = 0;
    for (let i = 0; i < names.length; i++) if (sortedReal[i] === sortedTwin[i]) pairs++;
    return pairs;
  })();

  const supporting = aggregateSupporting({
    level,
    realTop: data.agreement.real_top,
    twinTop: data.agreement.twin_top,
    friedmanP: data.real.friedman.p_value,
    friedmanSig: data.real.friedman.significant,
    sharedTiers: shared,
    totalConcepts: total,
    rankAgreementPairs: rankAgreement,
  });

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.05 }}
      className="bg-darpan-surface border border-darpan-border rounded-xl overflow-hidden"
      style={{
        borderLeftWidth: 3,
        borderLeftColor: cfg.color,
        boxShadow: `0 0 20px ${cfg.color}10`,
      }}
    >
      <div className="flex items-start justify-between gap-4 p-5">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <cfg.Icon className="w-4 h-4" style={{ color: cfg.color }} />
            <span
              className="text-xs font-semibold uppercase tracking-wider"
              style={{ color: cfg.color }}
            >
              {level}
            </span>
          </div>
          <h2 className="text-xl font-bold text-white mb-2">{aggregateHeadline(level)}</h2>
          <p className="text-sm text-white/60 leading-relaxed">{supporting}</p>
        </div>

        <div className="flex flex-col gap-2 shrink-0">
          <div className="bg-white/[0.03] border border-darpan-border rounded-lg px-3 py-2 text-right">
            <div className="text-[10px] text-white/30 uppercase tracking-wider">Agreement</div>
            <div className="font-mono text-base text-white tabular-nums">{agreementPct}%</div>
          </div>
          <div className="bg-white/[0.03] border border-darpan-border rounded-lg px-3 py-2 text-right">
            <div className="text-[10px] text-white/30 uppercase tracking-wider">Rank ρ</div>
            <div className="font-mono text-base text-white tabular-nums">{rho.toFixed(2)}</div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
```

- [ ] **Step 2: Build**

```bash
npm run build
```
Expected: success.

- [ ] **Step 3: Commit**

```bash
git add src/components/aggregate/HeroVerdictCard.tsx
git commit -m "validation-dashboard: add HeroVerdictCard"
```

---

### Task 11: Create ConceptAgreementTable

**Files:**
- Create: `src/components/aggregate/ConceptAgreementTable.tsx`

- [ ] **Step 1: Write the component**

```tsx
import { motion } from 'framer-motion';
import { CONCEPT_COLORS } from '../../constants/theme';
import { useDashboardStore } from '../../store/useDashboardStore';
import type { DashboardData } from '../../types';

function bucketFor(absDelta: number): { label: string; color: string } {
  if (absDelta < 5)  return { label: 'strong',   color: '#00FF88' };
  if (absDelta < 10) return { label: 'moderate', color: '#FFB800' };
  return                    { label: 'weak',     color: '#FF4444' };
}

function deltaBg(absDelta: number): string {
  if (absDelta < 5)  return 'rgba(0,255,136,0.10)';
  if (absDelta < 10) return 'rgba(255,184,0,0.10)';
  return                    'rgba(255,68,68,0.10)';
}

function t2bBg(v: number | null): string {
  if (v === null) return 'transparent';
  if (v >= 60) return 'rgba(0,255,136,0.15)';
  if (v >= 35) return 'rgba(255,184,0,0.15)';
  return              'rgba(255,68,68,0.15)';
}

interface Props {
  data: DashboardData;
}

export function ConceptAgreementTable({ data }: Props) {
  const dataSource = useDashboardStore((s) => s.dataSource);
  const names = Object.keys(data.real.composites).sort(
    (a, b) => (data.real.composites[b] ?? 0) - (data.real.composites[a] ?? 0),
  );

  const realDim = dataSource === 'twin' ? 'opacity-20' : '';
  const twinDim = dataSource === 'real' ? 'opacity-20' : '';

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.1 }}
      className="bg-darpan-surface border border-darpan-border rounded-xl overflow-hidden"
    >
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-darpan-border bg-darpan-bg/50">
              <th className="px-5 py-3.5 text-left text-xs font-medium text-white/40 uppercase tracking-wider">
                Concept
              </th>
              <th className={`px-4 py-3.5 text-center text-xs font-medium text-white/40 uppercase tracking-wider ${realDim}`}>
                Real
              </th>
              <th className={`px-4 py-3.5 text-center text-xs font-medium text-white/40 uppercase tracking-wider ${twinDim}`}>
                Twin
              </th>
              <th className="px-4 py-3.5 text-center text-xs font-medium text-white/40 uppercase tracking-wider">
                Δ
              </th>
              <th className="px-4 py-3.5 text-center text-xs font-medium text-white/40 uppercase tracking-wider">
                Agreement
              </th>
            </tr>
          </thead>
          <tbody>
            {names.map((name, i) => {
              const real = data.real.composites[name];
              const twin = data.twin.composites[name];
              const delta = twin - real;
              const bucket = bucketFor(Math.abs(delta));
              return (
                <tr
                  key={name}
                  className={`border-b border-darpan-border/50 ${i % 2 === 0 ? '' : 'bg-white/[0.01]'}`}
                >
                  <td className="px-5 py-3 text-sm font-medium text-white/80">
                    <div className="flex items-center gap-2">
                      <span
                        className="w-2.5 h-2.5 rounded-full shrink-0"
                        style={{ backgroundColor: CONCEPT_COLORS[name] }}
                      />
                      {name}
                    </div>
                  </td>
                  <td
                    className={`px-4 py-3 text-center text-sm font-mono tabular-nums text-white ${realDim}`}
                    style={{ backgroundColor: t2bBg(real) }}
                  >
                    {real.toFixed(1)}%
                  </td>
                  <td
                    className={`px-4 py-3 text-center text-sm font-mono tabular-nums text-white ${twinDim}`}
                    style={{ backgroundColor: t2bBg(twin) }}
                  >
                    {twin.toFixed(1)}%
                  </td>
                  <td
                    className="px-4 py-3 text-center text-sm font-mono tabular-nums text-white"
                    style={{ backgroundColor: deltaBg(Math.abs(delta)) }}
                  >
                    {delta >= 0 ? '+' : ''}{delta.toFixed(1)}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <div className="inline-flex items-center gap-1.5 text-xs" style={{ color: bucket.color }}>
                      <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: bucket.color }} />
                      {bucket.label}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="flex items-center gap-5 px-5 py-3 border-t border-darpan-border text-[11px] text-white/30">
        <span>Δ = twin − real (pp)</span>
        <span className="text-white/10">|</span>
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: 'rgba(0,255,136,0.3)' }} />
          strong &lt;5
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: 'rgba(255,184,0,0.3)' }} />
          moderate 5–10
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: 'rgba(255,68,68,0.3)' }} />
          weak &gt;10
        </span>
      </div>
    </motion.div>
  );
}
```

- [ ] **Step 2: Build**

```bash
npm run build
```

- [ ] **Step 3: Commit**

```bash
git add src/components/aggregate/ConceptAgreementTable.tsx
git commit -m "validation-dashboard: add ConceptAgreementTable"
```

---

### Task 12: Create RecommendationCard

**Files:**
- Create: `src/components/aggregate/RecommendationCard.tsx`

- [ ] **Step 1: Write the component**

```tsx
import { motion } from 'framer-motion';
import { Trophy, TrendingUp } from 'lucide-react';
import { CONCEPT_COLORS } from '../../constants/theme';
import type { DashboardData } from '../../types';

interface Props {
  data: DashboardData;
}

function composeRecommendation(data: DashboardData): string {
  const topConcept = data.agreement.real_top;
  const best2 = data.real.turf.best_2;
  const realTiers = data.real.tiers;
  const tier1Count = Object.values(realTiers).filter((t) => t === 1).length;
  const hasStatSeparation = tier1Count < Object.keys(realTiers).length;

  if (data.agreement.level === 'Divergent') {
    return `Results diverge between sources. Real favours ${data.agreement.real_top}, twins favour ${data.agreement.twin_top}. Further testing recommended.`;
  }
  if (!hasStatSeparation) {
    return `${topConcept} leads directionally but is not statistically distinguished from other concepts. If developing 2 concepts, ${best2.concepts.join(' + ')} maximises reach at ${best2.reach_pct}%.`;
  }
  if (data.agreement.level === 'Confirmed') {
    return `Lead with ${topConcept}. Optimal 2-concept portfolio: ${best2.concepts.join(' + ')} (${best2.reach_pct}% unduplicated reach).`;
  }
  return `${topConcept} leads with directional agreement. Consider ${best2.concepts.join(' + ')} for maximum reach (${best2.reach_pct}%).`;
}

function t2bColor(v: number): string {
  if (v >= 60) return '#00FF88';
  if (v >= 35) return '#FFB800';
  return '#FF4444';
}

export function RecommendationCard({ data }: Props) {
  const names = Object.keys(data.real.composites).sort(
    (a, b) => (data.real.composites[b] ?? 0) - (data.real.composites[a] ?? 0),
  );
  const recommended = new Set<string>(
    data.agreement.level === 'Divergent' ? [data.agreement.real_top] : [data.agreement.real_top],
  );
  const explanation = composeRecommendation(data);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.15 }}
      className="bg-darpan-surface border border-darpan-lime/20 rounded-xl overflow-hidden"
    >
      <div className="flex items-center gap-3 px-5 py-4 border-b border-darpan-border bg-darpan-lime/[0.03]">
        <div className="w-8 h-8 rounded-lg bg-darpan-lime/10 flex items-center justify-center">
          <Trophy className="w-4 h-4 text-darpan-lime" />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-white">Recommendation</h3>
          <p className="text-xs text-white/35">Based on real customer data, corroborated by twins</p>
        </div>
      </div>

      <div className="p-5 space-y-4">
        <p className="text-sm text-white/60 leading-relaxed">{explanation}</p>

        <div className="space-y-2">
          {names.map((name, i) => {
            const isRecommended = recommended.has(name);
            const real = data.real.composites[name];
            const twin = data.twin.composites[name];
            const delta = Math.abs(twin - real);
            const twinDot =
              delta < 5  ? { color: '#00FF88', label: 'strong' } :
              delta < 10 ? { color: '#FFB800', label: 'moderate' } :
                           { color: '#FF4444', label: 'weak' };

            return (
              <div
                key={name}
                className={`flex items-center gap-3 px-4 py-2.5 rounded-lg ${
                  isRecommended
                    ? 'bg-darpan-lime/[0.06] border border-darpan-lime/15'
                    : 'bg-white/[0.02] border border-transparent'
                }`}
              >
                <span
                  className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-semibold ${
                    isRecommended
                      ? 'bg-darpan-lime/20 text-darpan-lime'
                      : 'bg-white/5 text-white/30'
                  }`}
                >
                  {i + 1}
                </span>
                <span className={`w-2 h-2 rounded-full shrink-0`} style={{ backgroundColor: CONCEPT_COLORS[name] }} />
                <span className={`flex-1 text-sm ${isRecommended ? 'text-white font-medium' : 'text-white/40'}`}>
                  {name}
                </span>
                <div className="flex items-center gap-2">
                  <TrendingUp className="w-3.5 h-3.5" style={{ color: t2bColor(real) }} />
                  <span className="text-sm font-mono tabular-nums font-medium" style={{ color: t2bColor(real) }}>
                    {real.toFixed(1)}%
                  </span>
                </div>
                <div
                  className="flex items-center gap-1 text-[10px] tabular-nums font-mono"
                  style={{ color: twinDot.color }}
                  title={`twin agreement: ${twinDot.label}`}
                >
                  <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: twinDot.color }} />
                  {twin.toFixed(1)}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </motion.div>
  );
}
```

- [ ] **Step 2: Build**

```bash
npm run build
```

- [ ] **Step 3: Commit**

```bash
git add src/components/aggregate/RecommendationCard.tsx
git commit -m "validation-dashboard: add RecommendationCard (Results-style)"
```

---

### Task 13: Create UnifiedDiffHeatmap

**Files:**
- Create: `src/components/aggregate/UnifiedDiffHeatmap.tsx`

- [ ] **Step 1: Write the component**

```tsx
import { CONCEPT_COLORS, METRIC_LABELS } from '../../constants/theme';
import type { DashboardData } from '../../types';

const CORE_COLS = ['pi', 'uniqueness', 'relevance', 'believability'] as const;
const EXTRA_COLS = ['interest', 'brand_fit'] as const;

function diffBg(absDelta: number): string {
  if (absDelta < 5)  return 'rgba(0,255,136,0.18)';
  if (absDelta < 10) return 'rgba(255,184,0,0.18)';
  return                    'rgba(255,68,68,0.18)';
}

function diffColor(absDelta: number): string {
  if (absDelta < 5)  return '#00FF88';
  if (absDelta < 10) return '#FFB800';
  return                    '#FF4444';
}

interface Props {
  data: DashboardData;
}

export function UnifiedDiffHeatmap({ data }: Props) {
  const names = Object.keys(data.real.composites).sort(
    (a, b) => (data.real.composites[b] ?? 0) - (data.real.composites[a] ?? 0),
  );
  const allCols: readonly string[] = [...CORE_COLS, ...EXTRA_COLS];

  return (
    <div className="bg-darpan-surface border border-darpan-border rounded-xl p-4 overflow-x-auto">
      <div className="flex items-center justify-between mb-3">
        <div className="text-[10px] font-semibold uppercase tracking-widest text-white/40">
          Δ twin − real (pp)
        </div>
        <div className="flex items-center gap-3 text-[10px] text-white/30">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-sm" style={{ backgroundColor: diffBg(2) }} />
            |Δ|&lt;5
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-sm" style={{ backgroundColor: diffBg(7) }} />
            5–10
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-sm" style={{ backgroundColor: diffBg(15) }} />
            &gt;10
          </span>
        </div>
      </div>

      <div
        className="grid gap-px"
        style={{
          gridTemplateColumns: `140px repeat(${CORE_COLS.length}, 1fr) 8px repeat(${EXTRA_COLS.length}, 1fr)`,
        }}
      >
        <div />
        {CORE_COLS.map((m) => (
          <div key={m} className="text-[10px] text-center text-white/60 pb-2">
            {METRIC_LABELS[m] ?? m}
          </div>
        ))}
        <div />
        {EXTRA_COLS.map((m) => (
          <div key={m} className="text-[10px] text-center text-white/40 pb-2">
            {METRIC_LABELS[m] ?? m}
          </div>
        ))}

        {names.map((name) => (
          <div key={name} className="contents">
            <div className="flex items-center gap-1.5 pr-2 py-2">
              <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: CONCEPT_COLORS[name] }} />
              <span className="text-xs font-medium text-white truncate">{name}</span>
            </div>
            {CORE_COLS.map((m) => {
              const r = data.real.t2b[name]?.[m]?.t2b ?? null;
              const t = data.twin.t2b[name]?.[m]?.t2b ?? null;
              if (r === null || t === null) {
                return <div key={m} className="flex items-center justify-center py-2 text-[11px] text-white/20">—</div>;
              }
              const d = t - r;
              return (
                <div
                  key={m}
                  className="flex items-center justify-center py-2 font-mono tabular-nums text-xs"
                  style={{ backgroundColor: diffBg(Math.abs(d)), color: diffColor(Math.abs(d)) }}
                  title={`real ${r.toFixed(1)} · twin ${t.toFixed(1)} · Δ ${d.toFixed(1)}`}
                >
                  {d >= 0 ? '+' : ''}{d.toFixed(1)}
                </div>
              );
            })}
            <div className="border-l border-darpan-border" />
            {EXTRA_COLS.map((m) => {
              const r = data.real.t2b[name]?.[m]?.t2b ?? null;
              const t = data.twin.t2b[name]?.[m]?.t2b ?? null;
              if (r === null || t === null) {
                return <div key={m} className="flex items-center justify-center py-2 text-[11px] text-white/20">—</div>;
              }
              const d = t - r;
              return (
                <div
                  key={m}
                  className="flex items-center justify-center py-2 font-mono tabular-nums text-xs"
                  style={{ backgroundColor: diffBg(Math.abs(d)), color: diffColor(Math.abs(d)) }}
                  title={`real ${r.toFixed(1)} · twin ${t.toFixed(1)} · Δ ${d.toFixed(1)}`}
                >
                  {d >= 0 ? '+' : ''}{d.toFixed(1)}
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Build**

```bash
npm run build
```

- [ ] **Step 3: Commit**

```bash
git add src/components/aggregate/UnifiedDiffHeatmap.tsx
git commit -m "validation-dashboard: add UnifiedDiffHeatmap"
```

---

### Task 14: Move and restyle CompositeRankingChart

**Files:**
- Create: `src/components/aggregate/CompositeRankingChart.tsx`
- Delete (later in cleanup task): `src/components/row2-ranking/CompositeRankingChart.tsx`

- [ ] **Step 1: Copy the existing chart and tighten styling**

Create `src/components/aggregate/CompositeRankingChart.tsx`:

```tsx
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { CONCEPT_COLORS } from '../../constants/theme';
import { useDashboardStore } from '../../store/useDashboardStore';
import type { DashboardData } from '../../types';

interface Props {
  data: DashboardData;
}

export function CompositeRankingChart({ data }: Props) {
  const dataSource = useDashboardStore((s) => s.dataSource);
  const focusedConcept = useDashboardStore((s) => s.focusedConcept);
  const drilldownMetric = useDashboardStore((s) => s.drilldownMetric);

  const conceptNames = data.metadata.concept_short_names;

  const chartData = conceptNames
    .map((name) => {
      let realVal: number | null = null;
      let twinVal: number | null = null;
      if (drilldownMetric) {
        realVal = data.real.t2b[name]?.[drilldownMetric]?.t2b ?? null;
        twinVal = data.twin.t2b[name]?.[drilldownMetric]?.t2b ?? null;
      } else {
        realVal = data.real.composites[name] ?? null;
        twinVal = data.twin.composites[name] ?? null;
      }
      return { name, real: realVal, twin: twinVal };
    })
    .sort((a, b) => {
      const aVal = dataSource === 'twin' ? (a.twin ?? 0) : (a.real ?? 0);
      const bVal = dataSource === 'twin' ? (b.twin ?? 0) : (b.real ?? 0);
      return bVal - aVal;
    });

  const showBoth = dataSource === 'both';

  return (
    <div className="bg-darpan-surface border border-darpan-border rounded-xl p-4">
      {showBoth && (
        <div className="flex items-center gap-4 mb-3 pl-[100px]">
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-2 rounded-sm bg-white/70" />
            <span className="text-[10px] text-white/60 font-mono">Real</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-2 rounded-sm bg-white/25" />
            <span className="text-[10px] text-white/60 font-mono">Twin</span>
          </div>
        </div>
      )}

      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={chartData} layout="vertical" margin={{ top: 5, right: 30, left: 10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#2A2A2A" horizontal={false} />
          <XAxis
            type="number"
            domain={[0, 100]}
            tick={{ fill: '#666', fontSize: 10, fontFamily: 'JetBrains Mono' }}
            axisLine={{ stroke: '#2A2A2A' }}
          />
          <YAxis
            type="category"
            dataKey="name"
            width={100}
            tick={{ fill: '#A0A0A0', fontSize: 11 }}
            axisLine={{ stroke: '#2A2A2A' }}
          />
          <Tooltip
            cursor={{ fill: 'rgba(255,255,255,0.03)' }}
            contentStyle={{
              backgroundColor: '#111111',
              border: '1px solid #2A2A2A',
              borderRadius: 8,
              fontSize: 11,
              fontFamily: 'JetBrains Mono',
              color: '#FFFFFF',
            }}
            labelStyle={{ color: '#A0A0A0' }}
            itemStyle={{ color: '#FFFFFF' }}
            formatter={(value, name) => [`${Number(value)?.toFixed(1)}%`, name === 'real' ? 'Real' : 'Twin']}
          />
          {(dataSource === 'real' || dataSource === 'both') && (
            <Bar dataKey="real" name="real" radius={[0, 4, 4, 0]} barSize={showBoth ? 14 : 22}>
              {chartData.map((entry) => (
                <Cell
                  key={entry.name}
                  fill={CONCEPT_COLORS[entry.name]}
                  opacity={!focusedConcept || focusedConcept === entry.name ? 0.85 : 0.2}
                />
              ))}
            </Bar>
          )}
          {(dataSource === 'twin' || dataSource === 'both') && (
            <Bar dataKey="twin" name="twin" radius={[0, 4, 4, 0]} barSize={showBoth ? 14 : 22}>
              {chartData.map((entry) => (
                <Cell
                  key={entry.name}
                  fill={CONCEPT_COLORS[entry.name]}
                  opacity={!focusedConcept || focusedConcept === entry.name ? (showBoth ? 0.3 : 0.85) : 0.1}
                />
              ))}
            </Bar>
          )}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
```

- [ ] **Step 2: Build**

```bash
npm run build
```

- [ ] **Step 3: Commit**

```bash
git add src/components/aggregate/CompositeRankingChart.tsx
git commit -m "validation-dashboard: move + restyle CompositeRankingChart"
```

---

### Task 15: Create DiagnosticSection (disclosure)

**Files:**
- Create: `src/components/aggregate/DiagnosticSection.tsx`

- [ ] **Step 1: Write the component**

```tsx
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown } from 'lucide-react';
import { UnifiedDiffHeatmap } from './UnifiedDiffHeatmap';
import { CompositeRankingChart } from './CompositeRankingChart';
import type { DashboardData } from '../../types';

interface Props {
  data: DashboardData;
}

export function DiagnosticSection({ data }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2 }}
      className="bg-darpan-surface border border-darpan-border rounded-xl overflow-hidden"
    >
      <button
        type="button"
        onClick={() => setOpen((x) => !x)}
        className="w-full flex items-center justify-between px-5 py-4 text-left hover:bg-white/[0.02] transition-colors"
      >
        <div>
          <h3 className="text-sm font-semibold text-white">Diagnostic details</h3>
          <p className="text-xs text-white/35 mt-0.5">
            Unified Δ heatmap and composite ranking — expand to stress-test the verdict
          </p>
        </div>
        <ChevronDown
          className={`w-4 h-4 text-white/40 transition-transform ${open ? 'rotate-180' : ''}`}
        />
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="px-5 pb-5 space-y-4 border-t border-darpan-border pt-4">
              <UnifiedDiffHeatmap data={data} />
              <CompositeRankingChart data={data} />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
```

- [ ] **Step 2: Build**

```bash
npm run build
```

- [ ] **Step 3: Commit**

```bash
git add src/components/aggregate/DiagnosticSection.tsx
git commit -m "validation-dashboard: add DiagnosticSection (collapsible)"
```

---

### Task 16: Port TurfCard, OrderBiasCard, QualitativeInsightsCard (restyle)

**Files:**
- Create: `src/components/aggregate/TurfCard.tsx`
- Create: `src/components/aggregate/OrderBiasCard.tsx`
- Create: `src/components/aggregate/QualitativeInsightsCard.tsx`

- [ ] **Step 1: Copy and restyle TurfCard**

Open `src/components/row4-insights/TurfCard.tsx`, copy its full contents into the new file `src/components/aggregate/TurfCard.tsx`, then:
- Remove any `boxShadow` inline styles.
- Ensure outer container uses `bg-darpan-surface border border-darpan-border rounded-xl p-5`.
- Change body copy classes to `text-sm text-white/60 leading-relaxed`.
- Change eyebrow labels to `text-xs font-medium text-white/30 uppercase tracking-wider`.
- Change numeric values to `font-mono tabular-nums text-white`.
- Leave all data-access logic unchanged.

- [ ] **Step 2: Repeat for OrderBiasCard and QualitativeInsightsCard**

Same treatment for the other two files; place the copies in `src/components/aggregate/`.

- [ ] **Step 3: Build**

```bash
npm run build
```

- [ ] **Step 4: Commit**

```bash
git add src/components/aggregate/TurfCard.tsx src/components/aggregate/OrderBiasCard.tsx src/components/aggregate/QualitativeInsightsCard.tsx
git commit -m "validation-dashboard: port + restyle TURF/OrderBias/Qualitative cards"
```

---

### Task 17: Create AggregateTab container and wire into App.tsx

**Files:**
- Create: `src/components/aggregate/AggregateTab.tsx`
- Modify: `src/App.tsx`

- [ ] **Step 1: Write the container**

```tsx
import { motion } from 'framer-motion';
import { DataSourceToggle } from '../shared/DataSourceToggle';
import { ResearchQuestionCard } from './ResearchQuestionCard';
import { HeroVerdictCard } from './HeroVerdictCard';
import { ConceptAgreementTable } from './ConceptAgreementTable';
import { RecommendationCard } from './RecommendationCard';
import { DiagnosticSection } from './DiagnosticSection';
import { TurfCard } from './TurfCard';
import { OrderBiasCard } from './OrderBiasCard';
import { QualitativeInsightsCard } from './QualitativeInsightsCard';
import type { DashboardData } from '../../types';

interface Props {
  data: DashboardData;
}

const DEFAULT_RESEARCH_QUESTION =
  'Which body-wash concept resonates most with Indian women aged 25–45?';

export function AggregateTab({ data }: Props) {
  return (
    <div className="max-w-5xl mx-auto w-full px-4 sm:px-6 py-6 sm:py-8 space-y-6">
      <ResearchQuestionCard question={DEFAULT_RESEARCH_QUESTION} />

      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.03 }}
        className="flex justify-end"
      >
        <DataSourceToggle />
      </motion.div>

      <HeroVerdictCard data={data} />
      <ConceptAgreementTable data={data} />
      <RecommendationCard data={data} />
      <DiagnosticSection data={data} />

      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.25 }}
      >
        <h3 className="text-xs font-medium text-white/30 uppercase tracking-wider mb-3">
          Deep insights
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <TurfCard data={data} />
          <OrderBiasCard data={data} />
          <QualitativeInsightsCard data={data} />
        </div>
      </motion.div>
    </div>
  );
}
```

- [ ] **Step 2: Swap out the old row components in App.tsx**

Replace the existing `App.tsx` contents with:

```tsx
import { useState } from 'react';
import dashboardData from './data/dashboard-data.json';
import validationData from './data/individual-validation-data.json';
import extendedAggData from './data/extended-aggregate-data.json';
import extendedValData from './data/extended-validation-data.json';
import { DashboardHeader } from './components/layout/DashboardHeader';
import { AggregateTab } from './components/aggregate/AggregateTab';
import { IndividualValidationTab } from './components/individual/IndividualValidationTab';
import { ExtendedAggregateTab } from './components/extended-aggregate/ExtendedAggregateTab';
import { ExtendedValidationTab } from './components/extended-validation/ExtendedValidationTab';
import type { DashboardData, DashboardTab } from './types';
import type { IndividualValidationData } from './types/individual';
import type { ExtendedValidationData } from './types/extended';

const data = dashboardData as unknown as DashboardData;
const individualData = validationData as unknown as IndividualValidationData;
const extAggData = extendedAggData as unknown as DashboardData;
const extValData = extendedValData as unknown as ExtendedValidationData;

function App() {
  const [activeTab, setActiveTab] = useState<DashboardTab>('aggregate');

  return (
    <div className="min-h-screen bg-darpan-bg">
      <DashboardHeader
        data={data}
        extData={extAggData}
        activeTab={activeTab}
        onTabChange={setActiveTab}
      />
      <main>
        {activeTab === 'aggregate' ? (
          <AggregateTab data={data} />
        ) : activeTab === 'individual' ? (
          <IndividualValidationTab data={individualData} />
        ) : activeTab === 'extended-aggregate' ? (
          <div className="max-w-[1400px] mx-auto">
            <ExtendedAggregateTab data={extAggData} originalData={data} />
          </div>
        ) : (
          <div className="max-w-[1400px] mx-auto">
            <ExtendedValidationTab data={extValData} baselineData={individualData} />
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
```

Note: extended tabs retain their old 1400px canvas since they haven't been redesigned yet.

- [ ] **Step 3: Build and run dev server**

```bash
npm run build && npm run dev
```
Expected build: success. Open the page in a browser, Aggregate tab should now render with: research question → data-source toggle → hero verdict → concept agreement table → recommendation → collapsible diagnostic → deep insights. Stop the dev server when satisfied.

- [ ] **Step 4: Commit**

```bash
git add src/App.tsx src/components/aggregate/AggregateTab.tsx
git commit -m "validation-dashboard: wire new AggregateTab into App"
```

---

## Phase 4 — Individual tab

### Task 18: Restyle ParticipantConceptSelector to chip form

**Files:**
- Modify: `src/components/individual/ParticipantConceptSelector.tsx` (entire file replacement)

- [ ] **Step 1: Inspect current file**

```bash
cat src/components/individual/ParticipantConceptSelector.tsx
```
Note: it reads `useValidationStore` to get/set `selectedParticipant` and `selectedConcept` (-1 means "all"). It receives `data: IndividualValidationData` with `pairs[]` and each pair's `concepts[]`.

- [ ] **Step 2: Replace file contents**

```tsx
import { useValidationStore } from '../../store/useValidationStore';
import type { IndividualValidationData } from '../../types/individual';

interface Props {
  data: IndividualValidationData;
}

function Chip({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`px-2.5 py-1 rounded-md text-[11px] font-medium border transition-colors cursor-pointer ${
        active
          ? 'bg-darpan-lime/10 text-darpan-lime border-darpan-lime/20'
          : 'bg-white/[0.02] text-white/40 border-darpan-border hover:text-white/70 hover:border-darpan-border-active'
      }`}
    >
      {children}
    </button>
  );
}

export function ParticipantConceptSelector({ data }: Props) {
  const { selectedParticipant, selectedConcept, setParticipant, setConcept } = useValidationStore();
  const participants = data.pairs.map((p) => p.participant_id);
  const firstPair = data.pairs[0];
  const conceptNames = firstPair ? firstPair.concepts.map((c) => c.concept_name) : [];

  return (
    <div className="bg-darpan-surface border border-darpan-border rounded-xl px-5 py-4 space-y-3">
      <div>
        <p className="text-xs font-medium text-white/30 uppercase tracking-wider mb-2">Participant</p>
        <div className="flex flex-wrap gap-1.5">
          <Chip
            active={selectedParticipant === 'all'}
            onClick={() => setParticipant('all')}
          >
            All
          </Chip>
          {participants.map((pid) => (
            <Chip
              key={pid}
              active={selectedParticipant === pid}
              onClick={() => setParticipant(pid)}
            >
              {pid}
            </Chip>
          ))}
        </div>
      </div>

      <div>
        <p className="text-xs font-medium text-white/30 uppercase tracking-wider mb-2">Concept</p>
        <div className="flex flex-wrap gap-1.5">
          <Chip active={selectedConcept === -1} onClick={() => setConcept(-1)}>
            All Concepts
          </Chip>
          {conceptNames.map((name, idx) => (
            <Chip
              key={name}
              active={selectedConcept === idx}
              onClick={() => setConcept(idx)}
            >
              {name}
            </Chip>
          ))}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Verify the store exposes the expected setters**

```bash
grep -n 'setParticipant\|setConcept\|selectedParticipant\|selectedConcept' src/store/useValidationStore.ts
```
If the store currently uses different setter names (e.g. `setSelectedParticipant`), adjust the new component to match — do NOT rename the store. Leave a note in the commit if you had to.

- [ ] **Step 4: Build**

```bash
npm run build
```

- [ ] **Step 5: Commit**

```bash
git add src/components/individual/ParticipantConceptSelector.tsx
git commit -m "validation-dashboard: chip-form selector"
```

---

### Task 19: Create HeroFidelityCard

**Files:**
- Create: `src/components/individual/HeroFidelityCard.tsx`

- [ ] **Step 1: Write the component**

```tsx
import { motion } from 'framer-motion';
import { CheckCircle2, AlertTriangle, XCircle } from 'lucide-react';
import {
  individualHeadline,
  individualSupporting,
  type QualityTier,
} from '../../lib/verdict-utils';
import type { ConceptValidation } from '../../types/individual';

const TIER_CONFIG: Record<QualityTier, { color: string; Icon: typeof CheckCircle2 }> = {
  Good:       { color: '#00FF88', Icon: CheckCircle2 },
  Acceptable: { color: '#FFB800', Icon: AlertTriangle },
  Poor:       { color: '#FF4444', Icon: XCircle },
};

const TIER_ORDER: QualityTier[] = ['Good', 'Acceptable', 'Poor'];

function worstTier(q: { mae: QualityTier; accuracy: QualityTier; exact: QualityTier }): QualityTier {
  const idx = Math.max(
    TIER_ORDER.indexOf(q.mae),
    TIER_ORDER.indexOf(q.accuracy),
    TIER_ORDER.indexOf(q.exact),
  );
  return TIER_ORDER[idx];
}

interface Props {
  participantId: string;
  conceptName: string | null; // null when "All Concepts"
  concept: ConceptValidation;
}

export function HeroFidelityCard({ participantId, conceptName, concept }: Props) {
  const tier = worstTier(concept.quality);
  const cfg = TIER_CONFIG[tier];

  const perMetric = concept.per_metric ?? [];
  const withinOne = perMetric.filter((m) => Math.abs(m.diff) <= 1).length;
  const biggest = perMetric.length
    ? [...perMetric].sort((a, b) => Math.abs(b.diff) - Math.abs(a.diff))[0]
    : null;
  const supporting = individualSupporting({
    withinOneCount: withinOne,
    totalMetrics: perMetric.length,
    largestDeviation: biggest ? { metric: biggest.metric, real: biggest.real, twin: biggest.twin } : null,
  });

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.05 }}
      className="bg-darpan-surface border border-darpan-border rounded-xl overflow-hidden"
      style={{
        borderLeftWidth: 3,
        borderLeftColor: cfg.color,
        boxShadow: `0 0 20px ${cfg.color}10`,
      }}
    >
      <div className="flex items-start justify-between gap-4 p-5">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <cfg.Icon className="w-4 h-4" style={{ color: cfg.color }} />
            <span
              className="text-xs font-semibold uppercase tracking-wider"
              style={{ color: cfg.color }}
            >
              {tier} fidelity
            </span>
          </div>
          <h2 className="text-xl font-bold text-white mb-2">
            {individualHeadline(tier, participantId, conceptName)}
          </h2>
          <p className="text-sm text-white/60 leading-relaxed">{supporting}</p>
        </div>

        <div className="flex flex-col gap-2 shrink-0">
          <div className="bg-white/[0.03] border border-darpan-border rounded-lg px-3 py-2 text-right">
            <div className="text-[10px] text-white/30 uppercase tracking-wider">MAE</div>
            <div className="font-mono text-base text-white tabular-nums">
              {concept.mae !== null ? concept.mae.toFixed(2) : '—'}
            </div>
          </div>
          <div className="bg-white/[0.03] border border-darpan-border rounded-lg px-3 py-2 text-right">
            <div className="text-[10px] text-white/30 uppercase tracking-wider">±1 acc</div>
            <div className="font-mono text-base text-white tabular-nums">
              {concept.plus_minus_1_accuracy !== null
                ? `${concept.plus_minus_1_accuracy.toFixed(1)}%`
                : '—'}
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
```

- [ ] **Step 2: Build**

```bash
npm run build
```

- [ ] **Step 3: Commit**

```bash
git add src/components/individual/HeroFidelityCard.tsx
git commit -m "validation-dashboard: add HeroFidelityCard"
```

---

### Task 20: Restyle AccuracyCard (shrink)

**Files:**
- Modify: `src/components/individual/AccuracyCard.tsx`

- [ ] **Step 1: Read current file to preserve logic**

```bash
cat src/components/individual/AccuracyCard.tsx
```
Identify the metric-type to label/target/value mapping; keep that logic.

- [ ] **Step 2: Update card chrome and type scale**

In-place edits (do NOT change prop signature):
- Outer container → `bg-darpan-surface border border-darpan-border rounded-xl p-4`
- Value element → `text-lg font-mono tabular-nums` (was likely `text-3xl` or larger)
- Label → `text-xs text-white/40 uppercase tracking-wider`
- Quality indicator dot stays; color maps to `#00FF88`/`#FFB800`/`#FF4444` as before.
- Target line → `text-[10px] text-white/25`

- [ ] **Step 3: Build**

```bash
npm run build
```

- [ ] **Step 4: Commit**

```bash
git add src/components/individual/AccuracyCard.tsx
git commit -m "validation-dashboard: shrink AccuracyCard to support scale"
```

---

### Task 21: Restyle RadarChartOverlay and DeviationBarChart

**Files:**
- Modify: `src/components/individual/RadarChartOverlay.tsx`
- Modify: `src/components/individual/DeviationBarChart.tsx`

- [ ] **Step 1: Restyle RadarChartOverlay**

Adjustments only:
- Outer wrapper → `bg-darpan-surface border border-darpan-border rounded-xl p-4`
- Recharts `PolarGrid` stroke → `#2A2A2A`
- Recharts `PolarAngleAxis` tick fill → `#A0A0A0`, fontSize 10
- Real series: fill `rgba(200,255,0,0.15)`, stroke `#C8FF00`
- Twin series: fill `rgba(0,212,255,0.15)`, stroke `#00D4FF`
- Tooltip `contentStyle` → `{ backgroundColor: '#111111', border: '1px solid #2A2A2A', borderRadius: 8, fontSize: 11, fontFamily: 'JetBrains Mono', color: '#FFFFFF' }`

Remove any box-shadow `glow` inline styles.

- [ ] **Step 2: Restyle DeviationBarChart**

Adjustments only:
- Outer wrapper → `bg-darpan-surface border border-darpan-border rounded-xl p-4`
- Grid stroke → `#2A2A2A`
- Axis ticks → `{ fill: '#A0A0A0', fontSize: 10 }`
- Bars: positive diff → `#00D4FF`, negative → `#C8FF00`, reduced opacity (0.4) when `|diff|<=1`
- Same tooltip style as radar

- [ ] **Step 3: Build**

```bash
npm run build
```

- [ ] **Step 4: Commit**

```bash
git add src/components/individual/RadarChartOverlay.tsx src/components/individual/DeviationBarChart.tsx
git commit -m "validation-dashboard: restyle radar + deviation charts"
```

---

### Task 22: Restyle AggregateMatrix (make cells clickable) and AggregateSummaryCards

**Files:**
- Modify: `src/components/individual/AggregateMatrix.tsx`
- Modify: `src/components/individual/AggregateSummaryCards.tsx`

- [ ] **Step 1: AggregateMatrix — restyle and wire click handler**

- Outer wrapper → `bg-darpan-surface border border-darpan-border rounded-xl p-4`
- Section title above the grid → `text-sm font-semibold text-white mb-3` with subtitle `text-xs text-white/35`
- Each cell becomes a `<button type="button">` with:
  - `className="py-2 text-xs font-mono tabular-nums rounded-sm hover:ring-1 hover:ring-darpan-lime/40 transition"`
  - `onClick={() => { useValidationStore.getState().setParticipant(pid); useValidationStore.getState().setConcept(conceptIdx); }}`
- Background color tied to MAE tier: Good `rgba(0,255,136,0.15)`, Acceptable `rgba(255,184,0,0.15)`, Poor `rgba(255,68,68,0.15)`.
- Legend strip below: `<div className="mt-3 flex items-center gap-4 text-[10px] text-white/30">` with three coloured swatches.

- [ ] **Step 2: AggregateSummaryCards — restyle**

- Three-card grid → `grid grid-cols-3 gap-3`.
- Each card → `bg-darpan-surface border border-darpan-border rounded-xl px-4 py-3`.
- Label → `text-xs text-white/40 uppercase tracking-wider`.
- Value → `text-lg font-mono tabular-nums text-white`.

- [ ] **Step 3: Build**

```bash
npm run build
```

- [ ] **Step 4: Commit**

```bash
git add src/components/individual/AggregateMatrix.tsx src/components/individual/AggregateSummaryCards.tsx
git commit -m "validation-dashboard: restyle matrix + summary cards"
```

---

### Task 23: Rewrite IndividualValidationTab around the hero card

**Files:**
- Modify: `src/components/individual/IndividualValidationTab.tsx`

- [ ] **Step 1: Replace file contents**

```tsx
import { useMemo } from 'react';
import { motion } from 'framer-motion';
import { useValidationStore } from '../../store/useValidationStore';
import { ParticipantConceptSelector } from './ParticipantConceptSelector';
import { HeroFidelityCard } from './HeroFidelityCard';
import { AccuracyCard } from './AccuracyCard';
import { RadarChartOverlay } from './RadarChartOverlay';
import { DeviationBarChart } from './DeviationBarChart';
import { AggregateMatrix } from './AggregateMatrix';
import { AggregateSummaryCards } from './AggregateSummaryCards';
import { qualityTier } from '../../lib/validation-utils';
import type {
  IndividualValidationData,
  ConceptValidation,
  PerMetricEntry,
} from '../../types/individual';

interface Props {
  data: IndividualValidationData;
}

function aggregateConcepts(concepts: ConceptValidation[]): ConceptValidation | null {
  const valid = concepts.filter((c) => c.mae !== null);
  if (valid.length === 0) return null;

  const mae = valid.reduce((s, c) => s + (c.mae ?? 0), 0) / valid.length;
  const acc = valid.reduce((s, c) => s + (c.plus_minus_1_accuracy ?? 0), 0) / valid.length;
  const exact = valid.reduce((s, c) => s + (c.exact_match_rate ?? 0), 0) / valid.length;

  const allKeys = new Set<string>();
  valid.forEach((c) => {
    Object.keys(c.real_metrics).forEach((k) => allKeys.add(k));
    Object.keys(c.twin_metrics).forEach((k) => allKeys.add(k));
  });

  const realMetrics: Record<string, number> = {};
  const twinMetrics: Record<string, number> = {};
  const perMetric: PerMetricEntry[] = [];
  for (const key of allKeys) {
    const realVals = valid.map((c) => c.real_metrics[key]).filter((v) => v !== undefined);
    const twinVals = valid.map((c) => c.twin_metrics[key]).filter((v) => v !== undefined);
    if (realVals.length > 0 && twinVals.length > 0) {
      const rAvg = Math.round((realVals.reduce((a, b) => a + b, 0) / realVals.length) * 10) / 10;
      const tAvg = Math.round((twinVals.reduce((a, b) => a + b, 0) / twinVals.length) * 10) / 10;
      realMetrics[key] = rAvg;
      twinMetrics[key] = tAvg;
      perMetric.push({ metric: key, real: rAvg, twin: tAvg, diff: Math.round((tAvg - rAvg) * 10) / 10 });
    }
  }

  return {
    concept_idx: -1,
    concept_name: 'All Concepts',
    real_metrics: realMetrics,
    twin_metrics: twinMetrics,
    mae: Math.round(mae * 100) / 100,
    plus_minus_1_accuracy: Math.round(acc * 10) / 10,
    exact_match_rate: Math.round(exact * 10) / 10,
    per_metric: perMetric,
    quality: {
      mae: qualityTier(mae, 'mae') as 'Good' | 'Acceptable' | 'Poor',
      accuracy: qualityTier(acc, 'accuracy') as 'Good' | 'Acceptable' | 'Poor',
      exact: qualityTier(exact, 'exact') as 'Good' | 'Acceptable' | 'Poor',
    },
    n_metrics: perMetric.length,
  };
}

export function IndividualValidationTab({ data }: Props) {
  const { selectedParticipant, selectedConcept } = useValidationStore();
  const pair = data.pairs.find((p) => p.participant_id === selectedParticipant);

  const concept = useMemo(() => {
    if (!pair) return null;
    if (selectedConcept === -1) return aggregateConcepts(pair.concepts);
    return pair.concepts[selectedConcept] ?? null;
  }, [pair, selectedConcept]);

  const conceptNameForHero =
    selectedConcept === -1 ? null : concept?.concept_name ?? null;

  return (
    <div className="max-w-5xl mx-auto w-full px-4 sm:px-6 py-6 sm:py-8 space-y-6">
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
        <ParticipantConceptSelector data={data} />
      </motion.div>

      {pair && concept ? (
        <>
          <HeroFidelityCard
            participantId={pair.participant_id}
            conceptName={conceptNameForHero}
            concept={concept}
          />

          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="grid grid-cols-3 gap-3"
          >
            <AccuracyCard metricType="mae" value={concept.mae} quality={concept.quality.mae} />
            <AccuracyCard
              metricType="accuracy"
              value={concept.plus_minus_1_accuracy}
              quality={concept.quality.accuracy}
            />
            <AccuracyCard
              metricType="exact"
              value={concept.exact_match_rate}
              quality={concept.quality.exact}
            />
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
            className="grid grid-cols-2 gap-3"
          >
            <RadarChartOverlay concept={concept} />
            <DeviationBarChart perMetric={concept.per_metric} />
          </motion.div>
        </>
      ) : (
        <div className="bg-darpan-surface border border-darpan-border rounded-xl p-8 text-center text-white/30 text-sm">
          No data available for this selection.
        </div>
      )}

      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="space-y-3"
      >
        <div>
          <h3 className="text-sm font-semibold text-white">Across all participants</h3>
          <p className="text-xs text-white/35 mt-0.5">17 × 5 fidelity matrix — click a cell to jump.</p>
        </div>
        <AggregateSummaryCards data={data} />
        <AggregateMatrix data={data} />
      </motion.div>
    </div>
  );
}
```

- [ ] **Step 2: Build and run dev server**

```bash
npm run build && npm run dev
```
Open the Individual tab and confirm: chip selector → hero fidelity card → three accuracy cards → radar + deviation → summary + matrix. Stop the dev server.

- [ ] **Step 3: Commit**

```bash
git add src/components/individual/IndividualValidationTab.tsx
git commit -m "validation-dashboard: rewire IndividualValidationTab around hero card"
```

---

## Phase 5 — Header, shared components, cleanup

### Task 24: Restyle DashboardHeader (breadcrumb + quiet tabs)

**Files:**
- Modify: `src/components/layout/DashboardHeader.tsx`

- [ ] **Step 1: Replace file contents**

```tsx
import type { DashboardData, DashboardTab } from '../../types';

interface Props {
  data: DashboardData;
  extData?: DashboardData;
  activeTab: DashboardTab;
  onTabChange: (tab: DashboardTab) => void;
}

const TABS: { value: DashboardTab; label: string }[] = [
  { value: 'aggregate',           label: 'Aggregate' },
  { value: 'individual',          label: 'Individual' },
  { value: 'extended-aggregate',  label: 'Extended Aggregate' },
  { value: 'extended-validation', label: 'Extended Validation' },
];

export function DashboardHeader({ data, extData, activeTab, onTabChange }: Props) {
  const isExtended = activeTab === 'extended-aggregate' || activeTab === 'extended-validation';
  const displayData = isExtended && extData ? extData : data;

  return (
    <header className="sticky top-0 z-40 h-12 flex items-center justify-between px-6 bg-darpan-bg/80 backdrop-blur-md border-b border-darpan-border">
      <div className="flex items-center gap-2 text-sm">
        <span className="text-white/40">Studies</span>
        <span className="text-white/20">/</span>
        <span className="text-white/40 truncate max-w-[280px]">Dove Body Wash Concept Test</span>
        <span className="text-white/20">/</span>
        <span className="text-white/60 font-medium">Validation</span>
      </div>

      <div className="flex items-center gap-3">
        <div className="flex bg-darpan-surface rounded-lg p-0.5 border border-darpan-border">
          {TABS.map(({ value, label }) => (
            <button
              key={value}
              type="button"
              onClick={() => onTabChange(value)}
              className={`px-2.5 py-1 text-[11px] font-medium rounded-md transition-colors cursor-pointer border ${
                activeTab === value
                  ? 'bg-darpan-lime/10 text-darpan-lime border-darpan-lime/20'
                  : 'text-white/40 border-transparent hover:text-white/70'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-1.5">
          <span className="px-2 py-0.5 text-[10px] font-mono bg-white/[0.03] text-white/50 rounded border border-darpan-border">
            n={displayData.metadata.real_n} real
          </span>
          <span className="px-2 py-0.5 text-[10px] font-mono bg-white/[0.03] text-white/50 rounded border border-darpan-border">
            n={displayData.metadata.twin_n} twin{isExtended ? ' (5×17)' : ''}
          </span>
          <span className="px-2 py-0.5 text-[10px] font-mono bg-white/[0.03] text-white/50 rounded border border-darpan-border">
            {displayData.metadata.concepts_tested} Concepts
          </span>
        </div>
      </div>
    </header>
  );
}
```

- [ ] **Step 2: Build**

```bash
npm run build
```

- [ ] **Step 3: Commit**

```bash
git add src/components/layout/DashboardHeader.tsx
git commit -m "validation-dashboard: breadcrumb-style header + quiet tabs"
```

---

### Task 25: Restyle shared components (DataSourceToggle, ConceptPill, MetricTooltip)

**Files:**
- Modify: `src/components/shared/DataSourceToggle.tsx`
- Modify: `src/components/shared/ConceptPill.tsx`
- Modify: `src/components/shared/MetricTooltip.tsx`

- [ ] **Step 1: DataSourceToggle — segmented control treatment**

- Outer: `flex bg-darpan-surface rounded-lg p-0.5 border border-darpan-border`
- Each option: same tab treatment as header (`px-2.5 py-1 text-[11px] font-medium rounded-md cursor-pointer`, active `bg-darpan-lime/10 text-darpan-lime border border-darpan-lime/20`, inactive `text-white/40 border border-transparent hover:text-white/70`)
- Preserve all existing store wiring.

- [ ] **Step 2: ConceptPill — soften chrome**

- Remove any glow shadows.
- Outer: `inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[11px] bg-white/[0.03] border border-darpan-border`.
- Label colour stays driven by `CONCEPT_COLORS[name]` — pass as inline style.

- [ ] **Step 3: MetricTooltip — match tooltip visual**

- Outer: `bg-darpan-elevated border border-darpan-border rounded-lg shadow-lg text-xs p-3`.
- Title: `text-white font-medium mb-1`.
- Body: `text-white/60 leading-relaxed`.
- Monospace numbers retained.

- [ ] **Step 4: Build**

```bash
npm run build
```

- [ ] **Step 5: Commit**

```bash
git add src/components/shared
git commit -m "validation-dashboard: restyle shared components"
```

---

### Task 26: Restyle SectionRow

**Files:**
- Modify: `src/components/layout/SectionRow.tsx`

The new Aggregate and Individual tabs don't use `SectionRow` (they compose directly), but the Extended tabs still do. Keep the component but align its chrome.

- [ ] **Step 1: Update chrome**

- Outer wrapper: `py-6` (vertical rhythm only — no border, no bg).
- Title: `text-sm font-semibold text-white`.
- Subtitle: `text-xs text-white/35 mt-0.5`.
- Remove any pulse-dot / accent decoration from the title row.

- [ ] **Step 2: Build**

```bash
npm run build
```

- [ ] **Step 3: Commit**

```bash
git add src/components/layout/SectionRow.tsx
git commit -m "validation-dashboard: align SectionRow chrome"
```

---

### Task 27: Final cleanup — delete retired row directories

**Files:**
- Delete: `src/components/row1-winners/`
- Delete: `src/components/row2-ranking/`
- Delete: `src/components/row3-heatmap/`
- Delete: `src/components/row4-insights/`

- [ ] **Step 1: Confirm nothing imports the old dirs**

```bash
grep -rE "from '\.\./row[0-9]-|from '\./row[0-9]-|components/row[0-9]-" src --include="*.ts" --include="*.tsx" || echo "clean"
```
Expected: `clean`. If anything is still referenced, fix it before deleting.

- [ ] **Step 2: Delete the directories**

```bash
rm -rf src/components/row1-winners src/components/row2-ranking src/components/row3-heatmap src/components/row4-insights
```

- [ ] **Step 3: Build**

```bash
npm run build
```
Expected: success.

- [ ] **Step 4: Run full test suite**

```bash
npm test
```
Expected: 20 passed (verdict-utils tests).

- [ ] **Step 5: Run dev server and walk through all four tabs**

```bash
npm run dev
```
Walk through:
1. **Aggregate** — verify research question card, data-source toggle, hero verdict (right color + right headline), concept agreement table sorts by Real composite, recommendation shows #1 highlighted, Diagnostic details expands to show both heatmap and ranking chart, three deep-insights cards render.
2. **Individual** — select different participants and concepts via chips; hero card updates headline and metric chips correctly; switching to "All Concepts" shows the aggregate variant headline; click a cell in the validation matrix, selector jumps to that pair.
3. **Extended Aggregate** — still renders (may look older but shouldn't be broken).
4. **Extended Validation** — still renders.

Stop the dev server when satisfied.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "validation-dashboard: remove retired row directories"
```

---

## Self-review summary

**Spec coverage:** Every section of the spec (§4 architecture, §5 visual language, §6 Aggregate tab, §7 Individual tab, §8 computed fields, §9 component migration, §10 success criteria) is implemented by at least one task:
- §4.1 app location → no-op (working directory)
- §4.2 deps → Task 1
- §4.3 file changes → Tasks 9–17 (aggregate), 18–23 (individual), 24 (header), 25–27 (cleanup)
- §4.4 fonts → Task 2
- §5 tokens and chrome → Tasks 3–4
- §6.3 research question card → Task 9
- §6.4 data-source toggle → Task 17 wiring + Task 25 restyle
- §6.5 hero verdict → Task 10
- §6.6 concept agreement table → Task 11
- §6.7 recommendation → Task 12
- §6.8 diagnostic → Tasks 13, 14, 15
- §6.9 deep insights → Task 16
- §7 individual tab → Tasks 18–23
- §8 computed fields → Tasks 6, 7, 8
- §9 migration plan → Task 27 deletes, Task 16 restyles, Task 14 moves
- §10 success criteria → Task 27 step 5 (visual walkthrough)

**Placeholder scan:** No `TBD` / `implement later` / vague steps. Every code-writing step contains full code; every command is exact with expected outputs.

**Type consistency:** `AgreementLevel` and `QualityTier` defined in Task 8; consumed by Tasks 10 and 19 with identical casing. `ScoreMap` / `TierMap` are internal to verdict-utils. Component prop names (`participantId`, `conceptName`, `concept`) match across Task 19 and Task 23.
