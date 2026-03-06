# Twin Generation Pipeline — Progress

## Target: Body wash | Audience: Men & women, 20-30, metro India

## Current Status: Step 5 M8 Simulation COMPLETE for P01_T001 — Step 4 KG built, Step 5 SDE + M8 simulations done

---

### Step 1: Master Question Bank Design
- [x] 59 existing interview questions available (`questions.csv`, 7 modules M1-M7)
- [x] Question bank generation script created (`scripts/step1_question_bank.py`)
- [x] Prompt template for question generation created
- [x] Map existing 59 questions to 6 behavioral domains (via LLM)
- [x] Identify coverage gaps per domain
- [x] Generate 291 new scenario-based trade-off questions (body wash, India-specific, INR prices)
- [x] Regenerated with Opus 4.6 (previously used Sonnet)
- [x] Validate no redundancy, deduplication pass clean
- [x] Output: 350-question JSON bank → `data/output/question_bank.json`

**Status**: COMPLETE (350 questions: 59 existing + 291 generated, ~58-59 per domain, all generated with Opus 4.6)

---

### Step 2: Branching Question Selection + Variant Generation + Pruning
- [x] Prompt templates reworked per Core Principle (uncaptured dimensions only, concept/ad testing use cases)
- [x] Step 2a: Identify 5 uncaptured dimensions per participant — DONE
- [x] Step 2b: Select branching Qs from 291 new questions + generate 3 archetypes per dimension — DONE
- [x] Step 2c: Evaluate 243 combinations for coherence, prune contradictory, select 100 diverse — DONE
- [x] Resume support added (saves after each participant)
- [x] All LLM calls use Opus 4.6

**Results (2 participants)**:

| Participant | Dimensions | Combos | Contradictory | Coherent | Selected | Coherence Range |
|-------------|-----------|--------|---------------|----------|----------|-----------------|
| P01 (Male, Mumbai) | 5 | 243 | 86 | 157 | 100 | 0.52 - 0.87 |
| P02 (Female, Ahmedabad) | 5 | 243 | 39 | 204 | 100 | 0.52 - 0.85 |

**P01 Dimensions**: Emotional vs Analytical Ad Processing, Social Identity Signaling, Aspirational vs Authentic Tolerance, Decision Urgency/Deliberation Window, Masculinity Framing Sensitivity

**P02 Dimensions**: Emotional vs Analytical Ad Processing, Aspirational Identity vs Pragmatic Self, Visual Packaging Semiotics, Skepticism Toward Marketing Claims, Context-Dependent Mood-State Receptivity

**Archetype Distribution** (shows diversity selection is working — no archetype dominates):
- P01: Each dimension has 7-50 twins per archetype (A/B/C), no single archetype exceeds 50%
- P02: Each dimension has 12-50 twins per archetype, similarly well-distributed

**Output Files**:
- `data/output/step2_dimensions.json` — 5 dimensions per participant with concept/ad test impact analysis
- `data/output/step2_archetypes.json` — Selected branching questions + 3 archetypes per dimension with predictions
- `data/output/step2_pruned_twins.json` — 100 twin profiles per participant, each with 5 branch answers, coherence scores, and concept/ad predictions

**Status**: COMPLETE — 200 twin profiles generated. Ready for Step 3 (each twin has 64 Q&A pairs: 59 real + 5 branch).

---

### Step 3: Full Profile Expansion (ICL Generation)
- [x] Cost analysis: Opus $15 for 20 twins (P01 test), Sonnet $46 for 200 twins
- [x] Architecture decision: Direct context (no Vector RAG) — 64 Q&A pairs fit in 3,927 tokens
- [x] Approach decision: Batch-25 (25 questions per LLM call, 12 calls per twin)
- [x] Pre-step: Prune 100 → 20 twins using coherence + diversity selection
- [x] Script built: `scripts/step3_profile_expansion.py`
- [x] Prompt created: `prompts/step3_generate_answers.txt`
- [x] Config updated: `TARGET_TWINS_STEP3=20`, `STEP3_BATCH_SIZE=25`, `LLM_MAX_TOKENS_STEP3=4096`
- [x] Resume support: saves after each twin, skips completed twin_ids on restart
- [x] Run for P01 (20 twins, 240 LLM calls) — COMPLETE, 0 failures
- [x] Run for P02 (20 twins, 240 LLM calls, 5 parallel) — COMPLETE, 0 failures
- [ ] Quality validation: compare synthetic answer style vs real answers

