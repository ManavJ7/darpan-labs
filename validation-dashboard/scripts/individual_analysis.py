"""Individual-level twin validation: per-participant, per-concept accuracy metrics."""

import re

# Canonical semantic dimension names
SEMANTIC_DIMENSIONS = {
    "premiumness": ["Basic — Premium", "Basic-Premium", "Basic - Premium"],
    "excitement": ["Boring — Exciting", "Boring-Exciting", "Boring - Exciting"],
    "personal_fit": ["Not for me — Made for me", "Not for me-Made for me", "Not for me - Made for me"],
    "innovation": ["Old-fashioned — Innovative", "Old-fashioned-Innovative", "Old-fashioned - Innovative"],
    "memorability": ["Forgettable — Memorable", "Forgettable-Memorable", "Forgettable - Memorable"],
}

# All 12 base metrics (+ time_saving conditional)
BASE_METRICS = [
    "interest", "routine_fit", "pi", "uniqueness", "relevance",
    "believability", "brand_fit", "premiumness", "excitement",
    "personal_fit", "innovation", "memorability",
]

METRIC_LABELS = {
    "interest": "Interest",
    "routine_fit": "Routine Fit",
    "pi": "Purchase Intent",
    "uniqueness": "Uniqueness",
    "relevance": "Relevance",
    "believability": "Believability",
    "brand_fit": "Brand Fit",
    "premiumness": "Premiumness",
    "excitement": "Excitement",
    "personal_fit": "Personal Fit",
    "innovation": "Innovation",
    "memorability": "Memorability",
    "time_saving": "Time Saving",
}

# Quality thresholds
THRESHOLDS = {
    "mae": {"good": 1.0, "acceptable": 1.5},
    "accuracy": {"good": 85.0, "acceptable": 70.0},
    "exact": {"good": 45.0, "acceptable": 25.0},
}


def normalize_char_key(key: str) -> str | None:
    """Normalize characteristics key variants (em-dash/hyphen/spaces) to canonical name."""
    # Strip and normalize dashes
    normalized = re.sub(r'\s*[—–-]\s*', '-', key.strip())
    for canonical, variants in SEMANTIC_DIMENSIONS.items():
        for v in variants:
            v_norm = re.sub(r'\s*[—–-]\s*', '-', v.strip())
            if normalized.lower() == v_norm.lower():
                return canonical
    return None


def extract_semantic_scores(characteristics: dict) -> dict:
    """Extract 5 semantic dimension scores from a characteristics dict."""
    scores = {}
    if not isinstance(characteristics, dict):
        return scores
    for key, value in characteristics.items():
        canonical = normalize_char_key(key)
        if canonical is not None:
            try:
                scores[canonical] = int(value) if not isinstance(value, (int, float)) else int(value)
            except (ValueError, TypeError):
                pass
    return scores


def extract_all_metrics(concept_data: dict, concept_idx: int) -> dict:
    """Extract all 12-13 metric values from a respondent's concept data."""
    metrics = {}

    # Core KPIs (directly from concept data)
    for key in ("interest", "routine_fit", "pi", "uniqueness", "relevance", "believability", "brand_fit"):
        val = concept_data.get(key)
        if val is not None:
            try:
                metrics[key] = int(val)
            except (ValueError, TypeError):
                pass

    # Time saving (only concepts 0 and 1)
    if concept_idx in (0, 1):
        val = concept_data.get("time_saving")
        if val is not None:
            try:
                metrics["time_saving"] = int(val)
            except (ValueError, TypeError):
                pass

    # Semantic dimensions from characteristics
    chars = concept_data.get("characteristics", {})
    semantic = extract_semantic_scores(chars)
    metrics.update(semantic)

    return metrics


def compute_pair_metrics(real_metrics: dict, twin_metrics: dict) -> dict:
    """Compute MAE, +/-1 accuracy, exact match for a single concept pair."""
    shared_keys = sorted(set(real_metrics.keys()) & set(twin_metrics.keys()))
    if not shared_keys:
        return {"mae": None, "plus_minus_1_accuracy": None, "exact_match_rate": None,
                "per_metric": [], "n_metrics": 0}

    diffs = []
    per_metric = []
    for key in shared_keys:
        r = real_metrics[key]
        t = twin_metrics[key]
        diff = t - r
        abs_diff = abs(diff)
        diffs.append(abs_diff)
        per_metric.append({
            "metric": key,
            "real": r,
            "twin": t,
            "diff": diff,
        })

    n = len(diffs)
    mae = sum(diffs) / n
    accuracy = (sum(1 for d in diffs if d <= 1) / n) * 100
    exact = (sum(1 for d in diffs if d == 0) / n) * 100

    return {
        "mae": round(mae, 2),
        "plus_minus_1_accuracy": round(accuracy, 1),
        "exact_match_rate": round(exact, 1),
        "per_metric": per_metric,
        "n_metrics": n,
    }


def assign_quality_tier(value: float | None, metric_type: str) -> str:
    """Return Good/Acceptable/Poor based on thresholds."""
    if value is None:
        return "Poor"
    thresh = THRESHOLDS.get(metric_type, {})
    good = thresh.get("good", 0)
    acceptable = thresh.get("acceptable", 0)

    if metric_type == "mae":
        # Lower is better
        if value < good:
            return "Good"
        if value <= acceptable:
            return "Acceptable"
        return "Poor"
    else:
        # Higher is better
        if value >= good:
            return "Good"
        if value >= acceptable:
            return "Acceptable"
        return "Poor"


CONCEPT_NAMES = ["Body Spray", "Skip", "Night Wash", "Yours & Mine", "Skin ID"]


