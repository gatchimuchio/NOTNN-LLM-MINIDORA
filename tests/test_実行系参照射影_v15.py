from __future__ import annotations

import unittest
from unittest.mock import patch

from minidora import 公開HDSコンパイラ
from minidora.HDS参照 import HDS参照予算
from minidora.実行系 import ミニドラ, 要求


class _空R:
    名称 = "empty-r"
    並列安全 = True

    def 検索(self, 問合せ: str, 上限: int = 8):
        return ()


class 実行系参照射影V15試験(unittest.TestCase):
    def test_完全IRで予算を決め構文化器観測要求をRへ渡す(self) -> None:
        構文化器 = 公開HDSコンパイラ()
        実行系 = ミニドラ(参照供給器_=_空R(), HDSコンパイラ_=構文化器)
        予算 = HDS参照予算("max", 16, 4, 4)

        with (
            patch("minidora.実行系.HDS参照予算選択", return_value=予算) as choose_予算,
            patch("minidora.実行系.HDS参照検索", return_value=()) as search,
        ):
            実行系.実行(
                要求("Which molecule is least likely to inhibit Enzyme X?")
            )

        self.assertEqual(choose_予算.call_count, 1)
        full_ir = choose_予算.call_args.args[0]
        self.assertIn("least likely", str(full_ir.原文).casefold())
        self.assertTrue(any(str(c.種別).startswith("制御.") for c in full_ir.座標))

        self.assertEqual(search.call_count, 1)
        query_ir = search.call_args.args[1]
        self.assertEqual(query_ir, full_ir)

        kwargs = search.call_args.kwargs
        self.assertEqual(kwargs["上限"], 16)
        self.assertEqual(kwargs["一問合せ上限"], 4)
        self.assertEqual(kwargs["最大問合せ並列"], 4)
        requests = tuple(kwargs["観測要求"])
        self.assertTrue(requests)
        surfaces = tuple(str(item.外部検索表層).casefold() for item in requests)
        self.assertFalse(any("least likely" in surface for surface in surfaces))
        self.assertFalse(any("which molecule" in surface for surface in surfaces))


if __name__ == "__main__":
    unittest.main()
