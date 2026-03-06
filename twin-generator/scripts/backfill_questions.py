"""
One-time backfill: generate missing questions for underfilled domains.
Reads current question_bank.json, identifies shortfalls, generates to fill, and updates the bank.
"""
import asyncio
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import OUTPUT_DIR, INPUT_DIR, Q_TOTAL_BANK, PROMPTS_DIR, LLM_MAX_TOKENS_PRUNING
from scripts.llm_utils import call_llm
from scripts.step1_question_bank import DOMAINS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("backfill")

TARGET_PER_DOMAIN = Q_TOTAL_BANK // len(DOMAINS)  # 58
TARGET_REMAINDER = Q_TOTAL_BANK % len(DOMAINS)     # 2


def load_prompt(filename: str) -> str:
    with open(PROMPTS_DIR / filename) as f:
        return f.read()


async def backfill():
    with open(OUTPUT_DIR / "question_bank.json") as f:
        bank = json.load(f)

    # Count per domain
    domain_qs = {}
    for q in bank:
        d = q.get("domain_tag", "?")
        domain_qs.setdefault(d, []).append(q)

    # Find shortfalls
    shortfalls = {}
    for i, domain in enumerate(DOMAINS):
        target = TARGET_PER_DOMAIN + (1 if i < TARGET_REMAINDER else 0)
        current = len(domain_qs.get(domain, []))
        if current < target:
            shortfalls[domain] = target - current

    total_needed = sum(shortfalls.values())
    if total_needed == 0:
        logger.info("No shortfalls — bank is complete!")
        return

    logger.info(f"Need {total_needed} more questions across {len(shortfalls)} domains:")
    for d, n in shortfalls.items():
        logger.info(f"  {d}: need {n} more")

    # Generate for each underfilled domain
    prompt_template = load_prompt("step1_generate_questions.txt")
    all_new = []

    for domain_name, n_needed in shortfalls.items():
        existing_in_domain = domain_qs.get(domain_name, [])
        existing_text = "\n".join(
            f"- {q.get('question_text', '')} [signals: {q.get('behavioral_signals', 'N/A')}]"
            for q in existing_in_domain
        ) or "(none)"

        existing_signals = list(set(
            s.strip()
            for q in existing_in_domain
            for s in q.get("behavioral_signals", "").split(",")
            if s.strip()
        ))

        gap_text = (
            f"Existing signals covered: {', '.join(existing_signals)}\n"
            f"Need {n_needed} new questions that cover distinct behavioral dimensions not yet addressed."
        )

        prompt = (
            prompt_template
            .replace("{n_questions}", str(n_needed))
            .replace("{domain_name}", domain_name)
            .replace("{domain_description}", DOMAINS[domain_name])
            .replace("{existing_in_domain}", existing_text)
            .replace("{gap_analysis}", gap_text)
        )

        logger.info(f"Generating {n_needed} questions for {domain_name}...")
        result = await call_llm(
            prompt=prompt,
            system="You are a consumer research methodologist. Return valid JSON only.",
            max_tokens=LLM_MAX_TOKENS_PRUNING,
        )

        if isinstance(result, list):
            for q in result[:n_needed]:
                q["source"] = "generated"
            all_new.extend(result[:n_needed])
            logger.info(f"  Got {min(len(result), n_needed)} questions")
        else:
            logger.error(f"  Failed for {domain_name} — got {type(result)}")

    # Assign IDs continuing from current max
    max_new_id = 0
    for q in bank:
        qid = q.get("question_id", "")
        if qid.startswith("QN"):
            try:
                max_new_id = max(max_new_id, int(qid[2:]))
            except ValueError:
                pass

    for i, q in enumerate(all_new, max_new_id + 1):
        q["question_id"] = f"QN{i:03d}"
        if "question_type" not in q:
            q["question_type"] = "scenario-based"

    # Append to bank
    bank.extend(all_new)

    # Save
    with open(OUTPUT_DIR / "question_bank.json", "w") as f:
        json.dump(bank, f, indent=2)
    with open(INPUT_DIR / "question_bank.json", "w") as f:
        json.dump(bank, f, indent=2)

    # Final count
    counts = {}
    for q in bank:
        d = q.get("domain_tag", "?")
        counts[d] = counts.get(d, 0) + 1

    logger.info(f"Updated bank: {len(bank)} total")
    for d, c in sorted(counts.items()):
        logger.info(f"  {d}: {c}")


if __name__ == "__main__":
    asyncio.run(backfill())
