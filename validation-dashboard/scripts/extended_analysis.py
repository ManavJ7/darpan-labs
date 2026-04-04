"""Extended twin analysis: aggregate (n=85) and individual validation (average + best-match)."""

import os
import glob
import csv
import re
import json
import numpy as np

from data_processing import (
    CONCEPTS, CONCEPT_SHORT, TWIN_QID_MAP,
    parse_pi_twin, parse_likert_twin, parse_barriers_twin,
    parse_ranking_twin, parse_json_safe,
)
from individual_analysis import (
    extract_all_metrics, compute_pair_metrics, assign_quality_tier,
    CONCEPT_NAMES, BASE_METRICS, METRIC_LABELS, THRESHOLDS,
)


def load_all_extended_twins(step5_dir: str) -> dict:
    """Load all 85 extended twin CSVs, grouped by participant."""
    twin_files = sorted(glob.glob(os.path.join(step5_dir, "P*_T*_m8_qa_responses.csv")))
    print(f"  Found {len(twin_files)} extended twin files")

    all_twins = []
    by_participant = {}

    for filepath in twin_files:
        basename = os.path.basename(filepath)
        # Extract P01 and T001 from P01_T001_m8_qa_responses.csv
        parts = basename.split("_")
        pid = parts[0]  # P01
        tid = parts[1]  # T001
        p_num = int(pid[1:])

        respondent = {
            "id": f"T{p_num:02d}_{tid}",
            "participant_id": pid,
            "twin_id": tid,
            "source": "twin",
            "screening": {},
            "concepts": [{} for _ in range(5)],
            "ranking": [],
            "price_pi": None,
            "wtp": None,
        }

        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                qid = row.get("Question ID", "").strip()
                answer_val = row.get("Answer (Value)", "").strip()

                if qid not in TWIN_QID_MAP:
                    continue

                concept_idx, metric = TWIN_QID_MAP[qid]

                if concept_idx is None:
                    if metric == "ranking":
                        respondent["ranking"] = parse_ranking_twin(answer_val)
                    elif metric == "price_pi":
                        respondent["price_pi"] = parse_pi_twin(answer_val)
                    elif metric == "wtp":
                        try:
                            respondent["wtp"] = int(re.sub(r'[^\d]', '', answer_val))
                        except (ValueError, TypeError):
                            pass
                    elif metric == "importance":
                        respondent["screening"]["importance"] = parse_json_safe(answer_val)
                    continue

                if metric == "pi":
                    respondent["concepts"][concept_idx][metric] = parse_pi_twin(answer_val)
                elif metric in ("uniqueness", "relevance", "believability", "brand_fit"):
                    respondent["concepts"][concept_idx][metric] = parse_likert_twin(answer_val)
                elif metric in ("interest", "routine_fit", "time_saving"):
                    try:
                        respondent["concepts"][concept_idx][metric] = int(answer_val)
                    except (ValueError, TypeError):
                        pass
                elif metric in ("appealing", "change"):
                    respondent["concepts"][concept_idx][metric] = answer_val
                elif metric == "barriers":
                    respondent["concepts"][concept_idx][metric] = parse_barriers_twin(answer_val)
                elif metric == "characteristics":
                    respondent["concepts"][concept_idx][metric] = parse_json_safe(answer_val)
                else:
                    respondent["concepts"][concept_idx][metric] = answer_val

        all_twins.append(respondent)
        if pid not in by_participant:
            by_participant[pid] = []
        by_participant[pid].append(respondent)

    return {"all": all_twins, "by_participant": by_participant}


