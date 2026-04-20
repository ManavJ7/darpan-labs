"""Orchestrator — composes state machine, interviewer LLM, and DB.

Phase 1 flows end to end in this chunk. Phase 2 classification, Phase
3 variant bodies, and Phase 4 tail light up as later chunks register
their phase defs with `phase_defs.register_phase`.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import InterviewSession
from app.schemas import CompleteInterviewResponse, InterviewStateResponse, InterviewerMessage
from app.services.interviewer import Interviewer, TurnContext
from app.services.item_injections import resolve_item_prompt
from app.services.phase_defs import Archetype, find_item
from app.services.state_machine import (
    ARCHETYPE_PHASE_MAP,
    Cursor,
    compute_cursor,
    flatten_items,
    phase_label,
    progress_pct,
)
from app.services.turns_repo import (
    load_session,
    load_turns,
    next_turn_index,
    record_interviewer_turn,
    record_user_turn,
    to_records,
)
from app.services.widget_resolver import resolve_widget

STRUCTURED_KINDS = {"conjoint", "slider_matrix", "slider_battery", "rank", "tone_pair"}


def _clone_item_with_prompt(item, new_prompt: str):
    """Return a shallow copy of the item with `prompt` replaced.
    Used to inject archetype-specific text (e.g. projective close)
    without mutating the shared ItemDef registry."""
    import dataclasses
    return dataclasses.replace(item, prompt=new_prompt)

logger = logging.getLogger(__name__)


class Orchestrator:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.interviewer = Interviewer()

    # ------------------------- start ------------------------------

    async def start(
        self,
        user_id: UUID,
        input_mode: str = "text",
        language_preference: str = "auto",
    ) -> tuple[UUID, InterviewerMessage]:
        session = InterviewSession(
            id=uuid4(),
            user_id=user_id,
            status="active",
            input_mode=input_mode,
            language_preference=language_preference,
            settings={"archetype": None, "flags": {}},
        )
        self.db.add(session)
        await self.db.flush()

        # Welcome + first item
        opening = (
            "Hi — I'm an AI interviewer. I'd love about an hour of your "
            "time to understand how you think about technology you use "
            "every day, especially laptops. There are no right answers; "
            "I just want to understand your world. Nothing you say will "
            "be shared with your name attached."
        )
        message = await self._emit_next_interviewer_turn(
            session=session,
            prepend_text=opening,
        )
        return session.id, message

    # ------------------------- post_turn --------------------------

    async def post_turn(
        self,
        session_id: UUID,
        answer_text: Optional[str] = None,
        answer_structured: Optional[dict[str, Any]] = None,
        client_meta: Optional[dict[str, Any]] = None,
    ) -> InterviewerMessage:
        session = await load_session(self.db, session_id)
        if session is None:
            raise ValueError("Session not found")
        if session.status != "active":
            raise ValueError(f"Session is {session.status}")

        archetype: Optional[Archetype] = (session.settings or {}).get("archetype")
        turns = await load_turns(self.db, session_id)
        records = to_records(turns)
        cursor = compute_cursor(records, archetype)
        if cursor.item is None:
            raise ValueError("Interview already at terminal cursor")

        # The latest interviewer turn is the one we are answering.
        interviewer_turns = [t for t in turns if t.role == "interviewer"]
        if not interviewer_turns:
            raise ValueError("No interviewer question outstanding")
        latest = interviewer_turns[-1]
        module_code = latest.module_id

        idx = await next_turn_index(self.db, session_id)
        await record_user_turn(
            self.db,
            session_id=session_id,
            module_code=module_code,
            turn_index=idx,
            answer_text=answer_text,
            answer_structured=answer_structured,
            client_meta=client_meta,
        )

        # Reclassification trigger: if the most recent interviewer
        # turn reported a reclassify_signal AND we are already in a
        # phase-3 variant, re-run the classifier before emitting the
        # next turn. Capped by adaptive_max_reclassifications.
        await self._maybe_reclassify(session)

        # Re-read turns, then decide next interviewer move.
        return await self._emit_next_interviewer_turn(session=session)

    # ------------------------- get_state --------------------------

    async def get_state(self, session_id: UUID) -> Optional[InterviewStateResponse]:
        session = await load_session(self.db, session_id)
        if session is None:
            return None
        archetype: Optional[Archetype] = (session.settings or {}).get("archetype")
        turns = await load_turns(self.db, session_id)
        records = to_records(turns)
        cursor = compute_cursor(records, archetype)

        elapsed = 0
        if session.started_at:
            started = session.started_at
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
            elapsed = int((datetime.now(timezone.utc) - started).total_seconds())

        return InterviewStateResponse(
            session_id=session.id,
            status=session.status,
            phase=cursor.phase_id,
            block=cursor.item.block if cursor.item else None,
            archetype=archetype,
            progress_pct=progress_pct(records, archetype),
            elapsed_sec=elapsed,
        )

    # ------------------------- finalize (stub) --------------------

    async def finalize(self, session_id: UUID) -> Optional[CompleteInterviewResponse]:
        raise NotImplementedError("Implemented in chunk F")

    # ------------------------- internals --------------------------

    async def _emit_next_interviewer_turn(
        self,
        *,
        session: InterviewSession,
        prepend_text: Optional[str] = None,
    ) -> InterviewerMessage:
        """Compute cursor, invoke classifier/interviewer LLM if
        needed, persist the interviewer turn, and return the message."""
        archetype: Optional[Archetype] = (session.settings or {}).get("archetype")
        turns = await load_turns(self.db, session.id)
        records = to_records(turns)
        cursor = compute_cursor(records, archetype)

        # After phase 1 completes and no archetype is set, run classifier.
        if cursor.phase_id == "phase2":
            from app.services.classifier import run_phase2
            return await run_phase2(db=self.db, session=session, records=records)

        if cursor.is_terminal:
            return await self._emit_terminal_message(session)

        item = cursor.item
        assert item is not None

        # Resolve any dynamic prompt injections (e.g. archetype-
        # specific projective-close text) + materialize widget.
        resolved_prompt = resolve_item_prompt(item, archetype=archetype)
        resolved_widget = resolve_widget(item.widget, session.id, archetype)

        # Build history for the LLM (prior chat turns across all items).
        history = self._chat_history_from_turns(turns)

        transition_text: Optional[str] = None
        if cursor.is_phase_boundary and not prepend_text:
            transition_text = (
                f"We're now moving into the {phase_label(cursor.phase_id)} phase."
            )

        user_answer = None
        if cursor.probe_index > 0 and turns:
            user_turns = [t for t in turns if t.role == "user"]
            if user_turns:
                user_answer = user_turns[-1].answer_text

        # Auto-advance after a structured response. The respondent
        # submitted the widget's structured answer; mark the current
        # item satisfied via a synthetic interviewer row and recurse
        # to emit the NEXT item naturally.
        if (
            item.kind in STRUCTURED_KINDS
            and cursor.probe_index > 0
            and turns
            and turns[-1].role == "user"
            and turns[-1].answer_structured is not None
        ):
            idx = await next_turn_index(self.db, session.id)
            await record_interviewer_turn(
                self.db,
                session_id=session.id,
                module_code=item.module_code,
                turn_index=idx,
                question_text="[structured advance]",
                phase_id=item.phase,
                probe_index=cursor.probe_index,
                item_satisfied=True,
                widget=None,
                extra_meta={"auto_advance": True},
            )
            return await self._emit_next_interviewer_turn(session=session)

        # Use the item's fixed prompt verbatim for structured kinds so
        # the widget setup isn't paraphrased by the LLM.
        observed: list[str] = []
        reclassify: Optional[str] = None
        if item.kind in STRUCTURED_KINDS and cursor.probe_index == 0:
            body = resolved_prompt or item.prompt
            advance = False
        else:
            effective_item = item
            if resolved_prompt and resolved_prompt != item.prompt:
                effective_item = _clone_item_with_prompt(item, resolved_prompt)
            ctx = TurnContext(
                item=effective_item,
                history=history,
                probe_index=cursor.probe_index,
                phase_transition_text=transition_text,
                archetype=archetype,
            )
            decision = await self.interviewer.decide(ctx, user_answer)
            body = decision.message
            advance = decision.advance
            observed = decision.observed_signals
            reclassify = decision.reclassify_signal
            if cursor.probe_index > item.max_probes:
                advance = True

        if prepend_text:
            body = f"{prepend_text}\n\n{body}"

        idx = await next_turn_index(self.db, session.id)
        await record_interviewer_turn(
            self.db,
            session_id=session.id,
            module_code=item.module_code,
            turn_index=idx,
            question_text=body,
            phase_id=item.phase,
            probe_index=cursor.probe_index,
            item_satisfied=advance,
            widget=resolved_widget,
            extra_meta={
                "observed_signals": observed,
                "reclassify_signal": reclassify,
                "resolved_prompt": resolved_prompt,
            },
        )

        decision_observed = observed
        decision_reclassify = reclassify

        # Persist observed signals into session.settings for the
        # classifier to read later without re-walking every turn.
        if decision_observed or decision_reclassify:
            settings_blob = dict(session.settings or {})
            sig = list(settings_blob.get("signals", []))
            sig.extend(decision_observed or [])
            settings_blob["signals"] = sig
            if decision_reclassify:
                settings_blob.setdefault("reclassify_hints", []).append(decision_reclassify)
            session.settings = settings_blob

        progress_label = self._progress_label(records, archetype)

        return InterviewerMessage(
            phase=item.phase,
            block=item.block,
            item_id=item.id,
            text=body,
            widget=resolved_widget,
            progress_label=progress_label,
            is_terminal=False,
        )

    async def _maybe_reclassify(self, session: InterviewSession) -> None:
        archetype = (session.settings or {}).get("archetype")
        if archetype is None:
            return  # still in phase 1/2 — classifier handles it
        turns = await load_turns(self.db, session.id)
        interviewer_turns = [t for t in turns if t.role == "interviewer"]
        if not interviewer_turns:
            return
        latest_meta = interviewer_turns[-1].question_meta or {}
        hint = latest_meta.get("reclassify_signal")
        if not hint:
            return
        from app.services.classifier import trigger_reclassification
        await trigger_reclassification(self.db, session, hint)

    async def _emit_terminal_message(self, session: InterviewSession) -> InterviewerMessage:
        session.status = "completed"
        session.ended_at = datetime.now(timezone.utc)
        return InterviewerMessage(
            phase="complete",
            text=(
                "That's it — thanks for this. Your answers feed an "
                "anonymised model, not a named profile. You can close "
                "this tab."
            ),
            is_terminal=True,
        )

    @staticmethod
    def _chat_history_from_turns(turns) -> list[dict[str, str]]:
        """Trim & format prior turns for the LLM context window. Keep
        the last ~20 turns which is plenty for coherent probing."""
        recent = turns[-20:]
        messages: list[dict[str, str]] = []
        for t in recent:
            if t.role == "interviewer" and t.question_text:
                messages.append({"role": "assistant", "content": t.question_text})
            elif t.role == "user":
                content = t.answer_text or ""
                if t.answer_structured:
                    content += f" [structured: {t.answer_structured}]"
                messages.append({"role": "user", "content": content.strip() or "[no text]"})
        return messages

    @staticmethod
    def _progress_label(records, archetype) -> str:
        items = flatten_items(archetype)
        total = max(len(items), 1)
        done = sum(
            1 for i in items
            if any(
                r.module_code == i.module_code and r.role == "interviewer" and r.item_satisfied
                for r in records
            )
        )
        if done < total / 3:
            return "just getting started"
        if done < 2 * total / 3:
            return "about a third of the way"
        return "nearly there"
