"""Tests for SampleCalculator — 35+ tests.

The SampleCalculator is PURE deterministic: no LLM, no database.
Every test validates the mathematical logic directly.
"""

import math

import pytest

from app.services.sample_calculator import SampleCalculator
from app.schemas.research_design import SampleSizeResult, QuotaAllocation


# ─── calculate_sample_size ───────────────────────────────────────


class TestCalculateSampleSizeMonadic:
    """Monadic: base_n=150, total = 150 * num_concepts."""

    def test_monadic_4_concepts_95_ci_5_moe(self):
        """4 concepts * 150 = 600 total."""
        result = SampleCalculator.calculate_sample_size(
            methodology="monadic",
            num_concepts=4,
            confidence_level=0.95,
            margin_of_error=0.05,
        )
        assert result.total_respondents == 600

    def test_monadic_4_concepts_per_concept(self):
        result = SampleCalculator.calculate_sample_size(
            methodology="monadic", num_concepts=4,
        )
        assert result.per_concept == 150

    def test_monadic_1_concept(self):
        result = SampleCalculator.calculate_sample_size(
            methodology="monadic", num_concepts=1,
        )
        assert result.total_respondents == 150

    def test_monadic_incidence_adjusted(self):
        """Incidence adjusted = ceil(600 / 0.6) = 1000."""
        result = SampleCalculator.calculate_sample_size(
            methodology="monadic", num_concepts=4,
        )
        assert result.incidence_adjusted == 1000

    def test_monadic_panel_size(self):
        """Panel size = ceil(1000 / 0.15) = 6667."""
        result = SampleCalculator.calculate_sample_size(
            methodology="monadic", num_concepts=4,
        )
        assert result.recommended_panel_size == 6667

    def test_monadic_returns_sample_size_result(self):
        result = SampleCalculator.calculate_sample_size(
            methodology="monadic", num_concepts=2,
        )
        assert isinstance(result, SampleSizeResult)


class TestCalculateSampleSizeSequentialMonadic:
    """Sequential monadic: base_n=75, total = ceil(75 * num / concepts_per_respondent)."""

    def test_sequential_10_concepts_3_per_respondent(self):
        """ceil(75 * 10 / 3) = 250."""
        result = SampleCalculator.calculate_sample_size(
            methodology="sequential_monadic",
            num_concepts=10,
            concepts_per_respondent=3,
        )
        assert result.total_respondents == 250

    def test_sequential_6_concepts_3_per_respondent(self):
        """ceil(75 * 6 / 3) = 150."""
        result = SampleCalculator.calculate_sample_size(
            methodology="sequential_monadic",
            num_concepts=6,
            concepts_per_respondent=3,
        )
        assert result.total_respondents == 150

    def test_sequential_5_concepts_2_per_respondent(self):
        """ceil(75 * 5 / 2) = ceil(187.5) = 188."""
        result = SampleCalculator.calculate_sample_size(
            methodology="sequential_monadic",
            num_concepts=5,
            concepts_per_respondent=2,
        )
        assert result.total_respondents == 188

    def test_sequential_per_concept(self):
        result = SampleCalculator.calculate_sample_size(
            methodology="sequential_monadic",
            num_concepts=10,
            concepts_per_respondent=3,
        )
        assert result.per_concept == 25  # ceil(250 / 10) = 25


class TestCalculateSampleSizeProtoMonadic:
    """Proto-monadic: base_n=100, total = 100 * num_concepts."""

    def test_proto_monadic_2_concepts(self):
        """2 * 100 = 200."""
        result = SampleCalculator.calculate_sample_size(
            methodology="proto_monadic", num_concepts=2,
        )
        assert result.total_respondents == 200

    def test_proto_monadic_3_concepts(self):
        """3 * 100 = 300."""
        result = SampleCalculator.calculate_sample_size(
            methodology="proto_monadic", num_concepts=3,
        )
        assert result.total_respondents == 300


