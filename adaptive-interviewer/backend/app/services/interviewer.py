"""Interviewer LLM wrapper.

Given (current item, history, phase prompt), the LLM decides:
  1. what to say this turn
  2. whether the item is satisfied
  3. any reclassification signal

The state machine downstream acts on `advance` / `reclassify_signal`.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.llm.client import LLMClient, LLMError, get_llm_client
from app.services.phase_defs import ItemDef

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def _load_prompt(name: str) -> str:
    path = PROMPTS_DIR / name
    return path.read_text(encoding="utf-8")


SYSTEM_PROMPT = _load_prompt("interviewer_system.md")
PHASE_EXTRAS = {
    "phase1": _load_prompt("phase1_preamble.md"),
}


class InterviewerDecision(BaseModel):
    message: str = Field(..., min_length=1)
    advance: bool
    reclassify_signal: Optional[str] = None
    observed_signals: list[str] = Field(default_factory=list)


@dataclass
class TurnContext:
    """Everything the interviewer LLM needs for one decision."""

    item: ItemDef
    history: list[dict[str, str]]    # prior [{role, content}] turns in chat form
    probe_index: int                  # 0 for the initial ask, 1+ for follow-ups
    phase_transition_text: Optional[str] = None  # e.g. "great, now onto..." handoff
    archetype: Optional[str] = None   # current archetype (null in phase 1/2)
    is_last_item_in_phase: bool = False


def _user_message(ctx: TurnContext, user_answer: Optional[str]) -> str:
    """Compose the per-turn user prompt fed to the LLM."""
    parts: list[str] = []
    parts.append(f"CURRENT ITEM:\n  id: {ctx.item.id}\n  kind: {ctx.item.kind}\n"
                 f"  base_prompt: {ctx.item.prompt!r}\n"
                 f"  purpose: {ctx.item.purpose!r}")
    if ctx.item.probing_hints:
        parts.append("PROBING HINTS:\n- " + "\n- ".join(ctx.item.probing_hints))
    parts.append(f"MAX PROBES (including the first ask): {ctx.item.max_probes + 1}")
    parts.append(f"PROBE INDEX FOR THIS ITEM SO FAR: {ctx.probe_index}")
    if ctx.archetype:
        parts.append(f"CURRENT ARCHETYPE ROUTE: {ctx.archetype}")
    if ctx.phase_transition_text:
        parts.append(f"PHASE TRANSITION CUE (optional, weave in naturally): "
                     f"{ctx.phase_transition_text!r}")
    if user_answer is not None:
        parts.append(f"RESPONDENT JUST SAID:\n{user_answer!r}")
        parts.append("DECIDE: probe again or advance? Respond with JSON only.")
    else:
        parts.append(
            "This is the INITIAL ask for this item. Deliver the base "
            "prompt in your own warm voice (you may reflect one thing "
            "they said before, if appropriate). Set advance=false. "
            "Respond with JSON only."
        )
    return "\n\n".join(parts)


class Interviewer:
    def __init__(self, client: Optional[LLMClient] = None):
        self.client = client or get_llm_client()

    async def decide(
        self,
        ctx: TurnContext,
        user_answer: Optional[str],
    ) -> InterviewerDecision:
        system = SYSTEM_PROMPT
        extra = PHASE_EXTRAS.get(ctx.item.phase)
        if extra:
            system = f"{system}\n\n---\n{extra}"

        prompt = _user_message(ctx, user_answer)
        try:
            result = await self.client.generate(
                prompt=prompt,
                system=system,
                history=ctx.history,
                response_format=InterviewerDecision,
            )
        except LLMError as e:
            logger.error(f"Interviewer LLM failed on {ctx.item.id}: {e}")
            # Deterministic fallback so the interview can continue.
            return InterviewerDecision(
                message=ctx.item.prompt if user_answer is None else "Thanks — let's keep going.",
                advance=user_answer is not None,
                reclassify_signal=None,
                observed_signals=[],
            )
        assert isinstance(result, InterviewerDecision)
        return result
