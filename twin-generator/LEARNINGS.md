# Twin Generator — Learnings & Mistakes Log

This file tracks mistakes made during development, root causes, and fixes applied so they are never repeated.

---

## Format

Each entry follows:
```
### [Date] — Short title
**What went wrong**: ...
**Root cause**: ...
**Fix applied**: ...
**Rule going forward**: ...
```

---

## Learnings from Study Design Engine (carried over)

### JSON Extraction from LLM Output
**What went wrong**: LLM sometimes returns JSON wrapped in markdown code fences or with trailing commas.
**Fix applied**: Always use robust JSON extraction — strip code fences, handle trailing commas, use brace-matching to find valid JSON.
**Rule going forward**: Never do `json.loads(raw_response)` directly. Always clean/extract first.

### LLM Max Tokens
**What went wrong**: Truncated responses when max_tokens was too low for large outputs.
**Fix applied**: Use generous max_tokens (16000+) for generation tasks. Better to over-allocate than get truncated JSON.
**Rule going forward**: Set max_tokens based on expected output size, not a default.

### Optional Fields in LLM-Generated Schemas
**What went wrong**: LLM doesn't always return all expected fields in structured output.
**Fix applied**: Make non-critical fields Optional in Pydantic schemas. Validate only the essentials.
**Rule going forward**: When parsing LLM output into a schema, be permissive — use Optional for anything the LLM might skip.

---

## Twin Generator Specific Learnings

### 2026-03-03 — Branching must be on UNCAPTURED dimensions, not existing ones
**What went wrong**: Initial Step 2 prompt asked the LLM to "find 5 dimensions where people with this profile would most consequentially diverge" — looking at the person's answers to decide where to branch. This would branch on dimensions the 59 questions already cover (e.g., price sensitivity), creating different personas instead of twins of the same person.
**Root cause**: Confused "where do consumers differ" with "where is our knowledge of THIS person incomplete." The 59 answers are ground truth — twins must share them. Branching must happen on dimensions the 59 questions NEVER asked about.
**Fix applied**: Updated PLAN.md with Core Principle section. Step 2 prompt and logic need rework to: (1) identify what the 59 questions DO cover, (2) find dimensions OUTSIDE that coverage, (3) branch only on uncaptured dimensions, (4) select branching Qs only from the 291 new questions.
**Rule going forward**: The 59 real answers are LOCKED per twin. Branching = exploring uncertainty in unmeasured dimensions. Never branch on something the interview already captured.

### 2026-03-03 — CSV BOM causes KeyError on column names
**What went wrong**: `questions.csv` had a UTF-8 BOM (`\xef\xbb\xbf`), making the first column header `\ufeffmodule_id` instead of `module_id`. `csv.DictReader` couldn't find the expected key.
**Root cause**: File was saved from Excel/Google Sheets with BOM encoding.
**Fix applied**: Changed `encoding="utf-8"` to `encoding="utf-8-sig"` which auto-strips BOM.
**Rule going forward**: Always use `utf-8-sig` encoding when reading CSVs that may come from Excel.

### 2026-03-03 — Batch generation skip-on-failure loses questions
**What went wrong**: When LLM batch 1 for Information-Seeking Behavior returned a non-list, the code decremented `remaining` by `batch_size` (30), losing those questions entirely. Domain ended up with 29/59.
**Root cause**: Failure fallback skipped the batch instead of retrying.
**Fix applied**: Added retry counter (up to 2 retries) before skipping. Also created `backfill_questions.py` for targeted domain backfill.
**Rule going forward**: On LLM batch failure, retry at least twice before skipping. Always verify final counts match targets.

### 2026-03-03 — Dimension identification must be framed around use cases
**What went wrong**: Initial dimension prompt asked for "dimensions where people would diverge on body wash behavior" — too generic. Produced dimensions like "scent layering" and "travel routine flexibility" that are interesting but don't directly predict different responses to product concepts or ad campaigns.
**Root cause**: Didn't anchor the dimension search to the actual use cases for these digital twins (concept validation + ad campaign testing).
**Fix applied**: Rewrote prompt to explicitly frame around "what dimensions would cause different responses when shown a body wash concept or ad campaign." Added concept_test_impact and ad_test_impact fields to both dimensions and archetypes.
**Rule going forward**: Always anchor dimension identification to the downstream use case. The twins exist to predict concept/ad responses — every branching dimension must create measurable variation in those predictions.

