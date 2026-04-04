# Digital Twin MVP PRD v2.0

**Product Requirements Document**

Version 2.0 | February 2026

Status: MVP / Prototype

*Confidential*

---

## 1. Executive Summary

This PRD defines the revised MVP for a prompt-conditioned "Digital Twin" product with five modules:

1. **Voice-Based AI Interviewer** (bilingual: English, Hindi, Hinglish)
2. **Modular Interview Architecture** (mandatory + add-on modules, multi-session)
3. **ICL-Based Twin Creation** (incremental quality improvement as modules complete)
4. **Twin Chat Interface** (confidence + evidence grounding)
5. **Experiment Engine** (cohort simulation against digital twins)

The MVP uses a base LLM plus user interview data (no per-user fine-tuning) to create a behavioral/personality/preference twin. The design follows the "qualitative interview → persona conditioning → simulated responses" approach from large-scale digital twin research (Generative Agent Simulations of 1,000 People) and aligns with the Twin-2K prompt-template pattern.

### What Changed from v1.0

| Area | v1.0 | v2.0 |
|------|------|------|
| Interview input | Text-only | **Voice-first** (EN/HI/Hinglish) with text fallback |
| Interview structure | Single 12–18 min session | **Modular**: mandatory + add-on modules across sessions |
| Twin quality | Binary (ready/not) | **Incremental**: improves as modules complete |
| Experiment capability | Out of scope | **In scope (MVP+)**: cohort simulation engine |
| Language support | English only | **English, Hindi, Hinglish** (code-switching) |

### Key Design Decisions

- Voice-first interview with Whisper-based ASR + streaming TTS stack
- Modular interview: 4 mandatory modules (~12 min total) generate a usable twin; 4+ add-on modules improve fidelity
- Twin built via ICL prompt conditioning on structured + free-text interview outputs
- Twin chat returns answer + confidence + evidence snippets + uncertainty
- Experiment engine allows running scenarios against twin cohorts with individual reasoning + aggregate results
- Deterministic/low-temperature generation and JSON validation/retry loops

---

## 2. Product Vision and MVP Objective

### Product Vision

Create usable, inspectable digital twins of real users from short voice interviews, so product teams can explore likely user responses, run behavioral experiments on twin cohorts, and iterate faster than repeated live interviews.

### MVP Objective

Ship a prototype that can:

1. Interview a real user via voice (English/Hindi/Hinglish) across modular interview modules
2. Build a prompt-conditioned twin using only collected interview data (ICL, no fine-tuning)
3. Improve twin quality incrementally as the user completes additional modules
4. Let a human chat with the twin and inspect confidence/evidence
5. Run experiments on cohorts of digital twins and inspect individual + aggregate results

### MVP Success Definition

A live demo where:

- A user completes mandatory modules via voice in under 15 minutes
- System generates a twin in under 60 seconds
- Twin answers at least 10 varied follow-up questions with confidence/evidence
- User completes one add-on module and twin quality visibly improves
- An experiment runs across 5+ twins with individual reasoning and aggregate summary

---

## 3. Target Users and Primary Use Cases

### Target Users (MVP)

| User Type | Role | Why they care | MVP fit |
|-----------|------|---------------|---------|
| Product researchers / PMs | Early-stage validation | Fast hypothesis testing on likely user reactions | Strong |
| Founders | Messaging / concept testing | Quick simulation before field interviews | Strong |
| UX researchers | Pre-screening and probe design | Generate likely responses, identify uncertain areas | Medium-strong |
| Market researchers | Cohort behavior simulation | Run experiments on twin panels before live research | Strong |
| Internal demo audiences | Investors / teams | Understand digital twin + experiment capability | Strong |

### Primary Use Cases

1. **Behavioral Q&A simulation** — "How would this user react to a subscription paywall?"
2. **Preference prediction** — "Would this person prefer convenience or control in onboarding?"
3. **Cohort experiment** — "If we offer a 20% discount vs free trial, which do 50 twins prefer and why?"
4. **Persona-grounded ideation** — "What concerns would this user raise about data sharing?"
5. **Interview augmentation** — Use twin to generate likely follow-up questions before next real interview

---

## 4. Scope (In-Scope / Out-of-Scope)

### In-Scope (MVP)

**Product capabilities:**

- Voice-based adaptive AI interview (English, Hindi, Hinglish)
- Modular interview architecture with mandatory + add-on modules
- Multi-session module completion with progress persistence
- ICL-based twin generation with incremental quality improvement
- Twin chat with confidence + evidence
- Basic profile summary and coverage visualization
- Text fallback if voice fails

**MVP+ (included in build plan, last sprint):**

- Experiment engine: cohort creation, scenario execution, result inspection
- Aggregate experiment analytics

**Technical capabilities:**

- Real-time ASR (Whisper-based) with Hindi/Hinglish support
- Streaming TTS for interviewer voice output
- Turn-taking logic with silence/interruption handling
- Audio metadata storage + transcript persistence
- Versioned twin profile artifacts
- LLM abstraction layer for model swaps
- Consent + deletion workflow

### Out-of-Scope (MVP)

| Area | Out-of-scope item | Reason postponed |
|------|-------------------|------------------|
| Modeling | Per-user fine-tuning | Violates constraint, slower build |
| Data ingestion | Email/social/media auto-ingestion | Privacy complexity |
| Input modes | Video interview | Adds diarization/UX complexity |
| Memory | Longitudinal auto-updating twin | Requires continuous sync |
| Enterprise | Advanced RBAC, SSO, compliance | MVP speed focus |
| Safety | Clinical/medical/mental health inference | High-risk domain |
| Experiments | Statistical significance testing | Post-MVP validation |
| Experiments | A/B treatment assignment algorithms | Overengineering for MVP |

---

## 5. Modular Interview Architecture

This is the core structural change from v1.0. The interview is no longer a single monolithic session.

### Design Principles

1. **Mandatory modules first**: Generate a usable twin after mandatory modules are complete
2. **Add-on modules improve fidelity**: Each completed add-on module measurably improves twin quality
3. **Multi-session support**: Users can complete modules across different sessions/days
4. **Module independence**: Each module is self-contained with its own questions, scoring, and completion criteria
5. **Fatigue-aware**: Short modules (3–5 min each) reduce cognitive load

### Module Taxonomy

| Module ID | Module Name | Type | Est. Duration | Priority | Dependencies |
|-----------|-------------|------|---------------|----------|--------------|
| M1 | **Core Identity & Context** | Mandatory | 2–3 min | P0 | None |
| M2 | **Decision Logic & Risk** | Mandatory | 3–4 min | P0 | None |
| M3 | **Preferences & Values** | Mandatory | 3–4 min | P0 | None |
| M4 | **Communication & Social** | Mandatory | 2–3 min | P0 | None |
| A1 | Lifestyle & Routines | Add-on | 3–4 min | P1 | M1 |
| A2 | Spending & Financial Behavior | Add-on | 3–4 min | P1 | M2 |
| A3 | Career & Growth Aspirations | Add-on | 3–4 min | P1 | M1 |
| A4 | Work & Learning Style | Add-on | 3–4 min | P1 | M4 |
| A5 | Technology & Product Behavior | Add-on | 3–4 min | P2 | M3 |
| A6 | Health & Wellness Attitudes | Add-on (sensitive) | 3–4 min | P2 | M1, consent |

### Module Definitions

#### Mandatory Modules

**M1: Core Identity & Context** (2–3 min)

- **Goal:** Establish baseline demographic context and self-concept
- **Signal targets:** Age band, occupation type, living context, self-described personality, life stage
- **Question count:** 4–6 primary + 1–2 follow-ups
- **Question types:** Open-ended, forced-choice
- **Completion criteria:** coverage ≥ 0.70, confidence ≥ 0.65, at least 4 questions answered
- **Stopping signal:** User has provided enough context to interpret responses from other modules

**M2: Decision Logic & Risk** (3–4 min)

- **Goal:** Understand how the user makes decisions and handles uncertainty
- **Signal targets:** Speed vs deliberation, gut vs data, risk appetite, reversibility sensitivity, information needs
- **Question count:** 5–7 primary + 2–3 follow-ups
- **Question types:** Scenario-based, trade-off, forced-choice
- **Completion criteria:** coverage ≥ 0.75, confidence ≥ 0.70, at least 2 behavioral rules extracted
- **Stopping signal:** At least one conditional rule identified (e.g., "If X, then tends to Y")

**M3: Preferences & Values** (3–4 min)

- **Goal:** Capture stable priorities, product/service preferences, and value trade-offs
- **Signal targets:** Control vs convenience, price vs quality, privacy vs personalization, novelty vs familiarity
- **Question count:** 5–7 primary + 2–3 follow-ups
- **Question types:** Trade-off, Likert, scenario-based
- **Completion criteria:** coverage ≥ 0.75, confidence ≥ 0.70, at least 3 preference dimensions captured
- **Stopping signal:** Clear preference direction on at least 3 trade-off axes

**M4: Communication & Social** (2–3 min)

- **Goal:** Understand interaction style and social tendencies
- **Signal targets:** Directness, conflict style, introversion/extroversion, group size comfort, trust formation
- **Question count:** 4–6 primary + 1–2 follow-ups
- **Question types:** Open-ended, scenario-based
- **Completion criteria:** coverage ≥ 0.65, confidence ≥ 0.60, at least 3 signals captured
- **Stopping signal:** Communication style identifiable for simulated responses

