from __future__ import annotations

import unittest

from minidora.模型 import 成立候補, 言語状態, 標準模型核
from minidora.言語構造 import 言語関係構造
from minidora.関係連鎖演算 import (
    候補連鎖支持,
    関係数値ID,
    関係連鎖作用,
    関係連鎖作用名,
    関係連鎖演算,
    関係連鎖模型核,
)


def rel(kind: str, start: str, end: str, *, predicate=(), positive: bool = True):
    return 言語関係構造(
        kind,
        frozenset({start}) if start else frozenset(),
        frozenset({end}) if end else frozenset(),
        positive,
        (),
        frozenset(predicate),
    )


class 関係連鎖演算試験(unittest.TestCase):
    def test_異種関係を世界事実へ縮約せず数値列として保持する(self):
        result = 関係連鎖演算((
            ("r1", (rel("所属", "alpha", "beta"),)),
            ("r2", (rel("使用", "beta", "gamma"),)),
        ))
        states = [
            state for state in result.状態群
            if state.始点 == frozenset({"alpha"}) and state.終点 == frozenset({"gamma"})
        ]
        self.assertEqual(len(states), 1)
        state = states[0]
        self.assertEqual(state.深さ, 2)
        self.assertEqual(state.種別列, ("所属", "使用"))
        self.assertEqual(
            state.数値署名,
            ((関係数値ID(rel("所属", "x", "y")), 1, 1),
             (関係数値ID(rel("使用", "x", "y")), 1, 1)),
        )

    def test_相関は対称関係として逆向き連鎖できる(self):
        result = 関係連鎖演算((
            ("r1", (rel("相関", "beta", "alpha"),)),
            ("r2", (rel("使用", "beta", "gamma"),)),
        ))
        states = [
            state for state in result.状態群
            if state.始点 == frozenset({"alpha"}) and state.終点 == frozenset({"gamma"})
        ]
        self.assertTrue(states)
        self.assertEqual(states[0].数値列[0].方向, -1)

    def test_否定関係を反対の正関係として連鎖しない(self):
        result = 関係連鎖演算((
            ("r1", (rel("所属", "alpha", "beta", positive=False),)),
            ("r2", (rel("使用", "beta", "gamma"),)),
        ))
        self.assertFalse(any(
            state.始点 == frozenset({"alpha"}) and state.終点 == frozenset({"gamma"})
            for state in result.状態群
        ))

    def test_循環を経路増幅へ使わない(self):
        result = 関係連鎖演算((
            ("r1", (rel("所属", "a", "b"),)),
            ("r2", (rel("使用", "b", "a"),)),
            ("r3", (rel("生成", "b", "c"),)),
        ), 最大深さ=8)
        self.assertTrue(all(len(state.訪問節点) == len(set(state.訪問節点)) for state in result.状態群))
        self.assertLessEqual(result.最大到達深さ, 2)

    def test_広義問いは多段到達を一候補一差だけ受ける(self):
        core = 関係連鎖模型核(標準模型核())
        question = 言語状態(
            "which",
            関係構造=(rel("問い適合", "alpha", ""),),
        )
        candidate_a = 言語状態(
            "gamma",
            関係構造=(rel("問い適合", "alpha", "gamma"),),
        )
        candidate_b = 言語状態(
            "delta",
            関係構造=(rel("問い適合", "alpha", "delta"),),
        )
        result = core.評価言語状態(
            question,
            (成立候補("A", candidate_a), 成立候補("B", candidate_b)),
            参照状態=(
                言語状態("r1", 識別子="r1", 関係構造=(rel("所属", "alpha", "beta"),)),
                言語状態("r2", 識別子="r2", 関係構造=(rel("使用", "beta", "gamma"),)),
            ),
        )
        a = next(row for row in result.候補差 if row.候補ID == "A")
        b = next(row for row in result.候補差 if row.候補ID == "B")
        chain_a = [item for item in a.寄与 if item.関係名 == 関係連鎖作用名]
        chain_b = [item for item in b.寄与 if item.関係名 == 関係連鎖作用名]
        self.assertEqual([item.差 for item in chain_a], [1])
        self.assertEqual(chain_b, [])
        self.assertGreater(result.参照候補辞書()["A"], result.参照候補辞書()["B"])

    def test_複数経路でも候補差を票数で水増ししない(self):
        core = 関係連鎖模型核(標準模型核())
        action = next(item for item in core.能力作用群 if isinstance(item, 関係連鎖作用))
        context = core.文脈化(
            言語状態("which", 関係構造=(rel("問い適合", "a", ""),)),
            参照状態=(
                言語状態("r1", 識別子="r1", 関係構造=(rel("所属", "a", "b"), rel("使用", "b", "d"))),
                言語状態("r2", 識別子="r2", 関係構造=(rel("生成", "a", "c"), rel("位置", "c", "d"))),
            ),
        )
        candidate = core.言語対応.内部化(
            言語状態("d", 関係構造=(rel("問い適合", "a", "d"),))
        )
        contributions = action.評価群(context, (("A", candidate),))
        self.assertEqual(contributions["A"].差, 1)
        supported, evidence = 候補連鎖支持(context, candidate, action.演算(context))
        self.assertTrue(supported)
        self.assertGreaterEqual(len(evidence), 2)

    def test_反転問いで経路不存在を反証扱いしない(self):
        core = 関係連鎖模型核(標準模型核())
        action = next(item for item in core.能力作用群 if isinstance(item, 関係連鎖作用))
        context = core.文脈化(
            言語状態("except", 関係構造=(rel("問い適合", "a", ""),)),
            条件=("選択意図=反転",),
            参照状態=(
                言語状態("r1", 識別子="r1", 関係構造=(rel("所属", "a", "b"), rel("使用", "b", "d"))),
            ),
        )
        candidate = core.言語対応.内部化(
            言語状態("d", 関係構造=(rel("問い適合", "a", "d"),))
        )
        self.assertEqual(action.評価群(context, (("A", candidate),)), {})

    def test_関係連鎖作用は重複登録しない(self):
        first = 関係連鎖模型核(標準模型核())
        second = 関係連鎖模型核(first)
        self.assertEqual(
            sum(1 for item in second.能力作用群 if getattr(item, "名称", "") == 関係連鎖作用名),
            1,
        )


if __name__ == "__main__":
    unittest.main()