### 2026-03-03 — Use Opus 4.6 for all LLM calls, not Sonnet
**What went wrong**: Default model was set to Sonnet. For a pipeline that generates consumer psychology insights and nuanced behavioral archetypes, the quality gap matters.
**Fix applied**: Changed default in config/settings.py and .env.example to `anthropic/claude-opus-4-6`.
**Rule going forward**: All twin-generator LLM calls use Opus 4.6. Only downgrade to Sonnet/Haiku for high-volume low-stakes calls if cost becomes an issue.

### 2026-03-03 — Regenerate all dependent outputs when model changes
**What went wrong**: Step 1 question bank was generated with Sonnet. After switching to Opus 4.6, the question bank quality was inconsistent with the rest of the pipeline.
**Root cause**: Changing the model mid-pipeline creates a quality mismatch between steps. Earlier steps produce inputs that downstream steps build on.
**Fix applied**: Fully regenerated the 350-question bank with Opus 4.6 before running Step 2.
**Rule going forward**: When the LLM model changes, regenerate ALL pipeline outputs from scratch. Don't build new steps on top of outputs from a different model.

### 2026-03-03 — Resume support is essential for multi-participant pipelines
**What went wrong**: During exploration, API credits ran out mid-P02. Without resume support, the entire pipeline would need to re-run from scratch, including the already-completed P01.
**Root cause**: Long-running pipelines with external API dependencies will inevitably hit interruptions (rate limits, credit exhaustion, network errors).
**Fix applied**: Added resume logic to both explore_dimensions.py and step2_branching.py — saves results after each participant, loads existing results on startup, skips already-completed participant IDs.
**Rule going forward**: Every pipeline script that processes multiple participants must save intermediate results and support resume. Never assume a multi-hour pipeline will complete uninterrupted.

### 2026-03-03 — Contradiction rate varies significantly by participant profile
**What went wrong**: Not a bug, but an important observation. P01 had 86/243 (35%) contradictory combinations while P02 had only 39/243 (16%).
**Root cause**: P01's dimensions (social signaling + masculinity framing + aspirational vs authentic tolerance) have more natural tensions between archetype positions. P02's dimensions were more independent of each other.
**Implication**: The pruning step genuinely differentiates quality — it's not just rubber-stamping all combinations. The contradiction rate is a useful diagnostic metric per participant. If contradiction rate is very low (<10%), the dimensions may be too independent/uninteresting. If very high (>50%), the dimensions may be too correlated or the archetypes poorly designed.
**Rule going forward**: Monitor contradiction rate as a quality signal. Expect 15-40% range for well-chosen dimensions.

### 2026-03-03 — Filter question bank to source=="generated" for branching candidates
**What went wrong**: Initial Step 2 code passed the full 350-question bank to the archetype generation prompt, including the original 59 questions. This risks selecting a branching question from the original 59, which would branch on an already-captured dimension.
**Root cause**: The Core Principle says branching must only happen on uncaptured dimensions, so branching questions must come from the 291 NEW questions only.
**Fix applied**: Added filter `new_qs = [q for q in question_bank if q.get("source") == "generated"]` before passing candidates to the archetype prompt.
**Rule going forward**: When selecting branching questions, always filter to `source == "generated"`. The original 59 questions are locked truth and must never be used as branching points.

### 2026-03-03 — Direct context beats Vector RAG when context fits in window
**Scenario**: Step 3 needs to generate 289 answers per twin, conditioned on a 64 Q&A profile.
**Analysis**: Full 64 Q&A context is only ~3,900 tokens — trivially fits in any model's context window. RAG would retrieve partial context per question (5-10 fragments), risking contradictions and losing holistic coherence. Direct context ensures the LLM sees the complete person.
**Decision**: No Vector RAG. Direct in-context learning with full profile.
**Rule going forward**: Only use RAG when the knowledge base exceeds the context window. For profiles under ~10K tokens, always use direct context.

### 2026-03-03 — Batch-25 is the sweet spot for answer generation
**Analysis**: Compared one-by-one (57K calls, massive token waste), batch-10 (5.8K calls), batch-25 (2.4K calls), batch-50 (1.2K calls, quality risk), and one-shot (200 calls, severe quality degradation).
**Decision**: Batch-25 keeps output at ~1,500 tokens (well within quality range), amortizes the 3,900-token context across 25 questions, and costs ~$15 Opus for 20 twins.
**Rule going forward**: For multi-answer generation, batch size should keep output under 2,000 tokens. Beyond that, later answers start to degrade in quality.

