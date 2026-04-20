# Darpan Labs - Digital Twin Platform

A complete digital twin platform for consumer research. The platform enables creating AI-powered digital replicas of real consumers through structured interviews, then uses those twins to simulate survey responses for market research.

## Modules

This repository contains four independent modules. Each module is self-contained with its own dependencies, configuration, and run instructions.

```
darpan-labs-V2/
├── ai-interviewer/         # Module 1: AI Interview Platform (M1-M8, voice+text)
├── study-design-engine/    # Module 2: Research Study Designer
├── twin-generator/         # Module 3: Digital Twin Pipeline
└── adaptive-interviewer/   # Module 4: Adaptive AI Interviewer (laptop category, digital-twin capture)
```

---

### 1. AI Interviewer (`ai-interviewer/`)

**What:** An AI-powered interview platform that conducts structured voice/text interviews across 8 modules (M1-M8) covering identity, preferences, lifestyle, decision-making, and concept testing.

**How it works:**
- Users sign in via Google OAuth and complete interview modules
- AI interviewer asks adaptive questions, with follow-up probes based on answer quality
- Supports both text and voice input (Whisper ASR + LLM transcript correction)
- Admin dashboard for viewing transcripts and tracking progress
- Produces structured interview data that feeds into the Twin Generator

**Tech:** FastAPI (Python) + Next.js 14 (TypeScript) + PostgreSQL + Redis

**Run:** `cd ai-interviewer && docker-compose up`

**Ports:** Backend :8000, Frontend :3000

---

### 2. Study Design Engine (`study-design-engine/`)

**What:** An AI-assisted tool that converts a brand's unstructured research question into an execution-ready research study design through a 4-step human-in-the-loop workflow.

**How it works:**
1. **Step 1 - Study Brief:** AI generates a structured research brief from a free-form question
2. **Step 2 - Concept Boards:** AI creates product concept templates for testing
3. **Step 3 - Research Design:** AI recommends methodology, sample size, quotas
4. **Step 4 - Questionnaire:** AI generates a complete survey questionnaire

Each step follows: AI generates -> Human reviews -> Human edits -> Human locks.

The final questionnaire is used by the Twin Generator for simulation.

**Tech:** FastAPI (Python) + Next.js (TypeScript) + PostgreSQL

**Run:** `cd study-design-engine && docker-compose up`

**Ports:** Backend :8001, Frontend :3001

---

### 3. Twin Generator (`twin-generator/`)

**What:** A batch pipeline that creates digital twins of real consumers. Takes interview data from the AI Interviewer, generates branched synthetic profiles, builds inference layers (Vector DB + Knowledge Graph), and simulates survey responses using the questionnaire from the Study Design Engine.

**How it works:**
1. **Step 1 - Question Bank:** Expands 59 real interview questions to 350 using LLM
2. **Step 2 - Branching:** Identifies 5 uncaptured behavioral dimensions per participant, generates 3 archetype variants per dimension (243 raw combos), coherence-prunes to 100 twins per participant
3. **Step 3 - Profile Expansion:** Further prunes 100 → 20 twins per participant (coherence × diversity), then uses ICL to fill each twin's 289 unanswered questions → 353 Q&A per twin. Final deliverable: 20 × 20 = **400 twins**
4. **Step 4A - Vector DB:** Builds ChromaDB index with sentence-transformer embeddings
5. **Step 4B - Knowledge Graph:** Extracts behavioral traits into a NetworkX graph
6. **Step 5 - Survey Simulation:** Uses twins to answer research questionnaires with evidence-backed responses

**Tech:** Python scripts + LiteLLM + ChromaDB + NetworkX + sentence-transformers

**Run:** `cd twin-generator && pip install -r requirements.txt && python scripts/orchestrator.py`

---

### 4. Adaptive Interviewer (`adaptive-interviewer/`)

**What:** A 60-minute text-administered adaptive AI interview for digital-twin capture in the laptop category. Silently classifies respondents into one of three archetypes (prosumer, SMB IT buyer, consumer) and routes through archetype-specific JTBD, conjoint, brand, and tone blocks before a universal BFI-2-S personality + PVQ-10 values tail.

**How it works:**
1. **Phase 1 — Universal Preamble (10 min):** Six open items (P1-P6) capture role, device landscape, last-purchase episode, decision unit, process formality, and engagement.
2. **Phase 2 — Silent Classification:** LLM classifier emits archetype probability vector; disambiguation prompts when confidence < 0.50.
3. **Phase 3 — Variant Body (33 min):** JTBD narrative (8-9 items) + choice-based conjoint (8 sets × 3 alternatives) + brand-attribute slider lattice + tone-pair + projective close. Attribute sets and ad descriptions differ per archetype.
4. **Phase 4 — Universal Tail (15 min):** BFI-2-S (30 items) + PVQ-10 (10 items) + top-5 forced ranking on 10 aspirational adjectives + meta-feedback close.

Produces a structured per-respondent JSON object (`context`, `archetype`, `jtbd`, `conjoint` with estimated part-worths + WTP, `brand_lattice`, `personality`, `values`, `identity`, `tone_preference`, `projective`, `qa`) persisted to the `adaptive_outputs` table.

**Tech:** FastAPI (Python) + Next.js 14 (TypeScript) + PostgreSQL (shares `interview_sessions`/`interview_modules`/`interview_turns` tables with `ai-interviewer`) + LiteLLM (provider-agnostic)

**Run:** `cd adaptive-interviewer && docker-compose up`

**Ports:** Backend :8002, Frontend :3002

---

## How the Modules Connect

```
Study Design Engine                AI Interviewer              Twin Generator
┌──────────────────┐      ┌──────────────────────┐     ┌──────────────────────┐
│                  │      │                      │     │                      │
│ Research Question│      │  Real humans take     │     │ Step 1: Expand Qs    │
│       ↓          │      │  8-module interviews  │     │ Step 2: Branch twins  │
│ Study Brief      │      │  (voice or text)      │     │ Step 3: Expand profiles│
│       ↓          │      │       ↓               │     │ Step 4: Build VectorDB│
│ Concept Boards   │      │  Interview responses  │────→│         + KG          │
│       ↓          │      │  (structured Q&A)     │     │ Step 5: Simulate      │
│ Research Design  │      │                      │     │  survey responses     │
│       ↓          │      └──────────────────────┘     │       ↓               │
│ Questionnaire  ──│─────────────────────────────────→│ Answer questionnaire  │
│                  │                                    │  using digital twins  │
└──────────────────┘                                    └──────────────────────┘
                                                               ↓
                                                        Validation:
                                                        Compare twin responses
                                                        vs actual human responses
```

**Data flow:**
1. **Study Design Engine** produces a questionnaire for the research study
2. **AI Interviewer** collects real human interview responses (8 modules)
3. **Twin Generator** takes interview data, builds digital twins, and uses them to answer the questionnaire
4. Twin responses are validated against actual human survey responses

## Getting Started

Each module runs independently. See the README in each folder:

- [`ai-interviewer/README.md`](ai-interviewer/README.md)
- [`study-design-engine/README.md`](study-design-engine/README.md)
- [`twin-generator/README.md`](twin-generator/README.md)

## License

Confidential - Darpan Labs
