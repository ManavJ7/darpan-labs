"""LLM-based archetype classifier + routing.

Called from Orchestrator._emit_next_interviewer_turn when cursor
reports phase_id="phase2" (no archetype set yet). Either:

    (a) writes an AdaptiveClassification row, commits the archetype
        to session.settings, and hands control back for the first
        Phase 3 turn, OR

    (b) emits a short disambiguation question as a P2Dx turn when
        confidence < 0.50. After the respondent answers, the
        classifier runs again with the extra context. Max 2
        disambiguation rounds per spec §5.4.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings as app_settings
from app.llm.client import LLMError, get_classifier_client
from app.models import AdaptiveClassification, InterviewSession, InterviewTurn
from app.schemas import InterviewerMessage
from app.services.phase_defs import Archetype
from app.services.turns_repo import (
    load_turns,
    next_turn_index,
    record_interviewer_turn,
)

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
CLASSIFIER_SYSTEM = (PROMPTS_DIR / "classifier_system.md").read_text(encoding="utf-8")


class ProbVector(BaseModel):
    prosumer: float = Field(..., ge=0.0, le=1.0)
    smb_it: float = Field(..., ge=0.0, le=1.0)
    consumer: float = Field(..., ge=0.0, le=1.0)


class ClassifierResult(BaseModel):
    probs: ProbVector
    primary: Archetype
    secondary: Optional[Archetype] = None
    is_hybrid: bool = False
    is_enterprise_flag: bool = False
    confidence: float = Field(..., ge=0.0, le=1.0)
    rationale: str
    needs_disambiguation: bool = False
    disambiguation_question: Optional[str] = None


def _build_context(turns: list[InterviewTurn], disambig_round: int) -> str:
    """Shape the LLM prompt from persisted turns."""
    lines: list[str] = []
    for t in turns:
        if not t.module_id.startswith("P"):
            continue
        if t.role == "interviewer" and t.question_text:
            lines.append(f"Q ({t.module_id}): {t.question_text.strip()}")
        elif t.role == "user":
            body = (t.answer_text or "").strip()
            if t.answer_structured:
                body = f"{body} [structured: {t.answer_structured}]"
            lines.append(f"A: {body or '[no answer]'}")
    context = "\n".join(lines) if lines else "[no context]"
    return f"DISAMBIGUATION_ROUND: {disambig_round}\n\nCONTEXT:\n{context}"


async def _persist_classification(
    db: AsyncSession,
    session: InterviewSession,
    result: ClassifierResult,
    trigger: str,
) -> AdaptiveClassification:
    count_res = await db.execute(
        select(func.count(AdaptiveClassification.id))
        .where(AdaptiveClassification.session_id == session.id)
    )
    sequence_index = int(count_res.scalar() or 0)
    row = AdaptiveClassification(
        session_id=session.id,
        sequence_index=sequence_index,
        probs={
            "prosumer": result.probs.prosumer,
            "smb_it": result.probs.smb_it,
            "consumer": result.probs.consumer,
        },
        primary_archetype=result.primary,
        secondary_archetype=result.secondary,
        is_hybrid=result.is_hybrid,
        is_enterprise_flag=result.is_enterprise_flag,
        rationale=result.rationale,
        trigger=trigger,
    )
    db.add(row)
    await db.flush()
    return row


def _should_disambiguate(result: ClassifierResult, disambig_round: int) -> bool:
    if disambig_round >= 2:
        return False
    if result.confidence >= app_settings.adaptive_classify_min_confidence:
        return False
    if not result.needs_disambiguation:
        return False
    return bool(result.disambiguation_question and result.disambiguation_question.strip())


def _infer_hybrid(result: ClassifierResult) -> bool:
    """Belt-and-suspenders check against the LLM's own is_hybrid: if
    primary ∈ [hybrid_floor, min_confidence) AND secondary ≥
    hybrid_second, flag as hybrid regardless of what the LLM said."""
    if result.is_hybrid:
        return True
    probs = [result.probs.prosumer, result.probs.smb_it, result.probs.consumer]
    top, second = sorted(probs, reverse=True)[:2]
    return (
        app_settings.adaptive_classify_hybrid_floor <= top < app_settings.adaptive_classify_min_confidence
        and second >= app_settings.adaptive_classify_hybrid_second
    )


async def _invoke(turns: list[InterviewTurn], disambig_round: int) -> ClassifierResult:
    client = get_classifier_client()
    prompt = _build_context(turns, disambig_round)
    try:
        result = await client.generate(
            prompt=prompt,
            system=CLASSIFIER_SYSTEM,
            response_format=ClassifierResult,
        )
    except LLMError as e:
        logger.error(f"Classifier LLM failed: {e}")
        # Deterministic fallback: default to prosumer with low
        # confidence so the flow can continue. QA will flag this.
        result = ClassifierResult(
            probs=ProbVector(prosumer=0.40, smb_it=0.30, consumer=0.30),
            primary="prosumer",
            secondary="smb_it",
            is_hybrid=False,
            is_enterprise_flag=False,
            confidence=0.40,
            rationale=f"LLM error fallback: {e}",
            needs_disambiguation=False,
        )
    assert isinstance(result, ClassifierResult)
    return result


async def run_phase2(
    db: AsyncSession,
    session: InterviewSession,
    records=None,  # unused here; orchestrator passes for signature compat
) -> InterviewerMessage:
    """Core entry point — called when cursor.phase_id == 'phase2'."""
    turns = await load_turns(db, session.id)
    disambig_round = sum(
        1 for t in turns
        if t.role == "interviewer" and (t.module_id or "").startswith("P2D")
    )
    result = await _invoke(turns, disambig_round)
    result.is_hybrid = _infer_hybrid(result)

    trigger = "disambig" if disambig_round > 0 else "initial"
    await _persist_classification(db, session, result, trigger=trigger)

    if _should_disambiguate(result, disambig_round):
        question = result.disambiguation_question or ""
        module_code = f"P2D{disambig_round + 1}"[:10]
        idx = await next_turn_index(db, session.id)
        await record_interviewer_turn(
            db,
            session_id=session.id,
            module_code=module_code,
            turn_index=idx,
            question_text=question,
            phase_id="phase2",
            probe_index=0,
            item_satisfied=False,
            extra_meta={
                "classifier_probs": {
                    "prosumer": result.probs.prosumer,
                    "smb_it": result.probs.smb_it,
                    "consumer": result.probs.consumer,
                },
                "confidence": result.confidence,
                "rationale": result.rationale,
            },
        )
        return InterviewerMessage(
            phase="phase2",
            block="disambiguation",
            item_id=f"phase2.{module_code}",
            text=question,
            is_terminal=False,
            progress_label="just getting started",
        )

    # Commit archetype & hand back to orchestrator for first Phase 3 turn.
    settings_blob = dict(session.settings or {})
    settings_blob["archetype"] = result.primary
    settings_blob["is_hybrid"] = result.is_hybrid
    settings_blob["is_enterprise_flag"] = result.is_enterprise_flag
    if result.is_enterprise_flag:
        settings_blob.setdefault("flags", {})["enterprise"] = True
    session.settings = settings_blob
    await db.flush()

    # Late-import the Orchestrator to avoid a circular import at module load.
    from app.services.orchestrator import Orchestrator
    orch = Orchestrator(db)
    return await orch._emit_next_interviewer_turn(session=session)


async def trigger_reclassification(
    db: AsyncSession,
    session: InterviewSession,
    hint_archetype: str,
) -> Optional[str]:
    """Invoked by orchestrator when an interviewer turn reported a
    reclassify_signal. Runs classifier on the full turn log (not just
    phase1) and, if the new result disagrees with the current
    archetype, swaps it over.

    Returns the new archetype if it changed, else None.

    Respects `adaptive_max_reclassifications`.
    """
    current_archetype: Optional[Archetype] = (session.settings or {}).get("archetype")
    recls_res = await db.execute(
        select(func.count(AdaptiveClassification.id))
        .where(AdaptiveClassification.session_id == session.id)
        .where(AdaptiveClassification.trigger == "reclassify")
    )
    reclassifications_done = int(recls_res.scalar() or 0)
    if reclassifications_done >= app_settings.adaptive_max_reclassifications:
        return None

    turns = await load_turns(db, session.id)
    # Use a virtual "disambig_round" of 2 to force commitment (no
    # further disambiguation prompts during reclassification).
    result = await _invoke(turns, disambig_round=2)
    result.is_hybrid = _infer_hybrid(result)
    await _persist_classification(db, session, result, trigger="reclassify")

    if result.primary == current_archetype:
        return None

    settings_blob = dict(session.settings or {})
    settings_blob["archetype"] = result.primary
    settings_blob["is_hybrid"] = result.is_hybrid
    settings_blob.setdefault("reclassify_history", []).append(
        {"from": current_archetype, "to": result.primary, "hint": hint_archetype}
    )
    session.settings = settings_blob
    await db.flush()
    return result.primary
