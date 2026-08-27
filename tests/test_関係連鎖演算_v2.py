from __future__ import annotations

import unittest

from minidora.模型 import 成立候補, 言語状態, 標準模型核
from minidora.言語構造 import 言語関係構造
from minidora.関係連鎖演算 import 関係連鎖作用名
from minidora.関係連鎖演算_v2 import (
    推論文脈付き言語状態,
    推論文脈形成,
    候補連鎖支持V2,
    関係連鎖作用V2,
    関係連鎖模型核V2,
    関係連鎖演算V2,
)


def rel(kind: str, start, end, *, positive: bool = True):
    s = frozenset(start if isinstance(start, (set, frozenset, tuple, list)) else ({start} if start else ()))
    o = frozenset(end if isinstance(end, (set, frozenset, tuple, list)) else ({end} if end else ()))
    return 言語関係構造(kind, s, o, positive)


class 関係連鎖演算V2試験(unittest.TestCase):
    def test_片側包含だけでは端点同一とみなさない(self):
        result = 関係連鎖演算V2((
            ("r1", (rel("所属", {"protein"}, {"kinase"}),)),
            ("r2", (rel("使用", {"kinase", "alpha"}, {"gamma"}),)),
        ))
        self.assertFalse(any(
            state.始点 == frozenset({"protein"}) and state.終点 == frozenset({"gamma"})
            for state in result.状態群
        ))

    def test_双方75%以上が一致すれば端点を接続する(self):
        result = 関係連鎖演算V2((
            ("r1", (rel("所属", {"alpha"}, {"beta", "kinase", "protein", "cell"}),)),
            ("r2", (rel("使用", {"beta", "kinase", "protein"}, {"gamma"}),)),
        ))
        self.assertTrue(any(
            state.始点 == frozenset({"alpha"}) and state.終点 == frozenset({"gamma"})
            for state in result.状態群
        ))

    def test_複数候補へ共通到達した状態は候補差にしない(self):
        core = 関係連鎖模型核V2(標準模型核())
        question = 言語状態("which", 関係構造=(rel("問い適合", "a", ""),))
        reasoning = 言語状態(
            "",
            識別子="premise",
            関係構造=(
                rel("所属", "a", "b"),
                rel("所属", "a", "c"),
            ),
        )
        references = (
            言語状態("", 識別子="r1", 関係構造=(rel("使用", "b", "x"),)),
            言語状態("", 識別子="r2", 関係構造=(rel("使用", "c", "y"),)),
        )
        context = 推論文脈形成(core, question, 推論状態=(reasoning,), 参照状態=references)
        candidates = (
            成立候補("A", 言語状態("x", 関係構造=(rel("問い適合", "a", "x"),))),
            成立候補("B", 言語状態("y", 関係構造=(rel("問い適合", "a", "y"),))),
        )
        action = next(item for item in core.能力作用群 if isinstance(item, 関係連鎖作用V2))
        self.assertEqual(action.評価群(context, tuple((row.候補ID, core.言語対応.内部化(row.状態)) for row in candidates)), {})

    def test_一候補だけへ到達した時だけ差を返す(self):
        core = 関係連鎖模型核V2(標準模型核())
        question = 言語状態("which", 関係構造=(rel("問い適合", "a", ""),))
        reasoning = 言語状態("", 識別子="premise", 関係構造=(rel("所属", "a", "b"),))
        reference = 言語状態("", 識別子="r1", 関係構造=(rel("使用", "b", "x"),))
        context = 推論文脈形成(core, question, 推論状態=(reasoning,), 参照状態=(reference,))
        internal = (
            ("A", core.言語対応.内部化(言語状態("x", 関係構造=(rel("問い適合", "a", "x"),)))),
            ("B", core.言語対応.内部化(言語状態("y", 関係構造=(rel("問い適合", "a", "y"),)))),
        )
        action = next(item for item in core.能力作用群 if isinstance(item, 関係連鎖作用V2))
        contributions = action.評価群(context, internal)
        self.assertEqual(tuple(contributions), ("A",))
        self.assertEqual(contributions["A"].差, 1)

    def test_推論状態は通常文脈と分離して保持する(self):
        core = 関係連鎖模型核V2(標準模型核())
        question_relation = rel("問い適合", "a", "")
        premise_relation = rel("所属", "a", "b")
        context = 推論文脈形成(
            core,
            言語状態("question", 関係構造=(question_relation,)),
            推論状態=(言語状態("", 識別子="premise", 関係構造=(premise_relation,)),),
        )
        self.assertIsInstance(context, 推論文脈付き言語状態)
        self.assertEqual(context.現在.関係構造, (question_relation,))
        self.assertEqual(context.推論状態[0].関係構造, (premise_relation,))
        self.assertNotIn("premise", context.意味語集合)

    def test_v1作用を残さずv2へ一意置換する(self):
        first = 関係連鎖模型核V2(標準模型核())
        second = 関係連鎖模型核V2(first)
        actions = [item for item in second.能力作用群 if getattr(item, "名称", "") == 関係連鎖作用名]
        self.assertEqual(len(actions), 1)
        self.assertIsInstance(actions[0], 関係連鎖作用V2)


if __name__ == "__main__":
    unittest.main()
