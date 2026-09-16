from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class 外部評価契約RepositoryLockTest(unittest.TestCase):
    def test_required_評価契約_assets_exist(self) -> None:
        required = (
            "tools/評価契約.py",
            "tools/正本評価.py",
            '評価/評価契約_v2.md',
            "評価/GPQA_Diamond_MINIDORA30_E2E_正本_2026-09-09.md",
            "評価/GPQA_Diamond_MINIDORA30_E2E_正本_2026-09-09.json",
            '評価/GPQA_Diamond_MINIDORA80_Module_E2E_正本_2026-09-09.md',
            '評価/GPQA_Diamond_MINIDORA80_Module_E2E_正本_2026-09-09.json',
            "docs/SAVEPOINT_2026-09-09_MINIDORA30.md",
            "docs/SAVEPOINT_2026-09-09_MINIDORA80.md",
            "現行正本.md",
        )
        for path in required:
            self.assertTrue((ROOT / path).is_file(), path)

    def test_正本はMINIDORA30模型核とMINIDORA80システムを分離する(self) -> None:
        text = (ROOT / "現行正本.md").read_text(encoding="utf-8")
        self.assertIn("模型核正本基準: MINIDORA30", text)
        self.assertIn("能力モジュール込みシステム正本: MINIDORA80", text)
        self.assertIn("30 / 198 (15.15%)", text)
        self.assertIn("80 / 198", text)
        self.assertIn("GPQA正本評価: LIVE_ONLY", text)
        self.assertIn("GPQA固定参照資料: 禁止", text)
        self.assertIn('固定参照資料を禁止', text)
        self.assertIn('評価契約_v2.md', text)

    def test_AGENTSはGPQA固定参照禁止を要求する(self) -> None:
        text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn('GPQA正本では固定参照資料を禁止', text)
        self.assertIn("reference = LIVE_ONLY", text)
        self.assertIn("MINIDORA30 / 30/198", text)

    def test_厳密評価入口にGPQA固定再生経路がない(self) -> None:
        text = (ROOT / "tools/正本評価.py").read_text(encoding="utf-8")
        self.assertIn('sub.add_parser("gpqa-e2e"', text)
        self.assertNotIn('gpqa-fixed-再生', text)
        self.assertIn('"--no-openalex"', text)
        self.assertIn('"--controlled-ab"', text)

    def test_ツール説明は実参照正本評価入口を宣言する(self) -> None:
        text = (ROOT / "tools/README.md").read_text(encoding="utf-8")
        self.assertIn("正本GPQA入口", text)
        self.assertIn("LIVE_ONLY", text)
        self.assertIn('固定参照資料を正本性能評価へ使用しない', text)
        self.assertNotIn("benchmark_strict.py gpqa-fixed-replay", text)

    def test_MINIDORA30目録は機械固定される(self) -> None:
        path = ROOT / "評価/GPQA_Diamond_MINIDORA30_E2E_正本_2026-09-09.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["canonical_name"], "MINIDORA30")
        self.assertTrue(payload["canonical"])
        self.assertEqual(payload["result"]["current"]["correct"], 30)
        self.assertEqual(payload["result"]["current"]["total"], 198)
        self.assertEqual(payload["protocol"]["参照方式"], "LIVE_ONLY")
        self.assertFalse(payload["protocol"]["固定参照資料許可"])
        self.assertEqual(
            payload["protocol"]["資料集合CSV_SHA256"],
            "41d1213cd7a4998605a26c2798500652572007161b3a92817ba46b35befcd305",
        )
        self.assertEqual(payload["provenance"]["workflow_run_id"], 34281226412)

    def test_MINIDORA80目録は機械固定される(self) -> None:
        path = ROOT / '評価/GPQA_Diamond_MINIDORA80_Module_E2E_正本_2026-09-09.json'
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["canonical_name"], "MINIDORA80")
        self.assertFalse(payload["固定参照資料許可"])
        self.assertEqual(payload["module_off"]["correct"], 29)
        self.assertEqual(payload["module_off"]["total"], 198)
        self.assertEqual(payload["module_on"]["correct"], 80)
        self.assertEqual(payload["module_on"]["total"], 198)
        self.assertEqual(payload["delta"]["correct"], 51)
        self.assertEqual(payload["delta"]["improved"], 51)
        self.assertEqual(payload["delta"]["regressed"], 0)
        self.assertEqual(payload["delta"]["fired"], 55)
        self.assertEqual(payload["delta"]["fired_correct"], 55)
        self.assertEqual(payload["execution_evidence"]["workflow_run_id"], 34301888230)
        self.assertEqual(payload["execution_evidence"]["aggregate_artifact_id"], 10085678050)
        self.assertEqual(
            payload["資料集合CSV_SHA256"],
            "41d1213cd7a4998605a26c2798500652572007161b3a92817ba46b35befcd305",
        )

    def test_GPQA固定再生実行経路は廃止済み(self) -> None:
        for path in (
            "tools/GPQA再生記録.py",
            "tools/GPQA科学専門能力再生.py",
        ):
            text = (ROOT / path).read_text(encoding="utf-8")
            self.assertIn('GPQA_FIXED_参照_FORBIDDEN', text)
            self.assertNotIn('HDS選択肢再生収録(', text)
            self.assertNotIn("科学専門能力を通常MINIDORAへ接続(", text)

        workflow = (ROOT / ".github/workflows/GPQA科学専門能力_再生.yml").read_text(encoding="utf-8")
        self.assertIn("RETIRED", workflow)
        self.assertIn('GPQA_FIXED_参照_FORBIDDEN', workflow)
        self.assertNotIn("python tools/GPQA科学専門能力再生.py", workflow)
        self.assertNotIn("actions/upload-artifact", workflow)


if __name__ == "__main__":
    unittest.main()
