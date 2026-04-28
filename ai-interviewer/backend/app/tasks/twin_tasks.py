"""Celery tasks for twin pipeline: create_twin_pipeline, run_simulation_pipeline."""

import asyncio
import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.celery_app import celery_app
from app.config import settings
from app.database import sync_session_factory
from app.models.twin import (
    DigitalTwin,
    Participant,
    PipelineJob,
    PipelineStepOutput,
    SimulationRun,
)
from app.services.twin_service import (
    sync_create_twin,
    sync_get_participant,
    sync_get_step_output,
    sync_save_step_output,
    sync_update_job,
    sync_update_simulation_run,
)

logger = logging.getLogger(__name__)

TWIN_DATA_DIR = Path(settings.twin_data_dir)


def _load_question_bank() -> list[dict]:
    qb_path = TWIN_DATA_DIR / "input" / "question_bank.json"
    with open(qb_path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Task 1: Create Twin Pipeline (Steps 2-4)
# ---------------------------------------------------------------------------

@celery_app.task(bind=True, name="twin.create_pipeline")
def create_twin_pipeline(self, job_id: str, participant_id: str, n_twins: int = 1):
    """Run twin creation pipeline (steps 2-4) for a participant."""
    job_uuid = uuid.UUID(job_id)
    participant_uuid = uuid.UUID(participant_id)
    mode = "1to1" if n_twins == 1 else "branched"

    with sync_session_factory() as session:
        try:
            # Mark job as running
            sync_update_job(
                session, job_uuid,
                status="running",
                started_at=datetime.now(timezone.utc),
                celery_task_id=self.request.id,
            )
            session.commit()

            # Load participant and question bank
            participant = sync_get_participant(session, participant_uuid)
            if not participant:
                raise ValueError(f"Participant {participant_id} not found")

            question_bank = _load_question_bank()
            pid = participant.external_id
            output_dir = TWIN_DATA_DIR / "output" / pid
            output_dir.mkdir(parents=True, exist_ok=True)

            participant_data = {
                "participant_id": pid,
                "qa_pairs": participant.profile_qa,
            }
            real_qa = participant.profile_qa
            progress = {}

            # --- Step 2: Branching ---
            if mode == "1to1":
                progress["step2"] = "skipped"
                sync_update_job(session, job_uuid, current_step="step3", progress=progress)
                session.commit()
            else:
                existing_step2 = sync_get_step_output(session, participant_uuid, "step2_pruned", mode)
                if existing_step2:
                    logger.info(f"[{pid}] Step 2 already exists, skipping")
                    progress["step2"] = "skipped_existing"
                else:
                    sync_update_job(session, job_uuid, current_step="step2", progress=progress)
                    session.commit()
                    logger.info(f"[{pid}] Running Step 2: Branching...")
                    from scripts import step2_branching as step2
                    step2_result = asyncio.run(
                        step2.run_for_participant(participant_data, question_bank, output_dir)
                    )
                    # Save step2 outputs to DB
                    sync_save_step_output(
                        session, participant_id=participant_uuid,
                        step_name="step2_pruned", mode=mode,
                        output_data=step2_result, job_id=job_uuid,
                    )
                    # Also save dimensions and archetypes if files were written
                    for fname, step_name in [
                        ("step2_dimensions.json", "step2_dimensions"),
                        ("step2_archetypes.json", "step2_archetypes"),
                    ]:
                        fpath = output_dir / fname
                        if fpath.exists():
                            with open(fpath) as f:
                                data = json.load(f)
                            sync_save_step_output(
                                session, participant_id=participant_uuid,
                                step_name=step_name, mode=mode,
                                output_data=data, job_id=job_uuid,
                            )
                    progress["step2"] = "completed"
                    session.commit()

            # --- Step 3: Profile Expansion ---
            existing_step3 = sync_get_step_output(session, participant_uuid, "step3_profiles", mode)
            existing_twins = session.execute(
                DigitalTwin.__table__.select().where(
                    DigitalTwin.participant_id == participant_uuid
                )
            ).fetchall()

            if existing_step3 and existing_twins:
                logger.info(f"[{pid}] Step 3 already exists, skipping")
                progress["step3"] = "skipped_existing"
                sync_update_job(session, job_uuid, current_step="step4a", progress=progress)
                session.commit()
            else:
                sync_update_job(session, job_uuid, current_step="step3", progress=progress)
                session.commit()
                logger.info(f"[{pid}] Running Step 3: Profile Expansion ({mode})...")

                if mode == "1to1":
                    from scripts import step3_direct_expansion as step3
                    step3_result = asyncio.run(
                        step3.run_for_participant(pid, real_qa, question_bank, output_dir)
                    )
                else:
                    from scripts import step3_profile_expansion as step3
                    pruned_path = output_dir / "step2_pruned_twins.json"
                    with open(pruned_path) as f:
                        pruned_data = json.load(f)[0]
                    step3_result = asyncio.run(
                        step3.run_for_participant(pid, real_qa, pruned_data, question_bank, output_dir)
                    )

                # Save step3 to DB
                sync_save_step_output(
                    session, participant_id=participant_uuid,
                    step_name="step3_profiles", mode=mode,
                    output_data=step3_result, job_id=job_uuid,
                )

                # Create DigitalTwin rows from step3 output
                profiles_path = output_dir / "step3_complete_profiles.json"
                with open(profiles_path) as f:
                    profiles = json.load(f)
                for p_data in profiles:
                    for twin_data in p_data.get("twins", []):
                        from collections import Counter
                        qa_pairs = twin_data.get("qa_pairs", [])
                        sources = Counter(qa.get("source", "unknown") for qa in qa_pairs)
                        sync_create_twin(
                            session,
                            participant_id=participant_uuid,
                            twin_external_id=twin_data["twin_id"],
                            mode=mode,
                            profile_data=qa_pairs,
                            combo_id=twin_data.get("combo_id"),
                            coherence_score=twin_data.get("coherence_score"),
                            branch_choices=twin_data.get("choices"),
                            profile_stats={
                                "n_real": sources.get("real", 0),
                                "n_branch": sources.get("branch", 0),
                                "n_synthetic": sources.get("synthetic", 0),
                                "n_total": len(qa_pairs),
                            },
                            status="building",
                        )

                progress["step3"] = "completed"
                session.commit()

            # --- Step 4A: Vector Index ---
            existing_step4a = sync_get_step_output(session, participant_uuid, "step4_vector", mode)
            chroma_dir = output_dir / "step4_chromadb"
            if existing_step4a and chroma_dir.exists():
                logger.info(f"[{pid}] Step 4A already exists, skipping")
                progress["step4a"] = "skipped_existing"
                sync_update_job(session, job_uuid, current_step="step4b", progress=progress)
                session.commit()
            else:
                sync_update_job(session, job_uuid, current_step="step4a", progress=progress)
                session.commit()
                logger.info(f"[{pid}] Running Step 4A: Vector Index...")
                from scripts import step4_vector_index as step4_vector
                step4_vector.build_for_participant(pid, output_dir)
                sync_save_step_output(
                    session, participant_id=participant_uuid,
                    step_name="step4_vector", mode=mode,
                    output_data={"status": "built"},
                    job_id=job_uuid,
                    file_path=str(chroma_dir),
                )
                progress["step4a"] = "completed"
                session.commit()

            # --- Step 4B: Knowledge Graph ---
            existing_step4b = sync_get_step_output(session, participant_uuid, "step4_kg", mode)
            if existing_step4b and existing_step4b.output_data:
                logger.info(f"[{pid}] Step 4B already exists, skipping")
                progress["step4b"] = "skipped_existing"
            else:
                sync_update_job(session, job_uuid, current_step="step4b", progress=progress)
                session.commit()
                logger.info(f"[{pid}] Running Step 4B: Knowledge Graph...")
                from scripts import step4_kg_build as step4_kg
                asyncio.run(step4_kg.build_kg_for_participant(pid, output_dir))
                # Read KG from file and save to DB
                kg_path = output_dir / "step4_knowledge_graph.json"
                if kg_path.exists():
                    with open(kg_path) as f:
                        kg_data = json.load(f)
                    sync_save_step_output(
                        session, participant_id=participant_uuid,
                        step_name="step4_kg", mode=mode,
                        output_data=kg_data, job_id=job_uuid,
                    )
                progress["step4b"] = "completed"
                session.commit()

            # --- Mark all twins as ready ---
            from sqlalchemy import update
            session.execute(
                update(DigitalTwin)
                .where(DigitalTwin.participant_id == participant_uuid)
                .values(status="ready")
            )

            # Mark job as completed
            sync_update_job(
                session, job_uuid,
                status="completed",
                current_step=None,
                progress=progress,
                result_summary={"mode": mode, "steps": progress},
                completed_at=datetime.now(timezone.utc),
            )
            session.commit()
            logger.info(f"[{pid}] Twin creation pipeline complete: {progress}")

        except Exception as e:
            session.rollback()
            logger.error(f"Twin pipeline failed for {participant_id}: {e}", exc_info=True)
            with sync_session_factory() as err_session:
                sync_update_job(
                    err_session, job_uuid,
                    status="failed",
                    error_message=str(e),
                    completed_at=datetime.now(timezone.utc),
                )
                err_session.commit()
            raise


# ---------------------------------------------------------------------------
# Task 2: Run Simulation Pipeline (Step 5)
# ---------------------------------------------------------------------------

@celery_app.task(bind=True, name="twin.run_simulation")
def run_simulation_pipeline(self, job_id: str, simulation_id: str):
    """Run step 5 simulation for a single twin with a given questionnaire."""
    job_uuid = uuid.UUID(job_id)
    sim_uuid = uuid.UUID(simulation_id)

    with sync_session_factory() as session:
        try:
            # Mark job as running
            sync_update_job(
                session, job_uuid,
                status="running",
                current_step="step5",
                started_at=datetime.now(timezone.utc),
                celery_task_id=self.request.id,
            )
            sync_update_simulation_run(
                session, sim_uuid,
                status="running",
                started_at=datetime.now(timezone.utc),
            )
            session.commit()

            # Load simulation run
            sim_run = session.get(SimulationRun, sim_uuid)
            if not sim_run:
                raise ValueError(f"SimulationRun {simulation_id} not found")

            twin = session.get(DigitalTwin, sim_run.twin_id)
            if not twin:
                raise ValueError(f"Twin {sim_run.twin_id} not found")

            participant = session.get(Participant, twin.participant_id)
            if not participant:
                raise ValueError(f"Participant {twin.participant_id} not found")

            pid = participant.external_id
            output_dir = TWIN_DATA_DIR / "output" / pid

            # Verify prerequisites
            chroma_step = sync_get_step_output(session, participant.id, "step4_vector", twin.mode)
            kg_step = sync_get_step_output(session, participant.id, "step4_kg", twin.mode)

            if not chroma_step or not chroma_step.file_path:
                raise ValueError(f"Twin {twin.twin_external_id} missing ChromaDB (step4_vector)")
            if not Path(chroma_step.file_path).exists():
                raise ValueError(f"ChromaDB directory not found: {chroma_step.file_path}")
            if not kg_step or not kg_step.output_data:
                raise ValueError(f"Twin {twin.twin_external_id} missing knowledge graph (step4_kg)")

            # Extract questionnaire from snapshot
            snapshot = sim_run.questionnaire_snapshot
            questionnaire = snapshot.get("questions", [])
            concepts = snapshot.get("concepts", [])
            # Present only for ad_creative_testing — the Product Brief is passed
            # into every batch's prompt as per-study context but never written
            # to the twin's persistent memory.
            product_brief = snapshot.get("product_brief")
            inference_mode = sim_run.inference_mode

            # Load ChromaDB and KG
            from scripts.step4_inference import get_chroma_collection_for, get_kg_for
            collection = get_chroma_collection_for(output_dir)
            kg = get_kg_for(output_dir)

            # Run simulation
            from scripts.step5_m8_simulation import run_simulation
            m8_out = output_dir / "step5_m8_simulation"
            m8_out.mkdir(parents=True, exist_ok=True)

            responses = asyncio.run(
                run_simulation(
                    twin_id=twin.twin_external_id,
                    questionnaire=questionnaire,
                    concepts=concepts,
                    mode=inference_mode,
                    output_dir=m8_out,
                    participant_id=pid,
                    collection=collection,
                    kg=kg,
                    product_brief=product_brief,
                )
            )

            # Save results
            sync_update_simulation_run(
                session, sim_uuid,
                status="completed",
                responses=responses,
                summary_stats={
                    "question_count": len(questionnaire),
                    "answered_count": len([r for r in responses if not r.get("skipped")]),
                },
                completed_at=datetime.now(timezone.utc),
            )
            sync_update_job(
                session, job_uuid,
                status="completed",
                current_step=None,
                progress={"step5": "completed"},
                completed_at=datetime.now(timezone.utc),
            )
            session.commit()
            logger.info(f"Simulation complete for twin {twin.twin_external_id}")

        except Exception as e:
            session.rollback()
            logger.error(f"Simulation failed for job {job_id}: {e}", exc_info=True)
            with sync_session_factory() as err_session:
                sync_update_job(
                    err_session, job_uuid,
                    status="failed",
                    error_message=str(e),
                    completed_at=datetime.now(timezone.utc),
                )
                sync_update_simulation_run(
                    err_session, sim_uuid,
                    status="failed",
                )
                err_session.commit()
            raise
