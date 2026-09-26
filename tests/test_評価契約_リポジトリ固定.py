from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class 外部評価契約RepositoryLockTest(unittest.TestCase):
    def test_必須評価契約資産が存在する(self) -> None:
        required = (
            "tools/評価契約.py",
            "tools/正本評価.py",
            "評価/評価契約_v3.md",
            "評価/GPQA_Diamond_MINIDORA_中核_正本_2026-09-24.md",
            "評価/GPQA_Diamond_MINIDORA_中核_正本_2026-09-24.json",
            "評価/GPQA_Diamond_MINIDORA30_E2E_正本_2026-09-09.md",
            "評価/GPQA_Diamond_MINIDORA30_E2E_正本_2026-09-09.json",
            "評価/GPQA_Diamond_MINIDORA80_Module_E2E_正本_2026-09-09.md",
            "評価/GPQA_Diamond_MINIDORA80_Module_E2E_正本_2026-09-09.json",
            "開発正本履歴.md",
            "現行正本.md",
        )
        for path in required:
            self.assertTrue((ROOT / path).is_file(), path)

    def test_現行正本は39中核を現行値とし30と80を履歴へ分離する(self) -> None:
        text = (ROOT / "現行正本.md").read_text(encoding="utf-8")
        self.assertIn("現行性能正本: 現行MINIDORA中核", text)
        self.assertIn("39 / 198 (19.70%)", text)
        self.assertIn("旧MINIDORA30 / MINIDORA80: 履歴セーブポイント", text)
        self.assertIn("GPQA正本評価: LIVE_ONLY", text)
        self.assertIn("GPQA固定参照資料: 禁止", text)
        self.assertIn("評価/評価契約_v3.md", text)

    def test_現行中核正本目録は機械固定される(self) -> None:
        path = ROOT / "評価/GPQA_Diamond_MINIDORA_中核_正本_2026-09-24.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["正本名"], "現行MINIDORA中核")
        self.assertTrue(payload["正本"])
        self.assertEqual(payload["結果"]["正答"], 39)
        self.assertEqual(payload["結果"]["全数"], 198)
        self.assertEqual(payload["結果"]["回答"], 149)
        self.assertEqual(payload["実行内状態遷移"]["退行"], 0)
        self.assertEqual(payload["評価条件"]["参照方式"], "LIVE_ONLY")
        self.assertFalse(payload["評価条件"]["固定参照資料許可"])
        self.assertEqual(
            payload["評価条件"]["資料集合CSV_SHA256"],
            "41d1213cd7a4998605a26c2798500652572007161b3a92817ba46b35befcd305",
        )

    def test_AGENTSは評価固有情報の実装混入を禁止する(self) -> None:
        text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("評価用正解・問題固有情報の実装混入", text)
        self.assertIn("固定入力専用処理の一般能力化", text)

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
        self.assertIn("固定参照資料を正本性能評価へ使用しない", text)
        self.assertNotIn("benchmark_strict.py gpqa-fixed-replay", text)

    def test_MINIDORA30目録は履歴セーブポイントとして機械固定される(self) -> None:
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

    def test_MINIDORA80目録は履歴セーブポイントとして機械固定される(self) -> None:
        path = ROOT / "評価/GPQA_Diamond_MINIDORA80_Module_E2E_正本_2026-09-09.json"
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
            self.assertIn("GPQA_FIXED_参照_FORBIDDEN", text)
            self.assertNotIn("HDS選択肢再生収録(", text)
            self.assertNotIn("科学専門能力を通常MINIDORAへ接続(", text)

        workflow = (ROOT / ".github/workflows/GPQA科学専門能力_再生.yml").read_text(encoding="utf-8")
        self.assertIn("RETIRED", workflow)
        self.assertIn("GPQA_FIXED_参照_FORBIDDEN", workflow)
        self.assertNotIn("python tools/GPQA科学専門能力再生.py", workflow)
        self.assertNotIn("actions/upload-artifact", workflow)


if __name__ == "__main__":
    unittest.main()
