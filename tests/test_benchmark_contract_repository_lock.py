from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class BenchmarkContractRepositoryLockTest(unittest.TestCase):
    def test_required_benchmark_contract_assets_exist(self) -> None:
        required = (
            "tools/benchmark_contract.py",
            "tools/benchmark_strict.py",
            "評価/BENCHMARK_CONTRACT_v2.md",
            "評価/GPQA_Diamond_MINIDORA30_E2E_正本_2026-09-09.md",
            "評価/GPQA_Diamond_MINIDORA30_E2E_正本_2026-09-09.json",
            "docs/SAVEPOINT_2026-09-09_MINIDORA30.md",
            "CURRENT_CANONICAL.md",
        )
        for path in required:
            self.assertTrue((ROOT / path).is_file(), path)

    def test_canonical_is_minidora30_live_only(self) -> None:
        text = (ROOT / "CURRENT_CANONICAL.md").read_text(encoding="utf-8")
        self.assertIn("Canonical baseline: MINIDORA30", text)
        self.assertIn("30 / 198 (15.15%)", text)
        self.assertIn("GPQA-E2E-LIVE only", text)
        self.assertIn("固定参照Dataを禁止", text)
        self.assertIn("BENCHMARK_CONTRACT_v2.md", text)

    def test_agents_enforces_gpqa_no_fixed_reference_policy(self) -> None:
        text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("GPQA正本では固定参照Dataを禁止", text)
        self.assertIn("reference = LIVE_ONLY", text)
        self.assertIn("MINIDORA30 / 30/198", text)

    def test_strict_runner_has_no_gpqa_fixed_replay_entry(self) -> None:
        text = (ROOT / "tools/benchmark_strict.py").read_text(encoding="utf-8")
        self.assertIn('sub.add_parser("gpqa-e2e"', text)
        self.assertNotIn("gpqa-fixed-replay", text)
        self.assertIn('"--no-openalex"', text)
        self.assertIn('"--controlled-ab"', text)

    def test_tools_readme_declares_live_only_canonical_runner(self) -> None:
        text = (ROOT / "tools/README.md").read_text(encoding="utf-8")
        self.assertIn("正本GPQA入口", text)
        self.assertIn("LIVE_ONLY", text)
        self.assertIn("固定参照Dataを正本性能評価へ使用しない", text)
        self.assertNotIn("benchmark_strict.py gpqa-fixed-replay", text)

    def test_minidora30_manifest_is_machine_locked(self) -> None:
        path = ROOT / "評価/GPQA_Diamond_MINIDORA30_E2E_正本_2026-09-09.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["canonical_name"], "MINIDORA30")
        self.assertTrue(payload["canonical"])
        self.assertEqual(payload["result"]["current"]["correct"], 30)
        self.assertEqual(payload["result"]["current"]["total"], 198)
        self.assertEqual(payload["protocol"]["retrieval_mode"], "LIVE_ONLY")
        self.assertFalse(payload["protocol"]["fixed_reference_data_allowed"])
        self.assertEqual(
            payload["protocol"]["dataset_csv_sha256"],
            "41d1213cd7a4998605a26c2798500652572007161b3a92817ba46b35befcd305",
        )
        self.assertEqual(payload["provenance"]["workflow_run_id"], 34281226412)


if __name__ == "__main__":
    unittest.main()
