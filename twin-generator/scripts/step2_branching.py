"""
Step 2: Branching Question Selection + Variant Generation + Pruning

Pipeline:
  (a) For each participant, identify 5 behavioral dimensions NOT captured by the 59 questions
      but that would cause twins to respond differently to product concepts and ad campaigns
  (b) For each dimension, select a branching question (from 291 new questions) and generate
      3 answer archetypes plausible for this specific person
  (c) Enumerate all 243 (3^5) combinations, evaluate coherence, prune to top 100

Input:
  - data/input/real_qa_pairs.json        — participants × 59 Q&A pairs each
  - data/input/question_bank.json        — 350 questions (59 existing + 291 new)

Output:
  - data/output/step2_dimensions.json    — 5 uncaptured dimensions per participant
  - data/output/step2_archetypes.json    — branching Qs + 3 archetypes per dimension
  - data/output/step2_pruned_twins.json  — 100 selected twin profiles per participant
"""
import asyncio
import itertools
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import (
    INPUT_DIR,
    OUTPUT_DIR,
    Q_BRANCH,
    V_BRANCH,
    TARGET_TWINS_PER_PERSON,
    LLM_MAX_TOKENS_PRUNING,
    LLM_REASONING_MODEL,
)
from scripts.llm_utils import call_llm
from scripts.data_utils import load_prompt, format_qa, count_dimension_diffs

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("step2_branching")


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_real_qa_pairs() -> list[dict]:
    path = INPUT_DIR / "real_qa_pairs.json"
    if not path.exists():
        raise FileNotFoundError(f"Real Q&A pairs not found at {path}")
    with open(path) as f:
        data = json.load(f)
    logger.info(f"Loaded {len(data)} participants from {path}")
    return data


def load_question_bank() -> list[dict]:
    path = INPUT_DIR / "question_bank.json"
    if not path.exists():
        raise FileNotFoundError(f"Question bank not found at {path}")
    with open(path) as f:
        data = json.load(f)
    logger.info(f"Loaded {len(data)} questions from question bank")
    return data




# ---------------------------------------------------------------------------
# (a) Identify 5 uncaptured behavioral dimensions
# ---------------------------------------------------------------------------

async def identify_dimensions(participant: dict, participant_id: str = "default") -> list[dict]:
    pid = participant["participant_id"]
    logger.info(f"[{pid}] Identifying 5 uncaptured dimensions...")

    qa_text = format_qa(participant["qa_pairs"])
    prompt_template = load_prompt("step2a_identify_dimensions.txt")
    prompt = prompt_template.replace("{qa_pairs}", qa_text)

    result = await call_llm(
        prompt=prompt,
        system="You are a consumer research expert. Return valid JSON only.",
        max_tokens=LLM_MAX_TOKENS_PRUNING,
        temperature=0.5,
        model=LLM_REASONING_MODEL,
        participant_id=participant_id,
    )

    if not isinstance(result, list):
        raise ValueError(f"[{pid}] Expected list from dimension identification, got {type(result)}")

    logger.info(
        f"[{pid}] Got {len(result)} dimensions: "
        f"{[d.get('dimension_name', '?') for d in result]}"
    )
    return result


# ---------------------------------------------------------------------------
# (b) Generate branching questions + 3 archetypes per dimension
# ---------------------------------------------------------------------------

async def generate_archetypes(
    participant: dict,
    dimension: dict,
    question_bank: list[dict],
    participant_id: str = "default",
) -> dict:
    pid = participant["participant_id"]
    dim_name = dimension.get("dimension_name", "?")
    logger.info(f"[{pid}] Generating archetypes for: {dim_name}")

    qa_text = format_qa(participant["qa_pairs"])

    # Filter to generated questions only (the 291 new ones, not the original 59)
    new_qs = [q for q in question_bank if q.get("source") == "generated"]
    # Limit to 40 candidates to keep prompt manageable
    candidates_text = "\n".join(
        f"- [{q.get('question_id', 'N/A')}] {q['question_text']} (domain: {q.get('domain_tag', 'N/A')})"
        for q in new_qs[:40]
    )

    dimension_text = json.dumps(dimension, indent=2)

    prompt_template = load_prompt("step2b_generate_archetypes.txt")
    prompt = (
        prompt_template
        .replace("{qa_pairs}", qa_text)
        .replace("{dimension}", dimension_text)
        .replace("{dimension_name}", dim_name)
        .replace("{candidate_questions}", candidates_text)
    )

    result = await call_llm(
        prompt=prompt,
        system="You are a consumer research expert. Return valid JSON only.",
        max_tokens=LLM_MAX_TOKENS_PRUNING,
        temperature=0.5,
        model=LLM_REASONING_MODEL,
        participant_id=participant_id,
    )

    return result


