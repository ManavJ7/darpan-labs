"""
Step 3: ICL Profile Expansion — Batch-25 Answer Generation

For each pruned twin (top 20 per participant by coherence + diversity),
generate answers to all remaining questions from the 350-question bank.

Each twin has 64 existing Q&A pairs (59 real + 5 branch). This script
generates answers for the ~289 unanswered questions via in-context learning,
sending 25 questions per LLM call with the full 64-answer profile as context.

Input:
  - data/output/step2_pruned_twins.json  — 100 twins per participant
  - data/input/real_qa_pairs.json        — 59 real Q&A per participant
  - data/input/question_bank.json        — 350-question bank

Output:
  - data/output/step2_pruned_twins_20.json  — 20 re-selected twins per participant
  - data/output/step3_complete_profiles.json — 20 twins × 350 Q&A each
"""
import asyncio
import json
import logging
import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import (
    INPUT_DIR,
    OUTPUT_DIR,
    PROMPTS_DIR,
    TARGET_TWINS_STEP3,
    STEP3_BATCH_SIZE,
    LLM_MAX_TOKENS_STEP3,
    STEP3_PARALLEL_TWINS,
    Q_BRANCH,
    LLM_GENERATION_MODEL,
)
from scripts.llm_utils import call_llm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("step3_expansion")


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_pruned_twins() -> list[dict]:
    path = OUTPUT_DIR / "step2_pruned_twins.json"
    if not path.exists():
        raise FileNotFoundError(f"Pruned twins not found at {path}")
    with open(path) as f:
        data = json.load(f)
    logger.info(f"Loaded twins for {len(data)} participants")
    return data


def load_real_qa_pairs() -> dict[str, list[dict]]:
    """Returns {participant_id: [qa_pairs]}."""
    path = INPUT_DIR / "real_qa_pairs.json"
    with open(path) as f:
        data = json.load(f)
    return {p["participant_id"]: p["qa_pairs"] for p in data}


def load_question_bank() -> list[dict]:
    path = INPUT_DIR / "question_bank.json"
    with open(path) as f:
        return json.load(f)


def load_prompt(filename: str) -> str:
    path = PROMPTS_DIR / filename
    with open(path) as f:
        return f.read()


# ---------------------------------------------------------------------------
# Pre-step: Prune 100 → 20 twins using coherence + diversity
# ---------------------------------------------------------------------------

def _count_dimension_diffs(choices_a: dict, choices_b: dict) -> int:
    return sum(1 for k in choices_a if choices_a.get(k) != choices_b.get(k))


def select_diverse_subset(twins: list[dict], target: int) -> list[dict]:
    """
    From coherence-sorted twins, select `target` maximizing diversity.
    Same algorithm as step2 but re-applied to pick top 20 from 100.
    """
    if len(twins) <= target:
        return twins

    # Sort by coherence descending
    ranked = sorted(twins, key=lambda t: t["coherence_score"], reverse=True)

    selected = [ranked[0]]
    remaining = ranked[1:]

    while len(selected) < target and remaining:
        best_idx = 0
        best_score = -1.0

        for idx, candidate in enumerate(remaining):
            min_diff = min(
                _count_dimension_diffs(candidate["choices"], sel["choices"])
                for sel in selected
            )
            combined = candidate["coherence_score"] * 0.6 + (min_diff / Q_BRANCH) * 0.4
            if combined > best_score:
                best_score = combined
                best_idx = idx

        selected.append(remaining.pop(best_idx))

    return selected


def prune_twins(all_participants_data: list[dict], target: int) -> list[dict]:
    """Prune each participant's twins from 100 → target using diversity selection."""
    pruned = []
    for p_data in all_participants_data:
        pid = p_data["participant_id"]
        twins = p_data["twins"]
        selected = select_diverse_subset(twins, target)

        # Re-number twin IDs
        for idx, twin in enumerate(selected, 1):
            twin["twin_id"] = f"{pid}_T{idx:03d}"

        pruned.append({
            "participant_id": pid,
            "n_original": len(twins),
            "n_selected": len(selected),
            "twins": selected,
        })
        logger.info(
            f"[{pid}] Pruned {len(twins)} → {len(selected)} twins "
            f"(coherence: {selected[-1]['coherence_score']:.2f} - {selected[0]['coherence_score']:.2f})"
        )
    return pruned


