from __future__ import annotations

import unittest

from minidora.hds_choice_runtime import HDS選択推論実行
from minidora.hds_compiler_v1 import 公開HDSコンパイラ
from minidora.hds_model_projection import HDSMINIDORA模型評価
from minidora.k3_functional import K3相当能力核
from minidora.参照 import 参照記録
from minidora.能力状態差循環 import (
    MINIDORA能力状態差模型核,
    標準能力模型核,
    能力作用構造,
    能力作用記録,
    能力状態差記録,
    能力後続利用記録,
)
from minidora.模型 import 成立候補, 言語状態


class 能力状態差循環V1試験(unittest.TestCase):
    def test_状態差がなければ再作用しない(self) -> None:
        core = 標準能力模型核()
        result = core.評価言語状態(
            言語状態("which"),
            (
                成立候補("A", 言語状態("alpha")),
                成立候補("B", 言語状態("beta")),
                成立候補("C", 言語状態("gamma")),
            ),
            参照状態=(言語状態("common", 識別子="r0"),),
        )
        self.assertEqual(result.統計.checkpoint再活性数, 0)
        self.assertEqual(result.統計.大域再照合数, 0)
        self.assertEqual(result.統計.候補横断更新数, 0)
        self.assertEqual(result.統計.再作用回数, 0)
        self.assertFalse(any(cp.段階.startswith("RECONCILE_") for cp in result.checkpoint))

    def test_状態差が次作用を開き新しい候補差を作る(self) -> None:
        core = 標準能力模型核()
        result = core.評価言語状態(
            言語状態("which"),
            (
                成立候補("A", 言語状態("alpha common x")),
                成立候補("B", 言語状態("beta common x")),
                成立候補("C", 言語状態("beta common y")),
            ),
            参照状態=(
                言語状態("alpha", 識別子="r1"),
                言語状態("beta", 識別子="r2"),
            ),
        )

        self.assertGreaterEqual(result.統計.checkpoint再活性数, 1)
        self.assertGreaterEqual(result.統計.大域再照合数, 1)
        self.assertGreaterEqual(result.統計.候補横断更新数, 1)
        self.assertGreaterEqual(result.統計.寄与状態再利用数, 1)
        self.assertTrue(any(cp.段階 == "RECONCILE_1" for cp in result.checkpoint))

        rows = {row.候補ID: row for row in result.候補差}
        self.assertTrue(
            any(
                item.関係名.startswith("候補共同再照合") and any("r2" in str(x) for x in item.根拠)
                for item in rows["B"].寄与
            )
        )
        # r1の同じ証拠を段階名だけ変えて再加点しない。
        a_r1 = sum(
            1
            for item in rows["A"].寄与
            if item.関係名.startswith(("候補共同参照", "候補共同再照合"))
            and any("r1" in str(x) for x in item.根拠)
        )
        self.assertEqual(a_r1, 1)

    def test_Compiler作用差分を能力系が消費する(self) -> None:
        compiler = 公開HDSコンパイラ()
        question = compiler.問題IR("最終状態はどれか？", ("S1", "S2"))
        candidates = {
            "A": compiler.意味コンパイル("S1"),
            "B": compiler.意味コンパイル("S2"),
        }
        detail = compiler.詳細コンパイル("S0からS1へ遷移し、S1からS2へ遷移する。")
        self.assertGreaterEqual(detail.作用差分構造.後続利用数, 1)

        core = MINIDORA能力状態差模型核((), 能力作用群=(), 最大再作用回数=0)
        result = HDSMINIDORA模型評価(
            question,
            candidates,
            (detail.IR,),
            模型核=core,
            参照識別子=("状態遷移資料",),
            作用差分構造群=(detail.作用差分構造,),
        )
        self.assertEqual(result.状態, "APPROVE")
        self.assertEqual(result.回答ラベル, "B")
        self.assertIn("HDS_ACTION_DELTA_ATTACHED", result.理由)
        self.assertIn("HDS_ACTION_DELTA_CONSUMED", result.理由)
        self.assertTrue(
            any(
                item.関係名.startswith("候補共同参照:状態差連結")
                for row in result.模型結果.候補差
                for item in row.寄与
            )
        )

    def test_正式実行経路が作用差分消費を実測値として返す(self) -> None:
        compiler = 公開HDSコンパイラ()
        question = compiler.問題IR("最終状態はどれか？", ("S1", "S2"))
        reference = 参照記録(
            "r-state-chain",
            "状態遷移",
            "S0からS1へ遷移し、S1からS2へ遷移する。",
            "fixture",
            "固定資料",
            1.0,
        )
        core = MINIDORA能力状態差模型核((), 能力作用群=(), 最大再作用回数=0)
        result = HDS選択推論実行(
            question,
            (reference,),
            コンパイル=compiler.コンパイル,
            基礎能力核=K3相当能力核(),
            模型核=core,
            正式模型評価=True,
        )
        self.assertEqual(result.状態, "APPROVE")
        self.assertEqual(result.回答ラベル, "B")
        self.assertGreaterEqual(result.専門作用起動数, 1)
        self.assertIn("HDS_ACTION_DELTA_ATTACHED", result.理由)
        self.assertIn("HDS_ACTION_DELTA_CONSUMED", result.理由)
        self.assertIsNotNone(result.MINIDORA模型結果)

    def test_追加条件未確認なら後続作用を発火させない(self) -> None:
        structure = 能力作用構造(
            作用=(
                能力作用記録("A", "遷移", "S0", "S1"),
                能力作用記録("B", "条件遷移", "S1", "S2", ("条件C",)),
            ),
            状態差=(能力状態差記録("D", "A", "S0", "S1", True),),
            後続利用=(能力後続利用記録("D", "S1", "B", ("条件C",), True),),
        )
        core = MINIDORA能力状態差模型核((), 能力作用群=(), 最大再作用回数=0)
        result = core.評価言語状態(
            言語状態("最終状態"),
            (
                成立候補("A", 言語状態("S1")),
                成立候補("B", 言語状態("S2")),
            ),
            作用構造群=(structure,),
        )
        self.assertIsNone(result.参照最有力候補ID)
        self.assertFalse(
            any(
                item.関係名.startswith("候補共同参照:状態差連結")
                for row in result.候補差
                for item in row.寄与
            )
        )


if __name__ == "__main__":
    unittest.main()