# ---------------------------------------------------------------------------
# (c) Enumerate all 243 combinations
# ---------------------------------------------------------------------------

def enumerate_combinations(archetypes_per_dim: list[dict]) -> list[dict]:
    """
    Generate all 3^5 = 243 combinations of archetype choices.
    Each combo maps dimension index -> archetype_id (A/B/C).
    """
    archetype_ids = ["A", "B", "C"]
    n_dims = len(archetypes_per_dim)

    combos = []
    for i, choice_tuple in enumerate(itertools.product(archetype_ids, repeat=n_dims)):
        combo = {
            "combo_id": i,
            "choices": {},
            "branch_answers": [],
        }
        for dim_idx, arch_id in enumerate(choice_tuple):
            arch_data = archetypes_per_dim[dim_idx]
            archetypes = arch_data.get("archetypes", [])
            matching = [a for a in archetypes if a["archetype_id"] == arch_id]
            if not matching:
                matching = archetypes[:1]

            archetype = matching[0] if matching else {}
            combo["choices"][f"dim_{dim_idx}"] = arch_id
            combo["branch_answers"].append({
                "dimension_name": arch_data.get("dimension_name", f"dim_{dim_idx}"),
                "question_text": arch_data.get("selected_question", {}).get("question_text", ""),
                "archetype_id": arch_id,
                "archetype_label": archetype.get("archetype_label", ""),
                "answer_text": archetype.get("answer_text", ""),
            })
        combos.append(combo)

    logger.info(f"Enumerated {len(combos)} raw combinations")
    return combos


# ---------------------------------------------------------------------------
# (d) Evaluate coherence in batches + prune to 100
# ---------------------------------------------------------------------------

async def evaluate_coherence_batch(
    participant: dict,
    archetypes_per_dim: list[dict],
    combos_batch: list[dict],
    participant_id: str = "default",
) -> list[dict]:
    """Send a batch of combinations to the LLM for coherence evaluation."""
    qa_text = format_qa(participant["qa_pairs"])

    # Build dimensions summary
    dims_parts = []
    for dim_idx, arch_data in enumerate(archetypes_per_dim):
        dim_name = arch_data.get("dimension_name", f"Dimension {dim_idx + 1}")
        archetypes = arch_data.get("archetypes", [])
        lines = [f"Dimension {dim_idx + 1}: {dim_name}"]
        for a in archetypes:
            answer_preview = a.get("answer_text", "")[:150]
            lines.append(
                f"  {a['archetype_id']}: {a.get('archetype_label', '?')} "
                f"({a.get('position_on_dimension', '')}) — {answer_preview}..."
            )
        dims_parts.append("\n".join(lines))
    dims_summary = "\n\n".join(dims_parts)

    # Format combinations
    combos_lines = []
    for combo in combos_batch:
        choices_str = ", ".join(
            f"Dim{int(k.split('_')[1]) + 1}={v}"
            for k, v in sorted(combo["choices"].items())
        )
        combos_lines.append(f"combo_id={combo['combo_id']}: {choices_str}")
    combos_text = "\n".join(combos_lines)

    prompt_template = load_prompt("step2c_prune_combinations.txt")
    prompt = (
        prompt_template
        .replace("{core_profile}", qa_text)
        .replace("{dimensions_summary}", dims_summary)
        .replace("{combinations_batch}", combos_text)
    )

    result = await call_llm(
        prompt=prompt,
        system="You are a consumer research expert. Return valid JSON only.",
        max_tokens=LLM_MAX_TOKENS_PRUNING,
        temperature=0.3,
        model=LLM_REASONING_MODEL,
        participant_id=participant_id,
    )

    return result.get("evaluations", []) if isinstance(result, dict) else []