# ---------------------------------------------------------------------------
# Build context and identify unanswered questions
# ---------------------------------------------------------------------------

def build_qa_context(real_qa: list[dict], branch_answers: list[dict]) -> str:
    """Format 64 Q&A pairs (59 real + 5 branch) as context string."""
    lines = []
    for i, qa in enumerate(real_qa, 1):
        lines.append(f"Q{i}: {qa['question_text']}")
        lines.append(f"A{i}: {qa['answer_text']}")
        lines.append("")

    offset = len(real_qa)
    for j, ba in enumerate(branch_answers, 1):
        n = offset + j
        lines.append(f"Q{n}: {ba['question_text']}")
        lines.append(f"A{n}: {ba['answer_text']}")
        lines.append("")

    return "\n".join(lines)


def get_unanswered_questions(
    question_bank: list[dict],
    branch_texts: set[str],
) -> list[dict]:
    """
    Return generated questions from the bank that are NOT branch questions.
    Existing questions (source=existing) are already covered by real QA pairs.
    """
    unanswered = []
    for q in question_bank:
        if q.get("source") == "existing":
            continue
        if q["question_text"] in branch_texts:
            continue
        unanswered.append(q)
    return unanswered


def format_questions_block(questions: list[dict]) -> str:
    """Format a batch of questions for the prompt."""
    lines = []
    for i, q in enumerate(questions, 1):
        lines.append(f"{i}. [{q['question_id']}] {q['question_text']}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# LLM call for a batch of questions
# ---------------------------------------------------------------------------

async def generate_batch(
    qa_context: str,
    questions_batch: list[dict],
    prompt_template: str,
    participant_id: str = "default",
) -> list[dict]:
    """
    Generate answers for a batch of questions using ICL.
    Returns list of {question_id, question_text, answer_text}.
    """
    questions_block = format_questions_block(questions_batch)
    n_questions = len(questions_batch)

    prompt = (
        prompt_template
        .replace("{qa_context}", qa_context)
        .replace("{questions_block}", questions_block)
        .replace("{n_questions}", str(n_questions))
    )

    result = await call_llm(
        prompt=prompt,
        max_tokens=LLM_MAX_TOKENS_STEP3,
        temperature=0.5,
        model=LLM_GENERATION_MODEL,
        participant_id=participant_id,
    )

    # LLM sometimes wraps array in a dict — unwrap it
    if isinstance(result, dict):
        for key in ("answers", "responses", "results", "data"):
            if key in result and isinstance(result[key], list):
                result = result[key]
                break
        else:
            # Try the first list value in the dict
            for v in result.values():
                if isinstance(v, list):
                    result = v
                    break

    if not isinstance(result, list):
        raise ValueError(f"Expected list from LLM, got {type(result)}")

    # Build lookup for question_text from batch data
    batch_lookup = {q["question_id"]: q["question_text"] for q in questions_batch}
    expected_ids = set(batch_lookup.keys())

    # Validate and fill in missing fields
    for i, item in enumerate(result):
        if "answer_text" not in item or not item["answer_text"]:
            raise ValueError(f"Missing answer_text for item {i}")
        # Fix question_id if missing or wrong
        if item.get("question_id") not in expected_ids and i < len(questions_batch):
            item["question_id"] = questions_batch[i]["question_id"]
        # Always fill in question_text from our data (LLM may omit it)
        qid = item.get("question_id", "")
        item["question_text"] = batch_lookup.get(qid, questions_batch[i]["question_text"] if i < len(questions_batch) else "")

    return result


# ---------------------------------------------------------------------------
# Process a single twin
# ---------------------------------------------------------------------------

async def expand_twin(
    twin: dict,
    real_qa: list[dict],
    unanswered_questions: list[dict],
    prompt_template: str,
    participant_id: str = "default",
) -> dict:
    """
    Generate all synthetic answers for one twin.
    Returns complete profile with 350 Q&A pairs.
    """
    twin_id = twin["twin_id"]
    branch_answers = twin["branch_answers"]

    # Build 64 Q&A context
    qa_context = build_qa_context(real_qa, branch_answers)

    # Split unanswered questions into batches
    batches = [
        unanswered_questions[i:i + STEP3_BATCH_SIZE]
        for i in range(0, len(unanswered_questions), STEP3_BATCH_SIZE)
    ]
    n_batches = len(batches)
    logger.info(f"  [{twin_id}] {len(unanswered_questions)} questions in {n_batches} batches")

    synthetic_answers = []
    for batch_idx, batch in enumerate(batches):
        for attempt in range(3):
            try:
                answers = await generate_batch(qa_context, batch, prompt_template, participant_id=participant_id)
                synthetic_answers.extend(answers)
                break
            except Exception as e:
                if attempt < 2:
                    logger.warning(
                        f"  [{twin_id}] Batch {batch_idx + 1}/{n_batches} failed "
                        f"(attempt {attempt + 1}/3): {e}"
                    )
                    await asyncio.sleep(5 * (attempt + 1))
                else:
                    logger.error(
                        f"  [{twin_id}] Batch {batch_idx + 1}/{n_batches} failed after 3 attempts: {e}"
                    )
                    # Add placeholders for failed batch
                    for q in batch:
                        synthetic_answers.append({
                            "question_id": q["question_id"],
                            "question_text": q["question_text"],
                            "answer_text": "[GENERATION_FAILED]",
                        })

        if (batch_idx + 1) % 4 == 0 or batch_idx == n_batches - 1:
            logger.info(
                f"  [{twin_id}] Progress: {batch_idx + 1}/{n_batches} batches done "
                f"({len(synthetic_answers)} answers)"
            )

    # Assemble complete profile: 59 real + 5 branch + N synthetic
    complete_qa = []

    # Real Q&A pairs (59)
    for qa in real_qa:
        complete_qa.append({
            "question_id": None,  # real QA don't have bank IDs in this format
            "question_text": qa["question_text"],
            "answer_text": qa["answer_text"],
            "source": "real",
            "module_id": qa.get("module_id"),
        })

    # Branch Q&A pairs (5)
    for ba in branch_answers:
        complete_qa.append({
            "question_id": None,
            "question_text": ba["question_text"],
            "answer_text": ba["answer_text"],
            "source": "branch",
            "dimension_name": ba.get("dimension_name"),
            "archetype_id": ba.get("archetype_id"),
            "archetype_label": ba.get("archetype_label"),
        })

    # Synthetic Q&A pairs (~289)
    for sa in synthetic_answers:
        complete_qa.append({
            "question_id": sa.get("question_id"),
            "question_text": sa.get("question_text", ""),
            "answer_text": sa.get("answer_text", ""),
            "source": "synthetic",
        })

    n_failed = sum(1 for qa in complete_qa if qa["answer_text"] == "[GENERATION_FAILED]")

    return {
        "twin_id": twin["twin_id"],
        "participant_id": twin["participant_id"],
        "combo_id": twin["combo_id"],
        "coherence_score": twin["coherence_score"],
        "choices": twin["choices"],
        "n_real": len(real_qa),
        "n_branch": len(branch_answers),
        "n_synthetic": len(synthetic_answers),
        "n_total": len(complete_qa),
        "n_failed": n_failed,
        "qa_pairs": complete_qa,
    }


# ---------------------------------------------------------------------------
# Resume support
# ---------------------------------------------------------------------------

def load_completed_twins(output_path: Path) -> set[str]:
    """Load twin_ids already completed from the output file."""
    if not output_path.exists():
        return set()
    with open(output_path) as f:
        data = json.load(f)
    completed = set()
    for p in data:
        for twin in p.get("twins", []):
            completed.add(twin["twin_id"])
    return completed


def save_results(results: list[dict], output_path: Path):
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)