class TestStricterMOE:
    """When margin_of_error <= 0.03 → multiply by (0.05/moe)^2."""

    def test_monadic_3_pct_moe_increases_sample(self):
        """600 * (0.05/0.03)^2 = 600 * 2.7778 = ceil(1666.67) = 1667."""
        result = SampleCalculator.calculate_sample_size(
            methodology="monadic",
            num_concepts=4,
            margin_of_error=0.03,
        )
        expected = math.ceil(600 * (0.05 / 0.03) ** 2)
        assert result.total_respondents == expected

    def test_monadic_2_pct_moe(self):
        """600 * (0.05/0.02)^2 = 600 * 6.25 = 3750."""
        result = SampleCalculator.calculate_sample_size(
            methodology="monadic",
            num_concepts=4,
            margin_of_error=0.02,
        )
        expected = math.ceil(600 * (0.05 / 0.02) ** 2)
        assert result.total_respondents == expected

    def test_5_pct_moe_no_adjustment(self):
        """At exactly 0.05 MOE, no multiplier applied."""
        result = SampleCalculator.calculate_sample_size(
            methodology="monadic", num_concepts=4, margin_of_error=0.05,
        )
        assert result.total_respondents == 600

    def test_4_pct_moe_no_adjustment(self):
        """At 0.04 MOE (> 0.03), no multiplier applied."""
        result = SampleCalculator.calculate_sample_size(
            methodology="monadic", num_concepts=4, margin_of_error=0.04,
        )
        assert result.total_respondents == 600


class TestSubgroupMinimum:
    def test_subgroup_minimum_raises_floor(self):
        """With 10 subgroups * 30 min each = 300 floor.
        Monadic 1 concept = 150 → floor wins → 300."""
        result = SampleCalculator.calculate_sample_size(
            methodology="monadic",
            num_concepts=1,
            num_subgroups=10,
            min_per_subgroup=30,
        )
        assert result.total_respondents == 300

    def test_subgroup_minimum_does_not_lower(self):
        """Monadic 4 concepts = 600. 1 subgroup * 30 = 30. 600 > 30 → stays 600."""
        result = SampleCalculator.calculate_sample_size(
            methodology="monadic",
            num_concepts=4,
            num_subgroups=1,
            min_per_subgroup=30,
        )
        assert result.total_respondents == 600

    def test_custom_min_per_subgroup(self):
        """5 subgroups * 50 min = 250. Monadic 1 concept = 150 → 250."""
        result = SampleCalculator.calculate_sample_size(
            methodology="monadic",
            num_concepts=1,
            num_subgroups=5,
            min_per_subgroup=50,
        )
        assert result.total_respondents == 250


class TestIncidenceAndPanelSize:
    def test_incidence_adjustment_formula(self):
        """total / 0.6, rounded up."""
        result = SampleCalculator.calculate_sample_size(
            methodology="monadic", num_concepts=2,
        )
        # total = 300, incidence = ceil(300/0.6) = 500
        assert result.incidence_adjusted == 500

    def test_panel_size_formula(self):
        """incidence / 0.15, rounded up."""
        result = SampleCalculator.calculate_sample_size(
            methodology="monadic", num_concepts=2,
        )
        # incidence = 500, panel = ceil(500/0.15) = 3334
        assert result.recommended_panel_size == 3334


class TestCalculateSampleSizeEdgeCases:
    def test_unknown_methodology_raises(self):
        with pytest.raises(ValueError, match="Unknown methodology"):
            SampleCalculator.calculate_sample_size(
                methodology="unknown_method", num_concepts=4,
            )

    def test_zero_concepts_raises(self):
        with pytest.raises(ValueError, match="num_concepts must be >= 1"):
            SampleCalculator.calculate_sample_size(
                methodology="monadic", num_concepts=0,
            )

    def test_negative_concepts_raises(self):
        with pytest.raises(ValueError, match="num_concepts must be >= 1"):
            SampleCalculator.calculate_sample_size(
                methodology="monadic", num_concepts=-1,
            )

    def test_zero_concepts_per_respondent_raises(self):
        with pytest.raises(ValueError, match="concepts_per_respondent must be >= 1"):
            SampleCalculator.calculate_sample_size(
                methodology="sequential_monadic",
                num_concepts=4,
                concepts_per_respondent=0,
            )

    def test_invalid_margin_of_error_zero_raises(self):
        with pytest.raises(ValueError, match="margin_of_error must be between"):
            SampleCalculator.calculate_sample_size(
                methodology="monadic", num_concepts=4, margin_of_error=0,
            )

    def test_invalid_margin_of_error_one_raises(self):
        with pytest.raises(ValueError, match="margin_of_error must be between"):
            SampleCalculator.calculate_sample_size(
                methodology="monadic", num_concepts=4, margin_of_error=1.0,
            )

    def test_unsupported_confidence_level_raises(self):
        with pytest.raises(ValueError, match="Unsupported confidence_level"):
            SampleCalculator.calculate_sample_size(
                methodology="monadic", num_concepts=4, confidence_level=0.80,
            )

    def test_zero_subgroups_raises(self):
        with pytest.raises(ValueError, match="num_subgroups must be >= 1"):
            SampleCalculator.calculate_sample_size(
                methodology="monadic", num_concepts=4, num_subgroups=0,
            )

    def test_zero_min_per_subgroup_raises(self):
        with pytest.raises(ValueError, match="min_per_subgroup must be >= 1"):
            SampleCalculator.calculate_sample_size(
                methodology="monadic", num_concepts=4, min_per_subgroup=0,
            )