async def prune_to_target(
    participant: dict,
    archetypes_per_dim: list[dict],
    all_combos: list[dict],
    target: int = TARGET_TWINS_PER_PERSON,
    participant_id: str = "default",
) -> list[dict]:
    """
    Evaluate all 243 combinations for coherence in batches,
    then select the top `target` most coherent + diverse twins.
    """
    pid = participant["participant_id"]
    logger.info(f"[{pid}] Evaluating {len(all_combos)} combinations for coherence...")

    # Batch combinations (80 per batch for efficiency with Opus)
    batch_size = 80
    batches = [
        all_combos[i:i + batch_size]
        for i in range(0, len(all_combos), batch_size)
    ]

    logger.info(f"[{pid}] Sending {len(batches)} evaluation batches...")

    # Run batches sequentially to manage rate limits with Opus
    all_evals = []
    for batch_idx, batch in enumerate(batches):
        logger.info(f"[{pid}] Evaluating batch {batch_idx + 1}/{len(batches)} ({len(batch)} combos)...")
        try:
            evals = await evaluate_coherence_batch(participant, archetypes_per_dim, batch, participant_id=participant_id)
            all_evals.extend(evals)
        except Exception as e:
            logger.warning(f"[{pid}] Batch {batch_idx + 1} evaluation failed: {e}. Assigning default scores.")
            for combo in batch:
                all_evals.append({
                    "combo_id": combo["combo_id"],
                    "coherence_score": 0.5,
                    "is_contradictory": False,
                })

    # Build lookup: combo_id -> evaluation
    eval_lookup = {}
    for e in all_evals:
        cid = e.get("combo_id")
        if cid is not None:
            eval_lookup[cid] = e
            eval_lookup[str(cid)] = e

    # Score and filter combinations
    scored_combos = []
    n_contradictory = 0
    for combo in all_combos:
        cid = combo["combo_id"]
        evaluation = eval_lookup.get(cid, eval_lookup.get(str(cid), {}))
        coherence = evaluation.get("coherence_score", 0.5)
        is_contradictory = evaluation.get("is_contradictory", False)

        if is_contradictory:
            n_contradictory += 1
            continue

        scored_combos.append({
            **combo,
            "coherence_score": coherence,
            "differentiation_value": evaluation.get("differentiation_value", ""),
        })

    logger.info(
        f"[{pid}] Removed {n_contradictory} contradictory combinations. "
        f"{len(scored_combos)} coherent remain."
    )

    # Sort by coherence descending
    scored_combos.sort(key=lambda c: c["coherence_score"], reverse=True)

    # Select top `target` with diversity enforcement
    selected = _select_diverse_subset(scored_combos, target)

    logger.info(
        f"[{pid}] Final selection: {len(selected)} twins "
        f"(coherence range: {selected[-1]['coherence_score']:.2f} - {selected[0]['coherence_score']:.2f})"
    )
    return selected


def _select_diverse_subset(ranked_combos: list[dict], target: int) -> list[dict]:
    """
    From ranked (by coherence) combos, select `target` that maximize diversity.
    Greedy: pick most coherent first, then prefer combos that differ from
    already-selected ones on at least 2 dimensions.
    """
    if len(ranked_combos) <= target:
        return ranked_combos

    selected = [ranked_combos[0]]
    remaining = ranked_combos[1:]

    while len(selected) < target and remaining:
        best_idx = 0
        best_score = -1

        for idx, candidate in enumerate(remaining):
            min_diff = min(
                count_dimension_diffs(candidate["choices"], sel["choices"])
                for sel in selected
            )
            # Combined: coherence * 0.6 + diversity * 0.4
            combined = candidate["coherence_score"] * 0.6 + (min_diff / Q_BRANCH) * 0.4

            if combined > best_score:
                best_score = combined
                best_idx = idx

        selected.append(remaining.pop(best_idx))

    return selected