#### Add-on Modules

**A1: Lifestyle & Routines** (3–4 min)

- **Goal:** Habitual behavior patterns, daily structure, fitness/wellness habits
- **Signal targets:** Morning routines, planning style, schedule consistency, travel habits, fitness goals
- **Improvement to twin:** +8–12% fidelity on lifestyle/behavioral prediction questions
- **Completion criteria:** coverage ≥ 0.70, confidence ≥ 0.65

**A2: Spending & Financial Behavior** (3–4 min)

- **Goal:** Budget priorities, purchase decision patterns, financial comfort zones
- **Signal targets:** Impulse vs planned purchases, budget consciousness, subscription tolerance, deal sensitivity
- **Improvement to twin:** +10–15% fidelity on consumer/financial preference questions
- **Completion criteria:** coverage ≥ 0.70, confidence ≥ 0.65

**A3: Career & Growth Aspirations** (3–4 min)

- **Goal:** Professional trajectory, growth mindset, industry preferences
- **Signal targets:** 5-year goals, industry preferences, skill investment priorities, job satisfaction drivers
- **Improvement to twin:** +8–12% fidelity on professional/career behavior questions
- **Completion criteria:** coverage ≥ 0.70, confidence ≥ 0.65

**A4: Work & Learning Style** (3–4 min)

- **Goal:** Collaboration patterns, feedback preferences, ambiguity handling
- **Signal targets:** Solo vs collaborative, feedback response, structured vs flexible, ambiguity tolerance
- **Improvement to twin:** +8–12% fidelity on work behavior questions
- **Completion criteria:** coverage ≥ 0.70, confidence ≥ 0.65

**A5: Technology & Product Behavior** (3–4 min)

- **Goal:** App/product usage patterns, adoption behavior, feature preferences
- **Signal targets:** Early adopter vs late majority, feature exploration depth, notification tolerance, multi-device behavior
- **Improvement to twin:** +10–15% fidelity on product-specific prediction questions
- **Completion criteria:** coverage ≥ 0.70, confidence ≥ 0.65

**A6: Health & Wellness Attitudes** (3–4 min, sensitive, requires explicit consent)

- **Goal:** Health consciousness, wellness investment, medical decision style
- **Signal targets:** Health information seeking, prevention vs treatment mindset, wellness spending
- **Improvement to twin:** +5–8% fidelity on health/wellness questions
- **Completion criteria:** coverage ≥ 0.65, confidence ≥ 0.60
- **Special:** Requires separate sensitive-topic consent

### Twin Quality Progression

| Modules Completed | Twin Quality Label | Estimated Fidelity | Usable For |
|-------------------|-------------------|-------------------|------------|
| M1–M4 (mandatory only) | **Base Twin** | ~55–65% | General behavioral Q&A, basic preference prediction |
| + 1–2 add-ons | **Enhanced Twin** | ~65–75% | Domain-specific prediction in covered add-on areas |
| + 3–4 add-ons | **Rich Twin** | ~75–85% | Broad behavioral simulation, experiment participation |
| All modules | **Full Twin** | ~80–90% | High-fidelity simulation, detailed cohort experiments |

*Fidelity estimated as agreement rate on holdout questions within covered domains.*

### Module Session Management

```
module_session_state = {
  "user_id": "uuid",
  "completed_modules": ["M1", "M2", "M3", "M4", "A1"],
  "in_progress_module": "A2",
  "in_progress_state": {
    "questions_asked": 3,
    "coverage": 0.45,
    "confidence": 0.40,
    "last_turn_id": "t_42"
  },
  "available_modules": ["A3", "A4", "A5", "A6"],
  "twin_versions": [
    {"version": 1, "modules": ["M1","M2","M3","M4"], "quality": "base"},
    {"version": 2, "modules": ["M1","M2","M3","M4","A1"], "quality": "enhanced"}
  ],
  "total_interview_time_sec": 720,
  "sessions": [
    {"session_id": "s1", "modules_covered": ["M1","M2","M3","M4"], "date": "2026-02-24"},
    {"session_id": "s2", "modules_covered": ["A1"], "date": "2026-02-25"}
  ]
}
```

### Module Completion Evaluation Prompt

```
SYSTEM:
You are evaluating whether an interview module is complete.

Given the module definition, questions asked, and answers received,
determine if the module's coverage and confidence thresholds are met.

DEVELOPER:
Module: {module_id} - {module_name}
Required signals: {signal_targets}
Completion criteria: coverage >= {coverage_threshold}, confidence >= {confidence_threshold}

Questions and answers so far:
{module_turns}

TASK:
Evaluate module completion status.

OUTPUT JSON:
{
  "module_id": "M2",
  "is_complete": true|false,
  "coverage_score": 0.0,
  "confidence_score": 0.0,
  "signals_captured": ["speed_vs_deliberation", "risk_appetite"],
  "signals_missing": ["reversibility_sensitivity"],
  "behavioral_rules_extracted": [
    {"rule": "string", "confidence": 0.0, "evidence_turn_ids": []}
  ],
  "recommendation": "COMPLETE" | "ASK_MORE" | "SKIP_OPTIONAL",
  "suggested_next_questions": []
}
```

---

## 6. Voice Pipeline Design

### Architecture Overview

The voice interviewer uses a streaming pipeline: User speaks → ASR transcribes → LLM processes → TTS generates voice response → User hears next question.

### Technology Stack (MVP)

| Component | Recommended | Alternatives | Why |
|-----------|-------------|--------------|-----|
| **ASR (Speech-to-Text)** | Whisper large-v3 via API (Groq/Deepgram) | Azure Speech, Google STT | Best Hindi/Hinglish accuracy, fast API inference |
| **TTS (Text-to-Speech)** | ElevenLabs or Azure Neural TTS | Google Cloud TTS, Coqui | Natural Hindi/English voices, low latency |
| **Streaming ASR** | Deepgram streaming API | Whisper chunked streaming | Real-time partial transcripts for responsiveness |
| **Language detection** | Whisper built-in | fastText langdetect | Whisper auto-detects language per segment |
| **Orchestration** | Custom Python (FastAPI + WebSocket) | LiveKit | Simpler for MVP, full control |
| **Audio transport** | WebSocket (browser → server) | WebRTC | Simpler for MVP; WebRTC post-MVP for quality |

### Voice Pipeline Flow

```
[User Browser/App]
    │
    ├── Mic capture (WebAudio API, 16kHz mono PCM)
    │
    ├── WebSocket stream ──────► [Voice Orchestrator Service]
    │                               │
    │                               ├── Silence detection (VAD)
    │                               ├── End-of-turn detection
    │                               │
    │                               ├── ASR (Whisper/Deepgram)
    │                               │   ├── Partial transcript (streaming)
    │                               │   └── Final transcript + language tag
    │                               │
    │                               ├── Transcript correction (LLM post-process)
    │                               │
    │                               ├── Interview Orchestrator
    │                               │   ├── Answer processing
    │                               │   ├── Module state update
    │                               │   └── Next question generation
    │                               │
    │                               ├── TTS generation (streamed)
    │                               │   └── SSML with language tags
    │                               │
    │                               └── Audio chunks ──────► [User Browser]
    │                                                         └── Playback
    │
    └── Text fallback input (optional)
```

### Turn-Taking Logic

| Scenario | Detection | System Behavior |
|----------|-----------|-----------------|
| **User finishes speaking** | VAD silence > 1.5s after speech | Finalize transcript → process → respond |
| **User pauses mid-thought** | VAD silence 0.5–1.5s | Wait; show "listening..." indicator |
| **User interrupts system** | Speech detected during TTS playback | Stop TTS immediately, start new ASR capture |
| **Extended silence (>8s)** | No speech after system question | Gentle audio prompt: "Take your time, or I can move to the next question" |
| **Extended silence (>20s)** | No speech, no interaction | "Would you like to continue, or shall we pause and come back later?" |
| **Background noise** | VAD false positives | Require minimum speech duration (>0.3s) to trigger processing |

### Bilingual/Hinglish Support

**Language handling strategy:**

1. **ASR level:** Whisper large-v3 natively handles Hindi, English, and code-switched Hinglish. Set `language=None` to enable auto-detection per utterance.

2. **Transcript normalization:** Post-ASR, run a lightweight LLM pass to:
   - Correct common Hindi ASR errors (especially for Hinglish segments)
   - Normalize Romanized Hindi (e.g., "mujhe lagta hai" → tagged as Hindi)
   - Preserve code-switching boundaries for analysis

3. **LLM processing:** All interview orchestration prompts include instruction to understand and respond to Hindi/English/Hinglish. The LLM generates responses in the language the user is predominantly using.

4. **TTS output:**
   - Detect primary language of generated response
   - Use appropriate voice model (English voice for English, Hindi voice for Hindi)
   - For Hinglish responses, use a Hindi-accented English voice (closest natural match)

**Transcript correction prompt:**

```
SYSTEM:
You are correcting an ASR transcript of a voice interview.
The speaker may use English, Hindi, or Hinglish (mixed Hindi-English).

TASK:
Fix obvious ASR errors while preserving the speaker's intent and language choice.
Do NOT translate. Do NOT change meaning. Only fix recognition errors.

Tag each segment with language: [EN], [HI], or [HG] (Hinglish).

RAW TRANSCRIPT: {raw_transcript}
ASR CONFIDENCE: {confidence_score}
CONTEXT (previous turns): {recent_context}

OUTPUT JSON:
{
  "corrected_transcript": "string",
  "language_tags": [{"start": 0, "end": 24, "lang": "EN"}, ...],
  "primary_language": "EN|HI|HG",
  "correction_applied": true|false,
  "corrections": [{"original": "...", "corrected": "...", "reason": "..."}]
}
```

