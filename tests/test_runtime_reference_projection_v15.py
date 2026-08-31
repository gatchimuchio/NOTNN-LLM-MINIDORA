from __future__ import annotations

import unittest
from unittest.mock import patch

from minidora import 公開HDSコンパイラ
from minidora.hds_reference import HDS参照予算
from minidora.runtime import ミニドラ, 要求


class _空R:
    名称 = "empty-r"
    並列安全 = True

    def 検索(self, 問合せ: str, 上限: int = 8):
        return ()


class Runtime参照射影V15試験(unittest.TestCase):
    def test_完全IRで予算を決めR射影IRでqueryを作る(self) -> None:
        compiler = 公開HDSコンパイラ()
        runtime = ミニドラ(参照供給器_=_空R(), HDSコンパイラ_=compiler)
        budget = HDS参照予算("max", 16, 4, 4)

        # v0.5の通常実行責任はnative runtimeが所有する。
        # 旧runtime_v03ではなく現行責任moduleをpatchする。
        with (
            patch("minidora.runtime.HDS参照予算選択", return_value=budget) as choose_budget,
            patch("minidora.runtime.HDS参照検索", return_value=()) as search,
        ):
            runtime.実行(
                要求("Which molecule is least likely to inhibit Enzyme X?")
            )

        self.assertEqual(choose_budget.call_count, 1)
        full_ir = choose_budget.call_args.args[0]
        self.assertIn("least likely", str(full_ir.原文).casefold())
        self.assertTrue(any(str(c.種別).startswith("制御.") for c in full_ir.座標))

        self.assertEqual(search.call_count, 1)
        query_ir = search.call_args.args[1]
        self.assertNotIn("least likely", str(query_ir.原文).casefold())
        self.assertNotIn("which", str(query_ir.原文).casefold())
        self.assertFalse(any(str(c.種別).startswith("制御.") for c in query_ir.座標))

        kwargs = search.call_args.kwargs
        self.assertEqual(kwargs["上限"], 16)
        self.assertEqual(kwargs["一問合せ上限"], 4)
        self.assertEqual(kwargs["最大問合せ並列"], 4)


if __name__ == "__main__":
    unittest.main()
