"""Deterministic state machine over persisted turns.

Given an InterviewSession and its turns, compute "where are we" and
"what comes next". The LLM never decides flow — only natural
language. This separation is what lets QA coverage guarantees hold.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.services.phase_defs import (
    Archetype,
    ItemDef,
    PhaseDef,
    all_items,
    get_phase,
)

PHASE_ORDER_PRE_ARCHETYPE: list[str] = ["phase1", "phase2"]
PHASE_ORDER_POST_ARCHETYPE: list[str] = ["phase4"]

ARCHETYPE_PHASE_MAP: dict[Archetype, str] = {
    "prosumer": "phase3a",
    "smb_it": "phase3b",
    "consumer": "phase3c",
}


@dataclass
class Cursor:
    phase_id: str
    item: Optional[ItemDef]
    probe_index: int              # 0 = initial ask, 1+ = follow-ups already sent
    is_phase_boundary: bool       # True when item is the first in its phase
    is_terminal: bool = False


@dataclass
class TurnRecord:
    module_code: str
    role: str                     # "interviewer" | "user"
    probe_index: int
    item_satisfied: bool          # interviewer's own `advance` flag
    answer_text: Optional[str]
    answer_structured: Optional[dict]


def ordered_phase_ids(archetype: Optional[Archetype]) -> list[str]:
    """Full phase sequence for the current interview."""
    seq = list(PHASE_ORDER_PRE_ARCHETYPE)
    if archetype is not None:
        seq.append(ARCHETYPE_PHASE_MAP[archetype])
    seq.extend(PHASE_ORDER_POST_ARCHETYPE)
    return seq


def flatten_items(archetype: Optional[Archetype]) -> list[ItemDef]:
    items: list[ItemDef] = []
    for pid in ordered_phase_ids(archetype):
        if get_phase(pid) is None:
            continue
        items.extend(all_items(pid))
    return items


def compute_cursor(
    turns: list[TurnRecord],
    archetype: Optional[Archetype],
) -> Cursor:
    """Walk the item sequence in order. The cursor is the first item
    that either has zero interviewer turns or the most recent
    interviewer turn for that item did not advance (probe still owed)
    and has an associated user answer.
    """
    items = flatten_items(archetype)
    if not items:
        return Cursor(phase_id="complete", item=None, probe_index=0,
                      is_phase_boundary=False, is_terminal=True)

    # Group interviewer turns per item in order.
    per_item: dict[str, list[TurnRecord]] = {}
    for t in turns:
        per_item.setdefault(t.module_code, []).append(t)

    last_phase = None
    for item in items:
        records = per_item.get(item.module_code, [])
        interviewer_records = [r for r in records if r.role == "interviewer"]
        user_records = [r for r in records if r.role == "user"]

        if not interviewer_records:
            # Not asked yet — this is the cursor.
            return Cursor(
                phase_id=item.phase,
                item=item,
                probe_index=0,
                is_phase_boundary=(last_phase != item.phase),
            )

        latest_interviewer = interviewer_records[-1]
        if latest_interviewer.item_satisfied:
            # Item complete → continue scanning.
            last_phase = item.phase
            continue

        # Interviewer asked but item not yet satisfied.
        next_probe_index = latest_interviewer.probe_index + 1
        needs_user = len(user_records) < len(interviewer_records)
        if needs_user:
            # Awaiting user response — state machine shouldn't emit
            # a new interviewer turn yet.
            return Cursor(
                phase_id=item.phase,
                item=item,
                probe_index=next_probe_index,
                is_phase_boundary=False,
            )
        # User answered and interviewer hasn't advanced — probe.
        return Cursor(
            phase_id=item.phase,
            item=item,
            probe_index=next_probe_index,
            is_phase_boundary=False,
        )

    return Cursor(phase_id="complete", item=None, probe_index=0,
                  is_phase_boundary=False, is_terminal=True)


def progress_pct(turns: list[TurnRecord], archetype: Optional[Archetype]) -> float:
    items = flatten_items(archetype)
    if not items:
        return 0.0
    completed = 0
    per_item: dict[str, list[TurnRecord]] = {}
    for t in turns:
        if t.role == "interviewer":
            per_item.setdefault(t.module_code, []).append(t)
    for item in items:
        recs = per_item.get(item.module_code, [])
        if recs and recs[-1].item_satisfied:
            completed += 1
    return round(100.0 * completed / max(len(items), 1), 1)


def phase_label(phase_id: str) -> str:
    phase: Optional[PhaseDef] = get_phase(phase_id)
    return phase.label if phase else phase_id