### Audio Storage Design

| Data | Storage | Retention | Notes |
|------|---------|-----------|-------|
| Raw audio chunks | Object storage (S3) | 7 days (then delete) | For debugging/correction only |
| Audio metadata | Postgres | Matches user retention | Duration, sample rate, VAD events |
| ASR transcript (raw) | Postgres | Matches user retention | Before correction |
| ASR transcript (corrected) | Postgres | Matches user retention | After LLM correction |
| Language tags | Postgres (jsonb) | Matches user retention | Per-segment language labels |
| TTS audio cache | Object storage | 24h TTL | Avoid re-generating same questions |

### Fallback to Text

If voice fails (microphone denied, poor connection, ASR repeated failures):

1. System detects 3 consecutive ASR failures or user clicks "Switch to text"
2. UI transitions to text input mode (same question flow)
3. Module state is preserved; progress continues seamlessly
4. Transcript is stored as text-typed (no audio metadata)

### Voice-Specific NFRs

| Metric | Target | Notes |
|--------|--------|-------|
| ASR latency (final transcript) | p50 < 1.5s, p95 < 3s | From end-of-speech to transcript |
| TTS first audio byte | p50 < 800ms, p95 < 2s | From response ready to audio playing |
| End-to-end turn latency | p50 < 4s, p95 < 8s | User stops speaking → system starts speaking |
| ASR Word Error Rate (English) | < 8% | Standard benchmark |
| ASR WER (Hindi) | < 15% | Acceptable for MVP |
| ASR WER (Hinglish) | < 20% | Code-switching is harder |
| Transcript correction accuracy | > 90% | On flagged corrections |

---

## 7. AI Interviewer (Voice-Based, Modular)

### Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|-------------------|
| INT01 | Start voice interview session with consent and module selection | P0 | Session created with user_id/session_id, mic permissions granted |
| INT02 | Conduct interview via voice with real-time ASR | P0 | User speaks, system transcribes and processes |
| INT03 | Support English, Hindi, and Hinglish (code-switching) | P0 | ASR handles mixed language; LLM responds appropriately |
| INT04 | Ask questions via TTS voice output | P0 | Natural-sounding voice questions in appropriate language |
| INT05 | Track per-module coverage and confidence | P0 | Module-level scores visible in backend state |
| INT06 | Support module-by-module progression | P0 | User completes M1, then M2, etc. with state persisted |
| INT07 | Support multi-session resumption | P0 | User can close and resume from last incomplete module |
| INT08 | Detect turn-taking (silence, interruptions, pauses) | P0 | Turn-taking logic handles all scenarios in table above |
| INT09 | Generate adaptive follow-ups within modules | P0 | Follow-ups linked to parent question and rationale |
| INT10 | Evaluate module completion and transition | P0 | Module marked complete when criteria met; auto-advance to next |
| INT11 | Let user skip modules or questions | P0 | Skips recorded with reason code |
| INT12 | Periodic confirmation within module | P1 | "I heard that you..." recap at module end |
| INT13 | Detect fatigue and offer pause/resume | P1 | "Want to take a break?" if fatigue signals detected |
| INT14 | Transcript correction for ASR errors | P1 | LLM post-processing corrects errors before storage |
| INT15 | Fallback to text input | P1 | Seamless switch if voice fails |
| INT16 | Display real-time transcript to user | P1 | User sees what system heard; can correct |

### Voice Interviewer Turn Generation Prompt

```
SYSTEM:
You are a friendly, adaptive voice interviewer building a digital twin
of the person you are speaking with.

You are currently conducting module: {module_name}
Module goal: {module_goal}
Target signals: {signal_targets}

RULES:
1. Ask ONE question per turn. Keep it conversational and natural for voice.
2. Questions should be short (under 30 words for voice clarity).
3. Match the user's language. If they speak Hindi, respond in Hindi.
   If Hinglish, use natural Hinglish.
4. Avoid jargon. This is a conversation, not a survey.
5. Ask follow-ups only when the answer is vague or ambiguous.
6. Do not repeat questions already answered in this or prior modules.
7. Respect sensitivity settings: {sensitivity_settings}

DEVELOPER:
Module: {module_id} - {module_name}
Module status: {questions_asked}/{max_questions} questions, coverage={coverage}, confidence={confidence}
Signals captured so far: {captured_signals}
Signals still needed: {missing_signals}

Recent turns (voice transcript):
{recent_turns}

Cross-module context (from completed modules):
{cross_module_summary}

TASK:
Generate the next interviewer turn for this module.

OUTPUT JSON:
{
  "action": "ASK_QUESTION" | "ASK_FOLLOWUP" | "MODULE_COMPLETE" | "OFFER_BREAK",
  "question_text": "string (optimized for voice: short, clear, conversational)",
  "question_text_hindi": "string or null (Hindi version if user speaks Hindi)",
  "language": "EN" | "HI" | "HG",
  "question_type": "open_text | forced_choice | scenario | tradeoff | clarification",
  "target_signal": "string",
  "rationale_short": "string",
  "module_summary": "string or null (if MODULE_COMPLETE, summarize what was learned)"
}
```

### Question Selection Heuristic (Module-Level)

At each turn within a module, candidate questions are scored:

```
NextQuestionScore = 0.35 × SignalGap
                  + 0.25 × ConfidenceGap
                  + 0.20 × ExpectedInfoGain
                  + 0.10 × CrossModuleSynergy
                  - 0.10 × FatiguePenalty
```

Where:

- **SignalGap** = proportion of target signals not yet captured for this module
- **ConfidenceGap** = 1 - module confidence_score
- **ExpectedInfoGain** = estimated from question metadata + current ambiguity
- **CrossModuleSynergy** = bonus if question also fills gaps from other modules
- **FatiguePenalty** = increases with session time, consecutive long answers, skips

---

## 8. Twin Creation (ICL-Based, Incremental)

### Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|-------------------|
| TWIN01 | Build structured profile from completed modules | P0 | JSON profile generated per module set |
| TWIN02 | Generate twin after mandatory modules (M1–M4) complete | P0 | Base twin created automatically |
| TWIN03 | Regenerate/upgrade twin when add-on modules complete | P0 | New version with improved coverage |
| TWIN04 | Build persona summary text under token budget | P0 | Summary ≤ 2500 tokens |
| TWIN05 | Build evidence index for retrieval | P0 | Snippet IDs with embeddings available |
| TWIN06 | Mark low-coverage domains from incomplete modules | P0 | Uncertainty fields populated |
| TWIN07 | No per-user fine-tuning | P0 | Architecture enforces ICL-only |
| TWIN08 | Validate profile JSON and retry on schema failures | P0 | Bounded retry + error logging |
| TWIN09 | Track twin quality score based on modules completed | P0 | Quality label and score visible |

### Incremental Twin Generation Flow

```
User completes M1-M4 (mandatory)
    │
    ├── System generates Twin v1 (Base Twin, quality ~60%)
    │   └── Profile covers: identity, decisions, preferences, communication
    │
User completes A1 (Lifestyle)
    │
    ├── System generates Twin v2 (Enhanced Twin, quality ~68%)
    │   └── Profile adds: routines, habits, fitness
    │
User completes A2 (Spending)
    │
    ├── System generates Twin v3 (Enhanced Twin, quality ~75%)
    │   └── Profile adds: financial behavior, purchase patterns
    │
    ... and so on
```

Each twin regeneration:

1. Takes all completed module transcripts + answers
2. Runs profile extraction prompt with full context
3. Generates new persona summary incorporating all data
4. Re-indexes evidence snippets
5. Updates coverage/confidence map
6. Creates new immutable version

### Twin Artifact Definition (MVP)

A twin is a versioned bundle:

- `structured_profile_json` — core twin representation
- `persona_summary_text` — compact ICL prompt payload (≤ 2500 tokens)
- `persona_full_text` — full transcript-derived narrative (optional, recommended)
- `evidence_snippet_index` — chunked answers + embeddings
- `coverage_confidence_map` — per-module and per-domain scores
- `completed_modules` — list of modules included in this version
- `quality_label` — base / enhanced / rich / full
- `quality_score` — 0.0 to 1.0
- `prompt_template_version`
- `model_config`

---

## 9. Experiment Engine (Twin Cohort Simulation)

**Scope: MVP+ (Sprint 5–6). Core infrastructure in MVP, full UX in final sprint.**

### Overview

The experiment engine allows users to run scenarios/questions against cohorts of digital twins and inspect individual + aggregate results.

### Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|-------------------|
| EXP01 | Create a cohort from available twins | P0 (MVP+) | Cohort created with selected twin IDs |
| EXP02 | Define an experiment (scenario/question) | P0 (MVP+) | Experiment stored with prompt + parameters |
| EXP03 | Run experiment across cohort | P0 (MVP+) | All twins produce responses |
| EXP04 | Return individual twin responses with reasoning | P0 (MVP+) | Per-twin answer + confidence + evidence |
| EXP05 | Return aggregate results | P0 (MVP+) | Distribution, patterns, majority |
| EXP06 | Inspect individual twin response | P0 (MVP+) | Drill down into any twin's reasoning |
| EXP07 | Show confidence indicators per result | P1 (MVP+) | Per-twin and aggregate confidence |
| EXP08 | Support multiple question formats | P1 (MVP+) | Open-ended, forced-choice, Likert, scenario |

