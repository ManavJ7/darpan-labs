"""Statistical analysis for Dove concept validation."""

import numpy as np
from scipy import stats
from itertools import combinations
from data_processing import CONCEPTS, CONCEPT_SHORT

COMPOSITE_WEIGHTS = {"pi": 0.35, "uniqueness": 0.25, "relevance": 0.20, "believability": 0.20}

CORE_METRICS = ["pi", "uniqueness", "relevance", "believability"]
SUPPLEMENTARY_METRICS = ["interest", "brand_fit", "routine_fit", "time_saving"]
ALL_DISPLAY_METRICS = CORE_METRICS + ["interest", "brand_fit"]


def get_scores(respondents: list, concept_idx: int, metric: str) -> list:
    """Extract numeric scores for a metric across respondents."""
    scores = []
    for r in respondents:
        val = r["concepts"][concept_idx].get(metric)
        if val is not None and isinstance(val, (int, float)):
            scores.append(val)
    return scores


def t2b(scores: list) -> float | None:
    """Top-2-Box: % of scores that are 4 or 5."""
    if not scores:
        return None
    return round(100 * sum(1 for s in scores if s >= 4) / len(scores), 1)


def mean_score(scores: list) -> float | None:
    """Mean of scores."""
    if not scores:
        return None
    return round(np.mean(scores), 2)


def compute_t2b_and_means(respondents: list) -> dict:
    """Compute T2B% and mean for each concept × metric."""
    results = {}
    for ci in range(5):
        concept_data = {}
        for metric in CORE_METRICS + SUPPLEMENTARY_METRICS:
            scores = get_scores(respondents, ci, metric)
            if not scores:
                concept_data[metric] = {"t2b": None, "mean": None, "n": 0}
            else:
                concept_data[metric] = {
                    "t2b": t2b(scores),
                    "mean": mean_score(scores),
                    "n": len(scores),
                }
        results[CONCEPT_SHORT[ci]] = concept_data
    return results


def compute_composite(t2b_data: dict) -> dict:
    """Weighted composite score per concept using T2B values."""
    composites = {}
    for name in CONCEPT_SHORT:
        vals = {}
        for metric, weight in COMPOSITE_WEIGHTS.items():
            t = t2b_data[name][metric]["t2b"]
            if t is not None:
                vals[metric] = t * weight
        if vals:
            composites[name] = round(sum(vals.values()), 1)
        else:
            composites[name] = None
    return composites


def compute_composite_per_respondent(respondents: list) -> dict:
    """Compute per-respondent composite scores for statistical tests."""
    result = {name: [] for name in CONCEPT_SHORT}
    for r in respondents:
        for ci, name in enumerate(CONCEPT_SHORT):
            score_parts = []
            all_present = True
            for metric, weight in COMPOSITE_WEIGHTS.items():
                val = r["concepts"][ci].get(metric)
                if val is not None and isinstance(val, (int, float)):
                    score_parts.append(val * weight)
                else:
                    all_present = False
                    break
            if all_present:
                result[name].append(sum(score_parts))
            else:
                result[name].append(None)
    return result


def friedman_test(respondents: list) -> dict:
    """Friedman test on composite scores across concepts."""
    per_resp = compute_composite_per_respondent(respondents)

    # Only include respondents with scores for all 5 concepts
    n = len(respondents)
    valid_rows = []
    for i in range(n):
        row = [per_resp[name][i] for name in CONCEPT_SHORT]
        if all(v is not None for v in row):
            valid_rows.append(row)

    if len(valid_rows) < 3:
        return {"statistic": None, "p_value": None, "n": len(valid_rows), "significant": False}

    data = np.array(valid_rows)
    try:
        stat, p = stats.friedmanchisquare(*[data[:, i] for i in range(5)])
        return {
            "statistic": round(float(stat), 3),
            "p_value": round(float(p), 4),
            "n": len(valid_rows),
            "significant": bool(p < 0.05),
        }
    except Exception as e:
        return {"statistic": None, "p_value": None, "n": len(valid_rows), "significant": False, "error": str(e)}


