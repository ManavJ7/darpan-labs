"""
Exploration script: Identify 5 uncaptured behavioral dimensions and 3 archetypes each.
Runs for each participant, outputs readable results for human review.
"""
import asyncio
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import INPUT_DIR, OUTPUT_DIR, PROMPTS_DIR, LLM_MAX_TOKENS_PRUNING
from scripts.llm_utils import call_llm

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("explore_dimensions")

IDENTIFY_PROMPT = """You are a consumer psychology expert specializing in Indian body wash and personal care markets (men and women aged 20-30, metro India).

## Your Task

You are given:
1. A list of 59 interview questions that were asked to a real participant
2. That participant's actual answers to all 59 questions

The 59 answers are **locked truth** — they fully define what we know about this person. But there are behavioral dimensions that these 59 questions **never measured**.

Your task is to identify **exactly 5 behavioral dimensions that are NOT captured by the 59 questions** but would **cause this person's digital twins to respond DIFFERENTLY when shown product concepts or advertisement campaigns for body wash**.

## Critical Context: How These Twins Will Be Used

These digital twins will be used for exactly two things:
1. **Concept validation** — showing them new body wash product concepts (formulations, packaging, claims, positioning, pricing tiers) and predicting whether they'd buy, how much they'd pay, and what resonates
2. **Ad campaign testing** — showing them advertisements (social media ads, video ads, influencer content, in-store displays) and predicting click/engagement, emotional response, and purchase intent

So the 5 dimensions you identify must be ones where **variation would produce meaningfully different responses to product concepts and ad campaigns**. Think about:
- How they PROCESS advertising messages (emotional vs rational, visual vs text, aspirational vs relatable)
- How they EVALUATE new product concepts (feature-first vs benefit-first, comparison-driven vs standalone)
- How they RESPOND to different positioning strategies (premium vs value, clinical vs natural, Indian vs global)
- How they MAKE the final purchase decision when confronted with a concept (impulse vs deliberate, individual vs household consensus)
- How CONTEXT shapes their receptivity (mood state, occasion, who they're with, where they see the ad)

## What "Not Captured" Means

A dimension is NOT captured if none of the 59 questions directly ask about it, and the person's answers don't definitively reveal their position on it.

## What to AVOID

Do NOT pick dimensions that the 59 questions already cover. These are ALREADY captured:
- Price sensitivity / willingness to pay (covered by Q12, Q16, Q22, Q52, Q53)
- Brand loyalty / switching triggers (covered by Q17, Q23, Q24)
- Natural vs chemical preference (covered by Q13, Q19)
- Fragrance preferences (covered by Q36-Q39)
- Purchase channels / quick commerce (covered by Q21, Q26, Q27)
- Texture / lather / post-wash feeling (covered by Q40-Q42)
- Social media influence / discovery (covered by Q55-Q60)
- Skin concerns (covered by Q34)
- Indian vs international brand preference (covered by Q15)
- Current brands used / satisfaction (covered by Q44-Q50)

## The 59 Questions and This Person's Answers

{qa_pairs}

## Output Format

Return a JSON array of exactly 5 objects:

```json
[
  {{
    "dimension_id": 1,
    "dimension_name": "Short descriptive name (5-8 words)",
    "what_it_captures": "What behavioral territory this dimension covers that the 59 questions missed",
    "concept_test_impact": "How variation on this dimension would cause different responses when shown a body wash product concept",
    "ad_test_impact": "How variation on this dimension would cause different responses when shown a body wash advertisement",
    "what_we_can_infer": "What clues (if any) the person's 59 answers give us — but emphasize why it remains uncertain",
    "example_variation": "Two people with identical 59-answer profiles see the same body wash concept/ad — describe how they'd react differently based on this dimension"
  }}
]
```

Return ONLY the JSON array, no other text."""