### Cohort Management (MVP)

**How cohorts are created:**

In MVP, cohorts are manually assembled:

1. User selects from available twins in the system (own twins + shared/demo twins)
2. User creates a named cohort with N twins (MVP limit: 50 twins per cohort)
3. Cohort metadata stores twin IDs + quality labels

**Cohort selection filters (MVP):**

- Twin quality level (base / enhanced / rich / full)
- Modules completed (e.g., "only twins with A2 Spending module")
- Manual selection by name/ID

**Post-MVP:** Auto-generated cohorts by demographic segments, behavioral clusters.

### Experiment Definition

An experiment consists of:

```json
{
  "experiment_id": "exp_001",
  "name": "Subscription vs One-time Purchase Preference",
  "cohort_id": "cohort_alpha",
  "created_by": "user_xyz",
  "scenario": {
    "type": "forced_choice",
    "prompt": "You are considering a productivity app. Option A: $9.99/month subscription with all features. Option B: $79.99 one-time purchase with limited updates. Which would you choose and why?",
    "options": ["Option A: Subscription", "Option B: One-time purchase"],
    "context": "The app is something you would use daily for work."
  },
  "settings": {
    "require_reasoning": true,
    "max_response_tokens": 300,
    "temperature": 0.2
  },
  "status": "pending"
}
```

**Supported experiment types (MVP):**

| Type | Description | Output |
|------|-------------|--------|
| forced_choice | Pick A or B (or C) with reasoning | Choice + reasoning text |
| likert_scale | Rate 1–5 on a statement | Numeric score + reasoning |
| open_scenario | Describe what you would do in situation X | Free-text response |
| preference_rank | Rank 3–5 options | Ordered list + reasoning |

### Experiment Execution Flow

```
1. User creates experiment with scenario + cohort
2. System queues experiment job
3. For each twin in cohort:
   a. Load twin profile + evidence
   b. Compose twin response prompt with experiment scenario
   c. Generate response (ICL, low temperature)
   d. Validate response schema
   e. Store individual result
4. After all twins respond:
   a. Compute aggregate statistics
   b. Identify patterns/clusters
   c. Compute aggregate confidence
5. Return results to user
```

### Experiment Result Schema

```json
{
  "experiment_id": "exp_001",
  "name": "Subscription vs One-time Purchase Preference",
  "status": "completed",
  "cohort_size": 12,
  "completed_responses": 12,
  "execution_time_sec": 34,

  "aggregate_results": {
    "choice_distribution": {
      "Option A: Subscription": {"count": 5, "percentage": 41.7},
      "Option B: One-time purchase": {"count": 7, "percentage": 58.3}
    },
    "aggregate_confidence": 0.72,
    "confidence_distribution": {
      "high": 4,
      "medium": 6,
      "low": 2
    },
    "key_patterns": [
      {
        "pattern": "Twins with high risk tolerance preferred subscription",
        "supporting_twins": 4,
        "confidence": 0.78
      },
      {
        "pattern": "Twins with strong budget-consciousness preferred one-time purchase",
        "supporting_twins": 5,
        "confidence": 0.81
      }
    ],
    "dominant_reasoning_themes": [
      "Long-term cost calculation (mentioned by 8/12 twins)",
      "Fear of recurring charges (mentioned by 5/12 twins)",
      "Preference for flexibility (mentioned by 4/12 twins)"
    ]
  },

  "individual_results": [
    {
      "twin_id": "tw_101",
      "twin_name": "User A (Enhanced Twin)",
      "twin_quality": "enhanced",
      "modules_completed": ["M1","M2","M3","M4","A1","A2"],
      "choice": "Option B: One-time purchase",
      "reasoning": "I would choose the one-time purchase. I tend to calculate long-term costs, and $9.99/month adds up to $120/year. The one-time cost pays for itself in 8 months. I also dislike recurring charges — I prefer knowing exactly what I am paying upfront.",
      "confidence_score": 0.85,
      "confidence_label": "high",
      "evidence_used": [
        {"snippet_id": "s_spending_04", "why": "User expressed preference for upfront costs over subscriptions"},
        {"snippet_id": "s_decision_07", "why": "User calculates long-term cost before purchases"}
      ],
      "coverage_gaps": []
    },
    {
      "twin_id": "tw_102",
      "twin_name": "User B (Base Twin)",
      "twin_quality": "base",
      "modules_completed": ["M1","M2","M3","M4"],
      "choice": "Option A: Subscription",
      "reasoning": "I would probably go with the subscription because I prefer flexibility. If I stop using it, I can cancel. But I am not very confident — I do not have strong feelings about pricing models in general.",
      "confidence_score": 0.42,
      "confidence_label": "low",
      "evidence_used": [
        {"snippet_id": "s_pref_02", "why": "User values flexibility in commitments"}
      ],
      "coverage_gaps": ["No spending behavior module completed — financial preferences uncertain"]
    }
  ],

  "limitations_disclaimer": "These results are simulated based on interview-derived digital twin profiles. They represent approximations of likely responses, not actual user decisions. Confidence indicators reflect data coverage quality, not statistical significance. Do not use for high-stakes decisions without live validation."
}
```

### Twin Experiment Response Generation Prompt

```
SYSTEM:
You are simulating how a specific person would respond to a scenario.
You must answer AS this person, based on their profile and evidence.

RULES:
1. Stay consistent with the persona's stated preferences, values, and behavioral rules.
2. Ground your answer in evidence from their interview.
3. If the profile lacks data for this scenario, say so and give your best guess with low confidence.
4. Do not invent traits not supported by evidence.
5. Answer in first person, naturally.
6. Be specific — avoid generic responses.

DEVELOPER:
Experiment type: {experiment_type}
Persona Profile: {persona_profile_payload}
Relevant Evidence: {retrieved_evidence}
Completed modules: {completed_modules}

SCENARIO:
{experiment_prompt}

OPTIONS (if applicable):
{options}

OUTPUT JSON:
{
  "choice": "string or null",
  "choice_index": 0,
  "reasoning": "string (first-person, 50-150 words)",
  "confidence_score": 0.0,
  "confidence_label": "low|medium|high",
  "uncertainty_reason": "string or null",
  "evidence_used": [
    {"snippet_id": "string", "why": "string"}
  ],
  "coverage_gaps": ["string"]
}
```

### Experiment UX Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| UX-EXP-01 | Cohort creation: select twins with quality filters | P0 |
| UX-EXP-02 | Experiment builder: scenario text + type + options | P0 |
| UX-EXP-03 | Results dashboard: aggregate chart (bar/pie for choices) | P0 |
| UX-EXP-04 | Individual result cards: answer + confidence + evidence | P0 |
| UX-EXP-05 | Pattern/insight summary panel | P1 |
| UX-EXP-06 | Export results as JSON/CSV | P1 |
| UX-EXP-07 | Limitations disclaimer on every result | P0 |
| UX-EXP-08 | "Run again" with modified scenario | P1 |

### Guardrails and Limitations

1. **No statistical significance claims.** Experiment results are simulated approximations. UI must always display the limitations disclaimer.
2. **Confidence-weighted results.** Aggregate results should weight by individual twin confidence. Low-confidence twins are flagged.
3. **Minimum twin quality.** Warn if experiment includes base-quality twins without relevant modules.
4. **No sensitive experiments.** Block experiments that probe sensitive topics (health, political, financial) unless all participating twins have the relevant sensitive consent.
5. **Cohort size limits.** MVP: max 50 twins per experiment. Prevents cost overrun.

---

## 10. Twin Chat Experience

*(Largely unchanged from v1.0. Key additions: module-aware confidence.)*

### Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|-------------------|
| CHAT01 | Chat with selected twin version | P0 | User can send message and receive response |
| CHAT02 | Respond in persona voice/style | P0 | Prompt uses persona profile + evidence |
| CHAT03 | Acknowledge uncertainty when data insufficient | P0 | Low-confidence responses include uncertainty statement |
| CHAT04 | Return confidence and evidence references | P0 | API response includes confidence + evidence IDs |
| CHAT05 | Show which modules inform the answer | P1 | Response indicates relevant modules |
| CHAT06 | Suggest "complete module X to improve this answer" | P1 | When answer confidence low due to missing module |
| CHAT07 | Maintain chat session context | P1 | Session memory limited to current window |

---

## 11. Data Design (Updated)

### Updated Relational Schema

**users** — *unchanged from v1.0*

**interview_sessions** (updated for modules)

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| user_id | UUID | FK users.id |
| status | text | active / completed / paused |
| started_at | timestamptz | |
| ended_at | timestamptz | nullable |
| elapsed_sec | int | |
| input_mode | text | voice / text / mixed |
| modules_completed | text[] | array of module IDs |
| module_in_progress | text | nullable |
| settings | jsonb | topic preferences, sensitivity opts |

**interview_modules** (NEW)

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| session_id | UUID | FK interview_sessions.id |
| module_id | text | M1, M2, A1, etc. |
| status | text | active / completed / skipped |
| started_at | timestamptz | |
| ended_at | timestamptz | nullable |
| question_count | int | |
| coverage_score | float | |
| confidence_score | float | |
| signals_captured | jsonb | list of captured signal names |
| completion_eval | jsonb | LLM evaluation output |

