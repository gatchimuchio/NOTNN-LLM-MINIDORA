from __future__ import annotations

import unittest

from minidora.hds_choice_runtime import HDS選択実行結果
from minidora.hds_ir import HDSIR, HDS実行核, HDS座標
from minidora.hds統合runtime import HDS駆動選択実行
from minidora.hds統合判断主体 import HDS作用種別, MINIDORAHDS判断主体
from minidora.参照 import 参照記録


def choice_ir(*, required: bool = False) -> HDSIR:
    return HDSIR(
        原文="正しい候補を選べ A:猫 B:犬",
        正規化文="正しい候補を選べ A:猫 B:犬",
        認知世界ID="test-world",
        座標=(
            HDS座標("choice:A", "候補", "猫"),
            HDS座標("choice:B", "候補", "犬"),
        ),
        関係=(),
        残差=(),
        意味作用履歴=(),
        実行核=HDS実行核(),
        参照必須=required,
    )


def approved() -> HDS選択実行結果:
    return HDS選択実行結果(
        "APPROVE", "A", "猫", ("TEST_APPROVE",), None,
        2, 1, 0, 0, 1, 0,
    )


def suspended() -> HDS選択実行結果:
    return HDS選択実行結果(
        "SUSPEND", None, None, ("TEST_AMBIGUOUS",), None,
        2, 0, 0, 0, 0, 0,
    )


class FakeRuntime:
    def __init__(self, reference_available: bool) -> None:
        self.参照供給器 = object() if reference_available else None
        self.K3能力核 = object()

    def コンパイル(self, 問合せ: str):
        raise AssertionError("injected evaluatorではCompilerを呼ばない")


class HDS統合判断主体試験(unittest.TestCase):
    def test_参照_計算_COMMITを判断主体が順番に承認する(self):
        ref = 参照記録("r1", "q", "猫が正しい", "test", "test")
        runtime = FakeRuntime(True)
        result = HDS駆動選択実行(
            runtime,
            choice_ir(),
            参照実行=lambda _: (ref,),
            評価実行=lambda _ir, refs: approved() if refs else suspended(),
        )
        self.assertEqual(result.状態, "APPROVE")
        self.assertEqual(result.値, "猫")
        self.assertEqual(result.認知世界.状態, "COMMITTED")
        self.assertEqual(
            tuple(action for action, _ in result.認知世界.作用履歴),
            ("REFERENCE", "EVALUATE", "COMMIT"),
        )
        self.assertIn("HDS_JUDGEMENT_SUBJECT_COMMIT", result.理由)

    def test_候補生成結果だけでは自己COMMITしない(self):
        subject = MINIDORAHDS判断主体()
        world = subject.開始(choice_ir(), 参照利用可能=False)
        self.assertEqual(subject.次作用(world).作用, HDS作用種別.候補計算)
        world = subject.評価帰還(world, approved())
        self.assertEqual(world.状態, "OPEN")
        self.assertEqual(subject.次作用(world).作用, HDS作用種別.確定)
        world = subject.確定(world)
        self.assertEqual(world.状態, "COMMITTED")

    def test_必須参照が無ければ計算へ進まずSUSPENDする(self):
        result = HDS駆動選択実行(
            FakeRuntime(False),
            choice_ir(required=True),
            参照必須=True,
            評価実行=lambda _ir, _refs: (_ for _ in ()).throw(AssertionError("評価してはならない")),
        )
        self.assertEqual(result.状態, "SUSPEND")
        self.assertEqual(result.認知世界.状態, "SUSPENDED")
        self.assertEqual(
            tuple(action for action, _ in result.認知世界.作用履歴),
            ("SUSPEND",),
        )
        self.assertIn("HDS_REQUIRED_REFERENCE_UNAVAILABLE", result.理由)

    def test_評価が閉じなければSUSPENDし捏造回答を作らない(self):
        result = HDS駆動選択実行(
            FakeRuntime(False),
            choice_ir(),
            評価実行=lambda _ir, _refs: suspended(),
        )
        self.assertEqual(result.状態, "SUSPEND")
        self.assertIsNone(result.値)
        self.assertEqual(
            tuple(action for action, _ in result.認知世界.作用履歴),
            ("EVALUATE", "SUSPEND"),
        )
        self.assertIn("TEST_AMBIGUOUS", result.認知世界.残差)

    def test_留保後も理由付きで再開放できる(self):
        subject = MINIDORAHDS判断主体()
        world = subject.開始(choice_ir(), 参照利用可能=False)
        world = subject.評価帰還(world, suspended())
        world = subject.留保(world, ("不足",))
        reopened = subject.再開放(world, "新しい観測が到着")
        self.assertEqual(reopened.状態, "OPEN")
        self.assertIsNone(reopened.評価状態)
        self.assertGreater(reopened.版, world.版)
        self.assertIn("REOPEN:新しい観測が到着", reopened.残差)

    def test_作用予算超過は留保し無限循環しない(self):
        subject = MINIDORAHDS判断主体()
        world = subject.開始(choice_ir(), 参照利用可能=True, 作用予算=1)
        world = subject.参照帰還(world, 参照数=1)
        next_action = subject.次作用(world)
        self.assertEqual(next_action.作用, HDS作用種別.留保)
        self.assertIn("HDS_ACTION_BUDGET_EXHAUSTED", next_action.理由)


if __name__ == "__main__":
    unittest.main()