### 2026-03-03 — Synthetic answer style: no filler words, think-before-answering
**What matters**: LLMs default to verbose, hedging language ("I think", "well", "basically"). Real interview answers are direct and compressed. If synthetic answers have different texture than real ones, downstream models will learn the wrong signal.
**Fix applied**: Prompt explicitly instructs: (1) think through profile before each answer (internal reasoning), (2) no filler words, (3) match the tone/length/specificity of existing answers.
**Rule going forward**: When generating synthetic data that must match real data style, always specify anti-patterns (filler words, hedging) and provide explicit style anchoring to the real examples.

### 2026-03-03 — LLM max_tokens must account for echoed content, not just answers
**What went wrong**: Set `LLM_MAX_TOKENS_STEP3=4096` expecting 25 answers × ~60 tokens = 1,500 tokens. But the LLM echoed back full question text (including multi-choice options) in each JSON object, pushing output to 4K+ tokens. The response got truncated, `extract_json` found only the first `{...}` object, and `generate_batch` got a dict instead of a list.
**Fix applied**: (1) Increased max_tokens to 8192. (2) Updated prompt to say "do NOT echo back the question_text" — reduces output by ~60%. (3) Added dict-unwrap logic as fallback.
**Rule going forward**: When estimating max_tokens, check what the LLM actually returns (not what you asked for). If the prompt asks for structured output with fields that could be verbose, either suppress those fields or double the estimate.

### 2026-03-03 — Backfill pattern for failed batch answers
**What went wrong**: Transient API errors (529 overloaded, 500 internal) caused 89/7055 answers to fail as `[GENERATION_FAILED]` placeholders, concentrated in 2 twins.
**Fix applied**: Wrote a targeted backfill that loads the output, finds `[GENERATION_FAILED]` markers, re-batches those questions, calls the LLM, and patches the results back in. All 89 recovered successfully.
**Rule going forward**: Design pipelines with a backfill step. Use sentinel values (`[GENERATION_FAILED]`) instead of skipping failed items entirely — sentinels are easy to find and patch later.

### 2026-03-03 — Use lower temperature for evaluation vs generation tasks
**What went wrong**: Not a bug, but a deliberate design choice worth documenting.
**Rationale**: Dimension identification and archetype generation benefit from creativity (temperature 0.5) — we want the LLM to think broadly about uncaptured behavioral territory. But coherence evaluation needs consistency (temperature 0.3) — we want reliable, reproducible scores so the pruning step produces stable results.
**Rule going forward**: Generation tasks: temperature 0.5. Evaluation/scoring tasks: temperature 0.3. Never use high temperature for tasks that require consistent quantitative outputs.

---

## Step 4: Inference Layer Learnings

### 2026-03-04 — Use free local embeddings, not paid API, when quality is equivalent
**What went wrong**: Initial implementation used Voyage AI (`voyage-3-lite`) for embeddings — a paid API call ($0.02/M tokens). This adds cost, latency, and an external dependency for no meaningful quality gain at our scale.
**Root cause**: Defaulted to a "fancier" embedding model without checking whether a free local alternative was sufficient. The SSR paper (arXiv, Oct 2025) validated that sentence-transformer embeddings produce "statistically almost indistinguishable" results from human panel data — specifically on personal care products, our exact domain.
**Fix applied**: Switched to `all-MiniLM-L6-v2` via sentence-transformers. Runs locally, 384 dims, zero cost. 7,055 Q&A pairs indexed in ~78 seconds.
**Rule going forward**: For embedding tasks under ~100K documents, always start with free local models (sentence-transformers). Only upgrade to paid APIs if retrieval quality measurably suffers on your benchmark. At our scale (7K-700K pairs), local models are fast enough and accurate enough.