**interview_turns** (updated for voice)

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| session_id | UUID | FK |
| module_id | text | which module this turn belongs to |
| turn_index | int | |
| role | text | interviewer / user / system |
| input_mode | text | voice / text |
| question_text | text | interviewer turns |
| question_meta | jsonb | category, type, rationale, target_signal |
| answer_text | text | corrected transcript or typed text |
| answer_raw_transcript | text | raw ASR output (before correction) |
| answer_language | text | EN / HI / HG |
| answer_structured | jsonb | parsed values if any |
| answer_meta | jsonb | sentiment, specificity, confidence |
| audio_meta | jsonb | duration_ms, sample_rate, vad_events, asr_confidence |
| audio_storage_ref | text | S3 path for raw audio (nullable, TTL) |
| created_at | timestamptz | |

**twin_profiles** (updated for modules + quality)

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| user_id | UUID | FK |
| version | int | 1,2,3... |
| status | text | generating / ready / failed |
| modules_included | text[] | ["M1","M2","M3","M4","A1"] |
| quality_label | text | base / enhanced / rich / full |
| quality_score | float | 0.0–1.0 |
| structured_profile_json | jsonb | core twin representation |
| persona_summary_text | text | compact prompt payload |
| persona_full_text | text | optional but recommended |
| coverage_confidence | jsonb | per-module and per-domain map |
| extraction_meta | jsonb | model, prompt version, retries |
| created_at | timestamptz | |

**experiments** (NEW)

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| created_by | UUID | FK users.id |
| name | text | |
| cohort_id | UUID | FK cohorts.id |
| scenario | jsonb | type, prompt, options, context |
| settings | jsonb | temperature, max_tokens, etc. |
| status | text | pending / running / completed / failed |
| aggregate_results | jsonb | populated on completion |
| created_at | timestamptz | |
| completed_at | timestamptz | nullable |

**experiment_results** (NEW)

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| experiment_id | UUID | FK |
| twin_id | UUID | FK twin_profiles.id |
| choice | text | nullable |
| reasoning | text | |
| confidence_score | float | |
| confidence_label | text | |
| evidence_used | jsonb | |
| coverage_gaps | text[] | |
| model_meta | jsonb | model, tokens, latency |
| created_at | timestamptz | |

**cohorts** (NEW)

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| created_by | UUID | FK users.id |
| name | text | |
| twin_ids | UUID[] | |
| filters_used | jsonb | quality, modules, etc. |
| created_at | timestamptz | |

**evidence_snippets**, **twin_chat_sessions**, **twin_chat_messages**, **consent_events** — *unchanged from v1.0*

---

## 12. API Contracts (Updated)

### Start Voice Interview Session

**POST /api/v1/interviews/start**

Request:
```json
{
  "user_id": "7d8e2c3f-7f7d-4c4a-bf77-112233445566",
  "input_mode": "voice",
  "language_preference": "auto",
  "modules_to_complete": ["M1", "M2", "M3", "M4"],
  "sensitivity_settings": {
    "allow_sensitive_topics": false,
    "allowed_sensitive_categories": []
  },
  "consent": {
    "accepted": true,
    "consent_version": "v2.0",
    "allow_audio_storage_days": 7,
    "allow_data_retention_days": 30
  }
}
```

Response:
```json
{
  "session_id": "2b7a0b1c-1111-4444-9999-abcdef123456",
  "status": "active",
  "voice_config": {
    "websocket_url": "wss://api.example.com/ws/interview/2b7a0b1c...",
    "audio_format": "pcm_16khz_mono",
    "tts_voice": "en-IN-neural-female",
    "vad_config": {
      "silence_threshold_ms": 1500,
      "min_speech_duration_ms": 300
    }
  },
  "first_module": {
    "module_id": "M1",
    "module_name": "Core Identity & Context",
    "estimated_duration_min": 3,
    "first_question": {
      "question_id": "M1_q01",
      "question_text": "Hi! Let's start with getting to know you a bit. Can you tell me about what you do and what a typical week looks like for you?",
      "question_type": "open_text",
      "target_signal": "occupation_lifestyle_overview"
    }
  },
  "module_plan": [
    {"module_id": "M1", "status": "active", "est_min": 3},
    {"module_id": "M2", "status": "pending", "est_min": 4},
    {"module_id": "M3", "status": "pending", "est_min": 4},
    {"module_id": "M4", "status": "pending", "est_min": 3}
  ]
}
```

### WebSocket Voice Turn Protocol

**Client → Server (audio stream):**
```json
{"type": "audio_chunk", "data": "<base64_pcm>", "seq": 1}
{"type": "end_of_speech", "reason": "user_silence"}
{"type": "interrupt", "reason": "user_started_speaking"}
{"type": "switch_to_text", "text": "I prefer typing"}
```

**Server → Client:**
```json
{"type": "partial_transcript", "text": "I usually prefer to...", "confidence": 0.7}
{"type": "final_transcript", "text": "I usually prefer to plan things ahead", "language": "EN", "confidence": 0.92}
{"type": "tts_audio_chunk", "data": "<base64_audio>", "seq": 1}
{"type": "tts_complete", "question_text": "Interesting! When you say plan ahead..."}
{"type": "module_progress", "module_id": "M2", "coverage": 0.65, "confidence": 0.58}
{"type": "module_complete", "module_id": "M2", "summary": "You tend to research thoroughly for high-stakes decisions..."}
{"type": "system_message", "text": "Switching to next module: Preferences & Values"}
```

### Submit Module Completion / Generate Twin

**POST /api/v1/interviews/{session_id}/generate-twin**

Request:
```json
{
  "trigger": "mandatory_modules_complete",
  "modules_to_include": ["M1", "M2", "M3", "M4"]
}
```

Response:
```json
{
  "job_id": "job_456",
  "status": "queued",
  "expected_completion_sec": 30,
  "twin_version": 1,
  "quality_label": "base"
}
```

### Create Experiment

**POST /api/v1/experiments**

Request:
```json
{
  "name": "Subscription Preference Test",
  "cohort_id": "cohort_alpha",
  "scenario": {
    "type": "forced_choice",
    "prompt": "You are considering a productivity app. Option A: $9.99/month subscription. Option B: $79.99 one-time purchase. Which do you choose and why?",
    "options": ["Option A: Subscription", "Option B: One-time purchase"],
    "context": "You would use this app daily for work."
  },
  "settings": {
    "require_reasoning": true,
    "temperature": 0.2
  }
}
```

Response:
```json
{
  "experiment_id": "exp_001",
  "status": "queued",
  "cohort_size": 12,
  "estimated_completion_sec": 45
}
```

### Get Experiment Results

**GET /api/v1/experiments/{experiment_id}/results**

Response: *(See full result schema in Section 9)*

### Create Cohort

**POST /api/v1/cohorts**

Request:
```json
{
  "name": "High-quality consumer twins",
  "twin_ids": ["tw_101", "tw_102", "tw_103"],
  "filters": {
    "min_quality": "enhanced",
    "required_modules": ["M1", "M2", "M3", "M4", "A2"]
  }
}
```

---

## 13. System Architecture (Updated)

### Updated Architecture Components

| Layer | Component | Technology | Notes |
|-------|-----------|-----------|-------|
| Frontend | Web app | Next.js + TypeScript + Tailwind | |
| Frontend | Voice capture | WebAudio API + WebSocket | 16kHz mono PCM |
| Frontend | Audio playback | Web Audio API | For TTS streaming |
| Backend | API server | FastAPI + Pydantic | |
| Backend | Voice orchestrator | FastAPI + WebSocket handler | Manages ASR/TTS pipeline |
| Backend | ASR | Deepgram streaming API (primary) / Whisper API (fallback) | Hindi/Hinglish support |
| Backend | TTS | ElevenLabs API or Azure Neural TTS | Hindi + English voices |
| Backend | Interview orchestrator | Custom Python module | Module-aware question planning |
| Backend | Experiment runner | Celery worker | Parallel twin queries |
| DB | Core data | Postgres + pgvector | |
| Storage | Audio/artifacts | S3-compatible object storage | TTL for raw audio |
| Queue | Jobs | Redis + Celery | Twin generation, experiments |
| LLM | Abstraction | LiteLLM or custom wrapper | Model swapping |
| Auth | User auth | Supabase Auth / Clerk | |
| Deploy | Frontend | Vercel | |
| Deploy | Backend | Render / Fly / AWS ECS | |
| Observability | Errors | Sentry | |
| Observability | Product | PostHog | |
| Observability | LLM traces | Langfuse | |

### Updated Architecture Flow

```
Voice Interview Flow:
  Browser mic → WebSocket → Voice Orchestrator → ASR → Transcript
  → Transcript Corrector → Answer Parser → Coverage Scorer
  → Module Evaluator → Question Planner → TTS → WebSocket → Browser speaker

Twin Generation Flow:
  Module completion trigger → Profile Builder → Evidence Indexer
  → Twin Artifact Creator → Version Storage

Experiment Flow:
  Experiment created → Job queued → For each twin in cohort:
    Load profile → Compose prompt → Generate response → Validate → Store
  → Aggregate results → Return to user
```

---

## 14. Non-Functional Requirements