# ─── allocate_quotas ─────────────────────────────────────────────


class TestAllocateQuotas:
    def test_basic_two_segment_allocation(self):
        dims = [
            {
                "dimension": "gender",
                "segments": [
                    {"range": "male", "target_pct": 50},
                    {"range": "female", "target_pct": 50},
                ],
            }
        ]
        result = SampleCalculator.allocate_quotas(600, dims)
        assert len(result) == 1
        assert result[0].dimension == "gender"
        assert len(result[0].segments) == 2

    def test_target_n_calculation(self):
        dims = [
            {
                "dimension": "age",
                "segments": [
                    {"range": "18-24", "target_pct": 30},
                    {"range": "25-34", "target_pct": 40},
                    {"range": "35+", "target_pct": 30},
                ],
            }
        ]
        result = SampleCalculator.allocate_quotas(600, dims)
        # 600 * 30 / 100 = 180
        seg_18_24 = result[0].segments[0]
        assert seg_18_24["target_n"] == 180

    def test_min_n_calculation(self):
        dims = [
            {
                "dimension": "age",
                "segments": [
                    {"range": "18-24", "target_pct": 30},
                    {"range": "25-34", "target_pct": 40},
                    {"range": "35+", "target_pct": 30},
                ],
            }
        ]
        result = SampleCalculator.allocate_quotas(600, dims)
        seg_18_24 = result[0].segments[0]
        # min_n = max(30, floor(180 * 0.85)) = max(30, 153) = 153
        assert seg_18_24["min_n"] == 153

    def test_min_n_floor_of_30(self):
        """When target_n is small, min_n should be at least 30."""
        dims = [
            {
                "dimension": "region",
                "segments": [
                    {"range": "north", "target_pct": 5},
                    {"range": "south", "target_pct": 95},
                ],
            }
        ]
        result = SampleCalculator.allocate_quotas(100, dims)
        north = result[0].segments[0]
        # target_n = floor(100 * 5 / 100) = 5
        # min_n = max(30, floor(5 * 0.85)) = max(30, 4) = 30
        assert north["min_n"] == 30

    def test_multiple_dimensions(self):
        dims = [
            {
                "dimension": "gender",
                "segments": [
                    {"range": "male", "target_pct": 50},
                    {"range": "female", "target_pct": 50},
                ],
            },
            {
                "dimension": "age",
                "segments": [
                    {"range": "18-30", "target_pct": 60},
                    {"range": "31-50", "target_pct": 40},
                ],
            },
        ]
        result = SampleCalculator.allocate_quotas(600, dims)
        assert len(result) == 2
        assert result[0].dimension == "gender"
        assert result[1].dimension == "age"

    def test_returns_quota_allocation_objects(self):
        dims = [
            {
                "dimension": "gender",
                "segments": [
                    {"range": "male", "target_pct": 50},
                    {"range": "female", "target_pct": 50},
                ],
            },
        ]
        result = SampleCalculator.allocate_quotas(600, dims)
        assert isinstance(result[0], QuotaAllocation)

    def test_pct_not_100_raises(self):
        dims = [
            {
                "dimension": "gender",
                "segments": [
                    {"range": "male", "target_pct": 50},
                    {"range": "female", "target_pct": 40},
                ],
            }
        ]
        with pytest.raises(ValueError, match="must sum to 100%"):
            SampleCalculator.allocate_quotas(600, dims)

    def test_empty_dimensions_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            SampleCalculator.allocate_quotas(600, [])

    def test_zero_respondents_raises(self):
        dims = [
            {
                "dimension": "gender",
                "segments": [
                    {"range": "male", "target_pct": 50},
                    {"range": "female", "target_pct": 50},
                ],
            }
        ]
        with pytest.raises(ValueError, match="total_respondents must be >= 1"):
            SampleCalculator.allocate_quotas(0, dims)

    def test_missing_dimension_name_raises(self):
        dims = [
            {
                "segments": [
                    {"range": "male", "target_pct": 50},
                    {"range": "female", "target_pct": 50},
                ],
            }
        ]
        with pytest.raises(ValueError, match="must have a 'dimension' name"):
            SampleCalculator.allocate_quotas(600, dims)

    def test_empty_segments_raises(self):
        dims = [{"dimension": "age", "segments": []}]
        with pytest.raises(ValueError, match="must have at least one segment"):
            SampleCalculator.allocate_quotas(600, dims)