### 2026-03-04 — Use ChromaDB, not raw numpy, for vector storage
**What went wrong**: Initial implementation used raw numpy arrays + manual cosine similarity + .npz serialization. This required ~100 lines of custom code for what ChromaDB provides out of the box.
**Root cause**: Over-optimized for "no dependencies" when the dependency (ChromaDB) is trivial (`pip install chromadb`) and provides metadata filtering, persistent storage, and auto-embedding — all things we'd need to build manually.
**Fix applied**: Switched to ChromaDB with persistent SQLite backend. Metadata filtering by `twin_id`, `source`, `module_id` works natively via `where={"twin_id": "P01_T003"}`. Eliminated all custom search/serialization code.
**Rule going forward**: At 7K-1M vectors, use ChromaDB (MVP) or pgvector (if already running Postgres). Only go to raw numpy/FAISS if you need sub-microsecond search or custom distance functions. The own research doc recommends ChromaDB for pilot phase — follow it.

### 2026-03-04 — Anchor prompts in research, not intuition
**What went wrong**: Initial synthesis prompt was generic: "Based on this person's actual responses, answer the question concisely." This misses structural patterns validated by research papers.
**Root cause**: Wrote the prompt from scratch instead of studying how validated systems (ID-RAG, Li et al., Park et al.) structure their prompts.
**Fix applied**: Rewrote both prompts based on research findings:
- **Synthesis prompt**: Added ID-RAG-style identity anchoring (non-negotiable persona traits listed before evidence), Li et al.-style category context (Indian body wash market with price tiers, brands, channels), and a 4-step reasoning protocol with explicit source priority (real > branch > synthetic).
- **Trait extraction prompt**: Added confidence calibration rubric (0.9+ for 3+ REAL answers, 0.5-0.69 for synthetic-only), evidence quotes with source tags, predictive value per trait ("When shown [concept], this person would likely..."), and identity summary for quick anchoring.
**Rule going forward**: Before writing any LLM prompt, check if published research has validated a structure for that task. Specifically: (1) ID-RAG for persona consistency, (2) SSR for Likert-scale prediction, (3) Li et al. for consumer RAG, (4) Park et al. for interview-based agents. Anchor every prompt in a paper, not guesswork.

### 2026-03-04 — Question every LLM call: is there a non-LLM alternative?
**Observation**: When building the inference layer, three tasks defaulted to LLM calls that deserve scrutiny:
1. **Embeddings** — Switched to free local model. No LLM needed.
2. **KG trait extraction** — Could potentially be done rule-based using `behavioral_signals` metadata from question_bank.json. Kept Opus for nuance but the rule-based alternative exists as a $0 fallback.
3. **Domain classification at query time** — Could be done via keyword matching or a lightweight classifier. Kept Opus for accuracy.
**Rule going forward**: For every LLM call in the pipeline, ask: "Is there a non-LLM way to do this?" If yes, evaluate the quality tradeoff. Use the LLM only where its reasoning genuinely adds value (trait extraction, synthesis), not where simple heuristics suffice (embedding, classification).