| Category | Target | Notes |
|----------|--------|-------|
| Voice ASR latency | p50 < 1.5s, p95 < 3s | End of speech to transcript |
| Voice TTS first byte | p50 < 800ms, p95 < 2s | Response ready to audio |
| End-to-end voice turn | p50 < 4s, p95 < 8s | User stops → system starts speaking |
| Twin generation time | p50 < 20s, p95 < 60s | Background job |
| Twin chat first token | p50 < 2s, p95 < 5s | Streaming |
| Experiment per-twin | p50 < 5s per twin | Parallelized |
| Experiment total (50 twins) | p50 < 45s | With parallel execution |
| Availability | 99.0% | Internal beta |
| Interview session recovery | Resume within 7 days | Persist state after every turn |
| Cost per voice interview (4 modules) | Target < $2.50 | ASR + TTS + LLM combined |
| Cost per chat turn | Target < $0.05 | Summary + retrieval |
| Cost per experiment (50 twins) | Target < $3.00 | 50 × inference |
| Audio retention | 7 days default, then purged | User can delete anytime |
| Data retention | 30 days default (beta) | Configurable |

---

## 15. UX Requirements (Updated)

### Voice Interview UX

| ID | Requirement | Priority |
|----|-------------|----------|
| UX-VOICE-01 | Microphone permission request with clear explanation | P0 |
| UX-VOICE-02 | Voice waveform / "listening" indicator during user speech | P0 |
| UX-VOICE-03 | Real-time transcript display as user speaks | P1 |
| UX-VOICE-04 | "Correct transcript" option (edit what system heard) | P1 |
| UX-VOICE-05 | Module progress indicator (which module, how many left) | P0 |
| UX-VOICE-06 | Per-module completion celebration/transition | P1 |
| UX-VOICE-07 | "Switch to text" button always visible | P0 |
| UX-VOICE-08 | "Pause and resume later" option | P0 |
| UX-VOICE-09 | Language indicator showing detected language | P1 |
| UX-VOICE-10 | Mute/unmute control | P0 |

### Experiment UX

| ID | Requirement | Priority |
|----|-------------|----------|
| UX-EXP-01 | Cohort builder with twin quality filters | P0 |
| UX-EXP-02 | Experiment scenario editor (text + type selector + options) | P0 |
| UX-EXP-03 | Running state with progress bar (X/N twins complete) | P0 |
| UX-EXP-04 | Results dashboard: aggregate chart + key patterns | P0 |
| UX-EXP-05 | Individual twin result cards (expandable) | P0 |
| UX-EXP-06 | Confidence badge on each twin result + aggregate | P0 |
| UX-EXP-07 | Limitations disclaimer prominently displayed | P0 |
| UX-EXP-08 | Export results (JSON/CSV) | P1 |

### Twin Profile UX (Updated)

| ID | Requirement | Priority |
|----|-------------|----------|
| UX-PRO-01 | Display per-module and per-domain confidence map | P0 |
| UX-PRO-02 | Show completed vs available modules | P0 |
| UX-PRO-03 | "Complete module X" CTA to improve twin | P0 |
| UX-PRO-04 | Quality badge (base/enhanced/rich/full) | P0 |
| UX-PRO-05 | Version history with module diff | P1 |

---

## 16. UX Flows (Updated)

### Flow 1: Voice Interview (New User)

```
Landing → Consent + Mic Permission → Module Plan Overview
  → M1: Core Identity (voice conversation, 2-3 min)
    → Module complete summary → Transition
  → M2: Decision Logic (voice conversation, 3-4 min)
    → Module complete summary → Transition
  → M3: Preferences & Values (voice conversation, 3-4 min)
    → Module complete summary → Transition
  → M4: Communication & Social (voice conversation, 2-3 min)
    → Module complete summary
  → "Generating your Base Twin..." (loading)
  → Twin Profile Review (quality: Base)
    → "Your twin is ready! Complete more modules to improve accuracy."
    → CTA: "Chat with twin" | "Complete add-on modules" | "Run experiment"
```

### Flow 2: Add-on Module (Returning User)

```
Dashboard → Twin Profile → "Improve twin" CTA
  → Available modules list (with estimated improvement)
  → Select module A2: Spending Behavior
  → Voice interview for A2 (3-4 min)
  → Module complete
  → "Upgrading your twin..." (loading)
  → Updated Twin Profile (quality: Enhanced, +10-15% fidelity)
```

### Flow 3: Experiment

```
Dashboard → "New Experiment" CTA
  → Select/create cohort (filter by quality, modules)
  → Define scenario (type, prompt, options)
  → Review & launch
  → Running... (progress: 5/12 twins complete)
  → Results dashboard
    → Aggregate chart (bar chart of choices)
    → Key patterns panel
    → Individual twin cards (expandable)
    → Limitations disclaimer
  → Export / Run again with modifications
```

---

## 17. Edge Cases and Failure Handling (Updated)

| Edge Case | Detection | System Behavior | UX Behavior |
|-----------|-----------|-----------------|-------------|
| Mic permission denied | Browser API | Switch to text mode | "No mic access. Switching to text interview." |
| Poor ASR quality (>3 failures) | Consecutive low-confidence transcripts | Auto-switch to text | "Voice isn't working well. Let's continue in text." |
| Hinglish ASR confusion | Low confidence + language detection conflict | Flag for transcript correction | Show transcript with "Did I hear that right?" |
| User speaks unexpected language | Language detection | Continue with detected language | Respond in user's language |
| Module partially complete, session ends | User closes browser/app | Persist module state | On return: "Welcome back! You were on Module 2, question 3." |
| Twin quality insufficient for experiment | Check modules completed | Warn user, suggest completing modules | "3 twins in this cohort have low quality. Results may be less reliable." |
| Experiment timeout | Twin response > 30s | Retry once, then mark as failed for that twin | Show partial results + "1 twin failed to respond" |
| All other edge cases from v1.0 | *Same as v1.0* | *Same as v1.0* | *Same as v1.0* |

---

## 18. Privacy, Security, and Consent (Updated for Voice)

### Additional Voice-Specific Requirements

| Area | Requirement |
|------|-------------|
| Audio consent | Explicit consent for voice recording before mic activation |
| Audio storage | Raw audio stored max 7 days for debugging, then auto-purged |
| Audio processing | ASR processing happens server-side; no third-party audio storage beyond ASR API transit |
| Transcript ownership | User owns all transcripts; delete includes audio + transcripts |
| Language privacy | Language detected per-session is not used for profiling beyond interview |
| Voice biometrics | NOT collected. No voiceprints, no speaker ID. |

---

## 19. Risks and Mitigations (Updated)

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| Hindi/Hinglish ASR quality too low | Bad transcripts → bad twin | Medium | Transcript correction LLM pass + text fallback |
| Voice latency too high for natural conversation | Poor UX | Medium | Streaming ASR/TTS; optimize pipeline; set expectations |
| Modular interview feels disjointed | User confusion | Low | Smooth transitions with summaries; unified progress view |
| Experiment results overclaimed as "research" | Trust/legal risk | High | Mandatory disclaimers; no statistical claims; "approximation" framing |
| Audio storage privacy concerns | User drop-off | Medium | 7-day TTL; no voiceprints; clear consent |
| Cost blowup from voice APIs | Budget | Medium | Monitor per-session cost; cache TTS; batch ASR |
| All other risks from v1.0 | *Same* | *Same* | *Same* |

---

## 20. MVP Development Plan — Phased Vertical Slices

### Development Philosophy

**Do NOT split by feature** (voice vs modules vs experiments). Each feature in isolation is untestable and leads to painful integration. Instead, split into **5 vertical phases** — each phase delivers a working, end-to-end testable system that builds on the previous.

**Why vertical slices over feature splits:**

| Approach | Problem |
|----------|---------|
| Split by feature (voice / modules / experiments) | Voice and modules are deeply coupled — the voice pipeline IS the interview, and the interview IS modular. Building separately means rework at integration. Results in 3 large, loosely connected codebases. |
| Split by layer (frontend / backend / AI) | No phase produces a testable product. Integration bugs surface late. |
| **Split by vertical phase (recommended)** | Each phase delivers a runnable system. Dependencies flow forward. Testing is continuous. |

**Key principle:** Build the core interview → twin loop in text first (simpler to debug), then swap the input layer to voice. Voice is a transport layer, not a product logic layer.

### Team

- 1 PM / Founding PM
- 2 full-stack engineers
- 1 applied LLM / voice engineer (overlaps with backend)
- 1 designer (part-time)
- 1 QA (part-time or engineer-led)

### Phase Overview

| Phase | Name | Duration | What You Get at the End | Depends On |
|-------|------|----------|------------------------|------------|
| **P0** | Foundation | 1 week | Project skeleton, DB, schemas, CI/CD | Nothing |
| **P1** | Text Interview + Modules | 1.5 weeks | Complete M1–M4 adaptive interview via text → data persisted | P0 |
| **P2** | Twin Generation + Chat | 1.5 weeks | Interview → Base Twin → Chat with confidence/evidence | P1 |
| **P3** | Voice Pipeline | 1.5 weeks | Same interview, now via voice (EN/HI/Hinglish) with text fallback | P1 |
| **P4** | Experiments + Polish | 1.5 weeks | Cohort experiments + add-on modules + demo hardening | P2, P3 |

**Total: ~7 weeks.** P2 and P3 can run in parallel if you have 2 engineers (one on twin/chat, one on voice).

---

### Phase 0: Foundation (Week 1)

**Goal:** Lock architecture. Every subsequent phase inherits this foundation.

**Deliverables:**

