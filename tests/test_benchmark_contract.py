from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from benchmark_contract import (  # noqa: E402
    CONTRACT_SCHEMA,
    GPQA_E2E_LIVE_ID,
    GPQA_FIXED_REPLAY_ID,
    direct_comparison_verdict,
    fixed_replay_contract,
    gpqa_e2e_live_contract,
)


class BenchmarkContractTest(unittest.TestCase):
    def test_live_gpqa_is_not_cross_run_code_delta(self) -> None:
        protocol = {
            "dataset_csv_sha256": "dataset",
            "selected_indices": list(range(198)),
            "choice_shuffle_seed": 0,
            "openalex_enabled": False,
            "wikipedia_languages": ["en"],
            "compiler": "compiler",
            "runtime": "runtime",
        }
        left = {"benchmark_contract": gpqa_e2e_live_contract(protocol)}
        right = {"benchmark_contract": gpqa_e2e_live_contract(protocol)}
        allowed, _ = direct_comparison_verdict(left, right)
        self.assertFalse(allowed)
        self.assertEqual(left["benchmark_contract"]["schema"], CONTRACT_SCHEMA)
        self.assertEqual(left["benchmark_contract"]["benchmark_id"], GPQA_E2E_LIVE_ID)

    def test_same_fixed_replay_is_directly_comparable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp) / "replay.jsonl"
            bundle.write_text(json.dumps({"id": 1}, ensure_ascii=False) + "\n", encoding="utf-8")
            left = {"benchmark_contract": fixed_replay_contract(bundle)}
            right = {"benchmark_contract": fixed_replay_contract(bundle)}
            allowed, _ = direct_comparison_verdict(left, right)
            self.assertTrue(allowed)
            self.assertEqual(left["benchmark_contract"]["benchmark_id"], GPQA_FIXED_REPLAY_ID)

    def test_different_fixed_replay_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "first.jsonl"
            second = Path(tmp) / "second.jsonl"
            first.write_text("A\n", encoding="utf-8")
            second.write_text("B\n", encoding="utf-8")
            left = {"benchmark_contract": fixed_replay_contract(first)}
            right = {"benchmark_contract": fixed_replay_contract(second)}
            allowed, _ = direct_comparison_verdict(left, right)
            self.assertFalse(allowed)


if __name__ == "__main__":
    unittest.main()
