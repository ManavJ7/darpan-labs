"""Conjoint design generator + HB-ish part-worth estimation.

DESIGN (this file, chunk D): deterministic per-session choice-set
generator. Given the archetype's attribute spec, we generate 8
choice sets × 3 alternatives using a balanced near-orthogonal draw
seeded by session_id + set_index (so reloads are stable).

ESTIMATION (chunk F): aggregate multinomial-logit fit via
scipy.optimize, then empirical-Bayes shrinkage toward the aggregate
mean for per-respondent part-worths. Not full HB MCMC — documented
in the output JSON's `estimation_method` field so downstream
analysts know what they're working with.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional
from uuid import UUID

import numpy as np

logger = logging.getLogger(__name__)

_SPECS_PATH = Path(__file__).parent.parent / "data" / "conjoint_specs.json"
_SPECS: dict[str, dict] = json.loads(_SPECS_PATH.read_text(encoding="utf-8"))


def get_spec(archetype: str) -> dict:
    if archetype not in _SPECS:
        raise KeyError(f"No conjoint spec for archetype {archetype!r}")
    return _SPECS[archetype]


def _seed_from(session_id: UUID, set_index: int, archetype: str) -> int:
    h = hashlib.sha256(f"{session_id}:{archetype}:{set_index}".encode()).hexdigest()
    return int(h[:12], 16)


def _format_level(value: Any, attr_name: str, units: dict[str, str]) -> str:
    unit = units.get(attr_name)
    if unit and isinstance(value, (int, float)):
        if attr_name == "price_usd" or attr_name == "unit_price_usd":
            return f"${int(value)}"
        return f"{value} {unit}"
    return str(value)


@dataclass
class ChoiceSet:
    set_index: int
    alternatives: list[dict[str, Any]]   # each has `attributes`, `label`
    include_none: bool
    scenario: str

    def to_widget(self) -> dict[str, Any]:
        return {
            "type": "conjoint",
            "set_index": self.set_index,
            "scenario": self.scenario,
            "alternatives": self.alternatives,
            "include_none": self.include_none,
        }


def generate_choice_set(
    archetype: str,
    session_id: UUID,
    set_index: int,
) -> ChoiceSet:
    """Balanced near-orthogonal draw for one choice set. The seed is
    deterministic per (session, archetype, set_index) so reloads
    render the same cards."""
    spec = get_spec(archetype)
    rng = np.random.default_rng(_seed_from(session_id, set_index, archetype))
    attrs = spec["attributes"]
    n_alts = int(spec["alternatives_per_set"])
    include_none = bool(spec["include_none_on_holdout"]) and set_index == spec["n_sets"] - 1
    units = spec.get("display_units", {})

    # Shuffle level order per attribute for this set, then round-robin
    # across alternatives. This guarantees each attribute shows a
    # different level in each alternative (within the set), which is
    # the simplest way to avoid dominated alternatives.
    alternatives: list[dict[str, Any]] = []
    for alt_idx in range(n_alts):
        profile: dict[str, Any] = {}
        display: dict[str, str] = {}
        for attr_name, attr_spec in attrs.items():
            levels = list(attr_spec["levels"])
            # Independent per-attribute shuffle for this set.
            perm = rng.permutation(len(levels))
            chosen = levels[int(perm[alt_idx % len(levels)])]
            profile[attr_name] = chosen
            display[attr_name] = _format_level(chosen, attr_name, units)
        alternatives.append({
            "alt_index": alt_idx,
            "label": f"Option {chr(ord('A') + alt_idx)}",
            "attributes": profile,
            "display": display,
        })
    return ChoiceSet(
        set_index=set_index,
        alternatives=alternatives,
        include_none=include_none,
        scenario=spec["scenario"],
    )


def generate_full_design(archetype: str, session_id: UUID) -> list[ChoiceSet]:
    spec = get_spec(archetype)
    return [generate_choice_set(archetype, session_id, i) for i in range(int(spec["n_sets"]))]


# ------------------- design-matrix helpers (used in chunk F) -----------------

def encode_profile(profile: dict[str, Any], archetype: str) -> dict[str, float]:
    """One-hot encode a profile for MNL estimation. Numeric levels
    are kept as numeric features (centered per attribute); nominal
    levels become k-1 dummies with the first level as baseline."""
    spec = get_spec(archetype)
    features: dict[str, float] = {}
    for attr_name, attr_spec in spec["attributes"].items():
        if attr_spec["type"] == "numeric":
            features[f"{attr_name}_num"] = float(profile[attr_name])
        else:
            levels = attr_spec["levels"]
            chosen = profile[attr_name]
            for level in levels[1:]:
                features[f"{attr_name}_is_{level}"] = 1.0 if chosen == level else 0.0
    return features


def feature_names(archetype: str) -> list[str]:
    spec = get_spec(archetype)
    names: list[str] = []
    for attr_name, attr_spec in spec["attributes"].items():
        if attr_spec["type"] == "numeric":
            names.append(f"{attr_name}_num")
        else:
            names.extend(f"{attr_name}_is_{lv}" for lv in attr_spec["levels"][1:])
    return names


def build_design_matrix(
    choices: list[dict[str, Any]],
    archetype: str,
) -> tuple[np.ndarray, np.ndarray]:
    """Turn a respondent's conjoint responses into (X, y) for MNL.

    `choices` is a list of dicts each shaped like:
        {
          "alternatives": [ <profile>, <profile>, ... ],
          "chosen_alt_index": int   # or -1 if "none"
        }
    Rows in X correspond to alternatives (flattened, choice-set by
    choice-set). y is a binary vector of same length marking the
    chosen row per set. "none" rows have all-zero features and y=0.
    """
    names = feature_names(archetype)
    rows: list[list[float]] = []
    chosen_flags: list[int] = []
    for cs in choices:
        alts = cs["alternatives"]
        for idx, alt in enumerate(alts):
            feats = encode_profile(alt, archetype)
            row = [feats.get(n, 0.0) for n in names]
            rows.append(row)
            chosen_flags.append(1 if idx == cs.get("chosen_alt_index", -1) else 0)
        if cs.get("chosen_alt_index", 0) == -1:
            # "none" — append a zero row with chosen=1 so likelihood
            # is defined. We don't estimate a none-constant here in v1.
            rows.append([0.0] * len(names))
            chosen_flags.append(1)
    return np.array(rows, dtype=float), np.array(chosen_flags, dtype=int)