# ---------------------------------------------------------------------------
# Per-participant pipeline (used by orchestrator)
# ---------------------------------------------------------------------------

async def run_for_participant(
    participant_id: str,
    real_qa: list[dict],
    pruned_twins_data: dict,
    question_bank: list[dict],
    output_dir: Path,
) -> dict:
    """Run Step 3 for a single participant, writing to output_dir."""
    output_dir.mkdir(parents=True, exist_ok=True)
    prompt_template = load_prompt("step3_generate_answers.txt")

    twins = pruned_twins_data["twins"]

    # Prune 100 -> 20
    pruned_path = output_dir / "step2_pruned_twins_20.json"
    if pruned_path.exists():
        logger.info(f"[{participant_id}] Loading existing pruned-20 twins")
        with open(pruned_path) as f:
            pruned_data = json.load(f)
        twins = pruned_data[0]["twins"]
    else:
        selected = select_diverse_subset(twins, TARGET_TWINS_STEP3)
        for idx, twin in enumerate(selected, 1):
            twin["twin_id"] = f"{participant_id}_T{idx:03d}"
        pruned_result = [{
            "participant_id": participant_id,
            "n_original": len(twins),
            "n_selected": len(selected),
            "twins": selected,
        }]
        with open(pruned_path, "w") as f:
            json.dump(pruned_result, f, indent=2)
        twins = selected
        logger.info(f"[{participant_id}] Pruned {len(pruned_twins_data['twins'])} -> {len(twins)} twins")

    # Resume support
    output_path = output_dir / "step3_complete_profiles.json"
    completed_twin_ids = set()
    p_result = {"participant_id": participant_id, "twins": []}

    if output_path.exists():
        with open(output_path) as f:
            existing = json.load(f)
        if existing:
            p_result = existing[0]
            completed_twin_ids = {t["twin_id"] for t in p_result.get("twins", [])}

    incomplete = [(idx, twin) for idx, twin in enumerate(twins) if twin["twin_id"] not in completed_twin_ids]
    if completed_twin_ids:
        logger.info(f"[{participant_id}] Resuming: {len(completed_twin_ids)} twins done, {len(incomplete)} remaining")

    # Pre-compute unanswered questions per twin
    twin_unanswered = {}
    for _, twin in incomplete:
        branch_texts = {ba["question_text"] for ba in twin["branch_answers"]}
        twin_unanswered[twin["twin_id"]] = get_unanswered_questions(question_bank, branch_texts)

    # Process twins in parallel batches
    for batch_start in range(0, len(incomplete), STEP3_PARALLEL_TWINS):
        batch = incomplete[batch_start:batch_start + STEP3_PARALLEL_TWINS]

        tasks = [
            expand_twin(twin, real_qa, twin_unanswered[twin["twin_id"]], prompt_template, participant_id=participant_id)
            for _, twin in batch
        ]
        profiles = await asyncio.gather(*tasks)

        for (_, twin), profile in zip(batch, profiles):
            p_result["twins"].append(profile)
            completed_twin_ids.add(twin["twin_id"])

        # Save after each parallel batch
        with open(output_path, "w") as f:
            json.dump([p_result], f, indent=2)

    logger.info(f"[{participant_id}] Step 3 complete: {len(p_result['twins'])} twins expanded")
    return p_result