ARCHETYPE_PROMPT = """You are a consumer psychology expert specializing in Indian body wash and personal care markets (men and women aged 20-30, metro India).

## Your Task

You are given:
1. A real participant's 59 Q&A pairs (their locked truth profile)
2. A specific behavioral dimension that was NOT captured by those 59 questions — one that would cause different responses to product concepts and ad campaigns
3. The 291 new scenario-based questions from our question bank (these cover territory the original 59 did not)

For this uncaptured dimension, you must:
1. **Select the single best question** from the 291 new questions that would most effectively reveal this person's position on this dimension — specifically in ways that would predict different reactions to body wash concepts and ads. If no existing question fits well, generate a new one.
2. **Generate exactly 3 answer archetypes** — three plausible ways THIS SPECIFIC PERSON (given their locked 59 answers) might answer the question.

## Critical Context: Use Cases

These archetypes will create digital twins used for:
- **Concept validation**: Predicting response to new body wash concepts (formulation, packaging, claims, positioning)
- **Ad campaign testing**: Predicting response to advertisements (social media, video, influencer, in-store)

So each archetype must produce a twin that would respond **measurably differently** when shown the same product concept or ad campaign.

## Rules for Archetypes

- All 3 must be **plausible for this specific person** given their 59 real answers. Not generic consumer archetypes — personalized to who this person is.
- Each must represent a meaningfully different position on the dimension (e.g., low / medium / high)
- For each archetype, explain how this position would change their response to a product concept AND an ad campaign
- Written in a natural voice consistent with how this person answered the original 59 questions
- 2-4 sentences each
- Must reflect Indian consumer context (20-30 years old, metro India)

## This Person's Locked Profile (59 Q&A pairs)

{qa_pairs}

## The Uncaptured Dimension

{dimension}

## Available New Questions (from the 291 question bank, relevant to this dimension's domain)

{candidate_questions}

## Output Format

Return a JSON object:

```json
{{
  "dimension_name": "{dimension_name}",
  "selected_question": {{
    "question_id": "from bank or 'generated'",
    "question_text": "The question that best reveals this dimension",
    "why_selected": "Why this question is the best probe for this dimension given this person's profile"
  }},
  "archetypes": [
    {{
      "archetype_id": "A",
      "archetype_label": "Short label (3-5 words)",
      "position_on_dimension": "Where this archetype sits (e.g., 'low', 'high', 'context-dependent')",
      "answer_text": "How this person would answer the branching question under this archetype (2-4 sentences, personalized)",
      "why_plausible": "Why this answer is consistent with their 59 real answers",
      "concept_test_prediction": "How this twin would react differently to a body wash concept vs the other archetypes",
      "ad_test_prediction": "How this twin would react differently to a body wash ad campaign vs the other archetypes"
    }},
    {{
      "archetype_id": "B",
      "archetype_label": "...",
      "position_on_dimension": "...",
      "answer_text": "...",
      "why_plausible": "...",
      "concept_test_prediction": "...",
      "ad_test_prediction": "..."
    }},
    {{
      "archetype_id": "C",
      "archetype_label": "...",
      "position_on_dimension": "...",
      "answer_text": "...",
      "why_plausible": "...",
      "concept_test_prediction": "...",
      "ad_test_prediction": "..."
    }}
  ]
}}
```

Return ONLY the JSON object, no other text."""


def format_qa(qa_pairs: list[dict]) -> str:
    lines = []
    for i, qa in enumerate(qa_pairs, 1):
        lines.append(f"Q{i}: {qa['question_text']}")
        lines.append(f"A{i}: {qa['answer_text']}")
        lines.append("")
    return "\n".join(lines)


async def identify_dimensions(participant: dict) -> list[dict]:
    pid = participant["participant_id"]
    logger.info(f"[{pid}] Identifying 5 uncaptured dimensions...")

    qa_text = format_qa(participant["qa_pairs"])
    prompt = IDENTIFY_PROMPT.replace("{qa_pairs}", qa_text)

    result = await call_llm(
        prompt=prompt,
        system="You are a consumer research expert. Return valid JSON only.",
        max_tokens=LLM_MAX_TOKENS_PRUNING,
        temperature=0.5,
    )

    if isinstance(result, list):
        logger.info(f"[{pid}] Got {len(result)} dimensions")
        return result
    raise ValueError(f"Expected list, got {type(result)}")


