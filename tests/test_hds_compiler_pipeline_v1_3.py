from __future__ import annotations

import unittest

from minidora.hds_adapter import HDS独立コンパイル
from minidora.hds_compiler_v1 import 公開HDSコンパイラ
from minidora.計算実行境界 import 計算実行境界


class HDSCompilerPipelineV13試験(unittest.TestCase):
    def setUp(self) -> None:
        self.compiler = 公開HDSコンパイラ()

    def test_v1_2意味監査Architectureを維持しPipelineだけv1_3へ進める(self) -> None:
        self.assertEqual(self.compiler.Architecture版, "v1.2")
        self.assertEqual(self.compiler.Pipeline版, "v1.3")
        self.assertEqual(self.compiler.基底言語, "ja")

    def test_意味コンパイル正本はPと計算初期状態を内包しない(self) -> None:
        ir = self.compiler.意味コンパイル("2+3")
        self.assertIsNone(ir.手順)
        self.assertEqual(ir.初期状態, {})
        self.assertEqual(ir.種別, "算術")
        self.assertIn("計算P非内包", ir.実行核.検証)
        self.assertEqual(ir.閉包状態, "CLOSED_FOR_SEMANTIC_TRANSFER")

    def test_コンパイル束は意味IRとPを別フィールドで保持する(self) -> None:
        bundle = self.compiler.コンパイル束("2+3")
        self.assertIsNone(bundle.意味IR.手順)
        self.assertTrue(bundle.計算計画.手順.命令列)
        self.assertEqual(bundle.計算計画.種別, "算術")
        self.assertEqual(bundle.計算計画.初期状態, {"入力0": 2, "入力1": 3})

    def test_形成済み束の計算降下は自然言語を再解析しない(self) -> None:
        bundle = self.compiler.コンパイル束("2+3")

        class _再解析禁止:
            def 計画(self, 問合せ):
                raise AssertionError("計算降下で自然言語を再解析した")

        self.compiler._計算計画器 = _再解析禁止()
        lowered = self.compiler.計算降下(bundle)
        result = 計算実行境界().実行(lowered.計算IR, lowered.初期状態)
        self.assertEqual(result.出力, 5)
        self.assertIn("自然言語再解析なし", lowered.計算IR.検証)

    def test_計算コンパイルは意味IRを汚さずComputeIRを形成する(self) -> None:
        result = self.compiler.計算コンパイル("10-4")
        self.assertIsNone(result.意味IR.手順)
        self.assertEqual(result.意味IR.初期状態, {})
        self.assertEqual(result.種別, "算術")
        executed = 計算実行境界().実行(result.計算IR, result.初期状態)
        self.assertEqual(executed.出力, 6)

    def test_Legacyコンパイルだけが最外周でPを再付与する(self) -> None:
        semantic = self.compiler.意味コンパイル("2+3")
        legacy = self.compiler.コンパイル("2+3")
        self.assertIsNone(semantic.手順)
        self.assertIsNotNone(legacy.手順)
        self.assertEqual(legacy.初期状態, {"入力0": 2, "入力1": 3})
        self.assertTrue(legacy.実行可能)
        self.assertIn("COMPATIBILITY_BRIDGE", legacy.実行核.境界)
        self.assertEqual(semantic.座標, legacy.座標)
        self.assertEqual(semantic.関係, legacy.関係)
        self.assertEqual(semantic.残差, legacy.残差)

    def test_詳細コンパイルと選択問題IRは意味正本なのでPを持たない(self) -> None:
        detailed = self.compiler.詳細コンパイル("A causes B")
        choice = self.compiler.問題IR("Which is correct?", ("A", "B", "C"))
        self.assertIsNone(detailed.IR.手順)
        self.assertEqual(detailed.IR.初期状態, {})
        self.assertIsNone(choice.手順)
        self.assertEqual(choice.初期状態, {})
        self.assertTrue(choice.参照必須)

    def test_参照問題の意味IRはPなしでも参照必要性を保持する(self) -> None:
        ir = self.compiler.意味コンパイル("東京の人口は？")
        self.assertIsNone(ir.手順)
        self.assertTrue(ir.参照必須)
        self.assertEqual(ir.種別, "参照")

    def test_独立Dataコンパイルは意味入口を優先しPを混入しない(self) -> None:
        ir = HDS独立コンパイル(self.compiler, "A inhibits B")
        self.assertIsNone(ir.手順)
        self.assertEqual(ir.初期状態, {})
        self.assertTrue(any(rel.種別 == "阻害" for rel in ir.関係))


if __name__ == "__main__":
    unittest.main()
