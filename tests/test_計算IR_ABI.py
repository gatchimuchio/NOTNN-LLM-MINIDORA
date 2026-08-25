from __future__ import annotations

import unittest

from minidora.HDS計算降下 import HDS計算降下
from minidora.hds_ir import HDSIR, HDS実行核, HDS座標, 値状態
from minidora.命令 import 手順, 作用, 命令
from minidora.命令計算降下 import 命令計算降下
from minidora.計算中間表現 import (
    計算中間表現,
    計算作用,
    計算値,
    計算値種別,
    計算命令,
)
from minidora.計算実行器 import 計算実行器
from minidora.計算実行境界 import 計算実行境界


class 計算IR_ABI試験(unittest.TestCase):
    def test_Pの状態参照を型付き計算値へ降下する(self) -> None:
        plan = 手順(
            "加算計画",
            (
                命令("加算", 作用.加算, 引数=("$a", 2), 更新先="結果"),
            ),
        )
        ir = 命令計算降下(plan)
        first = ir.命令列[0].入力[0]
        self.assertEqual(first.種別, 計算値種別.状態値)
        self.assertEqual(first.内容, "a")
        self.assertNotEqual(first.内容, "$a")

    def test_ABIは計算中間表現だけで決定論的に実行する(self) -> None:
        ir = 計算中間表現(
            "直接加算",
            (
                計算命令(
                    "c1",
                    "加算",
                    計算作用.加算,
                    (計算値.即値(2), 計算値.即値(3)),
                    出力住所="結果",
                ),
            ),
        )
        abi = 計算実行境界()
        first = abi.実行(ir)
        second = abi.実行(ir)
        self.assertEqual(first.出力, 5)
        self.assertEqual(first, second)

    def test_計算実行器の旧P入口も内部では計算IRを通る(self) -> None:
        plan = 手順(
            "互換加算",
            (
                命令("設定", 作用.設定, 引数=(7,), 更新先="a"),
                命令("加算", 作用.加算, 引数=("$a", 5), 更新先="結果"),
            ),
        )
        executor = 計算実行器()
        ir = executor.計算化(plan)
        typed = executor.計算実行(ir)
        legacy = executor.実行(plan)
        self.assertEqual(typed.出力, 12)
        self.assertEqual(legacy.状態["結果"], 12)
        self.assertEqual(legacy.履歴[-1]["作用"], "加算")

    def test_交換は値参照ではなく状態住所を取る(self) -> None:
        plan = 手順(
            "交換",
            (命令("交換", 作用.交換, 引数=("a", "b")),),
        )
        ir = 命令計算降下(plan)
        self.assertTrue(all(item.種別 == 計算値種別.状態住所 for item in ir.命令列[0].入力))
        result = 計算実行器().計算実行(ir, {"a": 1, "b": 2})
        self.assertEqual(result.状態["a"], 2)
        self.assertEqual(result.状態["b"], 1)

    def test_HDS降下は自然言語を再解析せず閉包済み構造だけを使う(self) -> None:
        plan = 手順(
            "HDS加算",
            (命令("加算", 作用.加算, 引数=("$a", "$b"), 更新先="結果"),),
            由来="HDS",
        )
        hds = HDSIR(
            原文="この文字列自体は計算意味として再解析してはならない",
            正規化文="この文字列自体は計算意味として再解析してはならない",
            認知世界ID="cw:test",
            座標=(
                HDS座標("a", "値", 2),
                HDS座標("b", "値", 3),
            ),
            関係=(),
            残差=(),
            意味作用履歴=(),
            実行核=HDS実行核(
                作用="加算",
                入力座標=("a", "b"),
                出力座標="結果",
                境界=("整数入力",),
                検証=("結果確認",),
            ),
            初期状態={"a": 2, "b": 3},
            種別="算術",
            手順=plan,
        )
        ir = HDS計算降下(hds)
        self.assertEqual(ir.由来, "HDS-IR:cw:test")
        self.assertEqual(ir.境界, ("整数入力",))
        self.assertEqual(ir.検証, ("結果確認",))
        self.assertIn("a", ir.由来参照)
        self.assertEqual(計算実行器().計算実行(ir, hds.初期状態).出力, 5)

    def test_未確定HDS入力は計算IRへ昇格しない(self) -> None:
        plan = 手順(
            "未確定",
            (命令("加算", 作用.加算, 引数=("$a", "$b"), 更新先="結果"),),
        )
        hds = HDSIR(
            原文="x",
            正規化文="x",
            認知世界ID="cw:open",
            座標=(
                HDS座標("a", "値", 2, 値状態.確定),
                HDS座標("b", "値", None, 値状態.未確定),
            ),
            関係=(),
            残差=(),
            意味作用履歴=(),
            実行核=HDS実行核(作用="加算", 入力座標=("a", "b")),
            手順=plan,
        )
        with self.assertRaisesRegex(ValueError, "降下できない"):
            HDS計算降下(hds)

    def test_交換以外で状態住所を値として使うとABIが拒否する(self) -> None:
        ir = 計算中間表現(
            "不正",
            (
                計算命令(
                    "bad",
                    "不正加算",
                    計算作用.加算,
                    (計算値.状態住所("a"), 計算値.即値(1)),
                    出力住所="結果",
                ),
            ),
        )
        with self.assertRaisesRegex(ValueError, "状態住所"):
            計算実行境界().実行(ir, {"a": 2})


if __name__ == "__main__":
    unittest.main()