# ---------------------------------------------------------------------------
# Build final twin profiles
# ---------------------------------------------------------------------------

def build_twin_profiles(
    participant: dict,
    selected_combos: list[dict],
    archetypes_per_dim: list[dict],
) -> list[dict]:
    """Assemble final twin profile data structure from selected combinations."""
    pid = participant["participant_id"]
    twins = []

    for idx, combo in enumerate(selected_combos, 1):
        twin_id = f"{pid}_T{idx:03d}"
        branch_answers = []

        for dim_idx_str, arch_id in sorted(combo["choices"].items()):
            dim_idx = int(dim_idx_str.split("_")[1])
            arch_data = archetypes_per_dim[dim_idx]
            archetypes = arch_data.get("archetypes", [])
            matching = [a for a in archetypes if a["archetype_id"] == arch_id]

            if matching:
                arch = matching[0]
                branch_answers.append({
                    "dimension_name": arch_data.get("dimension_name", ""),
                    "question_text": arch_data.get("selected_question", {}).get("question_text", ""),
                    "archetype_id": arch_id,
                    "archetype_label": arch.get("archetype_label", ""),
                    "answer_text": arch.get("answer_text", ""),
                    "position_on_dimension": arch.get("position_on_dimension", ""),
                    "concept_test_prediction": arch.get("concept_test_prediction", ""),
                    "ad_test_prediction": arch.get("ad_test_prediction", ""),
                })

        twins.append({
            "twin_id": twin_id,
            "participant_id": pid,
            "combo_id": combo["combo_id"],
            "coherence_score": combo.get("coherence_score", 0),
            "choices": combo["choices"],
            "branch_answers": branch_answers,
        })

    return twins


# ---------------------------------------------------------------------------
# Intermediate saving
# ---------------------------------------------------------------------------

def _save_dimensions(all_dims: list[dict], output_dir: Path = OUTPUT_DIR):
    with open(output_dir / "step2_dimensions.json", "w") as f:
        json.dump(all_dims, f, indent=2)


def _save_archetypes(all_archs: list[dict], output_dir: Path = OUTPUT_DIR):
    with open(output_dir / "step2_archetypes.json", "w") as f:
        json.dump(all_archs, f, indent=2)


# ---------------------------------------------------------------------------
# Per-participant pipeline (used by orchestrator)
# ---------------------------------------------------------------------------

async def run_for_participant(
    participant: dict,
    question_bank: list[dict],
    output_dir: Path,
) -> dict:
    """Run the full Step 2 pipeline for a single participant, writing to output_dir."""
    pid = participant["participant_id"]
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"\n{'=' * 70}")
    logger.info(f"PARTICIPANT: {pid}")
    logger.info(f"{'=' * 70}")

    # (a) Identify 5 uncaptured dimensions
    dimensions = await identify_dimensions(participant, participant_id=pid)
    _save_dimensions([{"participant_id": pid, "dimensions": dimensions}], output_dir)

    # (b) Generate archetypes for each dimension
    archetypes_per_dim = []
    for dim in dimensions:
        arch = await generate_archetypes(participant, dim, question_bank, participant_id=pid)
        archetypes_per_dim.append(arch)

    _save_archetypes([{
        "participant_id": pid,
        "archetypes_per_dim": [
            {
                "dimension_name": a.get("dimension_name", ""),
                "selected_question": a.get("selected_question", {}),
                "archetypes": a.get("archetypes", []),
            }
            for a in archetypes_per_dim
        ],
    }], output_dir)

    # (c) Enumerate all 243 combinations
    all_combos = enumerate_combinations(archetypes_per_dim)

    # (d) Evaluate coherence and prune to 100
    selected = await prune_to_target(participant, archetypes_per_dim, all_combos, participant_id=pid)

    # (e) Build final twin profiles
    twins = build_twin_profiles(participant, selected, archetypes_per_dim)

    result = {
        "participant_id": pid,
        "n_dimensions": len(dimensions),
        "n_combinations": len(all_combos),
        "n_selected": len(twins),
        "twins": twins,
    }

    with open(output_dir / "step2_pruned_twins.json", "w") as f:
        json.dump([result], f, indent=2)

    logger.info(f"[{pid}] Done: {len(twins)} twins from {len(all_combos)} combinations")
    return result


