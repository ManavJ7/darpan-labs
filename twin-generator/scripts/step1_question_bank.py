"""
Step 1: Master Question Bank Design

Pipeline:
  (a) Read 59 existing questions from questions.csv
  (b) Map each to one of 6 behavioral domains via LLM
  (c) Identify coverage gaps per domain
  (d) Generate new scenario-based trade-off questions to fill gaps (target: 350 total)
  (e) Validate and deduplicate
  (f) Output final question bank JSON

Input:
  - questions.csv                        — 59 existing questions (7 modules)

Output:
  - data/output/question_bank.json       — full 350-question bank
  - data/output/step1_domain_mapping.json — existing questions mapped to domains
  - data/output/step1_gap_analysis.json  — coverage gap analysis
"""
import asyncio
import csv
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import (
    PROJECT_ROOT,
    OUTPUT_DIR,
    Q_TOTAL_BANK,
    Q_REAL_PER_PERSON,
    LLM_MAX_TOKENS_BRANCHING,
    LLM_MAX_TOKENS_PRUNING,
)
from scripts.llm_utils import call_llm
from scripts.data_utils import load_prompt

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("step1_question_bank")

# The 6 behavioral domains with descriptions
DOMAINS = {
    "Purchase Decision Mechanics": (
        "Price vs quality trade-off, deal sensitivity, value perception, willingness to pay, "
        "purchase triggers, INR price anchoring, discount behavior, value-for-money calculations"
    ),
    "Information-Seeking Behavior": (
        "Research depth, source trust, review reliance, how they discover and evaluate body wash products, "
        "ingredient label reading, influencer trust, online vs word-of-mouth information gathering"
    ),
    "Brand Relationship Patterns": (
        "Loyalty, switching triggers, consideration set size, Indian vs international brand preference, "
        "D2C brand awareness, brand perception hierarchy, emotional vs functional brand attachment"
    ),
    "Risk & Novelty Orientation": (
        "Experimentation willingness, comfort with new brands/ingredients/formulations, "
        "trial size preference, how they handle product failure, openness to unfamiliar formats"
    ),
    "Social & Contextual Drivers": (
        "Peer influence, family input, social media influence, occasion-driven buying, "
        "household dynamics, shared vs personal products, gifting, community recommendations"
    ),
    "Channel & Format Preferences": (
        "Online vs offline purchasing, quick commerce behavior (Blinkit/Zepto/Swiggy Instamart), "
        "subscription tolerance, discovery mode, packaging preferences, in-store vs app browsing"
    ),
}

# Target distribution: roughly equal across 6 domains
# 350 total / 6 domains ≈ 58 per domain
TARGET_PER_DOMAIN = Q_TOTAL_BANK // len(DOMAINS)  # 58
# Remainder goes to first domain
TARGET_REMAINDER = Q_TOTAL_BANK % len(DOMAINS)     # 2



# ---------------------------------------------------------------------------
# (a) Read existing questions from CSV
# ---------------------------------------------------------------------------

def load_existing_questions() -> list[dict]:
    """Read the 59 existing questions from questions.csv."""
    csv_path = PROJECT_ROOT / "questions.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"questions.csv not found at {csv_path}")

    questions = []
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, 1):
            questions.append({
                "index": i,
                "module_id": row["module_id"].strip(),
                "question_text": row["question_text"].strip(),
            })

    logger.info(f"Loaded {len(questions)} existing questions from {csv_path}")
    return questions


# ---------------------------------------------------------------------------
# (b) Map existing questions to domains via LLM
# ---------------------------------------------------------------------------

