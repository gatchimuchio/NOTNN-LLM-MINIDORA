from __future__ import annotations

from pathlib import Path
import unittest

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from benchmark_contract import (  # noqa: E402
    CONTRACT_SCHEMA,
    GPQA_CANONICAL_DATASET_CSV_SHA256,
    GPQA_E2E_LIVE_ID,
    direct_comparison_verdict,
    gpqa_e2e_live_contract,
    validate_gpqa_canonical_protocol,
)


def canonical_protocol() -> dict:
    return {
        "dataset_csv_sha256": GPQA_CANONICAL_DATASET_CSV_SHA256,
        "full_benchmark_total": 198,
        "selected_indices": list(range(198)),
        "choice_shuffle_seed": 0,
        "openalex_enabled": False,
        "wikipedia_languages": ["en"],
        "controlled_ab": True,
    }


class BenchmarkContractTest(unittest.TestCase):
    def test_live_gpqa_is_canonical_and_fixed_reference_is_forbidden(self) -> None:
        contract = gpqa_e2e_live_contract(canonical_protocol())
        self.assertEqual(contract["schema"], CONTRACT_SCHEMA)
        self.assertEqual(contract["benchmark_id"], GPQA_E2E_LIVE_ID)
        self.assertEqual(contract["evaluation_class"], "GENERIC_E2E_CANONICAL")
        self.assertEqual(contract["retrieval_mode"], "LIVE_ONLY")
        self.assertFalse(contract["fixed_reference_data_allowed"])
        self.assertTrue(contract["canonical_full_run"])
        self.assertTrue(contract["snapshot_score_chronology_allowed"])
        self.assertFalse(contract["cross_run_code_delta_direct"])

    def test_canonical_protocol_accepts_minidora30_conditions(self) -> None:
        self.assertEqual(validate_gpqa_canonical_protocol(canonical_protocol()), ())

    def test_partial_gpqa_is_rejected_as_canonical(self) -> None:
        protocol = canonical_protocol()
        protocol["selected_indices"] = list(range(24))
        errors = validate_gpqa_canonical_protocol(protocol)
        self.assertTrue(errors)
        with self.assertRaises(ValueError):
            gpqa_e2e_live_contract(protocol)

    def test_openalex_condition_change_is_rejected(self) -> None:
        protocol = canonical_protocol()
        protocol["openalex_enabled"] = True
        self.assertTrue(validate_gpqa_canonical_protocol(protocol))

    def test_dataset_hash_change_is_rejected(self) -> None:
        protocol = canonical_protocol()
        protocol["dataset_csv_sha256"] = "different"
        self.assertTrue(validate_gpqa_canonical_protocol(protocol))

    def test_live_gpqa_is_not_cross_run_code_only_delta(self) -> None:
        left = {"benchmark_contract": gpqa_e2e_live_contract(canonical_protocol())}
        right = {"benchmark_contract": gpqa_e2e_live_contract(canonical_protocol())}
        allowed, reason = direct_comparison_verdict(left, right)
        self.assertFalse(allowed)
        self.assertIn("LIVE", reason)


if __name__ == "__main__":
    unittest.main()
