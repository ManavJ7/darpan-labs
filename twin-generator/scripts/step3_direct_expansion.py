"""
Step 3 (1:1 mode): Direct Profile Expansion — No branching, 1 twin per participant.

Takes a participant's 59 real Q&A pairs and generates answers for the ~291
generated questions from the 350-question bank. No Step 2 needed — the twin
IS the participant, extended with synthetic answers.

Input:
  - data/input/real_qa_pairs.json   — 59 real Q&A per participant
  - data/input/question_bank.json   — 350-question bank

Output:
  - data/output/{PID}/step3_complete_profiles.json — 1 twin × 350 Q&A
"""
import asyncio
import json
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import (
    INPUT_DIR,
    OUTPUT_DIR,
    STEP3_BATCH_SIZE,
    LLM_MAX_TOKENS_STEP3,
    LLM_GENERATION_MODEL,
)
from scripts.llm_utils import call_llm
from scripts.data_utils import load_prompt, format_questions_block

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("step3_direct")



def build_qa_context(real_qa: list[dict]) -> str:
    """Format 59 real Q&A pairs as context string."""
    lines = []
    for i, qa in enumerate(real_qa, 1):
        lines.append(f"Q{i}: {qa['question_text']}")
        lines.append(f"A{i}: {qa['answer_text']}")
        lines.append("")
    return "\n".join(lines)


def get_unanswered_questions(question_bank: list[dict]) -> list[dict]:
    """Return generated questions (not existing ones already answered)."""
    return [q for q in question_bank if q.get("source") != "existing"]




async def generate_batch(
    qa_context: str,
    questions_batch: list[dict],
    prompt_template: str,
    participant_id: str = "default",
) -> list[dict]:
    """Generate answers for a batch of questions using ICL."""
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

    # Unwrap if dict
    if isinstance(result, dict):
        for key in ("answers", "responses", "results", "data"):
            if key in result and isinstance(result[key], list):
                result = result[key]
                break
        else:
            for v in result.values():
                if isinstance(v, list):
                    result = v
                    break

    if not isinstance(result, list):
        raise ValueError(f"Expected list from LLM, got {type(result)}")

    # Fix up fields
    batch_lookup = {q["question_id"]: q["question_text"] for q in questions_batch}
    expected_ids = set(batch_lookup.keys())

    for i, item in enumerate(result):
        if "answer_text" not in item or not item["answer_text"]:
            raise ValueError(f"Missing answer_text for item {i}")
        if item.get("question_id") not in expected_ids and i < len(questions_batch):
            item["question_id"] = questions_batch[i]["question_id"]
        qid = item.get("question_id", "")
        item["question_text"] = batch_lookup.get(
            qid, questions_batch[i]["question_text"] if i < len(questions_batch) else ""
        )

    return result


async def run_for_participant(
    participant_id: str,
    real_qa: list[dict],
    question_bank: list[dict],
    output_dir: Path,
) -> dict:
    """Run direct profile expansion for a single participant (1:1 mode)."""
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "step3_complete_profiles.json"

    # Resume: if already done, skip
    if output_path.exists():
        with open(output_path) as f:
            existing = json.load(f)
        if existing and existing[0].get("twins"):
            twin = existing[0]["twins"][0]
            if twin.get("n_failed", 0) == 0 and twin.get("n_total", 0) > 0:
                logger.info(f"[{participant_id}] Step 3 (1:1) already done, skipping")
                return existing[0]

    prompt_template = load_prompt("step3_generate_answers.txt")
    twin_id = f"{participant_id}_T001"

    # Build context from real QA only (no branch answers in 1:1 mode)
    qa_context = build_qa_context(real_qa)

    # Get unanswered questions
    unanswered = get_unanswered_questions(question_bank)
    logger.info(f"[{participant_id}] 1:1 mode: {len(real_qa)} real QA, {len(unanswered)} to generate")

    # Batch and generate
    batches = [
        unanswered[i:i + STEP3_BATCH_SIZE]
        for i in range(0, len(unanswered), STEP3_BATCH_SIZE)
    ]
    n_batches = len(batches)
    logger.info(f"[{participant_id}] {len(unanswered)} questions in {n_batches} batches")

    synthetic_answers = []
    for batch_idx, batch in enumerate(batches):
        for attempt in range(3):
            try:
                answers = await generate_batch(
                    qa_context, batch, prompt_template,
                    participant_id=participant_id,
                )
                synthetic_answers.extend(answers)
                break
            except Exception as e:
                if attempt < 2:
                    logger.warning(
                        f"[{participant_id}] Batch {batch_idx + 1}/{n_batches} failed "
                        f"(attempt {attempt + 1}/3): {e}"
                    )
                    await asyncio.sleep(5 * (attempt + 1))
                else:
                    logger.error(
                        f"[{participant_id}] Batch {batch_idx + 1}/{n_batches} failed after 3 attempts"
                    )
                    for q in batch:
                        synthetic_answers.append({
                            "question_id": q["question_id"],
                            "question_text": q["question_text"],
                            "answer_text": "[GENERATION_FAILED]",
                        })

        if (batch_idx + 1) % 4 == 0 or batch_idx == n_batches - 1:
            logger.info(
                f"[{participant_id}] Progress: {batch_idx + 1}/{n_batches} batches "
                f"({len(synthetic_answers)} answers)"
            )

    # Assemble complete profile: 59 real + N synthetic (no branch)
    complete_qa = []

    for qa in real_qa:
        complete_qa.append({
            "question_id": None,
            "question_text": qa["question_text"],
            "answer_text": qa["answer_text"],
            "source": "real",
            "module_id": qa.get("module_id"),
        })

    for sa in synthetic_answers:
        complete_qa.append({
            "question_id": sa.get("question_id"),
            "question_text": sa.get("question_text", ""),
            "answer_text": sa.get("answer_text", ""),
            "source": "synthetic",
        })

    n_failed = sum(1 for qa in complete_qa if qa["answer_text"] == "[GENERATION_FAILED]")

    twin_profile = {
        "twin_id": twin_id,
        "participant_id": participant_id,
        "combo_id": 0,
        "coherence_score": 1.0,
        "choices": {},
        "n_real": len(real_qa),
        "n_branch": 0,
        "n_synthetic": len(synthetic_answers),
        "n_total": len(complete_qa),
        "n_failed": n_failed,
        "qa_pairs": complete_qa,
    }

    p_result = {
        "participant_id": participant_id,
        "twins": [twin_profile],
    }

    with open(output_path, "w") as f:
        json.dump([p_result], f, indent=2)

    logger.info(
        f"[{participant_id}] Step 3 (1:1) complete: {twin_profile['n_total']} Q&A pairs "
        f"({twin_profile['n_real']} real + {twin_profile['n_synthetic']} synthetic)"
    )
    return p_result