async def map_existing_to_domains(questions: list[dict]) -> list[dict]:
    """Use LLM to map each of the 59 existing questions to a behavioral domain."""
    logger.info("Mapping 59 existing questions to behavioral domains via LLM...")

    # Format questions for prompt
    q_text = "\n".join(
        f"{i}. [{q['module_id']}] {q['question_text']}"
        for i, q in enumerate(questions, 1)
    )

    prompt_template = load_prompt("step1_map_existing.txt")
    prompt = prompt_template.replace("{existing_questions}", q_text)

    mapped = await call_llm(
        prompt=prompt,
        system="You are a consumer research methodologist. Return valid JSON only.",
        max_tokens=LLM_MAX_TOKENS_PRUNING,
    )

    if not isinstance(mapped, list):
        raise ValueError(f"Expected list from LLM, got {type(mapped)}")

    logger.info(f"Mapped {len(mapped)} questions to domains")

    # Add source tag
    for q in mapped:
        q["source"] = "existing"

    # Save intermediate output
    with open(OUTPUT_DIR / "step1_domain_mapping.json", "w") as f:
        json.dump(mapped, f, indent=2)
    logger.info(f"Saved domain mapping to {OUTPUT_DIR / 'step1_domain_mapping.json'}")

    return mapped


# ---------------------------------------------------------------------------
# (c) Analyze coverage gaps
# ---------------------------------------------------------------------------

def analyze_gaps(mapped_questions: list[dict]) -> dict:
    """Analyze how many questions exist per domain and compute gaps."""
    # Count existing per domain
    domain_counts = {d: 0 for d in DOMAINS}
    domain_questions = {d: [] for d in DOMAINS}

    for q in mapped_questions:
        domain = q.get("domain_tag", "")
        if domain in domain_counts:
            domain_counts[domain] += 1
            domain_questions[domain].append(q)
        else:
            # Try fuzzy match
            matched = False
            for d in DOMAINS:
                if d.lower() in domain.lower() or domain.lower() in d.lower():
                    domain_counts[d] += 1
                    domain_questions[d].append(q)
                    matched = True
                    break
            if not matched:
                logger.warning(f"Question mapped to unknown domain '{domain}': {q.get('question_text', '')[:50]}")

    # Compute targets and gaps
    gap_analysis = {}
    total_existing = sum(domain_counts.values())
    total_needed = Q_TOTAL_BANK - total_existing

    # Distribute new questions proportionally to fill gaps
    for i, (domain, count) in enumerate(domain_counts.items()):
        target = TARGET_PER_DOMAIN + (1 if i < TARGET_REMAINDER else 0)
        needed = max(0, target - count)
        gap_analysis[domain] = {
            "existing_count": count,
            "target_count": target,
            "new_needed": needed,
            "existing_signals": list(set(
                signal.strip()
                for q in domain_questions[domain]
                for signal in q.get("behavioral_signals", "").split(",")
                if signal.strip()
            )),
        }

    # Adjust to ensure total new = total_needed
    total_planned = sum(g["new_needed"] for g in gap_analysis.values())
    if total_planned < total_needed:
        # Distribute remainder to domains with most gaps
        diff = total_needed - total_planned
        sorted_domains = sorted(gap_analysis.keys(), key=lambda d: gap_analysis[d]["existing_count"])
        for d in sorted_domains:
            if diff <= 0:
                break
            gap_analysis[d]["new_needed"] += 1
            diff -= 1

    logger.info("Coverage gap analysis:")
    for domain, info in gap_analysis.items():
        logger.info(
            f"  {domain}: {info['existing_count']} existing, "
            f"{info['new_needed']} new needed (target: {info['target_count']})"
        )

    # Save
    with open(OUTPUT_DIR / "step1_gap_analysis.json", "w") as f:
        json.dump(gap_analysis, f, indent=2)

    return gap_analysis


# ---------------------------------------------------------------------------
# (d) Generate new questions per domain
# ---------------------------------------------------------------------------