# ---------------------------------------------------------------------------
# Main pipeline (CLI backward compat)
# ---------------------------------------------------------------------------

async def run_pipeline(participant_filter: str | None = None):
    """
    Run Step 3 profile expansion.

    Args:
        participant_filter: If set, only process this participant_id (e.g. "P01").
    """
    start_time = time.time()

    # Load inputs
    all_twins_data = load_pruned_twins()
    real_qa_by_pid = load_real_qa_pairs()
    question_bank = load_question_bank()
    prompt_template = load_prompt("step3_generate_answers.txt")

    # Filter participants if requested
    if participant_filter:
        all_twins_data = [p for p in all_twins_data if p["participant_id"] == participant_filter]
        if not all_twins_data:
            logger.error(f"No data found for participant {participant_filter}")
            return

    # Step 0: Prune 100 → 20 twins per participant
    pruned_path = OUTPUT_DIR / "step2_pruned_twins_20.json"
    if pruned_path.exists():
        logger.info(f"Loading existing pruned-20 twins from {pruned_path}")
        with open(pruned_path) as f:
            pruned_data = json.load(f)
        # Filter if needed
        if participant_filter:
            pruned_data = [p for p in pruned_data if p["participant_id"] == participant_filter]
    else:
        logger.info(f"Pruning twins: {TARGET_TWINS_STEP3} per participant...")
        pruned_data = prune_twins(all_twins_data, TARGET_TWINS_STEP3)
        save_results(pruned_data, pruned_path)
        logger.info(f"Saved pruned twins to {pruned_path}")

    # Resume support
    output_path = OUTPUT_DIR / "step3_complete_profiles.json"
    completed_twin_ids = load_completed_twins(output_path)
    if completed_twin_ids:
        logger.info(f"Resuming — {len(completed_twin_ids)} twins already completed")

    # Load existing results for resume
    all_results = []
    if output_path.exists():
        with open(output_path) as f:
            all_results = json.load(f)

    # Process each participant
    for p_data in pruned_data:
        pid = p_data["participant_id"]
        twins = p_data["twins"]
        real_qa = real_qa_by_pid.get(pid)

        if real_qa is None:
            logger.error(f"No real QA pairs for {pid}, skipping")
            continue

        logger.info(f"\n{'=' * 70}")
        logger.info(f"PARTICIPANT: {pid} — {len(twins)} twins to expand")
        logger.info(f"{'=' * 70}")

        # Find or create result entry for this participant
        p_result = None
        for r in all_results:
            if r["participant_id"] == pid:
                p_result = r
                break
        if p_result is None:
            p_result = {"participant_id": pid, "twins": []}
            all_results.append(p_result)

        # Collect incomplete twins
        incomplete = [
            (idx, twin) for idx, twin in enumerate(twins)
            if twin["twin_id"] not in completed_twin_ids
        ]
        n_skipped = len(twins) - len(incomplete)
        if n_skipped:
            logger.info(f"  Skipping {n_skipped} already-completed twins")

        # Pre-compute unanswered questions per twin
        twin_unanswered = {}
        for _, twin in incomplete:
            branch_texts = {ba["question_text"] for ba in twin["branch_answers"]}
            twin_unanswered[twin["twin_id"]] = get_unanswered_questions(question_bank, branch_texts)

        # Process twins in parallel batches
        for batch_start in range(0, len(incomplete), STEP3_PARALLEL_TWINS):
            batch = incomplete[batch_start:batch_start + STEP3_PARALLEL_TWINS]
            batch_end = batch_start + len(batch)

            logger.info(
                f"\n  --- Parallel batch {batch_start // STEP3_PARALLEL_TWINS + 1}: "
                f"twins {batch_start + 1}-{batch_end}/{len(incomplete)} ---"
            )
            for _, twin in batch:
                tid = twin["twin_id"]
                unanswered = twin_unanswered[tid]
                logger.info(f"  [{tid}] Context: {len(real_qa)} real + {len(twin['branch_answers'])} branch = 64 QA")
                logger.info(f"  [{tid}] Unanswered: {len(unanswered)} questions")

            tasks = [
                expand_twin(twin, real_qa, twin_unanswered[twin["twin_id"]], prompt_template)
                for _, twin in batch
            ]
            profiles = await asyncio.gather(*tasks)

            for (_, twin), profile in zip(batch, profiles):
                p_result["twins"].append(profile)
                completed_twin_ids.add(twin["twin_id"])

                n_failed = profile['n_failed']
                failed_str = f", {n_failed} failed" if n_failed else ""
                logger.info(
                    f"  [{twin['twin_id']}] DONE: {profile['n_total']} Q&A pairs "
                    f"({profile['n_real']} real + {profile['n_branch']} branch + "
                    f"{profile['n_synthetic']} synthetic{failed_str})"
                )

            # Save after each parallel batch for resume support
            save_results(all_results, output_path)

    # Print summary
    elapsed = time.time() - start_time
    total_twins = sum(len(r["twins"]) for r in all_results)
    total_qa = sum(t["n_total"] for r in all_results for t in r["twins"])
    total_failed = sum(t["n_failed"] for r in all_results for t in r["twins"])

    print(f"\n{'=' * 70}")
    print(f"STEP 3 COMPLETE")
    print(f"{'=' * 70}")
    for r in all_results:
        pid = r["participant_id"]
        n_twins = len(r["twins"])
        n_qa = sum(t["n_total"] for t in r["twins"])
        print(f"  {pid}: {n_twins} twins, {n_qa} total Q&A pairs")
    print(f"\n  Total: {total_twins} twins, {total_qa} Q&A pairs")
    if total_failed:
        print(f"  WARNING: {total_failed} answers failed to generate")
    print(f"  Elapsed: {elapsed / 60:.1f} minutes")
    print(f"\nOutputs:")
    print(f"  - {pruned_path}")
    print(f"  - {output_path}")
    print(f"{'=' * 70}")

    return all_results


if __name__ == "__main__":
    # Default: P01 only for initial test run
    pid_filter = sys.argv[1] if len(sys.argv) > 1 else "P01"
    if pid_filter.lower() == "all":
        pid_filter = None
    asyncio.run(run_pipeline(participant_filter=pid_filter))
