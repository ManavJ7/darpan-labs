"""
Orchestrator: Run the full twin generator pipeline (Steps 2-5) in parallel
across multiple participants, distributing API keys round-robin.

Usage:
    python scripts/orchestrator.py                         # all participants
    python scripts/orchestrator.py --participants P01 P03  # specific ones
    python scripts/orchestrator.py --dry-run               # show progress only
"""
import argparse
import asyncio
import json
import logging
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import (
    INPUT_DIR,
    OUTPUT_DIR,
    MAX_PARALLEL_PARTICIPANTS,
    participant_output_dir,
)
from scripts import (
    step2_branching as step2,
    step3_profile_expansion as step3,
    step4_vector_index as step4_vector,
    step4_kg_build as step4_kg,
)
from scripts.step4_inference import get_chroma_collection_for, get_kg_for
from scripts.step5_m8_simulation import run_m8_simulation

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("orchestrator")


# ---------------------------------------------------------------------------
# Progress detection
# ---------------------------------------------------------------------------

def detect_progress(pid: str) -> dict:
    """Check which steps are already completed for a participant."""
    out = participant_output_dir(pid)
    progress = {
        "step2": (out / "step2_pruned_twins.json").exists(),
        "step3": (out / "step3_complete_profiles.json").exists(),
        "step4a": (out / "step4_chromadb" / "chroma.sqlite3").exists(),
        # step4b always re-runs (has checkpoint resume)
        "step4b_checkpoint": (out / "step4_kg_checkpoint.json").exists(),
        "step4b_graph": (out / "step4_knowledge_graph.json").exists(),
    }
    # Step 5: check if all twins have per-twin CSV files
    m8_dir = out / "step5_m8_simulation"
    twin_ids = load_twin_ids(out)
    if twin_ids:
        progress["step5_done"] = all(
            (m8_dir / f"{tid}_m8_qa_responses.csv").exists() for tid in twin_ids
        )
    else:
        progress["step5_done"] = False
    return progress


def detect_completed_m8_twins(out_dir: Path) -> set[str]:
    """Detect which twins have completed M8 simulation results (per-twin files)."""
    m8_dir = out_dir / "step5_m8_simulation"
    if not m8_dir.exists():
        return set()
    done = set()
    for f in m8_dir.glob("*_m8_qa_responses.csv"):
        # filename: P01_T001_m8_qa_responses.csv -> twin_id = P01_T001
        twin_id = f.name.replace("_m8_qa_responses.csv", "")
        done.add(twin_id)
    return done


def load_twin_ids(out_dir: Path) -> list[str]:
    """Load all twin IDs from step3 profiles."""
    path = out_dir / "step3_complete_profiles.json"
    if not path.exists():
        return []
    with open(path) as f:
        data = json.load(f)
    ids = []
    for p in data:
        for t in p.get("twins", []):
            ids.append(t["twin_id"])
    return ids


# ---------------------------------------------------------------------------
# Data migration (one-time: shared -> per-participant)
# ---------------------------------------------------------------------------