async def generate_questions_for_domain(
    domain_name: str,
    n_questions: int,
    existing_in_domain: list[dict],
    gap_info: dict,
) -> list[dict]:
    """Generate new scenario-based questions for one domain."""
    if n_questions <= 0:
        return []

    logger.info(f"Generating {n_questions} new questions for '{domain_name}'...")

    existing_text = "\n".join(
        f"- {q.get('question_text', '')}"
        f"  [signals: {q.get('behavioral_signals', 'N/A')}]"
        for q in existing_in_domain
    ) or "(none)"

    gap_text = (
        f"Existing signals covered: {', '.join(gap_info.get('existing_signals', []))}\n"
        f"Need {n_questions} new questions that cover distinct behavioral dimensions not yet addressed."
    )

    prompt_template = load_prompt("step1_generate_questions.txt")
    prompt = (
        prompt_template
        .replace("{n_questions}", str(n_questions))
        .replace("{domain_name}", domain_name)
        .replace("{domain_description}", DOMAINS[domain_name])
        .replace("{existing_in_domain}", existing_text)
        .replace("{gap_analysis}", gap_text)
    )

    # For large batches, split into chunks of 30 to keep output quality high
    if n_questions > 30:
        all_questions = []
        remaining = n_questions
        batch_num = 0
        while remaining > 0:
            batch_size = min(30, remaining)
            batch_num += 1
            logger.info(f"  [{domain_name}] Batch {batch_num}: generating {batch_size} questions...")

            # Update prompt for this batch
            batch_prompt = prompt.replace(
                f"exactly {n_questions} new",
                f"exactly {batch_size} new"
            )
            if all_questions:
                # Add already-generated questions to avoid duplicates
                already_text = "\n".join(
                    f"- {q['question_text']}" for q in all_questions
                )
                batch_prompt += (
                    f"\n\n## Already Generated (DO NOT duplicate these)\n{already_text}"
                )

            batch_result = await call_llm(
                prompt=batch_prompt,
                system="You are a consumer research methodologist. Return valid JSON only.",
                max_tokens=LLM_MAX_TOKENS_PRUNING,
            )

            if isinstance(batch_result, list):
                all_questions.extend(batch_result)
                remaining -= len(batch_result)
                retries = 0
            else:
                retries = getattr(generate_questions_for_domain, '_retries', 0) + 1
                generate_questions_for_domain._retries = retries
                if retries >= 2:
                    logger.warning(f"  [{domain_name}] Batch {batch_num} failed after 2 retries, skipping {batch_size} questions")
                    remaining -= batch_size
                    generate_questions_for_domain._retries = 0
                else:
                    logger.warning(f"  [{domain_name}] Batch {batch_num} returned non-list, retrying (attempt {retries}/2)...")

        return all_questions[:n_questions]  # Trim to exact target
    else:
        result = await call_llm(
            prompt=prompt,
            system="You are a consumer research methodologist. Return valid JSON only.",
            max_tokens=LLM_MAX_TOKENS_PRUNING,
        )

        if not isinstance(result, list):
            logger.warning(f"Expected list for {domain_name}, got {type(result)}")
            return []

        return result[:n_questions]


async def generate_all_new_questions(
    mapped_questions: list[dict],
    gap_analysis: dict,
) -> list[dict]:
    """Generate new questions for all domains."""
    # Build per-domain existing question lists
    domain_existing = {d: [] for d in DOMAINS}
    for q in mapped_questions:
        domain = q.get("domain_tag", "")
        if domain in domain_existing:
            domain_existing[domain].append(q)

    # Generate per domain (sequentially to manage rate limits and quality)
    all_new = []
    for domain_name, gap_info in gap_analysis.items():
        n_needed = gap_info["new_needed"]
        if n_needed <= 0:
            continue

        new_qs = await generate_questions_for_domain(
            domain_name=domain_name,
            n_questions=n_needed,
            existing_in_domain=domain_existing[domain_name],
            gap_info=gap_info,
        )

        # Tag with source
        for q in new_qs:
            q["source"] = "generated"

        all_new.extend(new_qs)
        logger.info(f"  {domain_name}: generated {len(new_qs)} questions")

    logger.info(f"Total new questions generated: {len(all_new)}")
    return all_new


# ---------------------------------------------------------------------------
# (e) Validate and deduplicate
# ---------------------------------------------------------------------------