**Architecture**:
- 289 unanswered questions per twin (291 generated in bank - 2 used as branch questions)
- 12 batches of 25 questions per twin (last batch has 14)
- 240 total LLM calls for 20 twins
- Input per call: ~6,500 tokens (3,927 context + 2,074 for 25 questions + 500 prompt)
- Output per call: ~1,500 tokens (25 answers × ~60 tokens)
- Model: Opus 4.6 (proven quality for this pipeline)

**Pruning Results** (100 → 20):
- P01: coherence range 0.72 - 0.87 (top 20 by coherence × diversity)

**Run Results (P01, Sonnet 4)**:
- Model: `anthropic/claude-sonnet-4-20250514` (Opus was overloaded)
- 20 twins, 240 LLM calls, 289 synthetic answers per twin
- 7,055 total Q&A pairs, 0 failures (89 initial failures backfilled)
- Runtime: ~162 minutes (~8 min/twin)
- Output: 4.4 MB JSON

**Run Results (P02, Opus 4.6, 5-parallel)**:
- Model: `anthropic/claude-opus-4-6`
- 20 twins, 240 LLM calls, 5 twins in parallel via asyncio.gather
- 7,060 total Q&A pairs, 0 failures
- Runtime: ~52.8 minutes (~2.6 min/twin effective, 3.2x faster than P01 sequential)
- Heavy rate limiting (30K input / 8K output TPM) — backoff retries handled it

**Output Files**:
- `data/output/step2_pruned_twins_20.json` — 20 re-selected twins per participant
- `data/output/step3_complete_profiles.json` — complete profiles with all Q&A pairs

### Step 4: Digital Twin Inference Layers
- [x] Step 4 config added to `config/settings.py` (ChromaDB paths, vector top-k, KG traits, Opus query model)
- [x] Prompt templates created with research-informed design:
  - `prompts/step4_query.txt` — ID-RAG identity anchoring + category context + evidence reasoning protocol
  - `prompts/step4_extract_traits.txt` — Structured trait extraction with confidence calibration + predictive values
- [x] `scripts/step4_vector_index.py` — ChromaDB + sentence-transformers (all-MiniLM-L6-v2, free local, 384 dims)
- [x] `scripts/step4_kg_build.py` — Extract behavioral traits per twin via Opus, build networkx graph with resume/checkpoint
- [x] `scripts/step4_inference.py` — Main query CLI with 3 modes (vector, kg, combined) + interactive REPL
- [x] Dependencies: numpy, networkx, chromadb, scikit-learn, sentence-transformers
- [x] Vector index built: 7,055 entries in ChromaDB, ~78s build time, $0 cost (local embeddings) — P01 only, needs rebuild for P02
- [x] Sanity checks passed: top-3 retrieval for "What body wash brand do you use?" returns correct real answers (score=0.802)
- [ ] Rebuild vector index with P01+P02 data (14,115 entries expected)
- [x] KG built for P01_T001: 33 traits, 45 nodes, 90 edges (fixed max_tokens 8192→16000)
- [ ] Run KG build for remaining P01 twins + all P02 twins
- [ ] Test all 3 modes with sample queries
- [ ] Compare modes on 5 diverse query types

**Key Design Decisions (informed by `research_papers_vectordb_knowledgegraphs.docx`)**:
- **Embeddings**: sentence-transformers `all-MiniLM-L6-v2` — free, local, 384 dims. Validated by SSR paper on personal care products.
- **Vector DB**: ChromaDB persistent collection (pilot phase per doc recommendation). Metadata filtering by twin_id/source, cosine distance, SQLite backend.
- **KG**: NetworkX in-memory graph (pilot phase per doc recommendation). Opus for trait extraction, not rule-based — nuance matters for behavioral traits.
- **Synthesis**: Opus 4.6 for all query synthesis. Prompts use ID-RAG identity anchoring (MIT paper) + category context (Li et al.) + 4-step evidence reasoning protocol.
- **3 modes**: Vector-only, KG-only, Combined — will benchmark all three in Step 5 (doc recommends building both and comparing).

**Architecture**:
- **Mode 1 (vector)**: ChromaDB semantic search → top-15 weighted Q&A pairs → Opus synthesis
- **Mode 2 (kg)**: Classify query domains → traverse networkx trait graph → reasoning chain → Opus synthesis
- **Mode 3 (combined)**: Parallel vector + KG retrieval → merged evidence → Opus synthesis