def migrate_existing_data():
    """Split shared output files into per-participant directories."""
    # Check if migration is needed
    if (OUTPUT_DIR / "P01" / "step3_complete_profiles.json").exists():
        logger.info("Migration already done, skipping")
        return

    legacy_dir = OUTPUT_DIR / "_legacy"
    legacy_dir.mkdir(exist_ok=True)

    # Step 2 files
    for fname in ["step2_dimensions.json", "step2_archetypes.json",
                   "step2_pruned_twins.json", "step2_pruned_twins_20.json"]:
        path = OUTPUT_DIR / fname
        if not path.exists():
            continue
        with open(path) as f:
            data = json.load(f)
        # Split by participant_id
        by_pid: dict[str, list] = {}
        for item in data:
            pid = item.get("participant_id", "unknown")
            by_pid.setdefault(pid, []).append(item)
        for pid, items in by_pid.items():
            out = participant_output_dir(pid)
            with open(out / fname, "w") as f:
                json.dump(items, f, indent=2)
            logger.info(f"  Migrated {fname} -> {pid}/")
        # Move original to legacy
        shutil.copy2(path, legacy_dir / fname)

    # Step 3
    path = OUTPUT_DIR / "step3_complete_profiles.json"
    if path.exists():
        with open(path) as f:
            data = json.load(f)
        for item in data:
            pid = item.get("participant_id", "unknown")
            out = participant_output_dir(pid)
            with open(out / "step3_complete_profiles.json", "w") as f:
                json.dump([item], f, indent=2)
            logger.info(f"  Migrated step3_complete_profiles.json -> {pid}/")
        shutil.copy2(path, legacy_dir / "step3_complete_profiles.json")

    # Step 4: ChromaDB (P01 only)
    chroma_dir = OUTPUT_DIR / "step4_chromadb"
    if chroma_dir.exists():
        target = participant_output_dir("P01") / "step4_chromadb"
        if not target.exists():
            shutil.copytree(chroma_dir, target)
            logger.info("  Migrated step4_chromadb/ -> P01/")
        shutil.copytree(chroma_dir, legacy_dir / "step4_chromadb", dirs_exist_ok=True)

    # Step 4: KG files (P01 only)
    for fname in ["step4_kg_checkpoint.json", "step4_knowledge_graph.json"]:
        path = OUTPUT_DIR / fname
        if path.exists():
            target = participant_output_dir("P01") / fname
            if not target.exists():
                shutil.copy2(path, target)
            shutil.copy2(path, legacy_dir / fname)
            logger.info(f"  Migrated {fname} -> P01/")

    # Step 5 dirs (P01 only)
    for dname in ["step5_simulation", "step5_m8_simulation"]:
        src = OUTPUT_DIR / dname
        if src.exists():
            target = participant_output_dir("P01") / dname
            if not target.exists():
                shutil.copytree(src, target)
            shutil.copytree(src, legacy_dir / dname, dirs_exist_ok=True)
            logger.info(f"  Migrated {dname}/ -> P01/")

    logger.info("Migration complete. Originals backed up to _legacy/")


# ---------------------------------------------------------------------------
# Per-participant pipeline
# ---------------------------------------------------------------------------