# ---------------------------------------------------------------------------
# Main pipeline (CLI backward compat)
# ---------------------------------------------------------------------------

async def run_pipeline():
    """Run the full Step 2 pipeline for all participants."""
    # Load inputs
    participants = load_real_qa_pairs()
    question_bank = load_question_bank()

    logger.info(f"Starting Step 2 pipeline for {len(participants)} participants")
    logger.info(f"Question bank: {len(question_bank)} questions")

    # Resume support
    results_path = OUTPUT_DIR / "step2_pruned_twins.json"
    all_results = []
    all_dims_saved = []
    all_archs_saved = []
    completed_pids = set()

    if results_path.exists():
        with open(results_path) as f:
            all_results = json.load(f)
        completed_pids = {r["participant_id"] for r in all_results}
        if completed_pids:
            logger.info(f"Resuming — already completed: {completed_pids}")

    # Load saved intermediates for resume
    dims_path = OUTPUT_DIR / "step2_dimensions.json"
    archs_path = OUTPUT_DIR / "step2_archetypes.json"
    if dims_path.exists():
        with open(dims_path) as f:
            all_dims_saved = json.load(f)
    if archs_path.exists():
        with open(archs_path) as f:
            all_archs_saved = json.load(f)

    for participant in participants:
        pid = participant["participant_id"]
        if pid in completed_pids:
            logger.info(f"Skipping {pid} (already done)")
            continue

        logger.info(f"\n{'=' * 70}")
        logger.info(f"PARTICIPANT: {pid}")
        logger.info(f"{'=' * 70}")

        # (a) Identify 5 uncaptured dimensions
        dimensions = await identify_dimensions(participant)

        all_dims_saved.append({"participant_id": pid, "dimensions": dimensions})
        _save_dimensions(all_dims_saved)

        # (b) Generate archetypes for each dimension
        archetypes_per_dim = []
        for dim in dimensions:
            arch = await generate_archetypes(participant, dim, question_bank)
            archetypes_per_dim.append(arch)

        all_archs_saved.append({
            "participant_id": pid,
            "archetypes_per_dim": [
                {
                    "dimension_name": a.get("dimension_name", ""),
                    "selected_question": a.get("selected_question", {}),
                    "archetypes": a.get("archetypes", []),
                }
                for a in archetypes_per_dim
            ],
        })
        _save_archetypes(all_archs_saved)

        # (c) Enumerate all 243 combinations
        all_combos = enumerate_combinations(archetypes_per_dim)

        # (d) Evaluate coherence and prune to 100
        selected = await prune_to_target(participant, archetypes_per_dim, all_combos)

        # (e) Build final twin profiles
        twins = build_twin_profiles(participant, selected, archetypes_per_dim)

        result = {
            "participant_id": pid,
            "n_dimensions": len(dimensions),
            "n_combinations": len(all_combos),
            "n_selected": len(twins),
            "twins": twins,
        }
        all_results.append(result)

        # Save after each participant
        with open(results_path, "w") as f:
            json.dump(all_results, f, indent=2)

        logger.info(f"[{pid}] Done: {len(twins)} twins from {len(all_combos)} combinations")

    # Print summary
    total = sum(r["n_selected"] for r in all_results)
    print(f"\n{'=' * 70}")
    print(f"STEP 2 COMPLETE")
    print(f"{'=' * 70}")
    for r in all_results:
        print(f"  {r['participant_id']}: {r['n_selected']} twins selected from {r['n_combinations']} combinations")
    print(f"  Total twins: {total}")
    print(f"\nOutputs saved to:")
    print(f"  - {OUTPUT_DIR / 'step2_dimensions.json'}")
    print(f"  - {OUTPUT_DIR / 'step2_archetypes.json'}")
    print(f"  - {OUTPUT_DIR / 'step2_pruned_twins.json'}")
    print(f"{'=' * 70}")

    return all_results


if __name__ == "__main__":
    asyncio.run(run_pipeline())
