from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class 外部評価契約固定試験(unittest.TestCase):
    def test_必須評価契約資産が存在する(self) -> None:
        required = (
            "tools/評価契約.py",
            "tools/正本評価.py",
            "tools/中核正本評価.py",
            "評価/評価契約_v3.md",
            "評価/GPQA_Diamond_MINIDORA_中核_正本_2026-09-27.md",
            "評価/GPQA_Diamond_MINIDORA_中核_正本_2026-09-27.json",
            "開発正本履歴.md",
            "現行正本.md",
        )
        for path in required:
            self.assertTrue((ROOT / path).is_file(), path)

    def test_現行正本は40中核を現行値とする(self) -> None:
        text = (ROOT / "現行正本.md").read_text(encoding="utf-8")
        self.assertIn("現行性能正本: 現行MINIDORA中核", text)
        self.assertIn("40 / 198 (20.20%)", text)
        self.assertIn("旧39 / MINIDORA30 / MINIDORA80: 履歴セーブポイント", text)
        self.assertIn("GPQA正本評価: LIVE_ONLY", text)
        self.assertIn("GPQA固定参照資料: 禁止", text)
        self.assertIn("評価/評価契約_v3.md", text)

    def test_現行中核正本目録は機械固定される(self) -> None:
        path = ROOT / "評価/GPQA_Diamond_MINIDORA_中核_正本_2026-09-27.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["正本名"], "現行MINIDORA中核")
        self.assertTrue(payload["正本"])
        self.assertEqual(payload["結果"]["正答"], 40)
        self.assertEqual(payload["結果"]["全数"], 198)
        self.assertEqual(payload["結果"]["回答"], 144)
        self.assertEqual(payload["実行内状態遷移"]["改善"], 4)
        self.assertEqual(payload["実行内状態遷移"]["退行"], 0)
        self.assertEqual(payload["候補被覆"]["最終全候補被覆問題数"], 198)
        self.assertEqual(payload["評価条件"]["参照方式"], "LIVE_ONLY")
        self.assertFalse(payload["評価条件"]["固定参照資料許可"])
        self.assertEqual(
            payload["評価条件"]["資料集合CSV_SHA256"],
            "41d1213cd7a4998605a26c2798500652572007161b3a92817ba46b35befcd305",
        )
        self.assertEqual(payload["由来"]["workflow_run_id"], 36250119488)
        self.assertEqual(payload["由来"]["aggregate_artifact_id"], 10909137346)

    def test_AGENTSは評価固有情報の実装混入を禁止する(self) -> None:
        text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("評価用正解・問題固有情報の実装混入", text)
        self.assertIn("固定入力専用処理の一般能力化", text)

    def test_正本評価入口は現行中核実測器へ直結する(self) -> None:
        text = (ROOT / "tools/正本評価.py").read_text(encoding="utf-8")
        self.assertIn("from 中核正本評価 import GPQA中核正本を実行", text)
        self.assertIn('sub.add_parser("gpqa-e2e"', text)
        self.assertNotIn('"--controlled-ab"', text)
        self.assertNotIn("形式評価", text)

    def test_現行中核実測器は一問一問題束と中核入口を使う(self) -> None:
        text = (ROOT / "tools/中核正本評価.py").read_text(encoding="utf-8")
        self.assertIn("構文化器.問題コンパイル束(question, choices)", text)
        self.assertIn("HDS駆動コア", text)
        self.assertIn("カーネル正本=kernel", text)
        self.assertIn("EuropePMC有効=True", text)
        self.assertIn("Crossref有効=True", text)

    def test_ツール説明は実参照正本評価入口を宣言する(self) -> None:
        text = (ROOT / "tools/README.md").read_text(encoding="utf-8")
        self.assertIn("正本GPQA入口", text)
        self.assertIn("評価契約 v3", text)
        self.assertIn("LIVE_ONLY", text)
        self.assertIn("固定参照資料を正本性能評価へ使用しない", text)
        self.assertIn("python tools/正本評価.py gpqa-e2e", text)

    def test_旧39正本個票は履歴へ退避する(self) -> None:
        self.assertFalse((ROOT / "評価/GPQA_Diamond_MINIDORA_中核_正本_2026-09-24.md").exists())
        self.assertFalse((ROOT / "評価/GPQA_Diamond_MINIDORA_中核_正本_2026-09-24.json").exists())
        history = (ROOT / "開発正本履歴.md").read_text(encoding="utf-8")
        self.assertIn("8843695c2d4e498009340cadd68814d6cebee819", history)
        self.assertIn("39/198", history)
        self.assertIn("4e505c3ec2c78e26b4174c71284bd22fa1b7faf9", history)
        self.assertIn("40/198", history)

    def test_GPQA固定再生実行経路は廃止済み(self) -> None:
        for path in ("tools/GPQA再生記録.py", "tools/GPQA科学専門能力再生.py"):
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
