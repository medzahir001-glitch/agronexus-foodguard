"""Automated regression tests for FOODNEXA Risk Engine V2."""
import unittest

from foodguard_engine import (
    assess_dairy_food_safety_risk,
    TOTAL_MAX_SCORE,
    MODERATE_THRESHOLD_PERCENT,
    HIGH_THRESHOLD_PERCENT,
)


class TestFoodnexaRiskEngineV2(unittest.TestCase):
    def test_all_missing_never_gets_global_score(self):
        result = assess_dairy_food_safety_risk()
        self.assertEqual(result["status"], "SUCCESS")
        self.assertIsNone(result["risk_score"])
        self.assertEqual(result["risk_level"], "Données insuffisantes")
        self.assertEqual(result["data_completeness"], 0.0)
        self.assertEqual(result["available_factors"], 0)
        self.assertIsNone(result["confidence"])

    def test_low_signal_complete_case(self):
        result = assess_dairy_food_safety_risk(
            temperature=4, storage_days=2, ph=6.6,
            cold_chain_broken=False, hygiene_controlled=True,
            pasteurized=True, batch_id="TEST-AUDIT-002",
        )
        self.assertEqual(result["data_completeness"], 100.0)
        self.assertEqual(result["raw_score"], 0)
        self.assertEqual(result["risk_score"], 0.0)
        self.assertEqual(result["risk_level"], "Faible")

    def test_high_signal_is_normalized_not_clipped(self):
        result = assess_dairy_food_safety_risk(
            temperature=12, storage_days=10, ph=5.0,
            cold_chain_broken=True, hygiene_controlled=False,
            pasteurized=False, batch_id="TEST-AUDIT-003",
        )
        self.assertEqual(result["raw_score"], TOTAL_MAX_SCORE)
        self.assertEqual(result["risk_score"], 100.0)
        self.assertEqual(result["risk_level"], "Élevé")

    def test_partial_data_has_no_global_score_but_keeps_signals(self):
        result = assess_dairy_food_safety_risk(
            temperature=12, storage_days=None, ph=None,
            cold_chain_broken=True, hygiene_controlled=None,
            pasteurized=None,
        )
        self.assertIsNone(result["risk_score"])
        self.assertEqual(result["analysis_status"], "Données incomplètes")
        self.assertGreater(result["raw_score"], 0)
        self.assertIn("données", result["signal_summary"])

    def test_invalid_boolean_is_rejected(self):
        result = assess_dairy_food_safety_risk(
            temperature=4, storage_days=2, ph=6.6,
            cold_chain_broken="Non", hygiene_controlled=True,
            pasteurized=True,
        )
        self.assertEqual(result["status"], "ERROR")

    def test_nan_is_rejected(self):
        result = assess_dairy_food_safety_risk(
            temperature=float("nan"), storage_days=2, ph=6.6,
            cold_chain_broken=False, hygiene_controlled=True,
            pasteurized=True,
        )
        self.assertEqual(result["status"], "ERROR")

    def test_thresholds_are_ordered(self):
        self.assertLess(MODERATE_THRESHOLD_PERCENT, HIGH_THRESHOLD_PERCENT)


if __name__ == "__main__":
    unittest.main(verbosity=2)