async def validate_and_deduplicate(
    existing: list[dict],
    new_questions: list[dict],
) -> list[dict]:
    """
    Basic deduplication: remove new questions that are too similar to existing ones.
    Uses simple text overlap as a heuristic (no embedding needed at this stage).
    """
    logger.info("Validating and deduplicating...")

    existing_texts = {q.get("question_text", "").lower().strip() for q in existing}
    seen = set()
    deduplicated = []

    for q in new_questions:
        text = q.get("question_text", "").strip()
        text_lower = text.lower()

        # Skip empty
        if not text:
            continue

        # Skip exact duplicates
        if text_lower in existing_texts or text_lower in seen:
            logger.debug(f"  Removing duplicate: {text[:60]}...")
            continue

        seen.add(text_lower)
        deduplicated.append(q)

    removed = len(new_questions) - len(deduplicated)
    if removed > 0:
        logger.info(f"  Removed {removed} duplicate questions")

    return deduplicated


# ---------------------------------------------------------------------------
# (f) Assemble final question bank
# ---------------------------------------------------------------------------

def assemble_question_bank(
    mapped_existing: list[dict],
    new_questions: list[dict],
) -> list[dict]:
    """Combine existing + new questions into the final bank with IDs."""
    bank = []

    # Add existing questions with sequential IDs
    for i, q in enumerate(mapped_existing, 1):
        bank.append({
            "question_id": f"QE{i:03d}",
            "question_text": q.get("question_text", ""),
            "domain_tag": q.get("domain_tag", ""),
            "question_type": q.get("question_type", ""),
            "behavioral_signals": q.get("behavioral_signals", ""),
            "source": "existing",
            "module_id": q.get("module_id", ""),
        })

    # Add new questions
    for i, q in enumerate(new_questions, 1):
        bank.append({
            "question_id": f"QN{i:03d}",
            "question_text": q.get("question_text", ""),
            "domain_tag": q.get("domain_tag", ""),
            "question_type": q.get("question_type", "scenario-based"),
            "behavioral_signals": q.get("behavioral_signals", ""),
            "source": "generated",
            "format": q.get("format", ""),
        })

    return bank


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

async def run_pipeline():
    """Run the full Step 1 question bank design pipeline."""
    logger.info("=" * 60)
    logger.info("Step 1: Master Question Bank Design")
    logger.info("=" * 60)

    # (a) Load existing questions
    existing = load_existing_questions()

    # (b) Map to domains
    mapped = await map_existing_to_domains(existing)

    # (c) Analyze gaps
    gap_analysis = analyze_gaps(mapped)

    # (d) Generate new questions
    new_questions = await generate_all_new_questions(mapped, gap_analysis)

    # (e) Validate and deduplicate
    new_questions = await validate_and_deduplicate(mapped, new_questions)

    # (f) Assemble final bank
    bank = assemble_question_bank(mapped, new_questions)

    # Save final output
    output_path = OUTPUT_DIR / "question_bank.json"
    with open(output_path, "w") as f:
        json.dump(bank, f, indent=2)

    # Also copy to input dir so Step 2 can find it
    input_path = OUTPUT_DIR.parent / "input" / "question_bank.json"
    with open(input_path, "w") as f:
        json.dump(bank, f, indent=2)

    # Summary
    logger.info("=" * 60)
    logger.info("Step 1 complete!")
    logger.info(f"  Existing questions: {len(mapped)}")
    logger.info(f"  New questions generated: {len(new_questions)}")
    logger.info(f"  Total question bank: {len(bank)}")
    logger.info(f"  Saved to: {output_path}")

    # Per-domain breakdown
    domain_counts = {}
    for q in bank:
        d = q.get("domain_tag", "Unknown")
        domain_counts[d] = domain_counts.get(d, 0) + 1
    for domain, count in sorted(domain_counts.items()):
        logger.info(f"    {domain}: {count}")

    logger.info("=" * 60)

    return bank


if __name__ == "__main__":
    asyncio.run(run_pipeline())
