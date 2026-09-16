from __future__ import annotations

from pathlib import Path
import unittest

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from 評価契約 import (  # noqa: E402
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
        "Wikipedia言語群": ["en"],
        "統制AB": True,
    }


class 外部評価契約Test(unittest.TestCase):
    def test_実参照GPQAが正本で固定参照は禁止(self) -> None:
        契約 = GPQA実参照E2E契約(canonical_protocol())
        self.assertEqual(契約["契約形式"], 契約形式)
        self.assertEqual(契約["外部評価識別子"], GPQA実参照E2E識別子)
        self.assertEqual(契約["評価種別"], "GENERIC_E2E_CANONICAL")
        self.assertEqual(契約["参照方式"], "LIVE_ONLY")
        self.assertFalse(契約["固定参照資料許可"])
        self.assertTrue(契約["正本全数実行"])
        self.assertTrue(契約["スナップショット得点時系列保存許可"])
        self.assertFalse(契約["実行間コード差直接比較"])

    def test_正本手順はMINIDORA30条件を受理する(self) -> None:
        self.assertEqual(GPQA正本手順を検証(canonical_protocol()), ())

    def test_GPQA部分実行は正本として拒否する(self) -> None:
        protocol = canonical_protocol()
        protocol["選択番号群"] = list(range(24))
        errors = GPQA正本手順を検証(protocol)
        self.assertTrue(errors)
        with self.assertRaises(ValueError):
            GPQA実参照E2E契約(protocol)

    def test_OpenAlex条件変更を拒否する(self) -> None:
        protocol = canonical_protocol()
        protocol["OpenAlex有効"] = True
        self.assertTrue(GPQA正本手順を検証(protocol))

    def test_資料集合ハッシュ変更を拒否する(self) -> None:
        protocol = canonical_protocol()
        protocol["資料集合CSV_SHA256"] = "different"
        self.assertTrue(GPQA正本手順を検証(protocol))

    def test_実参照GPQAは実行間コード差のみではない(self) -> None:
        left = {"評価契約": GPQA実参照E2E契約(canonical_protocol())}
        right = {"評価契約": GPQA実参照E2E契約(canonical_protocol())}
        allowed, reason = 直接比較判定(left, right)
        self.assertFalse(allowed)
        self.assertIn("LIVE", reason)


if __name__ == "__main__":
    unittest.main()