def build_extended_validation(real_respondents: list, by_participant: dict) -> dict:
    """Build both average-twin and best-match validation data."""
    avg_pairs = []
    best_pairs = []
    avg_matrix = []
    best_matrix = []

    # Accumulators
    avg_all_maes, avg_all_accs, avg_all_exacts = [], [], []
    best_all_maes, best_all_accs, best_all_exacts = [], [], []
    avg_by_participant, best_by_participant = {}, {}
    avg_by_concept = {n: {"maes": [], "accs": [], "exacts": []} for n in CONCEPT_NAMES}
    best_by_concept = {n: {"maes": [], "accs": [], "exacts": []} for n in CONCEPT_NAMES}
    avg_by_metric, best_by_metric = {}, {}

    twin_selection_counts = {}

    for i, real in enumerate(real_respondents):
        pid = f"P{i+1:02d}"
        twins = by_participant.get(pid, [])
        if not twins:
            continue

        # --- Average twin approach ---
        avg_pair = {"participant_id": pid, "concepts": []}
        avg_p_maes, avg_p_accs, avg_p_exacts = [], [], []

        for c_idx in range(5):
            real_concept = real["concepts"][c_idx] if c_idx < len(real.get("concepts", [])) else {}
            real_metrics = extract_all_metrics(real_concept, c_idx)

            # Average the 5 twins' numeric metrics
            all_twin_metrics = []
            for t in twins:
                t_concept = t["concepts"][c_idx] if c_idx < len(t.get("concepts", [])) else {}
                all_twin_metrics.append(extract_all_metrics(t_concept, c_idx))

            avg_twin_metrics = {}
            all_keys = set()
            for tm in all_twin_metrics:
                all_keys.update(tm.keys())

            for key in all_keys:
                vals = [tm[key] for tm in all_twin_metrics if key in tm]
                if vals:
                    avg_twin_metrics[key] = round(sum(vals) / len(vals), 2)

            result = compute_pair_metrics(real_metrics, avg_twin_metrics)
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
                "twin_metrics": avg_twin_metrics,
                "mae": result["mae"],
                "plus_minus_1_accuracy": result["plus_minus_1_accuracy"],
                "exact_match_rate": result["exact_match_rate"],
                "per_metric": result["per_metric"],
                "quality": quality,
                "n_metrics": result["n_metrics"],
            }
            avg_pair["concepts"].append(concept_entry)

            if result["mae"] is not None:
                avg_all_maes.append(result["mae"])
                avg_p_maes.append(result["mae"])
                avg_by_concept[concept_name]["maes"].append(result["mae"])
                avg_all_accs.append(result["plus_minus_1_accuracy"])
                avg_p_accs.append(result["plus_minus_1_accuracy"])
                avg_by_concept[concept_name]["accs"].append(result["plus_minus_1_accuracy"])
                avg_all_exacts.append(result["exact_match_rate"])
                avg_p_exacts.append(result["exact_match_rate"])
                avg_by_concept[concept_name]["exacts"].append(result["exact_match_rate"])

            for pm in result["per_metric"]:
                m = pm["metric"]
                if m not in avg_by_metric:
                    avg_by_metric[m] = {"abs_diffs": [], "exact_count": 0, "within_1_count": 0, "total": 0}
                avg_by_metric[m]["abs_diffs"].append(abs(pm["diff"]))
                avg_by_metric[m]["total"] += 1
                if pm["diff"] == 0:
                    avg_by_metric[m]["exact_count"] += 1
                if abs(pm["diff"]) <= 1:
                    avg_by_metric[m]["within_1_count"] += 1

            avg_matrix.append({
                "participant": pid, "concept": concept_name,
                "mae": result["mae"], "accuracy": result["plus_minus_1_accuracy"],
                "exact": result["exact_match_rate"], "quality_mae": quality["mae"],
            })

        avg_by_participant[pid] = {
            "mae": round(sum(avg_p_maes) / len(avg_p_maes), 2) if avg_p_maes else None,
            "accuracy": round(sum(avg_p_accs) / len(avg_p_accs), 1) if avg_p_accs else None,
            "exact": round(sum(avg_p_exacts) / len(avg_p_exacts), 1) if avg_p_exacts else None,
        }
        avg_pairs.append(avg_pair)

        # --- Best-match twin approach ---
        # For each twin, compute overall MAE across all 5 concepts
        twin_overall_scores = []
        for t in twins:
            t_maes = []
            for c_idx in range(5):
                real_concept = real["concepts"][c_idx] if c_idx < len(real.get("concepts", [])) else {}
                t_concept = t["concepts"][c_idx] if c_idx < len(t.get("concepts", [])) else {}
                real_m = extract_all_metrics(real_concept, c_idx)
                twin_m = extract_all_metrics(t_concept, c_idx)
                r = compute_pair_metrics(real_m, twin_m)
                if r["mae"] is not None:
                    t_maes.append(r["mae"])
            overall_mae = round(sum(t_maes) / len(t_maes), 2) if t_maes else 999
            twin_overall_scores.append({
                "twin_id": t["twin_id"],
                "mae": overall_mae,
            })

        # Pick best twin
        twin_overall_scores.sort(key=lambda x: x["mae"])
        best_twin_id = twin_overall_scores[0]["twin_id"]
        best_twin = next(t for t in twins if t["twin_id"] == best_twin_id)

        # Track selection
        if best_twin_id not in twin_selection_counts:
            twin_selection_counts[best_twin_id] = {"count": 0, "maes": []}
        twin_selection_counts[best_twin_id]["count"] += 1
        twin_selection_counts[best_twin_id]["maes"].append(twin_overall_scores[0]["mae"])

        best_pair = {
            "participant_id": pid,
            "best_twin_id": best_twin_id,
            "all_twins": twin_overall_scores,
            "concepts": [],
        }
        best_p_maes, best_p_accs, best_p_exacts = [], [], []

        for c_idx in range(5):
            real_concept = real["concepts"][c_idx] if c_idx < len(real.get("concepts", [])) else {}
            best_concept = best_twin["concepts"][c_idx] if c_idx < len(best_twin.get("concepts", [])) else {}
            real_metrics = extract_all_metrics(real_concept, c_idx)
            twin_metrics = extract_all_metrics(best_concept, c_idx)
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
            best_pair["concepts"].append(concept_entry)

            if result["mae"] is not None:
                best_all_maes.append(result["mae"])
                best_p_maes.append(result["mae"])
                best_by_concept[concept_name]["maes"].append(result["mae"])
                best_all_accs.append(result["plus_minus_1_accuracy"])
                best_p_accs.append(result["plus_minus_1_accuracy"])
                best_by_concept[concept_name]["accs"].append(result["plus_minus_1_accuracy"])
                best_all_exacts.append(result["exact_match_rate"])
                best_p_exacts.append(result["exact_match_rate"])
                best_by_concept[concept_name]["exacts"].append(result["exact_match_rate"])

            for pm in result["per_metric"]:
                m = pm["metric"]
                if m not in best_by_metric:
                    best_by_metric[m] = {"abs_diffs": [], "exact_count": 0, "within_1_count": 0, "total": 0}
                best_by_metric[m]["abs_diffs"].append(abs(pm["diff"]))
                best_by_metric[m]["total"] += 1
                if pm["diff"] == 0:
                    best_by_metric[m]["exact_count"] += 1
                if abs(pm["diff"]) <= 1:
                    best_by_metric[m]["within_1_count"] += 1

            best_matrix.append({
                "participant": pid, "concept": concept_name,
                "mae": result["mae"], "accuracy": result["plus_minus_1_accuracy"],
                "exact": result["exact_match_rate"], "quality_mae": quality["mae"],
            })

        best_by_participant[pid] = {
            "mae": round(sum(best_p_maes) / len(best_p_maes), 2) if best_p_maes else None,
            "accuracy": round(sum(best_p_accs) / len(best_p_accs), 1) if best_p_accs else None,
            "exact": round(sum(best_p_exacts) / len(best_p_exacts), 1) if best_p_exacts else None,
        }
        best_pairs.append(best_pair)

    def safe_avg(lst, decimals=2):
        return round(sum(lst) / len(lst), decimals) if lst else None

    def build_by_concept_agg(by_concept):
        return {
            name: {
                "mae": safe_avg(acc["maes"]),
                "accuracy": safe_avg(acc["accs"], 1),
                "exact": safe_avg(acc["exacts"], 1),
            }
            for name, acc in by_concept.items()
        }

    def build_by_metric_agg(by_metric):
        result = {}
        for m, acc in by_metric.items():
            result[m] = {
                "mae": round(sum(acc["abs_diffs"]) / len(acc["abs_diffs"]), 2) if acc["abs_diffs"] else None,
                "accuracy": round(acc["within_1_count"] / acc["total"] * 100, 1) if acc["total"] else None,
                "exact": round(acc["exact_count"] / acc["total"] * 100, 1) if acc["total"] else None,
            }
        return result

    metrics_used = BASE_METRICS.copy()
    metrics_used.append("time_saving")

    # Twin selection summary
    twin_selection_summary = []
    for tid, info in sorted(twin_selection_counts.items()):
        twin_selection_summary.append({
            "twin_id": tid,
            "times_selected": info["count"],
            "avg_mae_when_selected": round(sum(info["maes"]) / len(info["maes"]), 2) if info["maes"] else None,
        })

    avg_overall_mae = safe_avg(avg_all_maes)
    avg_overall_acc = safe_avg(avg_all_accs, 1)
    avg_overall_exact = safe_avg(avg_all_exacts, 1)
    best_overall_mae = safe_avg(best_all_maes)
    best_overall_acc = safe_avg(best_all_accs, 1)
    best_overall_exact = safe_avg(best_all_exacts, 1)

    # --- Median twin approach ---
    med_pairs = []
    med_matrix = []
    med_all_maes, med_all_accs, med_all_exacts = [], [], []
    med_by_participant = {}
    med_by_concept = {n: {"maes": [], "accs": [], "exacts": []} for n in CONCEPT_NAMES}
    med_by_metric = {}

    for i, real in enumerate(real_respondents):
        pid = f"P{i+1:02d}"
        twins = by_participant.get(pid, [])
        if not twins:
            continue

        med_pair = {"participant_id": pid, "concepts": []}
        med_p_maes, med_p_accs, med_p_exacts = [], [], []

        for c_idx in range(5):
            real_concept = real["concepts"][c_idx] if c_idx < len(real.get("concepts", [])) else {}
            real_metrics = extract_all_metrics(real_concept, c_idx)

            all_twin_metrics = []
            for t in twins:
                t_concept = t["concepts"][c_idx] if c_idx < len(t.get("concepts", [])) else {}
                all_twin_metrics.append(extract_all_metrics(t_concept, c_idx))

            median_twin_metrics = {}
            all_keys = set()
            for tm in all_twin_metrics:
                all_keys.update(tm.keys())

            for key in all_keys:
                vals = [tm[key] for tm in all_twin_metrics if key in tm]
                if vals:
                    median_twin_metrics[key] = round(float(np.median(vals)), 2)

            result = compute_pair_metrics(real_metrics, median_twin_metrics)
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
                "twin_metrics": median_twin_metrics,
                "mae": result["mae"],
                "plus_minus_1_accuracy": result["plus_minus_1_accuracy"],
                "exact_match_rate": result["exact_match_rate"],
                "per_metric": result["per_metric"],
                "quality": quality,
                "n_metrics": result["n_metrics"],
            }
            med_pair["concepts"].append(concept_entry)

            if result["mae"] is not None:
                med_all_maes.append(result["mae"])
                med_p_maes.append(result["mae"])
                med_by_concept[concept_name]["maes"].append(result["mae"])
                med_all_accs.append(result["plus_minus_1_accuracy"])
                med_p_accs.append(result["plus_minus_1_accuracy"])
                med_by_concept[concept_name]["accs"].append(result["plus_minus_1_accuracy"])
                med_all_exacts.append(result["exact_match_rate"])
                med_p_exacts.append(result["exact_match_rate"])
                med_by_concept[concept_name]["exacts"].append(result["exact_match_rate"])

            for pm in result["per_metric"]:
                m = pm["metric"]
                if m not in med_by_metric:
                    med_by_metric[m] = {"abs_diffs": [], "exact_count": 0, "within_1_count": 0, "total": 0}
                med_by_metric[m]["abs_diffs"].append(abs(pm["diff"]))
                med_by_metric[m]["total"] += 1
                if pm["diff"] == 0:
                    med_by_metric[m]["exact_count"] += 1
                if abs(pm["diff"]) <= 1:
                    med_by_metric[m]["within_1_count"] += 1

            med_matrix.append({
                "participant": pid, "concept": concept_name,
                "mae": result["mae"], "accuracy": result["plus_minus_1_accuracy"],
                "exact": result["exact_match_rate"], "quality_mae": quality["mae"],
            })

        med_by_participant[pid] = {
            "mae": round(sum(med_p_maes) / len(med_p_maes), 2) if med_p_maes else None,
            "accuracy": round(sum(med_p_accs) / len(med_p_accs), 1) if med_p_accs else None,
            "exact": round(sum(med_p_exacts) / len(med_p_exacts), 1) if med_p_exacts else None,
        }
        med_pairs.append(med_pair)

    med_overall_mae = safe_avg(med_all_maes)
    med_overall_acc = safe_avg(med_all_accs, 1)
    med_overall_exact = safe_avg(med_all_exacts, 1)

    return {
        "median_twin": {
            "pairs": med_pairs,
            "aggregate": {
                "overall_mae": med_overall_mae,
                "overall_accuracy": med_overall_acc,
                "overall_exact": med_overall_exact,
                "overall_quality": {
                    "mae": assign_quality_tier(med_overall_mae, "mae"),
                    "accuracy": assign_quality_tier(med_overall_acc, "accuracy"),
                    "exact": assign_quality_tier(med_overall_exact, "exact"),
                },
                "by_participant": med_by_participant,
                "by_concept": build_by_concept_agg(med_by_concept),
                "by_metric": build_by_metric_agg(med_by_metric),
                "matrix": med_matrix,
            },
            "metadata": {
                "n_pairs": len(med_pairs),
                "n_concepts": 5,
                "n_twins_per_participant": 5,
                "metrics_used": metrics_used,
                "metric_labels": METRIC_LABELS,
                "thresholds": THRESHOLDS,
            },
        },
        "average_twin": {
            "pairs": avg_pairs,
            "aggregate": {
                "overall_mae": avg_overall_mae,
                "overall_accuracy": avg_overall_acc,
                "overall_exact": avg_overall_exact,
                "overall_quality": {
                    "mae": assign_quality_tier(avg_overall_mae, "mae"),
                    "accuracy": assign_quality_tier(avg_overall_acc, "accuracy"),
                    "exact": assign_quality_tier(avg_overall_exact, "exact"),
                },
                "by_participant": avg_by_participant,
                "by_concept": build_by_concept_agg(avg_by_concept),
                "by_metric": build_by_metric_agg(avg_by_metric),
                "matrix": avg_matrix,
            },
            "metadata": {
                "n_pairs": len(avg_pairs),
                "n_concepts": 5,
                "n_twins_per_participant": 5,
                "metrics_used": metrics_used,
                "metric_labels": METRIC_LABELS,
                "thresholds": THRESHOLDS,
            },
        },
        "best_match": {
            "pairs": best_pairs,
            "aggregate": {
                "overall_mae": best_overall_mae,
                "overall_accuracy": best_overall_acc,
                "overall_exact": best_overall_exact,
                "overall_quality": {
                    "mae": assign_quality_tier(best_overall_mae, "mae"),
                    "accuracy": assign_quality_tier(best_overall_acc, "accuracy"),
                    "exact": assign_quality_tier(best_overall_exact, "exact"),
                },
                "by_participant": best_by_participant,
                "by_concept": build_by_concept_agg(best_by_concept),
                "by_metric": build_by_metric_agg(best_by_metric),
                "matrix": best_matrix,
            },
            "twin_selection_summary": twin_selection_summary,
            "metadata": {
                "n_pairs": len(best_pairs),
                "n_concepts": 5,
                "n_twins_per_participant": 5,
                "metrics_used": metrics_used,
                "metric_labels": METRIC_LABELS,
                "thresholds": THRESHOLDS,
            },
        },
    }
