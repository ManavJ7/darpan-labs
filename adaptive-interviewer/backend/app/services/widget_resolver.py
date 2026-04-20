"""Runtime widget materialization.

Some items have static widget specs (e.g., a forced-rank list of
adjectives). Others — conjoint choice sets, brand lattice — need
per-session rendering. The orchestrator calls `resolve_widget`
before persisting an interviewer turn, replacing the static widget
template with the concrete widget payload the frontend renders.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

from app.services import conjoint

DATA_DIR = Path(__file__).parent.parent / "data"

_BRAND_LATTICE: dict = json.loads((DATA_DIR / "brand_lattice.json").read_text())
_TONE_PAIRS: dict = json.loads((DATA_DIR / "tone_pairs.json").read_text())


def resolve_widget(
    widget_template: Optional[dict],
    session_id: UUID,
    archetype: Optional[str],
) -> Optional[dict]:
    if not widget_template:
        return None
    kind = widget_template.get("type")
    if kind == "conjoint_set":
        set_index = int(widget_template.get("set_index", 0))
        if archetype is None:
            return None
        cs = conjoint.generate_choice_set(archetype, session_id, set_index)
        return cs.to_widget()

    if kind == "brand_lattice":
        if archetype is None:
            return None
        lattice = _BRAND_LATTICE.get(archetype)
        if lattice is None:
            return None
        return {
            "type": "brand_lattice",
            "brands": lattice["brands"],
            "attributes": lattice["attributes"],
            "scale": lattice["scale"],
            "dont_know_escape": lattice["dont_know_escape"],
        }

    if kind == "tone_pair":
        pair_key = widget_template.get("pair")
        if archetype is None or pair_key not in ("pair_a", "pair_b"):
            return None
        pair = _TONE_PAIRS.get(archetype, {}).get(pair_key)
        if pair is None:
            return None
        return {
            "type": "tone_pair",
            "prompt": pair["prompt"],
            "ad_a": pair["ad_a"],
            "ad_b": pair["ad_b"],
        }

    # Pass-through for widgets that are already fully specified (e.g.
    # slider batteries defined in chunk E, forced-rank for identity).
    return widget_template