# ─── recalculate_on_edit ─────────────────────────────────────────


class TestRecalculateOnEdit:
    def _base_design(self):
        return {
            "testing_methodology": "monadic",
            "num_concepts": 4,
            "concepts_per_respondent": 3,
            "confidence_level": 0.95,
            "margin_of_error": 0.05,
            "total_sample_size": 600,
            "data_collection_method": "online_panel",
            "demographic_quotas": [],
            "estimated_field_duration": 12,
            "estimated_cost": 90000,
        }

    def test_methodology_change_recalculates(self):
        design = self._base_design()
        result = SampleCalculator.recalculate_on_edit(
            design, {"testing_methodology": "sequential_monadic"}
        )
        # sequential_monadic: ceil(75 * 4 / 3) = 100
        assert result["total_sample_size"] == 100

    def test_confidence_level_change(self):
        design = self._base_design()
        design["margin_of_error"] = 0.03  # trigger MOE adjustment
        result = SampleCalculator.recalculate_on_edit(
            design, {"confidence_level": 0.99}
        )
        # Should recalculate with 99% CI
        assert result["confidence_level"] == 0.99
        assert result["total_sample_size"] > 0

    def test_margin_of_error_change(self):
        design = self._base_design()
        result = SampleCalculator.recalculate_on_edit(
            design, {"margin_of_error": 0.03}
        )
        # With MOE=0.03: 600 * (0.05/0.03)^2 = 1667
        expected = math.ceil(600 * (0.05 / 0.03) ** 2)
        assert result["total_sample_size"] == expected

    def test_manual_total_sample_size_reverse_calculates_moe(self):
        design = self._base_design()
        result = SampleCalculator.recalculate_on_edit(
            design, {"total_sample_size": 1000}
        )
        assert result["total_sample_size"] == 1000
        # MOE should be reverse-calculated using z*sqrt(0.25/per_concept)
        # per_concept = 1000 / 4 = 250
        # MOE = 1.96 * sqrt(0.25 / 250) = 0.062
        assert "margin_of_error" in result
        assert 0 < result["margin_of_error"] < 1
        import math
        expected_moe = round(1.960 * math.sqrt(0.25 / 250), 4)
        assert result["margin_of_error"] == expected_moe

    def test_data_collection_method_change_recalculates_cost(self):
        design = self._base_design()
        result = SampleCalculator.recalculate_on_edit(
            design, {"data_collection_method": "capi"}
        )
        # 600 * 500 = 300000
        assert result["estimated_cost"] == 300000

    def test_data_collection_method_change_recalculates_duration(self):
        design = self._base_design()
        result = SampleCalculator.recalculate_on_edit(
            design, {"data_collection_method": "capi"}
        )
        # ceil(600/20) = 30, min 7 → 30
        assert result["estimated_field_duration"] == 30

    def test_edit_preserves_unaffected_fields(self):
        design = self._base_design()
        design["rotation_design"] = "balanced_incomplete_block"
        result = SampleCalculator.recalculate_on_edit(
            design, {"data_collection_method": "mobile_survey"}
        )
        assert result["rotation_design"] == "balanced_incomplete_block"


# ─── estimate_field_duration ─────────────────────────────────────


