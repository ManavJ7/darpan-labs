"""Deterministic sample size calculator — PURE computation, no LLM, no database."""

import math

from app.schemas.research_design import SampleSizeResult, QuotaAllocation


class SampleCalculator:
    """Pure deterministic calculator for sample sizing, quota allocation,
    field duration estimation, and cost estimation.

    No LLM calls. No database access. All methods are static.
    """

    BASE_N_PER_CONCEPT = {
        "monadic": 150,
        "sequential_monadic": 75,
        "proto_monadic": 100,
    }

    # Extended methodologies — used as fallback when BASE_N_PER_CONCEPT
    # doesn't contain the methodology. Keeps backward compat with the
    # original 3-method dict while supporting additional methodologies.
    EXTENDED_BASE_N = {
        "maxdiff": 200,
        "conjoint_lite": 300,
        "van_westendorp": 200,
        "gabor_granger": 200,
        "perceptual_mapping": 150,
    }

    Z_SCORES = {
        0.90: 1.645,
        0.95: 1.960,
        0.99: 2.576,
    }

    # Cost per completed response in INR by data-collection method
    COST_PER_RESPONSE = {
        "online_panel": 150,
        "mobile_survey": 200,
        "capi": 500,
        "digital_twin_panel": 50,
    }

    # Field-duration parameters: (divisor, minimum_days)
    FIELD_DURATION_PARAMS = {
        "online_panel": (50, 3),
        "mobile_survey": (40, 4),
        "capi": (20, 7),
        "digital_twin_panel": (1, 1),  # instant — 1 day floor
    }

    # ── Sample Size ──────────────────────────────────────────────

    @staticmethod
    def calculate_sample_size(
        methodology: str,
        num_concepts: int,
        concepts_per_respondent: int = 3,
        confidence_level: float = 0.95,
        margin_of_error: float = 0.05,
        num_subgroups: int = 1,
        min_per_subgroup: int = 30,
    ) -> SampleSizeResult:
        """Calculate total respondents, per-concept n, incidence-adjusted n,
        and recommended panel size.

        Logic:
        1. base_n from BASE_N_PER_CONCEPT (default to monadic if unknown).
        2. total = base_n * num_concepts.
           For sequential_monadic: total = ceil(base_n * num_concepts / concepts_per_respondent).
        3. If MOE <= 0.03 → multiply total by (0.05 / margin_of_error)^2.
        4. Ensure subgroup minimum: total >= num_subgroups * min_per_subgroup.
        5. Incidence adjustment: incidence_adjusted = ceil(total / 0.6).
        6. Panel size: recommended_panel_size = ceil(incidence_adjusted / 0.15).
        """
        all_methods = {**SampleCalculator.BASE_N_PER_CONCEPT, **SampleCalculator.EXTENDED_BASE_N}
        if methodology not in all_methods:
            raise ValueError(
                f"Unknown methodology '{methodology}'. "
                f"Valid options: {list(all_methods.keys())}"
            )
        if num_concepts < 1:
            raise ValueError("num_concepts must be >= 1")
        if concepts_per_respondent < 1:
            raise ValueError("concepts_per_respondent must be >= 1")
        if margin_of_error <= 0 or margin_of_error >= 1:
            raise ValueError("margin_of_error must be between 0 (exclusive) and 1 (exclusive)")
        if confidence_level not in SampleCalculator.Z_SCORES:
            raise ValueError(
                f"Unsupported confidence_level {confidence_level}. "
                f"Supported: {list(SampleCalculator.Z_SCORES.keys())}"
            )
        if num_subgroups < 1:
            raise ValueError("num_subgroups must be >= 1")
        if min_per_subgroup < 1:
            raise ValueError("min_per_subgroup must be >= 1")

        base_n = all_methods[methodology]

        # Step 1 — raw total
        if methodology == "sequential_monadic":
            total = math.ceil(base_n * num_concepts / concepts_per_respondent)
        else:
            total = base_n * num_concepts

        # Step 2 — stricter MOE adjustment
        if margin_of_error <= 0.03:
            moe_multiplier = (0.05 / margin_of_error) ** 2
            total = math.ceil(total * moe_multiplier)

        # Step 3 — subgroup minimum
        subgroup_floor = num_subgroups * min_per_subgroup
        total = max(total, subgroup_floor)

        per_concept = math.ceil(total / num_concepts) if num_concepts > 0 else total

        # Step 4 — incidence adjustment (assume 60 % incidence rate)
        incidence_adjusted = math.ceil(total / 0.6)

        # Step 5 — panel size (assume 15 % response rate)
        recommended_panel_size = math.ceil(incidence_adjusted / 0.15)

        return SampleSizeResult(
            total_respondents=total,
            per_concept=per_concept,
            incidence_adjusted=incidence_adjusted,
            recommended_panel_size=recommended_panel_size,
        )

    # ── Quota Allocation ─────────────────────────────────────────

    @staticmethod
    def allocate_quotas(
        total_respondents: int,
        demographic_dimensions: list[dict],
    ) -> list[QuotaAllocation]:
        """Allocate quotas across demographic dimensions.

        Each dimension is a dict:
            {
                "dimension": "age",
                "segments": [
                    {"range": "18-24", "target_pct": 30},
                    {"range": "25-34", "target_pct": 40},
                    {"range": "35-44", "target_pct": 30},
                ]
            }

        Validation: sum of target_pct per dimension must equal 100.
        For each segment:
            target_n = total_respondents * target_pct / 100
            min_n = max(30, floor(target_n * 0.85))
        """
        if total_respondents < 1:
            raise ValueError("total_respondents must be >= 1")
        if not demographic_dimensions:
            raise ValueError("demographic_dimensions must not be empty")

        allocations: list[QuotaAllocation] = []

        for dim in demographic_dimensions:
            dimension_name = dim.get("dimension")
            segments = dim.get("segments", [])

            if not dimension_name:
                raise ValueError("Each demographic dimension must have a 'dimension' name")
            if not segments:
                raise ValueError(f"Dimension '{dimension_name}' must have at least one segment")

            pct_sum = sum(seg.get("target_pct", 0) for seg in segments)
            if pct_sum != 100:
                raise ValueError(
                    f"Segments for dimension '{dimension_name}' must sum to 100%, got {pct_sum}%"
                )

            computed_segments: list[dict] = []
            for seg in segments:
                target_pct = seg["target_pct"]
                target_n = math.floor(total_respondents * target_pct / 100)
                min_n = max(30, math.floor(target_n * 0.85))
                computed_segments.append({
                    "range": seg.get("range", ""),
                    "target_pct": target_pct,
                    "target_n": target_n,
                    "min_n": min_n,
                })

            allocations.append(
                QuotaAllocation(dimension=dimension_name, segments=computed_segments)
            )

        return allocations

    # ── Recalculate on Edit ──────────────────────────────────────

    @staticmethod
    def recalculate_on_edit(current_design: dict, edits: dict) -> dict:
        """Recalculate affected fields when the user edits the research design.

        Supported edit keys:
        - methodology → recalculate sample_size + quotas
        - confidence_level → recalculate sample_size
        - margin_of_error → recalculate sample_size
        - total_sample_size (manual) → reverse-calculate margin_of_error
        - num_concepts → recalculate sample_size
        - concepts_per_respondent → recalculate sample_size
        - num_subgroups → recalculate sample_size
        - data_collection_method → recalculate field duration + cost
        - demographic_quotas → re-allocate quotas

        Returns an updated design dict.
        """
        design = {**current_design}

        # Apply edits into the design
        for key, value in edits.items():
            design[key] = value

        # If total_sample_size was manually changed → reverse-calculate MOE
        if "total_sample_size" in edits and "margin_of_error" not in edits:
            manual_total = edits["total_sample_size"]
            methodology = design.get("testing_methodology", design.get("methodology", "monadic"))
            num_concepts = design.get("num_concepts", 1)
            confidence_level = design.get("confidence_level", 0.95)

            z = SampleCalculator.Z_SCORES.get(confidence_level, 1.960)
            # Using the standard formula: n = z^2 * p * (1-p) / MOE^2
            # where p = 0.5 (maximum variance), solve for MOE:
            # MOE = z * sqrt(p*(1-p)/n_per_concept)
            per_concept = manual_total / num_concepts if num_concepts > 0 else manual_total
            if per_concept > 0:
                moe = z * math.sqrt(0.25 / per_concept)
                design["margin_of_error"] = round(moe, 4)
            design["total_sample_size"] = manual_total

        # If methodology, confidence_level, margin_of_error, num_concepts, or
        # concepts_per_respondent changed → recalculate sample
        recalc_triggers = {
            "methodology", "testing_methodology", "confidence_level",
            "margin_of_error", "num_concepts", "concepts_per_respondent",
            "num_subgroups",
        }
        if recalc_triggers & set(edits.keys()) and "total_sample_size" not in edits:
            methodology = design.get("testing_methodology", design.get("methodology", "monadic"))
            num_concepts = design.get("num_concepts", 1)
            concepts_per_respondent = design.get("concepts_per_respondent", 3)
            confidence_level = design.get("confidence_level", 0.95)
            margin_of_error = design.get("margin_of_error", 0.05)
            num_subgroups = design.get("num_subgroups", 1)
            min_per_subgroup = design.get("min_per_subgroup", 30)

            result = SampleCalculator.calculate_sample_size(
                methodology=methodology,
                num_concepts=num_concepts,
                concepts_per_respondent=concepts_per_respondent,
                confidence_level=confidence_level,
                margin_of_error=margin_of_error,
                num_subgroups=num_subgroups,
                min_per_subgroup=min_per_subgroup,
            )
            design["total_sample_size"] = result.total_respondents

        # If demographic_quotas or total_sample_size changed → re-allocate quotas
        total = design.get("total_sample_size", 0)
        if "demographic_quotas" in edits and total > 0:
            raw_dims = edits["demographic_quotas"]
            if raw_dims:
                quotas = SampleCalculator.allocate_quotas(total, raw_dims)
                design["demographic_quotas"] = [q.model_dump() for q in quotas]

        # If methodology or data_collection_method changed → recalculate duration + cost
        data_collection_method = design.get("data_collection_method", "online_panel")
        total = design.get("total_sample_size", 0)

        if any(k in edits for k in ("methodology", "testing_methodology",
                                     "data_collection_method", "total_sample_size",
                                     "confidence_level", "margin_of_error",
                                     "num_concepts", "concepts_per_respondent",
                                     "num_subgroups")):
            if total > 0:
                design["estimated_field_duration"] = SampleCalculator.estimate_field_duration(
                    total, data_collection_method
                )
                methodology_for_cost = design.get(
                    "testing_methodology", design.get("methodology", "monadic")
                )
                design["estimated_cost"] = SampleCalculator.estimate_cost(
                    total, methodology_for_cost, data_collection_method
                )

        return design

    # ── Field Duration Estimate ──────────────────────────────────

    @staticmethod
    def estimate_field_duration(
        total_respondents: int,
        data_collection_method: str,
    ) -> int:
        """Estimate field duration in days.

        online_panel:       ceil(respondents / 50), min 3
        mobile_survey:      ceil(respondents / 40), min 4
        capi:               ceil(respondents / 20), min 7
        digital_twin_panel: 1 (instant)
        """
        if total_respondents < 1:
            raise ValueError("total_respondents must be >= 1")

        params = SampleCalculator.FIELD_DURATION_PARAMS.get(data_collection_method)
        if params is None:
            raise ValueError(
                f"Unknown data_collection_method '{data_collection_method}'. "
                f"Valid options: {list(SampleCalculator.FIELD_DURATION_PARAMS.keys())}"
            )

        divisor, minimum = params
        return max(minimum, math.ceil(total_respondents / divisor))

    # ── Cost Estimate ────────────────────────────────────────────

    @staticmethod
    def estimate_cost(
        total_respondents: int,
        methodology: str,
        data_collection_method: str,
    ) -> int:
        """Estimate total fieldwork cost in INR.

        cost = total_respondents * cost_per_response
        Cost per response by method (INR):
            online_panel:       150
            mobile_survey:      200
            capi:               500
            digital_twin_panel:  50
        """
        if total_respondents < 1:
            raise ValueError("total_respondents must be >= 1")

        cpr = SampleCalculator.COST_PER_RESPONSE.get(data_collection_method)
        if cpr is None:
            raise ValueError(
                f"Unknown data_collection_method '{data_collection_method}'. "
                f"Valid options: {list(SampleCalculator.COST_PER_RESPONSE.keys())}"
            )

        return total_respondents * cpr
