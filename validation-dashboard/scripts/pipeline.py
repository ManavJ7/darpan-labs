"""Orchestrator: load data → process → analyze → serialize JSON."""

import json
import os
import sys

# Add scripts dir to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_processing import load_all_data, CONCEPTS, CONCEPT_SHORT
from analysis import run_all_analyses
from llm_analysis import get_open_ended_responses, extract_themes_with_claude
from individual_analysis import build_individual_validation
from extended_analysis import load_all_extended_twins, build_extended_validation


def run_validation(
    twin_respondents: list[dict],
    real_respondents: list[dict] | None = None,
    mode: str = "synthesis",
    concept_names: list[str] | None = None,
    concept_short_names: list[str] | None = None,
    study_title: str = "Concept Validation",
    skip_themes: bool = False,
) -> dict:
    """Run the validation pipeline and return results as a dict.

    Args:
        twin_respondents: List of twin respondent dicts (same format as data_processing output).
        real_respondents: List of real respondent dicts. Required for "comparison" mode.
        mode: "comparison" (real vs twin) or "synthesis" (twin-only analysis).
        concept_names: Full concept names. Defaults to Dove concepts.
        concept_short_names: Short concept names. Defaults to Dove short names.
        study_title: Title for the report metadata.
        skip_themes: If True, skip LLM theme extraction (faster).

    Returns:
        Dict with dashboard data. In comparison mode includes "real", "twin", and "agreement".
        In synthesis mode includes only "twin" analysis.
    """
    c_names = concept_names or CONCEPTS
    c_short = concept_short_names or CONCEPT_SHORT
    n_concepts = len(c_names)

    concepts_list = [
        {
            "id": i,
            "name": c_names[i] if i < len(c_names) else f"Concept {i+1}",
            "short_name": c_short[i] if i < len(c_short) else f"C{i+1}",
            "color": ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6"][i % 5],
        }
        for i in range(n_concepts)
    ]

    # Analyze twin data
    twin_analysis = run_all_analyses(twin_respondents)
    if not skip_themes:
        twin_oe = get_open_ended_responses(twin_respondents)
        twin_analysis["themes"] = extract_themes_with_claude(twin_oe, "digital twin")
    else:
        twin_analysis["themes"] = {}

    result = {
        "metadata": {
            "study": study_title,
            "mode": mode,
            "concepts_tested": n_concepts,
            "twin_n": len(twin_respondents),
            "concept_names": c_names,
            "concept_short_names": c_short,
        },
        "concepts": concepts_list,
        "twin": twin_analysis,
    }

    if mode == "comparison" and real_respondents:
        real_analysis = run_all_analyses(real_respondents)
        if not skip_themes:
            real_oe = get_open_ended_responses(real_respondents)
            real_analysis["themes"] = extract_themes_with_claude(real_oe, "real customer")
        else:
            real_analysis["themes"] = {}

        agreement = compute_agreement(real_analysis, twin_analysis)

        result["real"] = real_analysis
        result["agreement"] = agreement
        result["metadata"]["real_n"] = len(real_respondents)

        # Individual-level validation if same number of respondents
        if len(real_respondents) == len(twin_respondents):
            from individual_analysis import build_individual_validation
            individual_data = build_individual_validation({
                "real": real_respondents,
                "twin": twin_respondents,
            })
            result["individual_validation"] = individual_data

    return result


