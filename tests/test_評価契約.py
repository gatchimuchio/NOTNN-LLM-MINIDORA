from __future__ import annotations

from pathlib import Path
import unittest
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from 評価契約 import (
    契約形式,
    GPQA正本資料集合CSV_SHA256,
    GPQA実参照E2E識別子,
    直接比較判定,
    GPQA実参照E2E契約,
    GPQA正本手順を検証,
)


def canonical_protocol() -> dict:
    return {
        "資料集合CSV_SHA256": GPQA正本資料集合CSV_SHA256,
        "全問題数": 198,
        "選択番号群": list(range(198)),
        "選択肢シャッフル種": 0,
        "OpenAlex有効": False,
        "EuropePMC有効": True,
        "Crossref有効": True,
        "Wikipedia言語群": ["en"],
        "参照方式": "LIVE_ONLY",
        "固定参照資料許可": False,
        "中核入口": "HDS駆動コア.選択実行",
        "問題束一問一形成": True,
    }


class 外部評価契約試験(unittest.TestCase):
    def test_実参照GPQAが現行中核正本で固定参照は禁止(self) -> None:
        契約 = GPQA実参照E2E契約(canonical_protocol())
        self.assertEqual(契約["契約形式"], 契約形式)
        self.assertEqual(契約["外部評価識別子"], GPQA実参照E2E識別子)
        self.assertEqual(契約["評価種別"], "CURRENT_INTEGRATED_KERNEL_CANONICAL")
        self.assertEqual(契約["参照方式"], "LIVE_ONLY")
        self.assertFalse(契約["固定参照資料許可"])
        self.assertTrue(契約["正本全数実行"])
        self.assertTrue(契約["同一実行内状態遷移記録許可"])
        self.assertFalse(契約["実行間コード差直接比較"])

    def test_現行中核正本条件を受理する(self) -> None:
        self.assertEqual(GPQA正本手順を検証(canonical_protocol()), ())

    def test_GPQA部分実行は正本として拒否する(self) -> None:
        protocol = canonical_protocol()
        protocol["選択番号群"] = list(range(24))
        errors = GPQA正本手順を検証(protocol)
        self.assertTrue(errors)
        with self.assertRaises(ValueError):
            GPQA実参照E2E契約(protocol)

    def test_標準参照条件変更を拒否する(self) -> None:
        for key, value in (("OpenAlex有効", True), ("EuropePMC有効", False), ("Crossref有効", False)):
            with self.subTest(key=key):
                protocol = canonical_protocol()
                protocol[key] = value
                self.assertTrue(GPQA正本手順を検証(protocol))

    def test_資料集合ハッシュ変更を拒否する(self) -> None:
        protocol = canonical_protocol()
        protocol["資料集合CSV_SHA256"] = "different"
        self.assertTrue(GPQA正本手順を検証(protocol))

    def test_固定参照と別中核入口を拒否する(self) -> None:
        protocol = canonical_protocol()
        protocol["固定参照資料許可"] = True
        self.assertTrue(GPQA正本手順を検証(protocol))
        protocol = canonical_protocol()
        protocol["中核入口"] = "旧入口"
        self.assertTrue(GPQA正本手順を検証(protocol))

    def test_実参照GPQAは実行間コード差のみではない(self) -> None:
        left = {"評価契約": GPQA実参照E2E契約(canonical_protocol())}
        right = {"評価契約": GPQA実参照E2E契約(canonical_protocol())}
        allowed, reason = 直接比較判定(left, right)
        self.assertFalse(allowed)
        self.assertIn("LIVE", reason)


if __name__ == "__main__":
    unittest.main()