### 2026-03-04 — Parallel twin processing via asyncio.gather with existing semaphore
**Scenario**: Step 3 processes 20 twins sequentially (P01 took 162 min). Need to speed up P02.
**Solution**: Process 5 twins in parallel using `asyncio.gather()`. Each twin's `expand_twin()` runs its 12 LLM batches sequentially, but 5 twins interleave through the existing `asyncio.Semaphore(5)` in `llm_utils.py`. Net effect: always 5 LLM calls in flight.
**Result**: P02 completed in 52.8 min (3.2x faster than P01's sequential 162 min). Would have been faster without rate limits.
**Key insight**: No changes needed to `llm_utils.py` — the semaphore already controlled concurrency perfectly. Just needed to launch multiple coroutines at the twin level.
**Rule going forward**: When parallelizing pipeline steps, check if the existing concurrency control (semaphore, rate limiter) already handles the coordination. Don't add a second layer of concurrency control.

### 2026-03-04 — Opus 4.6 rate limits are much tighter than Sonnet
**What happened**: P02 run with Opus 4.6 hit constant 429s — 30,000 input tokens/min and 8,000 output tokens/min. With 5 parallel twins each sending ~6,500 input tokens per call, the first 5 calls (~32K tokens) immediately exceed the input limit. Output limit is even tighter — 8K tokens/min means ~5 responses/min at ~1,500 tokens each.
**Impact**: The 5-retry exponential backoff (5s → 10s → 20s → 40s → 80s) handled it, but effective throughput was ~2-3 calls/min instead of the 5 concurrent calls we wanted. Runtime was 52.8 min vs the optimistic 32 min estimate.
**Rule going forward**: When using Opus 4.6 via API, expect 30K input / 8K output TPM limits. For batch workloads, the output token limit is usually the binding constraint. Effective parallelism with Opus is ~2-3 concurrent calls, not 5. Consider reducing `STEP3_PARALLEL_TWINS` to 3 for Opus, or use `LLM_MAX_CONCURRENT=3` to reduce wasted retry cycles.

### 2026-03-04 — Save after parallel batch, not after each twin, for parallel processing
**What changed**: Sequential mode saved after each twin (20 saves per participant). Parallel mode saves after each batch of 5 twins (4 saves per participant). Resume still works at twin granularity because `completed_twin_ids` is checked on startup.
**Trade-off**: If the process crashes mid-batch, up to 5 twins' work is lost (vs 1 in sequential mode). But with 5 twins × 12 batches × ~40s each = ~8 min per parallel batch, the risk window is small.
**Rule going forward**: For parallel processing, save after the `asyncio.gather` completes, not inside individual coroutines. Concurrent file writes from multiple coroutines can corrupt the output file.

### 2026-03-04 — Research doc exists — read it before implementing
**What went wrong**: Built the initial implementation without reading `research_papers_vectordb_knowledgegraphs.docx`, which already recommended ChromaDB for MVP, sentence-transformers for embeddings, and NetworkX for KG.
**Root cause**: Jumped to implementation before reading all available docs in the repository.
**Fix applied**: Read the doc, aligned implementation with its recommendations.
**Rule going forward**: Before starting any new pipeline step, search the repo for relevant docs (`.docx`, `.md`, `.pdf`). The research doc was sitting in the project root the entire time.

---

## Step 5: Survey Simulation Learnings

### 2026-03-06 — Batch by question type for LLM consistency
**Scenario**: Survey questions have different answer formats (single_select, rating, open_text, ranking). Mixing types in a single LLM batch causes format confusion — the LLM might return a number for a text question or a paragraph for a rating question.
**Solution**: Group questions by `question_type` before batching. Each batch contains only one type, so the LLM can lock into a consistent response format. This also simplifies parsing — each batch uses one parse path.
**Rule going forward**: When batching structured questions to an LLM, always group by expected output format. Never mix rating + open_text + single_select in the same batch.

### 2026-03-06 — Persistent memory creates a virtuous consistency loop
**Observation**: Writing each batch's answers to ChromaDB before processing the next batch means later batches can retrieve earlier survey answers as evidence. This creates a feedback loop: the twin's answers to "How often do you shower?" (batch 1) become evidence when answering "What body wash features matter most?" (batch 5).
**Impact**: Without this, each batch is answered in isolation based only on the original 353 Q&A profile. With it, the twin builds a coherent survey narrative where later answers are informed by earlier ones — just like a real respondent whose mindset evolves during a survey.
**Rule going forward**: For multi-batch simulation, always persist intermediate results to the retrieval layer between batches. The consistency gain is worth the ~5ms ChromaDB write per batch.

### 2026-03-06 — SDE stores concept templates, not expanded questionnaires
**What went wrong**: The SDE questionnaire API returns 24 template questions where concept-dependent sections (S3, S4, S5, S7) reference a single concept. With 5 concepts, the actual survey is ~92 questions. Passing the raw 24 questions to the simulation would only test 1 concept.
**Root cause**: The SDE is designed for human respondents who see one concept at a time via a survey tool that handles rotation. The simulation bridge needs to expand templates into per-concept questions.
**Fix applied**: Added `expand_questionnaire()` that clones concept-dependent sections for each concept (C1-C5), generating unique question_ids (e.g., Q10_C1, Q10_C2) and section names (e.g., S3_concept_exposure_concept_1). Skips concept_exposure instruction questions (not answerable). Replaces hardcoded concept names in question text with the target concept's name.
**Rule going forward**: When bridging between a survey design tool and a simulation engine, always check whether the questionnaire is a template or a fully expanded survey. Templates need expansion before simulation.

### 2026-03-06 — KG trait extraction needs 16K+ tokens, not 8K
**What went wrong**: `LLM_MAX_TOKENS_KG_EXTRACT` was set to 8192. With 353 Q&A pairs and 33 traits (each with evidence quotes, confidence scores, predictive values), the output consistently exceeded 8K tokens. All 5 retry attempts were truncated, producing invalid JSON.
**Root cause**: The initial estimate assumed ~200 tokens per trait × 35 traits = 7K tokens. But each trait also has an evidence quote (~30 tokens), predictive value (~40 tokens), and the identity_summary (~200 tokens), pushing total to ~12K.
**Fix applied**: Increased `LLM_MAX_TOKENS_KG_EXTRACT` default to 16000 in config/settings.py.
**Rule going forward**: For structured JSON outputs with many nested objects, estimate total tokens as: (fields_per_object × avg_tokens_per_field × object_count) + overhead. Then add 50% buffer.

### 2026-03-06 — Duplicate question_ids across SDE sections require disambiguation
**What went wrong**: The SDE questionnaire had Q12 in both S3_concept_exposure and S4_core_kpi (different questions, same ID). After concept expansion, `Q12_C1` appeared twice, causing ChromaDB `DuplicateIDError` when persisting answers.
**Root cause**: SDE question_ids are unique within a section but not globally. The expansion function used only question_id as the base, not section+question_id.
**Fix applied**: Added duplicate detection: if any question_id appears in multiple sections, the expanded ID includes a section prefix (e.g., `S3_Q12_C1`, `S4_Q12_C1`).
**Rule going forward**: Never assume IDs from external systems are globally unique. Always check for duplicates before using them as keys, especially after expansion/cloning operations.

### 2026-03-06 — Standalone questionnaire scripts avoid SDE coupling issues
**Scenario**: The SDE-based simulation (step5_survey_simulation.py) depends on the SDE API being running, handles template expansion, and deals with question_id collisions across sections. For M8 Concept Test validation, we needed to bypass all of this.
**Solution**: Created `step5_m8_simulation.py` with the full 64-question M8 questionnaire hardcoded in Python. No SDE dependency, no expansion logic, no duplicate ID issues. Each question has its own unique ID (M8_q01 through M8_q82), options, scales, and matrix items embedded directly.
**Benefit**: Faster iteration (no server startup), no ID collision bugs, questions exactly match the PDF, and answer label resolution is trivially correct because each question carries its own options/scale.
**Rule going forward**: When validating against a specific paper questionnaire, hardcode it in a standalone script rather than routing through a design tool's API. The indirection adds bugs without value for single-questionnaire runs.

### 2026-03-06 — fpdf2 Unicode encoding requires explicit ASCII fallback
**What went wrong**: Generating a PDF from LLM log responses failed with encoding errors. LLM output contained Unicode characters (em dash \u2014, smart quotes \u201c/\u201d, rupee sign \u20b9, bullet \u2022) that fpdf2's built-in Helvetica/Courier fonts can't render.
**Root cause**: fpdf2 uses Latin-1 encoding for built-in fonts. Any character outside Latin-1 causes an error.
**Fix applied**: Created `safe_text()` function with explicit Unicode→ASCII replacement map (em dash→--, smart quotes→", rupee→Rs., bullet→*, etc.) plus a final `encode("latin-1", errors="replace").decode("latin-1")` safety net. Function must be defined BEFORE any class that calls it in `header()`/`footer()`.
**Rule going forward**: When generating PDFs from LLM output, always sanitize text before rendering. LLMs produce Unicode freely. Either use a Unicode-capable font (TTF) or strip to ASCII with meaningful replacements.

### 2026-03-06 — Answer label resolution must be embedded with the question, not looked up externally
**What went wrong**: The SDE-based CSV export tried to resolve answer values (e.g., "4") to labels (e.g., "Very likely") by fetching option metadata from the SDE API. But duplicate question_ids (Q14 in both S3 and S4) caused wrong label lookups — a time-saving question showed "Very unique" because the lookup found the S4 uniqueness question's scale instead.
**Root cause**: Resolving labels via a separate lookup table breaks when IDs collide. The label must travel with the question, not be resolved after the fact.
**Fix applied**: In the M8 standalone script, each question dict carries its own `options` and `scale` with full labels. `resolve_answer_label()` operates on the question's own metadata, so there's zero ambiguity — every question knows its own answer space.
**Rule going forward**: For structured survey simulations, keep answer options/scales co-located with the question throughout the pipeline. Never resolve labels via a separate lookup that requires globally unique IDs.
