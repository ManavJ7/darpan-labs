"""Static phase / block / item definitions.

Driving philosophy: the *flow* is deterministic (state machine code
below), the *natural language* around each item is LLM-generated
using these definitions as anchors. This keeps coverage guarantees
independent of LLM behavior.

Phase IDs:
    phase1  — universal preamble (all respondents)
    phase2  — silent classification (no user-facing items)
    phase3a — prosumer body
    phase3b — smb_it body
    phase3c — consumer body
    phase4  — universal tail

module_id values stored in interview_turns / interview_modules are
short codes under 10 chars — see ItemDef.module_code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

Archetype = Literal["prosumer", "smb_it", "consumer"]


@dataclass
class ItemDef:
    """One question / battery / widget the interviewer must cover."""

    id: str                       # fully qualified, e.g. "phase1.P1"
    module_code: str              # short id stored in DB, <=10 chars e.g. "P1"
    phase: str
    block: str
    kind: str                     # "open" | "slider_battery" | "conjoint" | "rank" | "tone_pair" | "projective"
    prompt: str                   # base question delivered to the respondent
    purpose: str                  # purpose/signals — fed to interviewer prompt
    probing_hints: list[str] = field(default_factory=list)
    max_probes: int = 2           # how many follow-ups before force-advance
    required: bool = True         # if false, skippable under time pressure
    widget: Optional[dict] = None # structured widget spec (kind != "open")


@dataclass
class BlockDef:
    id: str
    phase: str
    label: str
    budget_minutes: int
    items: list[ItemDef]


@dataclass
class PhaseDef:
    id: str
    label: str
    budget_minutes: int
    blocks: list[BlockDef]
    archetype: Optional[Archetype] = None


# ----------------------- Phase 1 — Universal Preamble -----------------------

PREAMBLE_ITEMS: list[ItemDef] = [
    ItemDef(
        id="phase1.P1",
        module_code="P1",
        phase="phase1",
        block="preamble",
        kind="open",
        prompt=(
            "To get started — what do you do for work, and where? "
            "Just a sentence or two is fine."
        ),
        purpose=(
            "Occupational category + employer size signal. Routing "
            "markers: 'I run / my business / our company' → SMB; "
            "'I work at <large co>' → prosumer; 'student / retired / "
            "between jobs' → consumer."
        ),
        probing_hints=[
            "If the answer is under 15 words, ask ONE clarifying follow-up about industry, company size estimate, or role seniority.",
        ],
        max_probes=1,
    ),
    ItemDef(
        id="phase1.P2",
        module_code="P2",
        phase="phase1",
        block="preamble",
        kind="open",
        prompt=(
            "What laptops or computers do you use regularly — for work, "
            "personally, or both? Include how old they are if you remember."
        ),
        purpose=(
            "Device landscape: count, work vs. personal, recency. "
            "Multiple devices across multiple users → SMB. One-two "
            "personal devices → consumer. Work-issued + personal → "
            "prosumer."
        ),
    ),
    ItemDef(
        id="phase1.P3",
        module_code="P3",
        phase="phase1",
        block="preamble",
        kind="open",
        prompt=(
            "Think about the most recent laptop purchase in your life — "
            "whether you bought it, someone bought it for you, or your "
            "company issued it. When was it, and who made the decision?"
        ),
        purpose=(
            "Strong routing signal. 'I bought it' → prosumer/consumer. "
            "'IT/CTO' → prosumer at large co. 'I decided for the team' "
            "→ SMB. 'Parent/spouse bought it' → consumer."
        ),
        probing_hints=[
            "If the respondent says 'can't remember' or 'a while ago', pivot: 'the last time you were thinking about replacing it — what prompted that?' — don't force a reconstruction that doesn't exist.",
        ],
    ),
    ItemDef(
        id="phase1.P4",
        module_code="P4",
        phase="phase1",
        block="preamble",
        kind="open",
        prompt=(
            "When a new laptop needs to be bought in your world — yours "
            "or others — who's typically involved in that decision? And "
            "whose money pays for it?"
        ),
        purpose=(
            "Decision unit size + budget source disambiguate archetypes "
            "most cleanly."
        ),
    ),
    ItemDef(
        id="phase1.P5",
        module_code="P5",
        phase="phase1",
        block="preamble",
        kind="open",
        prompt=(
            "Walk me through how a laptop decision typically gets made. "
            "Is it pretty informal — you pick and buy — or is there a "
            "process with approvals, quotes, or multiple people signing "
            "off?"
        ),
        purpose=(
            "Hard discriminator. Keywords 'RFP', 'procurement', "
            "'approval', 'three quotes' push toward SMB IT or enterprise."
        ),
    ),
    ItemDef(
        id="phase1.P6",
        module_code="P6",
        phase="phase1",
        block="preamble",
        kind="open",
        prompt=(
            "Last question before we go deeper: how much do you think "
            "about your laptop day-to-day? Is it something you care "
            "about, or just a tool in the background?"
        ),
        purpose=(
            "Involvement / engagement. High → richer JTBD expected; "
            "low → shorten Block 1 narrative probing, lean on choice-"
            "based methods."
        ),
        required=False,  # skippable if preamble ran long
    ),
]


PHASE1 = PhaseDef(
    id="phase1",
    label="Universal Preamble",
    budget_minutes=10,
    blocks=[
        BlockDef(
            id="preamble",
            phase="phase1",
            label="Context & routing signals",
            budget_minutes=10,
            items=PREAMBLE_ITEMS,
        ),
    ],
)


# ----------------------- Phase 2 — Silent Classification --------------------

# Phase 2 has no user-facing items in the base path; disambiguation
# prompts (when top archetype probability < 0.60) are generated on the
# fly by the classifier service. A sentinel PhaseDef keeps the flow
# uniform.

PHASE2 = PhaseDef(
    id="phase2",
    label="Silent Classification",
    budget_minutes=1,
    blocks=[],
)


# Phase 3 (archetype bodies) and Phase 4 (universal tail) are defined
# in chunks D and E. A lookup dict exposes the completed phases so the
# state machine can enumerate them.

_PHASES: dict[str, PhaseDef] = {
    "phase1": PHASE1,
    "phase2": PHASE2,
}


def get_phase(phase_id: str) -> Optional[PhaseDef]:
    return _PHASES.get(phase_id)


def register_phase(phase: PhaseDef) -> None:
    """Called by chunks D/E to attach their phase defs at import time."""
    _PHASES[phase.id] = phase


def all_items(phase_id: str) -> list[ItemDef]:
    phase = _PHASES.get(phase_id)
    if phase is None:
        return []
    return [item for block in phase.blocks for item in block.items]


def find_item(phase_id: str, item_id: str) -> Optional[ItemDef]:
    for item in all_items(phase_id):
        if item.id == item_id or item.module_code == item_id:
            return item
    return None