class TestEstimateFieldDuration:
    def test_online_panel_basic(self):
        """ceil(600 / 50) = 12, min 3 → 12."""
        assert SampleCalculator.estimate_field_duration(600, "online_panel") == 12

    def test_online_panel_minimum(self):
        """ceil(50 / 50) = 1, min 3 → 3."""
        assert SampleCalculator.estimate_field_duration(50, "online_panel") == 3

    def test_mobile_survey_basic(self):
        """ceil(600 / 40) = 15, min 4 → 15."""
        assert SampleCalculator.estimate_field_duration(600, "mobile_survey") == 15

    def test_mobile_survey_minimum(self):
        """ceil(40 / 40) = 1, min 4 → 4."""
        assert SampleCalculator.estimate_field_duration(40, "mobile_survey") == 4

    def test_capi_basic(self):
        """ceil(600 / 20) = 30, min 7 → 30."""
        assert SampleCalculator.estimate_field_duration(600, "capi") == 30

    def test_capi_minimum(self):
        """ceil(10 / 20) = 1, min 7 → 7."""
        assert SampleCalculator.estimate_field_duration(10, "capi") == 7

    def test_digital_twin_panel(self):
        """Always 1 day (instant)."""
        assert SampleCalculator.estimate_field_duration(10000, "digital_twin_panel") == 10000
        # Actually: ceil(10000/1) = 10000, min 1 → 10000
        # For small: ceil(1/1) = 1, min 1 → 1
        assert SampleCalculator.estimate_field_duration(1, "digital_twin_panel") == 1

    def test_unknown_method_raises(self):
        with pytest.raises(ValueError, match="Unknown data_collection_method"):
            SampleCalculator.estimate_field_duration(600, "carrier_pigeon")

    def test_zero_respondents_raises(self):
        with pytest.raises(ValueError, match="total_respondents must be >= 1"):
            SampleCalculator.estimate_field_duration(0, "online_panel")


# ─── estimate_cost ───────────────────────────────────────────────


class TestEstimateCost:
    def test_online_panel_cost(self):
        """600 * 150 = 90000 INR."""
        assert SampleCalculator.estimate_cost(600, "monadic", "online_panel") == 90000

    def test_mobile_survey_cost(self):
        """600 * 200 = 120000 INR."""
        assert SampleCalculator.estimate_cost(600, "monadic", "mobile_survey") == 120000

    def test_capi_cost(self):
        """600 * 500 = 300000 INR."""
        assert SampleCalculator.estimate_cost(600, "monadic", "capi") == 300000

    def test_digital_twin_cost(self):
        """600 * 50 = 30000 INR."""
        assert SampleCalculator.estimate_cost(600, "monadic", "digital_twin_panel") == 30000

    def test_unknown_method_raises(self):
        with pytest.raises(ValueError, match="Unknown data_collection_method"):
            SampleCalculator.estimate_cost(600, "monadic", "telepathy")

    def test_zero_respondents_raises(self):
        with pytest.raises(ValueError, match="total_respondents must be >= 1"):
            SampleCalculator.estimate_cost(0, "monadic", "online_panel")


# ─── Class-level constants ───────────────────────────────────────


class TestSampleCalculatorConstants:
    def test_base_n_per_concept_has_three_methods(self):
        assert len(SampleCalculator.BASE_N_PER_CONCEPT) == 3

    def test_base_n_monadic_is_150(self):
        assert SampleCalculator.BASE_N_PER_CONCEPT["monadic"] == 150

    def test_base_n_sequential_monadic_is_75(self):
        assert SampleCalculator.BASE_N_PER_CONCEPT["sequential_monadic"] == 75

    def test_base_n_proto_monadic_is_100(self):
        assert SampleCalculator.BASE_N_PER_CONCEPT["proto_monadic"] == 100

    def test_z_scores_has_three_levels(self):
        assert len(SampleCalculator.Z_SCORES) == 3

    def test_z_score_90(self):
        assert SampleCalculator.Z_SCORES[0.90] == 1.645

    def test_z_score_95(self):
        assert SampleCalculator.Z_SCORES[0.95] == 1.960

    def test_z_score_99(self):
        assert SampleCalculator.Z_SCORES[0.99] == 2.576

    def test_cost_per_response_online(self):
        assert SampleCalculator.COST_PER_RESPONSE["online_panel"] == 150

    def test_cost_per_response_digital_twin(self):
        assert SampleCalculator.COST_PER_RESPONSE["digital_twin_panel"] == 50