def build_dashboard_json(base_dir: str, output_path: str):
    """Build the complete dashboard JSON file (original CLI entry point)."""
    print("=" * 60)
    print("Dove Concept Validation - Data Pipeline")
    print("=" * 60)

    # Load data
    data = load_all_data(base_dir)
    real_respondents = data["real"]
    twin_respondents = data["twin"]

    # Run analyses
    print("\nAnalyzing REAL customer data...")
    real_analysis = run_all_analyses(real_respondents)

    print("\nAnalyzing TWIN data...")
    twin_analysis = run_all_analyses(twin_respondents)

    # Theme extraction
    print("\nExtracting themes from open-ended responses...")
    real_oe = get_open_ended_responses(real_respondents)
    twin_oe = get_open_ended_responses(twin_respondents)

    real_themes = extract_themes_with_claude(real_oe, "real customer")
    twin_themes = extract_themes_with_claude(twin_oe, "digital twin")

    real_analysis["themes"] = real_themes
    twin_analysis["themes"] = twin_themes

    # Determine agreement between real and twin
    agreement = compute_agreement(real_analysis, twin_analysis)

    # Build output JSON
    dashboard_data = {
        "metadata": {
            "study": "Dove Body Wash Concept Validation",
            "concepts_tested": 5,
            "real_n": len(real_respondents),
            "twin_n": len(twin_respondents),
            "concept_names": CONCEPTS,
            "concept_short_names": CONCEPT_SHORT,
        },
        "concepts": [
            {
                "id": i,
                "name": CONCEPTS[i],
                "short_name": CONCEPT_SHORT[i],
                "color": ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6"][i],
            }
            for i in range(5)
        ],
        "real": real_analysis,
        "twin": twin_analysis,
        "agreement": agreement,
    }

    # Individual-level twin validation
    print("\nBuilding individual twin validation...")
    individual_data = build_individual_validation(data)
    individual_path = os.path.join(os.path.dirname(output_path), "individual-validation-data.json")
    os.makedirs(os.path.dirname(individual_path), exist_ok=True)
    with open(individual_path, "w") as f:
        json.dump(individual_data, f, indent=2, default=str)
    print(f"Individual validation data written to: {individual_path}")
    print(f"  {individual_data['metadata']['n_pairs']} pairs x {individual_data['metadata']['n_concepts']} concepts")
    print(f"  Overall MAE: {individual_data['aggregate']['overall_mae']}")
    print(f"  Overall ±1 Accuracy: {individual_data['aggregate']['overall_accuracy']}%")
    print(f"  Overall Exact Match: {individual_data['aggregate']['overall_exact']}%")

    # Extended twin analysis (85 twins)
    print("\n" + "=" * 60)
    print("Extended Twin Analysis (85 twins)")
    print("=" * 60)
    step5_dir = os.path.join(base_dir, "step5_per_twin_csvs")
    if os.path.isdir(step5_dir):
        print("Loading all extended twins...")
        extended_twins = load_all_extended_twins(step5_dir)
        print(f"  Loaded {len(extended_twins['all'])} extended twins across {len(extended_twins['by_participant'])} participants")

        # Extended aggregate analysis (n=85)
        print("\nRunning aggregate analysis on 85 extended twins...")
        extended_agg_analysis = run_all_analyses(extended_twins["all"])

        # Theme extraction for extended twins
        print("\nExtracting themes from extended twin open-ended responses...")
        ext_oe = get_open_ended_responses(extended_twins["all"])
        ext_themes = extract_themes_with_claude(ext_oe, "extended digital twin")
        extended_agg_analysis["themes"] = ext_themes

        # Agreement vs real
        ext_agreement = compute_agreement(real_analysis, extended_agg_analysis)

        extended_agg_data = {
            "metadata": {
                "study": "Dove Body Wash Concept Validation - Extended Twins",
                "concepts_tested": 5,
                "real_n": len(real_respondents),
                "twin_n": len(extended_twins["all"]),
                "twins_per_participant": 5,
                "n_participants": len(extended_twins["by_participant"]),
                "concept_names": CONCEPTS,
                "concept_short_names": CONCEPT_SHORT,
            },
            "concepts": [
                {
                    "id": i,
                    "name": CONCEPTS[i],
                    "short_name": CONCEPT_SHORT[i],
                    "color": ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6"][i],
                }
                for i in range(5)
            ],
            "real": real_analysis,
            "twin": extended_agg_analysis,
            "agreement": ext_agreement,
        }

        ext_agg_path = os.path.join(os.path.dirname(output_path), "extended-aggregate-data.json")
        with open(ext_agg_path, "w") as f:
            json.dump(extended_agg_data, f, indent=2, default=str)
        print(f"\nExtended aggregate data written to: {ext_agg_path}")
        print(f"  Agreement vs real: {ext_agreement['level']} - {ext_agreement['description']}")

        # Extended validation (average twin + best match)
        print("\nBuilding extended validation (average + best-match)...")
        extended_val = build_extended_validation(real_respondents, extended_twins["by_participant"])

        ext_val_path = os.path.join(os.path.dirname(output_path), "extended-validation-data.json")
        with open(ext_val_path, "w") as f:
            json.dump(extended_val, f, indent=2, default=str)
        print(f"Extended validation data written to: {ext_val_path}")
        print(f"  Median twin  - Overall MAE: {extended_val['median_twin']['aggregate']['overall_mae']}")
        print(f"  Median twin  - Overall ±1 Accuracy: {extended_val['median_twin']['aggregate']['overall_accuracy']}%")
        print(f"  Average twin - Overall MAE: {extended_val['average_twin']['aggregate']['overall_mae']}")
        print(f"  Average twin - Overall ±1 Accuracy: {extended_val['average_twin']['aggregate']['overall_accuracy']}%")
        print(f"  Best-match   - Overall MAE: {extended_val['best_match']['aggregate']['overall_mae']}")
        print(f"  Best-match   - Overall ±1 Accuracy: {extended_val['best_match']['aggregate']['overall_accuracy']}%")
        print(f"  Twin selection: {extended_val['best_match']['twin_selection_summary']}")
    else:
        print(f"  Warning: {step5_dir} not found, skipping extended analysis")

    # Write output
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(dashboard_data, f, indent=2, default=str)

    print(f"\nDashboard data written to: {output_path}")
    print(f"File size: {os.path.getsize(output_path) / 1024:.1f} KB")

    # Verify output
    verify_output(dashboard_data)