**CLI**:
```bash
python scripts/step4_vector_index.py                              # Build ChromaDB index (~78s, $0)
python scripts/step4_kg_build.py                                   # Build KG (~$24)
python scripts/step4_inference.py --twin P01_T003 --mode vector --query "..."
python scripts/step4_inference.py --twin all --mode combined --query "..."
python scripts/step4_inference.py --interactive --mode combined    # Interactive REPL
```

**Status**: VECTOR INDEX + KG BUILT for P01_T001 — P02 rebuild + multi-twin query testing remaining

---

### Step 5: Survey Simulation (Batched)
- [x] Script built: `scripts/step5_survey_simulation.py`
- [x] Batch prompt created: `prompts/step5_batch_survey.txt`
- [x] Batched inference: groups questions by type, 1 LLM call per batch (default 8 Qs/batch)
- [x] Persistent memory: answers written to ChromaDB after each batch (self-consistency)
- [x] Persistent memory: KG updated with survey-derived traits after all batches (1 Opus call)
- [x] LLM call logging: JSONL per twin with prompt, response, timing, model
- [x] show_if / skip-logic evaluation with deferred question re-evaluation
- [x] Concept expansion: `expand_questionnaire()` expands template sections (S3, S4, S5, S7) across all concepts
- [x] Response parsing: type-aware (single_select, multi_select, rating/likert, ranking, open_text)
- [x] Export: JSON + CSV (wide format)
- [x] Upload to SDE API (optional)
- [x] Legacy per-question mode (--no-batch) preserved
- [x] Run simulation for P01_T001 with combined mode — COMPLETE
- [x] Verify 87 answered questions across 5 concepts — COMPLETE
- [ ] Benchmark synthetic answers vs real human responses

**Architecture**:
- SDE questionnaire has 24 template questions; concept-dependent sections (S3, S4, S5, S7) are expanded per concept
- 7 common questions + (17 per-concept × 5 concepts) = 92 total, minus 5 concept_exposure instructions = **87 answerable**
- Batching by question_type ensures consistent LLM output formatting
- ChromaDB persistence creates a virtuous loop: earlier answers become evidence for later batches
- KG persistence extracts behavioral traits from survey answers, enriching the twin's knowledge graph

**CLI**:
```bash
python scripts/step5_survey_simulation.py \
  --study-id <UUID> \
  --twins P01_T001 \
  --mode combined --batch --batch-size 8
```

**Run Results (P01_T001, Opus 4.6, combined mode)**:
- 87/87 questions answered, 0 skipped
- 12 batches (6 single_select, 2 open_text, 3 rating, 1 multi_select)
- Total runtime: 393s (~6.5 min), including KG extraction
- ChromaDB: 87 survey answers persisted (7,055 + 87 = 7,142 entries)
- KG: 30 new traits extracted, graph grew from 45→75 nodes, 90→166 edges
- LLM log: JSONL with all prompts/responses/timing

**Status**: SDE SIMULATION COMPLETE — benchmarking remaining

---

### Step 5b: M8 Concept Test Simulation (Standalone)
- [x] Standalone script: `scripts/step5_m8_simulation.py` — hardcodes M8 questionnaire (no SDE dependency)
- [x] 64 questions from M8 Concept Test PDF across 7 sections
- [x] Same batched inference engine as Step 5 (ChromaDB/KG persistence, LLM logging)
- [x] Question types: single_select, multi_select, scale, matrix_scale, rank_order, numeric, open_text
- [x] Answer label resolution: CSV maps raw values to human-readable labels per question
- [x] LLM log export: `scripts/export_llm_log_pdf.py` for formatted PDF of all prompts/responses
- [x] Run for P01_T001 with combined mode — COMPLETE

**M8 Questionnaire Structure** (64 questions):
- Category Screening: 4 questions (usage frequency, brands, satisfaction, improvements)
- Concept 1-5 evaluation blocks: ~12 questions each (interest, appeal, improve, routine fit, time saving, purchase intent, uniqueness, relevance, believability, brand fit, paired characteristics matrix, concerns)
- Comparative & Pricing: 4 questions (importance factors matrix, concept ranking, purchase likelihood, expected price)

