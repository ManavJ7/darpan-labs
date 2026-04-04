"""
Import existing 17 participants' 1:1 Sonnet-generated twin data into the unified DB.

Reads from:
  - twin-generator/data/input/real_qa_pairs.json  (participant profiles)
  - twin-generator/data/output_1to1/P{XX}/         (step3, step4, step5 outputs)

Idempotent: skips participants whose external_id already exists.

Usage:
    cd ai-interviewer/backend
    python scripts/import_1to1_data.py
"""

import json
import sys
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.database import sync_session_factory, sync_engine, Base
from app.models.twin import (
    DigitalTwin,
    Participant,
    PipelineJob,
    PipelineStepOutput,
    SimulationRun,
)
from app.models.user import User

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent  # darpan-labs-V2-reorganized
TWIN_GEN = PROJECT_ROOT / "twin-generator"
INPUT_DIR = TWIN_GEN / "data" / "input"
OUTPUT_1TO1 = TWIN_GEN / "data" / "output_1to1"


def get_user_by_email_prefix(session, pid: str):
    """Find user by participant email pattern."""
    email = f"{pid.lower()}@darpan-participant.local"
    result = session.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


def import_participants():
    """Main import function."""
    # Load all participant QA pairs
    qa_path = INPUT_DIR / "real_qa_pairs.json"
    if not qa_path.exists():
        print(f"ERROR: {qa_path} not found")
        return

    with open(qa_path) as f:
        all_participants = json.load(f)

    qa_by_pid = {p["participant_id"]: p["qa_pairs"] for p in all_participants}

    # Get list of participants with 1:1 data
    pids = sorted([d.name for d in OUTPUT_1TO1.iterdir() if d.is_dir() and d.name.startswith("P")])
    print(f"Found {len(pids)} participants with 1:1 data: {pids}")

    # Build M8 questionnaire snapshot for existing simulation results
    m8_snapshot = _build_m8_questionnaire_snapshot()

    with sync_session_factory() as session:
        imported = 0
        skipped = 0

        for pid in pids:
            # Check if already imported
            existing = session.execute(
                select(Participant).where(Participant.external_id == pid)
            ).scalar_one_or_none()

            if existing:
                print(f"  {pid}: already exists, skipping")
                skipped += 1
                continue

            print(f"  {pid}: importing...")
            out_dir = OUTPUT_1TO1 / pid

            # Get QA pairs
            qa_pairs = qa_by_pid.get(pid)
            if not qa_pairs:
                print(f"    WARNING: No QA pairs found in real_qa_pairs.json for {pid}, skipping")
                skipped += 1
                continue

            # Find linked user
            user = get_user_by_email_prefix(session, pid)
            user_id = user.id if user else None

            # Create participant
            participant = Participant(
                external_id=pid,
                profile_qa=qa_pairs,
                user_id=user_id,
                display_name=user.display_name if user else pid,
                source="import",
                metadata_={"import_source": "output_1to1", "model": "claude-sonnet-4"},
            )
            session.add(participant)
            session.flush()

            # Create completed pipeline job
            job = PipelineJob(
                job_type="create_twin",
                participant_id=participant.id,
                status="completed",
                progress={
                    "step2": "skipped",
                    "step3": "completed",
                    "step4a": "completed",
                    "step4b": "completed",
                },
                result_summary={"mode": "1to1", "imported": True},
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
            )
            session.add(job)
            session.flush()

            # Step 3: Complete profiles
            step3_path = out_dir / "step3_complete_profiles.json"
            if step3_path.exists():
                with open(step3_path) as f:
                    step3_data = json.load(f)

                session.add(PipelineStepOutput(
                    participant_id=participant.id,
                    job_id=job.id,
                    step_name="step3_profiles",
                    mode="1to1",
                    output_data=step3_data,
                ))

                # Create DigitalTwin from step3 profile
                for p_data in step3_data:
                    for twin_data in p_data.get("twins", []):
                        qa = twin_data.get("qa_pairs", [])
                        sources = Counter(q.get("source", "unknown") for q in qa)
                        twin = DigitalTwin(
                            participant_id=participant.id,
                            twin_external_id=twin_data["twin_id"],
                            mode="1to1",
                            profile_data=qa,
                            profile_stats={
                                "n_real": sources.get("real", 0),
                                "n_branch": sources.get("branch", 0),
                                "n_synthetic": sources.get("synthetic", 0),
                                "n_total": len(qa),
                            },
                            status="ready",
                        )
                        session.add(twin)
                        session.flush()

                        # Step 5: Simulation results
                        sim_path = out_dir / "step5_m8_simulation" / f"{twin_data['twin_id']}_m8_simulation_results.json"
                        if sim_path.exists():
                            with open(sim_path) as f:
                                sim_data = json.load(f)

                            sim_run = SimulationRun(
                                job_id=job.id,
                                twin_id=twin.id,
                                questionnaire_snapshot=m8_snapshot,
                                inference_mode=sim_data.get("inference_mode", "combined"),
                                status="completed",
                                responses=sim_data.get("responses"),
                                summary_stats={
                                    "question_count": sim_data.get("question_count", 0),
                                    "answered_count": len([
                                        r for r in sim_data.get("responses", [])
                                        if not r.get("skipped")
                                    ]),
                                },
                                started_at=datetime.now(timezone.utc),
                                completed_at=datetime.now(timezone.utc),
                            )
                            session.add(sim_run)

            # Step 4A: ChromaDB (file path reference)
            chroma_dir = out_dir / "step4_chromadb"
            if chroma_dir.exists():
                session.add(PipelineStepOutput(
                    participant_id=participant.id,
                    job_id=job.id,
                    step_name="step4_vector",
                    mode="1to1",
                    output_data={"status": "built"},
                    file_path=str(chroma_dir),
                ))

            # Step 4B: Knowledge graph
            kg_path = out_dir / "step4_knowledge_graph.json"
            if kg_path.exists():
                with open(kg_path) as f:
                    kg_data = json.load(f)
                session.add(PipelineStepOutput(
                    participant_id=participant.id,
                    job_id=job.id,
                    step_name="step4_kg",
                    mode="1to1",
                    output_data=kg_data,
                ))

            session.flush()
            imported += 1
            print(f"    OK: participant + twin + step outputs created")

        session.commit()
        print(f"\nDone: {imported} imported, {skipped} skipped")


def _build_m8_questionnaire_snapshot() -> dict:
    """Build a questionnaire snapshot from the hardcoded M8 questionnaire for imported data."""
    try:
        # Import from twin-generator
        twin_gen_root = str(TWIN_GEN)
        if twin_gen_root not in sys.path:
            sys.path.insert(0, twin_gen_root)
        from scripts.step5_m8_simulation import build_m8_questionnaire, M8_CONCEPTS
        questions = build_m8_questionnaire()
        concepts = [
            {
                "concept_index": c["concept_index"],
                "product_name": c["product_name"],
                "consumer_insight": c.get("consumer_insight", ""),
                "key_benefit": c.get("key_benefit", ""),
                "how_it_works": c.get("how_it_works", ""),
                "price": c.get("price", ""),
            }
            for c in M8_CONCEPTS
        ]
        return {"questions": questions, "concepts": concepts}
    except Exception as e:
        print(f"WARNING: Could not build M8 questionnaire snapshot: {e}")
        return {"questions": [], "concepts": [], "note": "M8 questionnaire not available at import time"}


if __name__ == "__main__":
    # Ensure tables exist
    Base.metadata.create_all(sync_engine)
    import_participants()
