"""
Simulation endpoints: serve questionnaire payload for twin simulation,
store and retrieve simulation results.
"""
import csv
import io
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_session
from app.models.study import Study, StepVersion
from app.models.simulation import SimulationRun
from app.schemas.simulation import (
    SimulationPayload,
    SimulationQuestion,
    ConceptText,
    SimulationResultUpload,
    SimulationRunResponse,
)

router = APIRouter(
    prefix=f"{settings.API_V1_PREFIX}/studies/{{study_id}}",
    tags=["simulation"],
)


def _extract_concept_text(components: dict, concept_index: int) -> ConceptText:
    """Extract display text from concept components, handling raw/refined/approved formats."""
    def _get(field: str) -> str:
        comp = components.get(field, {})
        if isinstance(comp, dict):
            # Prefer approved brand_edit > refined > raw_input
            return comp.get("brand_edit") or comp.get("refined") or comp.get("raw_input") or ""
        return str(comp)

    return ConceptText(
        concept_index=concept_index,
        product_name=_get("product_name"),
        consumer_insight=_get("consumer_insight"),
        key_benefit=_get("key_benefit"),
        reasons_to_believe=_get("reasons_to_believe"),
    )


@router.get("/simulation-payload", response_model=SimulationPayload)
async def get_simulation_payload(
    study_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
):
    """Serve a clean questionnaire + concept text payload for twin simulation."""
    # Load study
    result = await db.execute(select(Study).where(Study.id == study_id))
    study = result.scalar_one_or_none()
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")

    if study.status not in ("step_4_locked", "complete"):
        raise HTTPException(
            status_code=400,
            detail=f"Study must be locked or complete to simulate. Current status: {study.status}",
        )

    # Get locked questionnaire (step 4, latest version with status=locked)
    q_result = await db.execute(
        select(StepVersion)
        .where(StepVersion.study_id == study_id, StepVersion.step == 4, StepVersion.status == "locked")
        .order_by(StepVersion.version.desc())
        .limit(1)
    )
    q_version = q_result.scalar_one_or_none()
    if not q_version:
        raise HTTPException(status_code=400, detail="No locked questionnaire found")

    content = q_version.content

    # Extract questions from sections
    questions: list[SimulationQuestion] = []
    for section in content.get("sections", []):
        for q in section.get("questions", []):
            questions.append(SimulationQuestion(
                question_id=q["question_id"],
                question_text=q.get("question_text", {}),
                question_type=q.get("question_type", "open_text"),
                scale=q.get("scale"),
                show_if=q.get("show_if"),
                required=q.get("required", True),
                section=section.get("section_id", ""),
                position_in_section=q.get("position_in_section", 0),
            ))

    # Get locked concept boards (step 2)
    concepts: list[ConceptText] = []
    c_result = await db.execute(
        select(StepVersion)
        .where(StepVersion.study_id == study_id, StepVersion.step == 2, StepVersion.status == "locked")
        .order_by(StepVersion.version.desc())
        .limit(1)
    )
    c_version = c_result.scalar_one_or_none()
    if c_version and c_version.content:
        for c in c_version.content.get("concepts", []):
            comp = c.get("components", {})
            idx = c.get("concept_index", 0)
            concepts.append(_extract_concept_text(comp, idx))

    return SimulationPayload(
        study_id=str(study_id),
        study_title=study.title,
        brand_name=study.brand_name,
        category=study.category,
        questions=questions,
        concepts=concepts,
    )


@router.post("/simulation-results", response_model=SimulationRunResponse)
async def upload_simulation_results(
    study_id: uuid.UUID,
    data: SimulationResultUpload,
    db: AsyncSession = Depends(get_session),
):
    """Upload simulation results from the bridge script."""
    # Verify study exists
    result = await db.execute(select(Study).where(Study.id == study_id))
    study = result.scalar_one_or_none()
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")

    run = SimulationRun(
        study_id=study_id,
        status="completed",
        inference_mode=data.inference_mode,
        twin_count=data.twin_count,
        question_count=data.question_count,
        results=data.model_dump(),
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    return SimulationRunResponse(
        id=run.id,
        study_id=run.study_id,
        status=run.status,
        inference_mode=run.inference_mode,
        twin_count=run.twin_count,
        question_count=run.question_count,
        results=run.results,
        summary=run.summary,
        created_at=run.created_at,
    )


@router.get("/simulation-results", response_model=list[SimulationRunResponse])
async def list_simulation_results(
    study_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
):
    """List all simulation runs for a study."""
    result = await db.execute(
        select(SimulationRun)
        .where(SimulationRun.study_id == study_id)
        .order_by(SimulationRun.created_at.desc())
    )
    runs = result.scalars().all()
    return [
        SimulationRunResponse(
            id=r.id,
            study_id=r.study_id,
            status=r.status,
            inference_mode=r.inference_mode,
            twin_count=r.twin_count,
            question_count=r.question_count,
            results=r.results,
            summary=r.summary,
            created_at=r.created_at,
        )
        for r in runs
    ]


@router.get("/simulation-results/{run_id}/export")
async def export_simulation_results(
    study_id: uuid.UUID,
    run_id: uuid.UUID,
    format: str = "json",
    db: AsyncSession = Depends(get_session),
):
    """Export simulation results as JSON or CSV."""
    result = await db.execute(
        select(SimulationRun).where(
            SimulationRun.id == run_id,
            SimulationRun.study_id == study_id,
        )
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Simulation run not found")

    data = run.results

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)

        # Build header from first twin's responses
        twin_results = data.get("results", [])
        if not twin_results:
            raise HTTPException(status_code=400, detail="No results to export")

        # Collect all question IDs in order
        q_ids = []
        for resp in twin_results[0].get("responses", []):
            q_ids.append(resp["question_id"])

        header = ["twin_id", "participant_id", "coherence_score"]
        for qid in q_ids:
            header.extend([qid, f"{qid}_raw"])
        writer.writerow(header)

        for twin in twin_results:
            row = [
                twin.get("twin_id", ""),
                twin.get("participant_id", ""),
                twin.get("coherence_score", ""),
            ]
            resp_map = {r["question_id"]: r for r in twin.get("responses", [])}
            for qid in q_ids:
                r = resp_map.get(qid, {})
                row.append(r.get("structured_answer", ""))
                row.append(r.get("raw_answer", ""))
            writer.writerow(row)

        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=simulation_{run_id}.csv"},
        )

    # Default: JSON
    return data