**Concepts**:
1. Dove 60-Second Body Spray — clean in 60 seconds, minimal rinsing
2. Dove Skip — 12-hour moisturized skin, no body lotion needed
3. Dove Night Wash — calming ritual for evening shower, helps sleep
4. Dove Yours & Mine — partner scent connection
5. Dove Skin ID — custom body wash for unique skin needs

**CLI**:
```bash
python scripts/step5_m8_simulation.py \
  --twins P01_T001 \
  --mode combined --batch-size 8
```

**Run Results (P01_T001, Opus 4.6, combined mode)**:
- 64/64 questions answered, 0 skipped
- 12 batches (4 single_select, 1 multi_select, 2 open_text, 2 scale, 1 matrix_scale, 1 rank_order, 1 numeric)
- Total runtime: 343s (~5.7 min), including KG extraction
- ChromaDB: 64 survey answers persisted (7,142 + 64 = 7,206 entries)
- KG: 30 new traits extracted, graph grew from 75→103 nodes, 166→236 edges
- LLM log: JSONL with all prompts/responses/timing

**Output Files**:
- `data/output/step5_m8_simulation/m8_simulation_results.json` — Full JSON results
- `data/output/step5_m8_simulation/m8_llm_log_P01_T001_*.jsonl` — LLM call log
- `data/output/step5_m8_simulation/m8_qa_responses.csv` — Structured CSV (Section, Q ID, Question, Value, Label, Reasoning)

**Status**: M8 SIMULATION COMPLETE for P01_T001 — benchmarking remaining

---

## Change Log

| Date | Change |
|------|--------|
| 2026-03-03 | Repository created. Step 2 branching/pruning script built. |
| 2026-03-03 | Context corrected: audience 20-30, male+female, body wash category. |
| 2026-03-03 | Step 1 question bank generator script + prompt created. |
| 2026-03-03 | CRITICAL FIX: Branching must be on uncaptured dimensions, not existing ones. Step 2 prompts flagged for rework. |
| 2026-03-03 | Step 1 COMPLETE: 350-question bank generated. |
| 2026-03-03 | Exploration script run with Opus 4.6 for P01+P02 dimension/archetype validation. |
| 2026-03-03 | Step 1 REGENERATED with Opus 4.6 (was Sonnet). All 350 questions regenerated. |
| 2026-03-03 | Step 2 COMPLETE: Prompts reworked, pipeline run for P01+P02. 200 twin profiles selected (100 each). |
| 2026-03-03 | Step 3 SCRIPT BUILT: Batch-25 expansion pipeline, prune 100→20, resume support. |
| 2026-03-03 | Step 3 P01 COMPLETE: 20 twins × 353 QA, 7055 total pairs, 0 failures. Model: Sonnet 4 (Opus overloaded). 162 min runtime. |
| 2026-03-04 | Step 4 CODE COMPLETE: Vector index builder, KG builder, 3-mode inference CLI with interactive REPL. |
| 2026-03-04 | Step 4 REWRITE: Switched to ChromaDB + local sentence-transformers (free). Improved prompts based on research papers (ID-RAG, SSR, Li et al.). Vector index built: 7,055 entries, 78s, $0. |
| 2026-03-04 | Step 3 P02 COMPLETE: 20 twins × 353 QA, 7060 total pairs, 0 failures. Model: Opus 4.6, 5-parallel. 52.8 min runtime. Total: 40 twins, 14,115 QA pairs across P01+P02. |
| 2026-03-06 | Step 5 CODE COMPLETE: Batched survey simulation with ChromaDB/KG persistence, LLM logging, concept expansion (24 template → 87 answerable questions), type-aware response parsing. |
| 2026-03-06 | Step 4 KG built for P01_T001: 33 traits, 45 nodes, 90 edges. Fixed max_tokens 8192→16000 for trait extraction (was truncating). |
| 2026-03-06 | Step 5 FIRST RUN COMPLETE: P01_T001, 87/87 answered, 12 batches, 393s, combined mode. KG grew to 75 nodes/166 edges. |
| 2026-03-06 | Step 5b M8 standalone script built: 64 hardcoded questions from M8 Concept Test PDF, no SDE dependency. Same inference engine. |
| 2026-03-06 | Step 5b M8 RUN COMPLETE: P01_T001, 64/64 answered, 12 batches, 343s, combined mode. KG grew to 103 nodes/236 edges. |
| 2026-03-06 | LLM log PDF export utility created: `scripts/export_llm_log_pdf.py` — converts JSONL log to formatted PDF with prompts/responses. |