def compute_agreement(real: dict, twin: dict) -> dict:
    """Determine agreement between real and twin analyses."""
    real_tier1 = [name for name, tier in real["tiers"].items() if tier == 1]
    twin_tier1 = [name for name, tier in twin["tiers"].items() if tier == 1]

    real_top = max(real["composites"].items(), key=lambda x: x[1] or 0)[0]
    twin_top = max(twin["composites"].items(), key=lambda x: x[1] or 0)[0]

    # Check overlap
    overlap = set(real_tier1) & set(twin_tier1)

    if real_top == twin_top:
        level = "Confirmed"
        description = f"Both sources agree: {real_top} is the top concept"
    elif overlap:
        level = "Directional"
        description = f"Overlap in Tier 1: {', '.join(overlap)}"
    else:
        level = "Divergent"
        description = f"Real favors {real_top}, Twin favors {twin_top}"

    return {
        "level": level,
        "description": description,
        "real_tier1": real_tier1,
        "twin_tier1": twin_tier1,
        "real_top": real_top,
        "twin_top": twin_top,
    }


def verify_output(data: dict):
    """Verify the output JSON has all required fields."""
    print("\nVerification:")
    checks = [
        ("metadata", "metadata" in data),
        ("concepts array", len(data.get("concepts", [])) == 5),
        ("real.t2b", "t2b" in data.get("real", {})),
        ("real.composites", "composites" in data.get("real", {})),
        ("real.friedman", "friedman" in data.get("real", {})),
        ("real.wilcoxon", "wilcoxon" in data.get("real", {})),
        ("real.tiers", "tiers" in data.get("real", {})),
        ("real.turf", "turf" in data.get("real", {})),
        ("real.themes", "themes" in data.get("real", {})),
        ("real.barriers", "barriers" in data.get("real", {})),
        ("twin.t2b", "t2b" in data.get("twin", {})),
        ("twin.composites", "composites" in data.get("twin", {})),
        ("agreement", "agreement" in data),
    ]

    all_pass = True
    for name, passed in checks:
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_pass = False
        print(f"  [{status}] {name}")

    # Print key results
    print("\nKey Results:")
    real_composites = data["real"]["composites"]
    sorted_concepts = sorted(real_composites.items(), key=lambda x: x[1] or 0, reverse=True)
    for name, score in sorted_concepts:
        tier = data["real"]["tiers"].get(name, "?")
        print(f"  {name}: {score} (Tier {tier})")

    print(f"\n  Agreement: {data['agreement']['level']} - {data['agreement']['description']}")
    print(f"  Friedman p={data['real']['friedman'].get('p_value', 'N/A')}")

    turf = data["real"]["turf"]
    if turf.get("best_2"):
        print(f"  TURF Best 2: {' + '.join(turf['best_2']['concepts'])} ({turf['best_2']['reach_pct']}% reach)")


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_path = os.path.join(base_dir, "dove-dashboard", "src", "data", "dashboard-data.json")
    build_dashboard_json(base_dir, output_path)
