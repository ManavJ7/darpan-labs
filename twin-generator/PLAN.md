# Twin Generation Pipeline — Plan

## Overview
Generate 2,000 digital twin profiles from 20 real interview participants (men and women, aged 20-30, metro India) for the **body wash** product category using a branching + ICL expansion approach. Then build two inference layers (Vector DB + Knowledge Graph) and benchmark both against real human responses.

## Target Audience
- **Age**: 20-30 years old
- **Gender**: Male and female
- **Geography**: Metro India
- **Product category**: Body wash

## Pipeline Steps

### Step 1: Master Question Bank Design
- **Status**: COMPLETE
- **Input**: 59 existing interview questions (CSV, 7 modules M1-M7)
- **Output**: 350-question JSON bank (59 existing + 291 new) across 6 behavioral domains
- **Domains**: Purchase Decision Mechanics, Information-Seeking Behavior, Brand Relationship Patterns, Risk & Novelty Orientation, Social & Contextual Drivers, Channel & Format Preferences
- **Approach**: Map existing 59 questions to domains, identify gaps, generate 291 new scenario-based trade-off questions via LLM. All questions focus on body wash category.

### Step 2: Branching Question Selection + Variant Generation
- **Status**: Exploration running, awaiting human validation of dimensions
- **Input**: 291 new questions + 20 sets of real Q&A pairs
- **Output**: 5 branching questions per person × 3 answer archetypes each → 100 pruned twins per person
- **Sub-steps**:
  - (a) Identify 5 behavioral dimensions **NOT captured** by the 59 questions but that would cause twins to respond **differently to product concepts and ad campaigns**. Framed around the two use cases: concept validation + ad testing.
  - (b) For each uncaptured dimension, select 1 question **only from the 291 new questions** (never from the original 59) and produce 3 answer archetypes that are all plausible *for this specific person* given their locked 59 real answers. Each archetype includes concept test + ad test predictions.
  - (c) Evaluate all 243 combinations (3^5) for coherence against the person's real 59 answers, prune contradictory ones, select 100 most coherent + diverse.
- **Key Risk**: LLM may over-index on Western consumer patterns. Must validate against Indian consumer segmentation.

### Step 3: Full Profile Expansion (ICL Generation)
- **Status**: Not started
- **Input**: 100 branch-twin profiles per person (64 Q&A pairs each: 59 real + 5 branch)
- **Output**: 2,000 complete profiles with 350 Q&A pairs each (700,000 total Q&A pairs)
- **Approach**: Batch ICL generation (~10 Qs per LLM call), conditioned on full path context
- **Compute**: ~57,000 LLM calls, ~$15-25 total, 4-6 hours with parallel batching

### Step 4A: Vector DB Inference Layer
- **Status**: Not started
- **Approach**: Embed 700K Q&A pairs, store in ChromaDB/pgvector, use cosine distance for contrast twin selection

### Step 4B: Knowledge Graph Inference Layer
- **Status**: Not started
- **Approach**: Extract 25-35 behavioral trait nodes per twin, build weighted edge graphs, traverse for reasoning subgraphs

### Step 5: Benchmark
- **Status**: Not started
- **Metrics**: JS Divergence, Top-Box Agreement, Variance Match, Segment-Level Accuracy, Reasoning Plausibility

## Locked Parameters

| Parameter | Value |
|-----------|-------|
| N_real (people interviewed) | 20 |
| Q_real (questions per person) | 59 |
| Q_total (master question bank) | 350 |
| Q_new (to generate) | 291 |
| Q_branch (branching questions) | 5 |
| V_branch (variants per branch Q) | 3 (→ 3^5 = 243 raw combos → prune to 100) |
| N_twins (per person) | 100 |
| N_total (total twin pool) | 2,000 |
| Q_remaining (synthetic per twin) | ~286 |

## Data Source Weights

| Source | Questions | Weight | Tag |
|--------|-----------|--------|-----|
| Real interview answers | 59 | 1.0 | source=real |
| Branch-selected answers | 5 | 0.9 | source=branch |
| ICL-generated answers | 286 | 0.7 | source=synthetic |

## Core Principle: Branching on Uncaptured Dimensions

**The 59 real answers are locked truth.** Every twin of Participant P01 shares the exact same 59 answers. Twins do NOT differ on dimensions the interview already measured.

**Branching happens on what we DON'T know.** The 59 questions leave behavioral blind spots — dimensions we never asked about. The branching explores those blind spots: "given everything we know about this person, what could they plausibly be like on dimensions we didn't measure?"

**Why this matters:**
- Wrong approach: "This person is price-sensitive (from Q22). Let's make twins where some are price-sensitive and some aren't." → This creates different people, not twins of the same person.
- Right approach: "We know this person's price sensitivity (locked). But we never asked about their mood-dependent product switching, or how they behave when traveling, or their sustainability trade-offs in practice. Those are where the uncertainty lives."

**Implementation consequences:**
1. Step 1 must explicitly identify which behavioral territory the 59 questions cover and which they don't
2. Step 2a must find dimensions **outside** what the 59 questions captured
3. Step 2b must select branching questions **only from the 291 new questions**, never the original 59
4. Step 2c must check that each branch archetype is plausible *for this specific person* given their real answers — not just generically plausible
5. Step 3 (ICL expansion) generates answers to the remaining ~286 questions, conditioned on the locked 59 + the 5 branch answers

## Architecture Decisions
- Standalone scripts (not a web service) — this is a batch data pipeline
- Python with async LLM calls for parallelism
- LiteLLM for model abstraction (same pattern as study-design-engine)
- JSON-based intermediate outputs for debuggability
- Each step produces files in `data/output/` that feed the next step