async def generate_archetypes(
    participant: dict,
    dimension: dict,
    question_bank: list[dict],
) -> dict:
    pid = participant["participant_id"]
    dim_name = dimension.get("dimension_name", "?")
    logger.info(f"[{pid}] Generating archetypes for: {dim_name}")

    qa_text = format_qa(participant["qa_pairs"])

    # Filter to generated questions only (the 291 new ones)
    new_qs = [q for q in question_bank if q.get("source") == "generated"]
    # Limit to 40 candidates to keep prompt manageable
    candidates_text = "\n".join(
        f"- [{q.get('question_id', 'N/A')}] {q['question_text']} (domain: {q.get('domain_tag', 'N/A')})"
        for q in new_qs[:40]
    )

    dimension_text = json.dumps(dimension, indent=2)

    prompt = (
        ARCHETYPE_PROMPT
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
    )

    return result


async def run_exploration():
    # Load data
    with open(INPUT_DIR / "real_qa_pairs.json") as f:
        participants = json.load(f)
    with open(INPUT_DIR / "question_bank.json") as f:
        question_bank = json.load(f)

    logger.info(f"Loaded {len(participants)} participants, {len(question_bank)} questions in bank")

    # Resume support: load existing results and skip already-completed participants
    results_path = OUTPUT_DIR / "exploration_results.json"
    all_results = []
    completed_pids = set()
    if results_path.exists():
        with open(results_path) as f:
            all_results = json.load(f)
        completed_pids = {r["participant_id"] for r in all_results}
        if completed_pids:
            logger.info(f"Resuming — already completed: {completed_pids}")

    for participant in participants:
        if participant["participant_id"] in completed_pids:
            logger.info(f"Skipping {participant['participant_id']} (already done)")
            continue
        pid = participant["participant_id"]
        logger.info(f"\n{'='*70}")
        logger.info(f"PARTICIPANT: {pid}")
        logger.info(f"{'='*70}")

        # Step 1: Identify uncaptured dimensions
        dimensions = await identify_dimensions(participant)

        # Step 2: Generate archetypes for each dimension
        archetypes = []
        for dim in dimensions:
            arch = await generate_archetypes(participant, dim, question_bank)
            archetypes.append(arch)

        result = {
            "participant_id": pid,
            "dimensions": dimensions,
            "archetypes": archetypes,
        }
        all_results.append(result)

        # Save after each participant
        with open(OUTPUT_DIR / "exploration_results.json", "w") as f:
            json.dump(all_results, f, indent=2)

    # Print readable summary
    print("\n" + "=" * 80)
    print("EXPLORATION RESULTS — UNCAPTURED DIMENSIONS & ARCHETYPES")
    print("=" * 80)

    for result in all_results:
        pid = result["participant_id"]
        print(f"\n{'─'*80}")
        print(f"PARTICIPANT: {pid}")
        print(f"{'─'*80}")

        for i, (dim, arch) in enumerate(zip(result["dimensions"], result["archetypes"]), 1):
            print(f"\n  DIMENSION {i}: {dim['dimension_name']}")
            print(f"  What it captures: {dim['what_it_captures']}")
            print(f"  Concept test impact: {dim.get('concept_test_impact', dim.get('why_it_matters_for_body_wash', ''))}")
            print(f"  Ad test impact: {dim.get('ad_test_impact', '')}")
            print(f"  What we can infer: {dim['what_we_can_infer']}")

            sq = arch.get("selected_question", {})
            print(f"\n  Branching Question: {sq.get('question_text', 'N/A')}")
            print(f"  (Why: {sq.get('why_selected', 'N/A')})")

            for a in arch.get("archetypes", []):
                print(f"\n    [{a['archetype_id']}] {a.get('archetype_label', '?')} ({a.get('position_on_dimension', '')})")
                print(f"    Answer: {a.get('answer_text', '')}")
                print(f"    Plausible because: {a.get('why_plausible', '')}")
                print(f"    → Concept test: {a.get('concept_test_prediction', '')}")
                print(f"    → Ad test: {a.get('ad_test_prediction', '')}")

    print(f"\n{'='*80}")
    print(f"Full results saved to: {OUTPUT_DIR / 'exploration_results.json'}")


if __name__ == "__main__":
    asyncio.run(run_exploration())
