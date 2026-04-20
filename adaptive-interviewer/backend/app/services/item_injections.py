"""Dynamic prompt injections.

Some item prompts depend on archetype — notably the projective-
close (T3) and occasional brand unaided-recall phrasing. Rather
than duplicating three variants of each item in phase_defs, the
base ItemDef carries a placeholder and this module returns the
archetype-specific text at turn-emission time.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from app.services.phase_defs import ItemDef

DATA_DIR = Path(__file__).parent.parent / "data"
_TONE_PAIRS = json.loads((DATA_DIR / "tone_pairs.json").read_text())


def resolve_item_prompt(item: ItemDef, archetype: Optional[str]) -> Optional[str]:
    """Return an archetype-specific prompt override, or None to use
    the item's default `prompt` field as-is."""
    if item.kind == "projective" and item.block == "tone" and archetype:
        archetype_tones = _TONE_PAIRS.get(archetype, {})
        return archetype_tones.get("projective_close")
    return None