def wilcoxon_pairwise(respondents: list) -> list:
    """Pairwise Wilcoxon signed-rank tests on composite scores with Bonferroni."""
    per_resp = compute_composite_per_respondent(respondents)
    n = len(respondents)
    pairs = list(combinations(range(5), 2))
    bonferroni = len(pairs)  # 10
    results = []

    for i, j in pairs:
        name_i, name_j = CONCEPT_SHORT[i], CONCEPT_SHORT[j]
        scores_i, scores_j = [], []
        for k in range(n):
            vi, vj = per_resp[name_i][k], per_resp[name_j][k]
            if vi is not None and vj is not None:
                scores_i.append(vi)
                scores_j.append(vj)

        if len(scores_i) < 3:
            results.append({
                "pair": [name_i, name_j],
                "statistic": None, "p_value": None, "p_adjusted": None,
                "significant": False, "n": len(scores_i),
            })
            continue

        try:
            diff = np.array(scores_i) - np.array(scores_j)
            if np.all(diff == 0):
                results.append({
                    "pair": [name_i, name_j],
                    "statistic": 0, "p_value": 1.0, "p_adjusted": 1.0,
                    "significant": False, "n": len(scores_i),
                })
                continue
            stat, p = stats.wilcoxon(scores_i, scores_j)
            p_adj = min(p * bonferroni, 1.0)
            results.append({
                "pair": [name_i, name_j],
                "statistic": round(float(stat), 3),
                "p_value": round(float(p), 4),
                "p_adjusted": round(float(p_adj), 4),
                "significant": bool(p_adj < 0.05),
                "n": len(scores_i),
            })
        except Exception as e:
            results.append({
                "pair": [name_i, name_j],
                "statistic": None, "p_value": None, "p_adjusted": None,
                "significant": False, "n": len(scores_i), "error": str(e),
            })

    return results


def assign_tiers(composites: dict, wilcoxon_results: list) -> dict:
    """Assign tiers: Tier 1 = not significantly different from top scorer."""
    sorted_concepts = sorted(composites.items(), key=lambda x: x[1] or 0, reverse=True)
    top_name = sorted_concepts[0][0]

    # Build significance lookup
    sig_pairs = set()
    for w in wilcoxon_results:
        if w["significant"]:
            sig_pairs.add((w["pair"][0], w["pair"][1]))
            sig_pairs.add((w["pair"][1], w["pair"][0]))

    tiers = {}
    for name, score in sorted_concepts:
        if name == top_name:
            tiers[name] = 1
        elif (top_name, name) not in sig_pairs:
            tiers[name] = 1  # Not significantly different from top
        else:
            tiers[name] = 2

    return tiers


def compute_mixed_model(respondents: list) -> dict:
    """Simple variance decomposition: concept vs position vs respondent effects."""
    # Since we can't easily run a mixed model without complex setup,
    # compute variance decomposition via ANOVA-style approach
    concept_scores = {name: [] for name in CONCEPT_SHORT}
    position_scores = {pos: [] for pos in range(5)}
    respondent_scores = {}

    per_resp = compute_composite_per_respondent(respondents)

    for ri, r in enumerate(respondents):
        rid = r["id"]
        respondent_scores[rid] = []
        for ci, name in enumerate(CONCEPT_SHORT):
            val = per_resp[name][ri]
            if val is not None:
                concept_scores[name].append(val)
                position_scores[ci].append(val)  # Position = presentation order
                respondent_scores[rid].append(val)

    all_scores = []
    for name in CONCEPT_SHORT:
        all_scores.extend(concept_scores[name])

    if not all_scores:
        return {"concept_var_pct": 0, "position_var_pct": 0, "respondent_var_pct": 0, "verdict": "Insufficient data"}

    grand_mean = np.mean(all_scores)
    total_var = np.var(all_scores)

    if total_var == 0:
        return {"concept_var_pct": 0, "position_var_pct": 0, "respondent_var_pct": 0, "verdict": "No variance"}

    # Concept variance
    concept_means = [np.mean(concept_scores[name]) for name in CONCEPT_SHORT if concept_scores[name]]
    concept_var = np.var(concept_means) if concept_means else 0

    # Position variance
    position_means = [np.mean(position_scores[pos]) for pos in range(5) if position_scores[pos]]
    position_var = np.var(position_means) if position_means else 0

    # Respondent variance
    resp_means = [np.mean(v) for v in respondent_scores.values() if v]
    respondent_var = np.var(resp_means) if resp_means else 0

    var_sum = concept_var + position_var + respondent_var
    if var_sum == 0:
        return {"concept_var_pct": 33, "position_var_pct": 33, "respondent_var_pct": 34, "verdict": "Uniform"}

    concept_pct = round(100 * concept_var / var_sum, 1)
    position_pct = round(100 * position_var / var_sum, 1)
    respondent_pct = round(100 * respondent_var / var_sum, 1)

    if position_pct > 30:
        verdict = "Significant order bias detected"
    elif position_pct > 15:
        verdict = "Moderate order effects"
    else:
        verdict = "Minimal order bias"

    return {
        "concept_var_pct": concept_pct,
        "position_var_pct": position_pct,
        "respondent_var_pct": respondent_pct,
        "verdict": verdict,
    }