async def run_participant_pipeline(
    pid: str,
    participant_data: dict,
    question_bank: list[dict],
    progress: dict,
    skip_step5: bool = False,
):
    """Run all pending steps for one participant."""
    out = participant_output_dir(pid)
    t0 = time.time()

    logger.info(f"[{pid}] Starting pipeline (progress: {progress})")

    # Step 2: Branching
    if not progress["step2"]:
        logger.info(f"[{pid}] Running Step 2: Branching...")
        await step2.run_for_participant(participant_data, question_bank, out)
    else:
        logger.info(f"[{pid}] Step 2 already done")

    # Step 3: Profile Expansion
    if not progress["step3"]:
        logger.info(f"[{pid}] Running Step 3: Profile Expansion...")
        with open(out / "step2_pruned_twins.json") as f:
            pruned_data = json.load(f)[0]
        real_qa = participant_data["qa_pairs"]
        await step3.run_for_participant(pid, real_qa, pruned_data, question_bank, out)
    else:
        logger.info(f"[{pid}] Step 3 already done")

    # Step 4A: Vector Index
    if not progress["step4a"]:
        logger.info(f"[{pid}] Running Step 4A: Vector Index...")
        step4_vector.build_for_participant(pid, out)
    else:
        logger.info(f"[{pid}] Step 4A already done")

    # Step 4B: Knowledge Graph
    if not progress["step4b_graph"]:
        logger.info(f"[{pid}] Running Step 4B: Knowledge Graph...")
        await step4_kg.build_kg_for_participant(pid, out)
    else:
        logger.info(f"[{pid}] Step 4B already done")

    # Step 5: M8 Simulation
    if skip_step5:
        logger.info(f"[{pid}] Skipping Step 5 (--skip-step5)")
    elif not progress["step5_done"]:
        logger.info(f"[{pid}] Running Step 5: M8 Simulation...")
        twin_ids = load_twin_ids(out)
        done_twins = detect_completed_m8_twins(out)
        pending_twins = [t for t in twin_ids if t not in done_twins]

        if pending_twins:
            # Load per-participant ChromaDB and KG for isolation
            try:
                collection = get_chroma_collection_for(out)
            except RuntimeError:
                collection = None
            try:
                kg = get_kg_for(out)
            except FileNotFoundError:
                kg = None

            m8_out = out / "step5_m8_simulation"
            for twin_id in pending_twins:
                logger.info(f"[{pid}] Simulating {twin_id}...")
                await run_m8_simulation(
                    twin_id=twin_id,
                    mode="combined",
                    output_dir=m8_out,
                    participant_id=pid,
                    collection=collection,
                    kg=kg,
                )
        else:
            logger.info(f"[{pid}] All twins already simulated")
    else:
        logger.info(f"[{pid}] Step 5 already done")

    elapsed = time.time() - t0
    logger.info(f"[{pid}] Pipeline complete in {elapsed / 60:.1f} minutes")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def run(args):
    """Main orchestrator entry point."""
    # Load shared inputs
    qa_path = INPUT_DIR / "real_qa_pairs.json"
    qb_path = INPUT_DIR / "question_bank.json"

    if not qa_path.exists():
        logger.error(f"Real Q&A pairs not found at {qa_path}")
        logger.error("Run `python scripts/convert_excel.py` first if using Excel files.")
        return
    if not qb_path.exists():
        logger.error(f"Question bank not found at {qb_path}")
        return

    with open(qa_path) as f:
        all_participants = json.load(f)
    with open(qb_path) as f:
        question_bank = json.load(f)

    logger.info(f"Loaded {len(all_participants)} participants, {len(question_bank)} questions")

    # Filter participants if requested
    if args.participants:
        pids = set(args.participants)
        all_participants = [p for p in all_participants if p["participant_id"] in pids]
        if not all_participants:
            logger.error(f"No matching participants found for: {args.participants}")
            return

    # Run migration if needed
    migrate_existing_data()

    # Detect progress for each participant
    participant_tasks = []
    for p in all_participants:
        pid = p["participant_id"]
        progress = detect_progress(pid)
        participant_tasks.append((pid, p, progress))

    # Print progress table
    print(f"\n{'=' * 70}")
    print(f"ORCHESTRATOR — {len(participant_tasks)} participants")
    print(f"{'=' * 70}")
    print(f"{'PID':<6} {'Step2':<8} {'Step3':<8} {'Step4A':<8} {'Step4B':<8} {'Step5':<8}")
    print(f"{'-' * 6} {'-' * 8} {'-' * 8} {'-' * 8} {'-' * 8} {'-' * 8}")
    for pid, _, progress in participant_tasks:
        s2 = "done" if progress["step2"] else "pending"
        s3 = "done" if progress["step3"] else "pending"
        s4a = "done" if progress["step4a"] else "pending"
        s4b = "done" if progress["step4b_graph"] else ("partial" if progress["step4b_checkpoint"] else "pending")
        s5 = "done" if progress["step5_done"] else "pending"
        print(f"{pid:<6} {s2:<8} {s3:<8} {s4a:<8} {s4b:<8} {s5:<8}")
    print(f"{'=' * 70}")
    print(f"Max parallel participants: {MAX_PARALLEL_PARTICIPANTS}")
    print()

    if args.dry_run:
        print("DRY RUN — no work performed")
        return

    # Run pipelines with concurrency limit
    sem = asyncio.Semaphore(MAX_PARALLEL_PARTICIPANTS)

    async def limited_run(pid, data, progress):
        async with sem:
            try:
                await run_participant_pipeline(pid, data, question_bank, progress, skip_step5=args.skip_step5)
                return pid, None
            except Exception as e:
                logger.error(f"[{pid}] Pipeline failed: {e}", exc_info=True)
                return pid, str(e)

    t0 = time.time()
    tasks = [limited_run(pid, data, progress) for pid, data, progress in participant_tasks]
    results = await asyncio.gather(*tasks)

    # Summary
    elapsed = time.time() - t0
    print(f"\n{'=' * 70}")
    print(f"ORCHESTRATOR COMPLETE — {elapsed / 60:.1f} minutes")
    print(f"{'=' * 70}")
    for pid, error in results:
        status = "FAILED: " + error if error else "OK"
        print(f"  {pid}: {status}")
    n_failed = sum(1 for _, e in results if e)
    if n_failed:
        print(f"\n  {n_failed} participant(s) failed")
    print(f"{'=' * 70}")


def main():
    parser = argparse.ArgumentParser(description="Twin Generator Pipeline Orchestrator")
    parser.add_argument("--participants", nargs="*", help="Specific participant IDs (default: all)")
    parser.add_argument("--dry-run", action="store_true", help="Show progress without running")
    parser.add_argument("--skip-step5", action="store_true", help="Stop after Step 4 (skip M8 simulation)")
    args = parser.parse_args()

    asyncio.run(run(args))


if __name__ == "__main__":
    main()
