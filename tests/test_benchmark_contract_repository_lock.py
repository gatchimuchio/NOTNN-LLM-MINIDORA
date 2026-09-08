from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class BenchmarkContractRepositoryLockTest(unittest.TestCase):
    def test_required_benchmark_contract_assets_exist(self) -> None:
        required = (
            "tools/benchmark_contract.py",
            "tools/benchmark_strict.py",
            "評価/BENCHMARK_CONTRACT_v1.md",
            "CURRENT_CANONICAL.md",
        )
        for path in required:
            self.assertTrue((ROOT / path).is_file(), path)

    def test_canonical_core37_is_labeled_fixed_replay(self) -> None:
        text = (ROOT / "CURRENT_CANONICAL.md").read_text(encoding="utf-8")
        self.assertIn("GPQA-FIXED-REPLAY / C2 / Core+HDS / 37/198", text)
        self.assertIn("汎用E2E性能として扱わない", text)
        self.assertIn("BENCHMARK_CONTRACT_v1.md", text)

    def test_tools_readme_declares_strict_runner_as_canonical(self) -> None:
        text = (ROOT / "tools/README.md").read_text(encoding="utf-8")
        self.assertIn("benchmark_strict.py", text)
        self.assertIn("正本Benchmark入口", text)
        self.assertIn("GPQA-E2E-LIVE", text)
        self.assertIn("GPQA-FIXED-REPLAY", text)


if __name__ == "__main__":
    unittest.main()