| Task | Owner | Details |
|------|-------|---------|
| Project structure | Full-stack | Monorepo: `/frontend` (Next.js + TS + Tailwind), `/backend` (FastAPI + Pydantic), `/prompts` (template files), `/migrations` (Alembic) |
| DB schema + migrations | Backend | All tables from Section 11: users, interview_sessions, interview_modules, interview_turns, twin_profiles, evidence_snippets, twin_chat_sessions, twin_chat_messages, cohorts, experiments, experiment_results, consent_events |
| Pydantic models | Backend | Request/response models for all APIs in Section 12. Strict validation. |
| LLM abstraction layer | LLM eng | Thin wrapper (LiteLLM or custom) supporting model swapping, retry, logging. Not an agent framework. |
| Prompt file structure | LLM eng | `/prompts/interviewer_question.txt`, `/prompts/module_completion.txt`, `/prompts/profile_extraction.txt`, `/prompts/twin_response.txt`, `/prompts/experiment_response.txt`, `/prompts/transcript_correction.txt` |
| Seed question bank | PM + LLM eng | 15–25 questions per mandatory module (M1–M4), mapped to signal targets. JSON format. |
| CI/CD + environments | Full-stack | GitHub Actions, staging env, Sentry, basic PostHog |
| Auth skeleton | Full-stack | Supabase Auth / Clerk integration, bearer token middleware |

**Exit criteria:**

- `docker-compose up` runs frontend + backend + Postgres + Redis
- All DB tables created via migration
- All Pydantic models pass schema validation tests
- LLM wrapper returns a response from at least one provider
- Seed question bank loaded and queryable

---

### Phase 1: Text Interview + Modular Engine (Weeks 2–3)

**Goal:** Complete end-to-end modular interview via text input. This is the product's core loop without the voice complexity.

**Why text first:** Debugging LLM-based adaptive questioning, module state transitions, and follow-up logic is 5× easier with text than voice. All logic built here is reused when voice is plugged in.

**Sprint 1a (Week 2): Static Interview + Module State**

| Task | Owner | Details |
|------|-------|---------|
| `POST /api/v1/interviews/start` | Backend | Create session, initialize module plan, return first question |
| `POST /api/v1/interviews/{id}/answers` | Backend | Accept text answer, persist turn, return ack |
| `POST /api/v1/interviews/{id}/next-question` | Backend | Static question sequencing across M1–M4 |
| Module state engine | Backend + LLM | Per-module tracking: coverage_score, confidence_score, signals_captured. Updated after each answer. |
| Interview UI (text) | Frontend | Single-question-per-screen flow, text input, progress bar by modules, skip button |
| Module transitions | Backend | When module complete → transition to next. Show module summary. |
| Session persistence | Backend | State saved after every turn. Resume on reconnect. |

**Exit criteria:**

- User can complete M1–M4 via text with static questions
- Module state updates correctly after each answer
- Session resumes after browser close

**Sprint 1b (Week 3): Adaptive Questioning + Follow-ups**

| Task | Owner | Details |
|------|-------|---------|
| Question planner prompt | LLM eng | LLM-based adaptive question selection using `interviewer_question.txt` template |
| Answer parser | LLM eng | Extract specificity, conditions, contradiction signals from answers |
| Coverage/confidence scorer | LLM eng | Update module scores based on parsed answer quality |
| Follow-up rules | LLM eng | Follow-up triggered only when: vague answer, low specificity, contradiction, high-leverage topic |
| Module completion evaluator | LLM eng | LLM evaluates if module criteria met using `module_completion.txt` prompt |
| Stopping heuristic | Backend | Module stops when coverage ≥ threshold AND confidence ≥ threshold |
| Multi-session resume | Backend | User can close mid-M2, return next day, continue from exact turn |
| Recap/confirmation | LLM eng | At module end, summarize what was learned and confirm with user |

**Exit criteria:**

- Interview asks adaptive follow-ups (not static) and stops modules automatically
- Follow-ups are triggered appropriately (not every turn)
- User can complete mandatory modules across 2 separate sessions
- Module completion evaluation produces valid JSON with scores

**Tests to write first (TDD):**

```
test_module_state_updates_on_answer()
test_coverage_score_increases_with_specific_answers()
test_followup_triggered_on_vague_answer()
test_followup_not_triggered_on_specific_answer()
test_module_completes_when_threshold_met()
test_session_resumes_from_last_turn()
test_question_planner_respects_sensitivity_settings()
test_skip_records_reason_code()
```

---

### Phase 2: Twin Generation + Chat (Weeks 3.5–5)

**Goal:** Completed interview produces a versioned twin. User can chat with twin and see confidence/evidence.

**Can run in parallel with P3 if team allows.**

**Sprint 2a (Week 3.5–4): Twin Generation Pipeline**

| Task | Owner | Details |
|------|-------|---------|
| Profile extraction prompt | LLM eng | Module-aware extraction using `profile_extraction.txt`. Takes all completed module transcripts. |
| Persona summary generator | LLM eng | ≤ 2500 token summary from structured profile |
| Evidence chunking + embeddings | Backend + LLM | Chunk answers, generate embeddings (provider API), store in pgvector |
| Twin versioning | Backend | Create immutable twin version. Track modules_included, quality_label, quality_score. |
| Incremental regeneration | Backend | When add-on module completes → regenerate twin with expanded data → new version |
| JSON validation + retry | Backend | Schema validation on all LLM outputs. Bounded retry (max 3). |
| Twin profile API | Backend | `GET /api/v1/twins/{id}` returns full profile with coverage map |
| Twin profile UI | Frontend | Summary, per-module confidence bars, uncertainty gaps, quality badge, "Improve twin" CTA |

**Exit criteria:**

- Completed M1–M4 interview auto-triggers twin generation
- Base Twin (v1) created with quality_label = "base"
- Profile UI shows coverage, confidence, uncertainties
- Completing A1 add-on → regenerates twin v2 with quality_label = "enhanced"

**Sprint 2b (Weeks 4–5): Twin Chat**

| Task | Owner | Details |
|------|-------|---------|
| Chat session APIs | Backend | `POST /api/v1/twins/{id}/chat` with session management |
| Evidence retrieval | Backend + LLM | Semantic search over evidence snippets (pgvector). Top-k by relevance + category diversity. |
| Twin response prompt | LLM eng | `twin_response.txt` template. Persona profile + evidence + chat context + user question. |
| Confidence scoring | LLM eng | Score based on evidence coverage + module completion for query topic |
| Module-aware suggestions | LLM eng | "Complete module A2 to improve this answer" when confidence low due to missing module |
| Chat UI | Frontend | Message cards with: answer, confidence badge, expandable evidence drawer, uncertainty reason |
| Streaming responses | Backend + Frontend | SSE streaming for chat responses |
| Safety filter | LLM eng | Basic rule-based + LLM check for sensitive/harmful outputs |

**Exit criteria:**

- User can chat with twin and receive grounded responses
- Confidence badge shows High/Medium/Low correctly
- Evidence snippets are expandable and relevant
- Low-coverage questions trigger "complete module X" suggestion

**Tests to write first (TDD):**

```
test_twin_generation_from_completed_modules()
test_twin_version_increments_on_addon_module()
test_quality_label_upgrades_with_more_modules()
test_evidence_retrieval_returns_relevant_snippets()
test_confidence_score_low_for_uncovered_topics()
test_twin_response_includes_evidence_ids()
test_chat_session_maintains_context()
test_json_validation_retry_on_malformed_output()
```

---

### Phase 3: Voice Pipeline (Weeks 3.5–5)

**Goal:** Replace text input with voice input. All interview logic from P1 is reused — voice is a transport layer.

**Can run in parallel with P2 if a separate engineer handles it.**

**Sprint 3a (Week 3.5–4): Voice Infrastructure**

| Task | Owner | Details |
|------|-------|---------|
| WebSocket endpoint | Backend | `wss://api/ws/interview/{session_id}` for bidirectional audio/text |
| Browser mic capture | Frontend | WebAudio API, 16kHz mono PCM, stream to WebSocket |
| ASR integration | Voice eng | Deepgram streaming API (primary). Whisper API (fallback). Language auto-detection. |
| TTS integration | Voice eng | ElevenLabs API or Azure Neural TTS. Hindi + English voices. Streamed audio chunks. |
| Turn-taking (VAD) | Voice eng | Silence detection (1.5s threshold), interruption handling (stop TTS on user speech), min speech duration (0.3s) |
| Audio storage | Backend | Raw audio → S3 with 7-day TTL. Audio metadata → Postgres. |
| Voice UI | Frontend | Waveform/listening indicator, mute button, "Switch to text" button |

**Exit criteria:**

- User can speak, system transcribes, responds via TTS
- Turn-taking works (silence, interrupts, pauses)
- Audio stored with metadata

**Sprint 3b (Weeks 4–5): Bilingual + Integration**

| Task | Owner | Details |
|------|-------|---------|
| Hindi/Hinglish ASR | Voice eng | Whisper large-v3 with `language=None` for auto-detection. Validate on Hindi/Hinglish test set. |
| Transcript correction | LLM eng | Post-ASR LLM pass using `transcript_correction.txt` prompt. Language tagging per segment. |
| Integration with interview logic | Backend | Voice transcripts feed into the same answer processing pipeline from P1. Input_mode = "voice" flagged on turns. |
| Real-time transcript display | Frontend | Show partial + final transcript. "Did I hear that right?" correction option. |
| Text fallback | Backend + Frontend | Auto-switch after 3 consecutive ASR failures or user click. Module state preserved. |
| Language-adaptive responses | LLM eng | Interviewer responds in user's detected language (EN/HI/Hinglish) |
| Extended silence handling | Voice eng | 8s → gentle prompt; 20s → offer to pause/resume |