def build_individual_validation(data: dict) -> dict:
    """Main: pair real[i] with twin[i], compute all metrics."""
    real_respondents = data["real"]
    twin_respondents = data["twin"]

    n_pairs = min(len(real_respondents), len(twin_respondents))
    pairs = []
    matrix = []

    # Accumulators for aggregates
    all_maes = []
    all_accs = []
    all_exacts = []
    by_participant = {}
    by_concept = {name: {"maes": [], "accs": [], "exacts": []} for name in CONCEPT_NAMES}
    by_metric = {}

    for i in range(n_pairs):
        real = real_respondents[i]
        twin = twin_respondents[i]
        pid = f"P{i+1:02d}"

        pair_data = {"participant_id": pid, "concepts": []}
        p_maes, p_accs, p_exacts = [], [], []

        for c_idx in range(5):
            real_concept = real["concepts"][c_idx] if c_idx < len(real.get("concepts", [])) else {}
            twin_concept = twin["concepts"][c_idx] if c_idx < len(twin.get("concepts", [])) else {}

            real_metrics = extract_all_metrics(real_concept, c_idx)
            twin_metrics = extract_all_metrics(twin_concept, c_idx)
            result = compute_pair_metrics(real_metrics, twin_metrics)

            concept_name = CONCEPT_NAMES[c_idx]
            quality = {
                "mae": assign_quality_tier(result["mae"], "mae"),
                "accuracy": assign_quality_tier(result["plus_minus_1_accuracy"], "accuracy"),
                "exact": assign_quality_tier(result["exact_match_rate"], "exact"),
            }

            concept_entry = {
                "concept_idx": c_idx,
                "concept_name": concept_name,
                "real_metrics": real_metrics,
                "twin_metrics": twin_metrics,
                "mae": result["mae"],
                "plus_minus_1_accuracy": result["plus_minus_1_accuracy"],
                "exact_match_rate": result["exact_match_rate"],
                "per_metric": result["per_metric"],
                "quality": quality,
                "n_metrics": result["n_metrics"],
            }
            pair_data["concepts"].append(concept_entry)

            # Accumulate
            if result["mae"] is not None:
                all_maes.append(result["mae"])
                p_maes.append(result["mae"])
                by_concept[concept_name]["maes"].append(result["mae"])

                all_accs.append(result["plus_minus_1_accuracy"])
                p_accs.append(result["plus_minus_1_accuracy"])
                by_concept[concept_name]["accs"].append(result["plus_minus_1_accuracy"])

                all_exacts.append(result["exact_match_rate"])
                p_exacts.append(result["exact_match_rate"])
                by_concept[concept_name]["exacts"].append(result["exact_match_rate"])

            # Per-metric accumulation
            for pm in result["per_metric"]:
                m = pm["metric"]
                if m not in by_metric:
                    by_metric[m] = {"abs_diffs": [], "exact_count": 0, "within_1_count": 0, "total": 0}
                by_metric[m]["abs_diffs"].append(abs(pm["diff"]))
                by_metric[m]["total"] += 1
                if pm["diff"] == 0:
                    by_metric[m]["exact_count"] += 1
                if abs(pm["diff"]) <= 1:
                    by_metric[m]["within_1_count"] += 1

            matrix.append({
                "participant": pid,
                "concept": concept_name,
                "mae": result["mae"],
                "accuracy": result["plus_minus_1_accuracy"],
                "exact": result["exact_match_rate"],
                "quality_mae": quality["mae"],
            })

        by_participant[pid] = {
            "mae": round(sum(p_maes) / len(p_maes), 2) if p_maes else None,
            "accuracy": round(sum(p_accs) / len(p_accs), 1) if p_accs else None,
            "exact": round(sum(p_exacts) / len(p_exacts), 1) if p_exacts else None,
        }

        pairs.append(pair_data)

    # Build aggregate
    def safe_avg(lst, decimals=2):
        return round(sum(lst) / len(lst), decimals) if lst else None

    overall_mae = safe_avg(all_maes)
    overall_acc = safe_avg(all_accs, 1)
    overall_exact = safe_avg(all_exacts, 1)

    by_concept_agg = {}
    for name, acc in by_concept.items():
        by_concept_agg[name] = {
            "mae": safe_avg(acc["maes"]),
            "accuracy": safe_avg(acc["accs"], 1),
            "exact": safe_avg(acc["exacts"], 1),
        }

    by_metric_agg = {}
    for m, acc in by_metric.items():
        by_metric_agg[m] = {
            "mae": round(sum(acc["abs_diffs"]) / len(acc["abs_diffs"]), 2) if acc["abs_diffs"] else None,
            "accuracy": round(acc["within_1_count"] / acc["total"] * 100, 1) if acc["total"] else None,
            "exact": round(acc["exact_count"] / acc["total"] * 100, 1) if acc["total"] else None,
        }

    metrics_used = BASE_METRICS.copy()
    if any(m.get("metric") == "time_saving" for entry in matrix for pair in pairs for c in pair["concepts"] for m in c["per_metric"]):
        metrics_used.append("time_saving")

    return {
        "pairs": pairs,
        "aggregate": {
            "overall_mae": overall_mae,
            "overall_accuracy": overall_acc,
            "overall_exact": overall_exact,
            "overall_quality": {
                "mae": assign_quality_tier(overall_mae, "mae"),
                "accuracy": assign_quality_tier(overall_acc, "accuracy"),
                "exact": assign_quality_tier(overall_exact, "exact"),
            },
            "by_participant": by_participant,
            "by_concept": by_concept_agg,
            "by_metric": by_metric_agg,
            "matrix": matrix,
        },
        "metadata": {
            "n_pairs": n_pairs,
            "n_concepts": 5,
            "metrics_used": metrics_used,
            "metric_labels": METRIC_LABELS,
            "thresholds": THRESHOLDS,
        },
    }