def compute_turf(respondents: list) -> dict:
    """TURF analysis: best 2-concept and 3-concept portfolios by unduplicated PI T2B reach."""
    # For each respondent, determine which concepts they'd consider (PI T2B: score >= 4)
    n = len(respondents)
    concept_reach = {name: set() for name in CONCEPT_SHORT}

    for ri, r in enumerate(respondents):
        for ci, name in enumerate(CONCEPT_SHORT):
            pi_val = r["concepts"][ci].get("pi")
            if pi_val is not None and pi_val >= 4:
                concept_reach[name].add(ri)

    # Individual reach
    individual_reach = {name: round(100 * len(reached) / n, 1) for name, reached in concept_reach.items()}

    # Best 2-concept portfolio
    best_2 = {"concepts": [], "reach_pct": 0, "reach_n": 0}
    for i, j in combinations(range(5), 2):
        combined = concept_reach[CONCEPT_SHORT[i]] | concept_reach[CONCEPT_SHORT[j]]
        reach = len(combined)
        if reach > best_2["reach_n"]:
            best_2 = {
                "concepts": [CONCEPT_SHORT[i], CONCEPT_SHORT[j]],
                "reach_pct": round(100 * reach / n, 1),
                "reach_n": reach,
            }

    # Best 3-concept portfolio
    best_3 = {"concepts": [], "reach_pct": 0, "reach_n": 0}
    for i, j, k in combinations(range(5), 3):
        combined = concept_reach[CONCEPT_SHORT[i]] | concept_reach[CONCEPT_SHORT[j]] | concept_reach[CONCEPT_SHORT[k]]
        reach = len(combined)
        if reach > best_3["reach_n"]:
            best_3 = {
                "concepts": [CONCEPT_SHORT[i], CONCEPT_SHORT[j], CONCEPT_SHORT[k]],
                "reach_pct": round(100 * reach / n, 1),
                "reach_n": reach,
            }

    return {
        "individual_reach": individual_reach,
        "best_2": best_2,
        "best_3": best_3,
    }


def compute_barriers(respondents: list) -> dict:
    """Barrier frequency per concept."""
    results = {}
    for ci, name in enumerate(CONCEPT_SHORT):
        barrier_counts = {}
        total = 0
        for r in respondents:
            barriers = r["concepts"][ci].get("barriers", [])
            if isinstance(barriers, list):
                for b in barriers:
                    b_clean = b.strip().lower()
                    if b_clean:
                        barrier_counts[b_clean] = barrier_counts.get(b_clean, 0) + 1
                        total += 1

        # Sort by frequency
        sorted_barriers = sorted(barrier_counts.items(), key=lambda x: x[1], reverse=True)
        results[name] = {
            "barriers": [{"name": b, "count": c, "pct": round(100 * c / len(respondents), 1)} for b, c in sorted_barriers],
            "total_mentions": total,
        }
    return results