**Exit criteria:**

- User can complete M1–M4 via voice in English, Hindi, or Hinglish
- Transcript correction improves ASR errors
- Text fallback works seamlessly mid-module
- Same adaptive interview logic from P1 works identically via voice

**Tests to write first (TDD):**

```
test_websocket_audio_round_trip()
test_asr_returns_transcript_for_english()
test_asr_returns_transcript_for_hindi()
test_tts_generates_audio_for_response()
test_turn_taking_silence_detection()
test_turn_taking_interruption_stops_tts()
test_transcript_correction_fixes_common_errors()
test_text_fallback_preserves_module_state()
test_language_detection_tags_correctly()
test_voice_answer_feeds_into_same_pipeline_as_text()
```

---

### Phase 4: Experiments + Add-ons + Polish (Weeks 5.5–7)

**Goal:** Experiment engine, add-on modules, and demo-readiness.

**Sprint 4a (Weeks 5.5–6): Experiment Engine**

| Task | Owner | Details |
|------|-------|---------|
| Cohort CRUD | Backend | `POST /api/v1/cohorts` — create cohort from twin IDs with quality filters |
| Experiment definition API | Backend | `POST /api/v1/experiments` — scenario, type, options, settings |
| Experiment execution engine | Backend + LLM | Celery workers. For each twin: load profile → compose prompt → generate → validate → store. Parallelized. |
| Aggregate result computation | Backend | Choice distribution, confidence distribution, pattern detection, dominant themes |
| Experiment result API | Backend | `GET /api/v1/experiments/{id}/results` — full schema from Section 9 |
| Experiment UI: setup | Frontend | Cohort builder (filter by quality, modules), scenario editor (type + prompt + options) |
| Experiment UI: results | Frontend | Aggregate chart (bar/pie), pattern panel, individual twin cards (expandable), export button |
| Limitations disclaimer | Frontend | Mandatory display on every result view |

**Exit criteria:**

- User can create cohort, define experiment, run it, inspect results
- Individual twin results show reasoning + confidence + evidence
- Aggregate results show distribution + patterns
- Disclaimer displayed on all result views

**Sprint 4b (Weeks 6–7): Add-ons + Polish + Demo**

| Task | Owner | Details |
|------|-------|---------|
| Add-on module question banks | PM + LLM eng | A1–A4 question banks (15–25 questions each), mapped to signal targets |
| Add-on module flow | Backend | Same adaptive logic as mandatory modules, trigger twin regeneration on completion |
| Holdout evaluation mode | LLM eng | Reserve 8–12 benchmark questions. Compare twin vs real user answers. |
| Metrics dashboard | Backend + Frontend | Completion rate, duration, latency, fidelity basics |
| Error handling + fallbacks | Backend | Fallback models, graceful degradation, retry logic hardening |
| Privacy controls | Backend + Frontend | Delete twin/session/audio buttons. Data export (JSON). |
| Voice UX polish | Frontend | Smoother transitions, better waveform, loading states |
| Demo script rehearsal | PM | 8–10 minute demo covering interview → twin → chat → experiment |
| End-to-end integration tests | QA | Full flow: voice interview → twin → chat → experiment |

**Exit criteria:**

- Add-on modules A1–A4 functional and trigger twin quality upgrades
- Holdout eval produces comparison report
- Demo runs smoothly end-to-end
- Privacy controls work (delete everything)
- No critical bugs in happy path

**Tests to write first (TDD):**

```
test_cohort_creation_with_quality_filter()
test_experiment_execution_parallel()
test_experiment_aggregate_results_correct()
test_individual_twin_result_has_reasoning()
test_addon_module_triggers_twin_regeneration()
test_twin_quality_upgrades_after_addon()
test_holdout_eval_compares_twin_vs_real()
test_delete_twin_removes_all_data()
test_delete_session_removes_audio()
```

---

### Phase Dependency Graph

```
P0 (Foundation)
 │
 ▼
P1 (Text Interview + Modules)
 │
 ├──────────────┐
 ▼              ▼
P2 (Twin +     P3 (Voice
 Chat)          Pipeline)
 │              │
 └──────┬───────┘
        ▼
P4 (Experiments + Polish)
```

**P2 and P3 are parallelizable.** If you have 2 engineers, one takes P2 (twin generation + chat) while the other takes P3 (voice pipeline). They share the P1 codebase and merge at P4.

### Milestones

| Milestone | Deliverable | When | Demo Value |
|-----------|-------------|------|------------|
| M0 | Foundation running, schemas in code | End Week 1 | Internal only |
| M1 | Text interview (M1–M4) working with adaptive logic | End Week 3 | "Look, the interview works and adapts" |
| M2 | Twin generation + chat with confidence/evidence | End Week 5 | "Interview → twin → chat with grounding" |
| M3 | Voice pipeline integrated (EN/HI/Hinglish) | End Week 5 | "Now do it by talking" |
| M4 | Experiments + add-ons + demo-ready | End Week 7 | Full investor/stakeholder demo |

### Claude Code Session Planning

For each phase, create a focused Claude Code session with scoped context. Do NOT dump the entire PRD — give it only what it needs.

| Phase | What to Give Claude Code | Estimated Sessions |
|-------|-------------------------|-------------------|
| P0 | Section 11 (schemas), Section 13 (architecture), project structure spec | 1 session |
| P1a | Section 5 (modules), Section 7 (interviewer requirements), seed question bank, Pydantic models from P0 | 1 session |
| P1b | Section 7 (adaptive logic), interviewer prompt templates, test specs | 1 session |
| P2a | Section 8 (twin creation), profile extraction prompt, evidence schema | 1 session |
| P2b | Section 10 (chat), twin response prompt, confidence logic | 1 session |
| P3a | Section 6 (voice pipeline), WebSocket protocol, ASR/TTS integration specs | 1 session |
| P3b | Transcript correction prompt, bilingual logic, integration with P1 pipeline | 1 session |
| P4a | Section 9 (experiments), experiment result schema, experiment prompt | 1 session |
| P4b | Add-on question banks, holdout eval, polish items | 1 session |

**Total: ~9 Claude Code sessions across 7 weeks.**

For each session, structure the prompt as:

```
You are building Phase X of a Digital Twin product.

## Context
[Paste relevant PRD section]

## Existing Code
[Reference the repo structure / key files from previous phases]

## Task
Build [specific deliverables for this sprint].

## Schemas
[Paste Pydantic models / DB schemas needed]

## API Contracts
[Paste relevant API specs]

## Prompts
[Paste LLM prompt templates to implement]

## Tests (write these first)
[Paste test specs]

## Constraints
- Python 3.11+, FastAPI, Pydantic v2
- Next.js 14+, TypeScript, Tailwind
- Postgres + pgvector
- Write tests first, then implementation
- Keep prompts in /prompts/ directory as .txt files, not hardcoded
- No per-user fine-tuning — ICL only
```

---

## 21. Trade-offs: What Is Included vs Postponed

| Decision | Included (MVP) | Postponed (Post-MVP) |
|----------|----------------|---------------------|
| Voice | Whisper/Deepgram ASR + streaming TTS | WebRTC for better audio quality |
| Language | EN + HI + Hinglish | Other Indian languages (Tamil, Telugu, etc.) |
| Interview structure | 4 mandatory + 4 add-on modules | Dynamic module generation, custom modules |
| Twin quality | Incremental by module | Longitudinal updates from conversations |
| Experiments | Manual cohort + single scenario | A/B treatments, multi-step scenarios, statistical tests |
| Experiment cohorts | Manual twin selection | Auto-segmented cohorts, demographic panels |
| Transcript correction | LLM post-processing | User-editable transcript in real-time |
| Audio | Server-side ASR, 7-day audio TTL | Client-side ASR option, no audio storage |
| Twin sharing | Own twins only | Share twins, team workspace |
| Enterprise | Single-user | RBAC, SSO, compliance |

---

## 22. Open Questions / Assumptions

### Assumptions

1. **Voice ASR quality:** Whisper large-v3 / Deepgram provides adequate Hindi/Hinglish accuracy for MVP. If not, text fallback is always available.
2. **Module independence:** Modules can be completed in any order after M1 (which provides baseline context). M2/M3/M4 do not strictly depend on each other.
3. **Twin quality scores:** Fidelity estimates (55–90%) are directional targets based on domain coverage, not empirically validated until holdout evaluation.
4. **Experiment validity:** Experiment results are explicitly framed as simulated approximations. No statistical significance claims.
5. **ICL approach:** Twin creation remains prompt-conditioned (no fine-tuning), following Twin-2K methodology.
6. **Model provider:** Hosted LLM APIs (not self-hosted). ASR/TTS via external APIs.

### Open Questions

1. Should module order be enforced (M1 always first) or fully flexible?
2. What is the minimum twin quality required to participate in experiments?
3. Should experiments support multi-turn scenarios (e.g., "What if they said X in response to your choice?")?
4. How should twin versioning work when the same module is re-completed (re-interview)?
5. Should the voice interviewer's persona (name, tone, gender) be customizable?
6. What is the right balance between ASR accuracy and latency for the Hindi/Hinglish use case?
7. Do we need real-time transcript editing by the user, or is post-correction sufficient?
8. For experiments: should we allow "control" and "treatment" groups within a cohort?

---

*End of PRD v2.0*
