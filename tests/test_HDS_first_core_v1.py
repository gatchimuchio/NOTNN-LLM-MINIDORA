from __future__ import annotations

import unittest

from minidora.HDS実行主体 import (
    HDS作用結果,
    HDS作用状態,
    HDS実行主体,
    HDS実行状態,
    HDS終端,
    HDS関数作用,
)
from minidora.HDS駆動コア import HDS駆動コア
from minidora.HDS中間表現 import HDSIR, HDS実行核
from minidora.製品版.能力契約 import 能力文脈
from minidora.製品版.能力レジストリ import 能力レジストリ
from minidora.製品版.型 import 能力結果


class _能力:
    def __init__(self, name: str, score: float, priority: int = 0) -> None:
        self.名前 = name
        self.版 = "v1"
        self.優先度 = priority
        self.score = score
        self.calls = 0

    def 判定(self, 文脈):
        return self.score

    def 実行(self, 文脈):
        self.calls += 1
        return 能力結果(True, f"{self.名前}:{文脈.入力文}")


class _構文化器:
    def コンパイル(self, text: str, **kwargs):
        return HDSIR(
            原文=text,
            正規化文=text,
            認知世界ID="test",
            座標=(),
            関係=(),
            残差=(),
            意味作用履歴=(),
            実行核=HDS実行核(),
        )


class HDSFirstCoreTests(unittest.TestCase):
    def test_action_success_does_not_equal_commit(self):
        action = HDS関数作用(
            "局所処理",
            lambda state: HDS作用結果(
                HDS作用状態.成立,
                追加状態=frozenset({"局所成立"}),
            ),
            出力状態=("局所成立",),
        )
        initial = HDS実行状態(要求状態=frozenset({"最終成立"}))
        result = HDS実行主体((action,), 最大作用回数=4).実行(initial)
        self.assertEqual(result.終端, HDS終端.保留)
        self.assertIn("局所成立", result.状態.成立状態)
        self.assertNotIn("最終成立", result.状態.成立状態)

    def test_residual_coverage_precedes_high_priority_unrelated_action(self):
        order = []

        unrelated = HDS関数作用(
            "高優先度だが無関係",
            lambda state: (
                order.append("unrelated")
                or HDS作用結果(HDS作用状態.成立, 追加状態=frozenset({"装飾"}))
            ),
            出力状態=("装飾",),
            優先度=100.0,
        )
        reference = HDS関数作用(
            "参照取得",
            lambda state: (
                order.append("reference")
                or HDS作用結果(
                    HDS作用状態.成立,
                    追加状態=frozenset({"資料あり"}),
                    解消残差=frozenset({"観測不足"}),
                )
            ),
            出力状態=("資料あり",),
            解消対象=("観測不足",),
            優先度=0.0,
        )
        finish = HDS関数作用(
            "回答形成",
            lambda state: (
                order.append("finish")
                or HDS作用結果(HDS作用状態.成立, 追加状態=frozenset({"回答済み"}))
            ),
            入力状態=("資料あり",),
            出力状態=("回答済み",),
            優先度=1.0,
        )
        initial = HDS実行状態(
            要求状態=frozenset({"回答済み"}),
            残差=frozenset({"観測不足"}),
        )
        result = HDS実行主体((unrelated, reference, finish), 最大作用回数=6).実行(initial)
        self.assertEqual(result.終端, HDS終端.採用)
        self.assertEqual(order[:2], ["reference", "finish"])
        self.assertNotIn("unrelated", order)

    def test_same_action_same_input_is_not_repeated(self):
        calls = []
        action = HDS関数作用(
            "無進展",
            lambda state: calls.append(state.状態署名) or HDS作用結果(HDS作用状態.保留),
        )
        initial = HDS実行状態(要求状態=frozenset({"未達"}))
        result = HDS実行主体((action,), 最大作用回数=8).実行(initial)
        self.assertEqual(result.終端, HDS終端.保留)
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(result.履歴), 1)
        self.assertFalse(result.履歴[0].状態差.変化有無)

    def test_same_action_can_run_again_after_real_state_change(self):
        def run(state):
            if "段階1" not in state.成立状態:
                return HDS作用結果(HDS作用状態.成立, 追加状態=frozenset({"段階1"}))
            return HDS作用結果(HDS作用状態.成立, 追加状態=frozenset({"段階2"}))

        action = HDS関数作用(
            "段階作用",
            run,
            出力状態=("段階1", "段階2"),
            機会判定=lambda state: "段階2" not in state.成立状態,
        )
        initial = HDS実行状態(要求状態=frozenset({"段階2"}))
        result = HDS実行主体((action,), 最大作用回数=4).実行(initial)
        self.assertEqual(result.終端, HDS終端.採用)
        self.assertEqual([row.作用ID for row in result.履歴], ["段階作用", "段階作用"])
        self.assertTrue(all(row.状態差.変化有無 for row in result.履歴))

    def test_subject_state_is_owned_by_hds_state(self):
        action = HDS関数作用(
            "主体更新",
            lambda state: HDS作用結果(
                HDS作用状態.成立,
                解消残差=frozenset({"主体更新待ち"}),
                主体状態差分=(("現在目的", "検証"),),
            ),
            解消対象=("主体更新待ち",),
        )
        initial = HDS実行状態(
            残差=frozenset({"主体更新待ち"}),
            主体状態=(("現在目的", "未設定"),),
        )
        result = HDS実行主体((action,), 最大作用回数=2).実行(initial)
        self.assertEqual(result.終端, HDS終端.採用)
        self.assertEqual(result.状態.主体辞書()["現在目的"], "検証")
        self.assertIn("現在目的", result.履歴[0].状態差.変更主体状態)

    def test_registry_exposes_all_candidates_and_keeps_legacy_selection(self):
        a = _能力("A", 0.8, 1)
        b = _能力("B", 0.9, 0)
        registry = 能力レジストリ((a, b))
        context = 能力文脈("hello", "s")
        candidates = registry.候補群(context)
        self.assertEqual([item.モジュール.名前 for item in candidates], ["B", "A"])
        selected = registry.選択(context)
        self.assertIsNotNone(selected)
        self.assertEqual(selected.モジュール.名前, "B")
        actions = registry.HDS作用群(
            context,
            出力状態={"A": ("A完了",), "B": ("B完了",)},
        )
        self.assertEqual(len(actions), 2)

    def test_registry_capability_is_committed_only_by_hds_goal(self):
        module = _能力("答える", 0.9)
        registry = 能力レジストリ((module,))
        context = 能力文脈("question", "s")
        actions = registry.HDS作用群(context, 出力状態={"答える": ("回答済み",)})
        initial = HDS実行状態(要求状態=frozenset({"回答済み"}))
        result = HDS実行主体(actions, 最大作用回数=4).実行(initial)
        self.assertEqual(result.終端, HDS終端.採用)
        self.assertEqual(module.calls, 1)
        self.assertIn("能力結果:答える", result.状態.成果辞書())

    def test_hds_driven_core_compiles_as_cognitive_action(self):
        core = HDS駆動コア(HDSコンパイラ=_構文化器(), 最大作用回数=3)
        result = core.実行(
            "入力",
            目的=("意味構文化",),
            要求状態=("HDS意味構文化済み",),
        )
        self.assertEqual(result.終端, HDS終端.採用)
        self.assertEqual([row.作用ID for row in result.履歴], ["HDS構文化"])
        self.assertIn("HDS_IR", result.状態.成果辞書())


if __name__ == "__main__":
    unittest.main()