def compute_direct_ranking(respondents: list) -> dict:
    """Analyze direct ranking data (top-3 counts)."""
    concept_key_map = {
        "concept1_bodyspray": "Body Spray", "concept1": "Body Spray",
        "dove 60-second body spray": "Body Spray", "body spray": "Body Spray",
        "concept2_skip": "Skip", "concept2": "Skip",
        "dove skip": "Skip", "skip": "Skip",
        "concept3_nightwash": "Night Wash", "concept3": "Night Wash",
        "dove night wash": "Night Wash", "night wash": "Night Wash",
        "concept4_yoursmine": "Yours & Mine", "concept4": "Yours & Mine",
        "dove yours & mine": "Yours & Mine", "yours & mine": "Yours & Mine",
        "concept5_skinid": "Skin ID", "concept5": "Skin ID",
        "dove skin id": "Skin ID", "skin id": "Skin ID",
    }

    top3_counts = {name: 0 for name in CONCEPT_SHORT}
    rank1_counts = {name: 0 for name in CONCEPT_SHORT}
    n = len(respondents)

    for r in respondents:
        ranking = r.get("ranking", [])
        if not isinstance(ranking, list):
            continue
        for pos, item in enumerate(ranking[:3]):
            item_lower = item.strip().lower()
            matched_name = concept_key_map.get(item_lower)
            if matched_name:
                top3_counts[matched_name] += 1
                if pos == 0:
                    rank1_counts[matched_name] += 1

    results = {}
    for name in CONCEPT_SHORT:
        results[name] = {
            "top3_count": top3_counts[name],
            "top3_pct": round(100 * top3_counts[name] / n, 1) if n > 0 else 0,
            "rank1_count": rank1_counts[name],
            "rank1_pct": round(100 * rank1_counts[name] / n, 1) if n > 0 else 0,
        }
    return results


def compute_price_data(respondents: list) -> dict:
    """Price-qualified PI and WTP analysis."""
    price_pi_scores = [r.get("price_pi") for r in respondents if r.get("price_pi") is not None]
    wtp_values = [r.get("wtp") for r in respondents if r.get("wtp") is not None]

    return {
        "price_pi": {
            "t2b": t2b(price_pi_scores),
            "mean": mean_score(price_pi_scores),
            "n": len(price_pi_scores),
        },
        "wtp": {
            "mean": round(np.mean(wtp_values), 0) if wtp_values else None,
            "median": round(float(np.median(wtp_values)), 0) if wtp_values else None,
            "min": min(wtp_values) if wtp_values else None,
            "max": max(wtp_values) if wtp_values else None,
            "n": len(wtp_values),
        },
    }


def compute_screening_context(respondents: list) -> dict:
    """Summarize screening/category context."""
    frequencies = {}
    satisfaction = {}
    brands = {}

    for r in respondents:
        s = r.get("screening", {})
        freq = s.get("frequency", "").strip().lower()
        if freq:
            frequencies[freq] = frequencies.get(freq, 0) + 1

        sat = s.get("satisfaction", "").strip().lower()
        if sat:
            satisfaction[sat] = satisfaction.get(sat, 0) + 1

        brand_str = s.get("brands", "")
        if brand_str:
            for b in brand_str.split(","):
                b_clean = b.strip().lower()
                if b_clean:
                    brands[b_clean] = brands.get(b_clean, 0) + 1

    return {
        "frequencies": dict(sorted(frequencies.items(), key=lambda x: x[1], reverse=True)),
        "satisfaction": dict(sorted(satisfaction.items(), key=lambda x: x[1], reverse=True)),
        "top_brands": dict(sorted(brands.items(), key=lambda x: x[1], reverse=True)[:10]),
        "n": len(respondents),
    }


def run_all_analyses(respondents: list) -> dict:
    """Run all statistical analyses on a respondent set."""
    print("  Computing T2B and means...")
    t2b_data = compute_t2b_and_means(respondents)

    print("  Computing composites...")
    composites = compute_composite(t2b_data)

    print("  Running Friedman test...")
    friedman = friedman_test(respondents)

    print("  Running pairwise Wilcoxon tests...")
    wilcoxon = wilcoxon_pairwise(respondents)

    print("  Assigning tiers...")
    tiers = assign_tiers(composites, wilcoxon)

    print("  Computing mixed model...")
    mixed_model = compute_mixed_model(respondents)

    print("  Computing TURF...")
    turf = compute_turf(respondents)

    print("  Computing barriers...")
    barriers = compute_barriers(respondents)

    print("  Computing direct ranking...")
    direct_ranking = compute_direct_ranking(respondents)

    print("  Computing price data...")
    price_data = compute_price_data(respondents)

    print("  Computing screening context...")
    screening = compute_screening_context(respondents)

    return {
        "n": len(respondents),
        "t2b": t2b_data,
        "composites": composites,
        "friedman": friedman,
        "wilcoxon": wilcoxon,
        "tiers": tiers,
        "mixedModel": mixed_model,
        "turf": turf,
        "barriers": barriers,
        "directRanking": direct_ranking,
        "priceData": price_data,
        "screeningContext": screening,
    }
