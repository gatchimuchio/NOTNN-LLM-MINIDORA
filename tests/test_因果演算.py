from __future__ import annotations

import unittest

from minidora.因果演算 import (
    候補因果差,
    因果演算作用,
    因果演算模型核,
    因果関係演算,
)
from minidora.模型 import 成立候補, 言語状態, 標準模型核
from minidora.言語構造 import 言語関係構造


def rel(kind: str, start: str, end: str, *, predicate: tuple[str, ...] = ()) -> 言語関係構造:
    return 言語関係構造(
        kind,
        frozenset({start}),
        frozenset({end}),
        True,
        (),
        frozenset(predicate),
    )


def derived_value(result, start: str, end: str) -> int | None:
    for item in result.導出群:
        if item.始点 == frozenset({start}) and item.終点 == frozenset({end}):
            return item.値
    return None


class 因果演算試験(unittest.TestCase):
    def test_増加と減少を連鎖して負作用を導出する(self):
        result = 因果関係演算((
            ("r1", (rel("増加", "a", "b"),)),
            ("r2", (rel("減少", "b", "c"),)),
        ))
        self.assertEqual(derived_value(result, "a", "c"), -1)
        self.assertGreaterEqual(result.最大到達深さ, 2)

    def test_阻害を二回通すと正作用へ戻る(self):
        result = 因果関係演算((
            ("r1", (rel("阻害", "a", "b"),)),
            ("r2", (rel("阻害", "b", "c"),)),
        ))
        self.assertEqual(derived_value(result, "a", "c"), 1)

    def test_独立経路は加算し競合経路は相殺する(self):
        result = 因果関係演算((
            ("p1", (rel("増加", "a", "b"), rel("増加", "b", "c"))),
            ("n1", (rel("増加", "a", "d"), rel("減少", "d", "c"))),
        ))
        self.assertEqual(derived_value(result, "a", "c"), 0)

    def test_相関は因果辺へ昇格しない(self):
        result = 因果関係演算((
            ("r1", (rel("相関", "a", "b"),)),
            ("r2", (rel("増加", "b", "c"),)),
        ))
        self.assertEqual(result.基礎辺数, 1)
        self.assertIsNone(derived_value(result, "a", "c"))

    def test_否定された因果を逆作用として伝播しない(self):
        denied = 言語関係構造("因果", frozenset({"a"}), frozenset({"b"}), False)
        result = 因果関係演算((
            ("r1", (denied,)),
            ("r2", (rel("増加", "b", "c"),)),
        ))
        self.assertEqual(result.基礎辺数, 1)
        self.assertIsNone(derived_value(result, "a", "c"))

    def test_問い適合でも述語の因果符号を使える(self):
        result = 因果関係演算((
            ("r1", (rel("増加", "a", "b"),)),
            ("r2", (rel("減少", "b", "c"),)),
        ))
        negative = rel("問い適合", "a", "c", predicate=("rel:減少",))
        positive = rel("問い適合", "a", "c", predicate=("rel:増加",))
        neg_score, _ = 候補因果差((negative,), result)
        pos_score, _ = 候補因果差((positive,), result)
        self.assertGreater(neg_score, 0)
        self.assertLess(pos_score, 0)

    def test_深さ1は因果演算として二重加点しない(self):
        core = 因果演算模型核(標準模型核())
        candidate = rel("問い適合", "a", "c", predicate=("rel:増加",))
        result = core.評価言語状態(
            言語状態("which"),
            (成立候補("A", 言語状態("candidate", 関係構造=(candidate,))),),
            参照状態=(言語状態("direct", 識別子="r1", 関係構造=(rel("増加", "a", "c"),)),),
        )
        causal = [
            item
            for row in result.候補差
            for item in row.寄与
            if item.関係名 == 因果演算作用.名称
        ]
        self.assertEqual(causal, [])

    def test_正式模型核で導出関係が参照候補差へ入る(self):
        core = 因果演算模型核(標準模型核())
        decrease = rel("問い適合", "a", "c", predicate=("rel:減少",))
        increase = rel("問い適合", "a", "c", predicate=("rel:増加",))
        result = core.評価言語状態(
            言語状態("which"),
            (
                成立候補("A", 言語状態("decrease", 関係構造=(decrease,))),
                成立候補("B", 言語状態("increase", 関係構造=(increase,))),
            ),
            参照状態=(
                言語状態("a increases b", 識別子="r1", 関係構造=(rel("増加", "a", "b"),)),
                言語状態("b decreases c", 識別子="r2", 関係構造=(rel("減少", "b", "c"),)),
            ),
        )
        self.assertEqual(result.参照最有力候補ID, "A")
        self.assertGreater(result.参照候補辞書()["A"], result.参照候補辞書()["B"])
        a_row = next(row for row in result.候補差 if row.候補ID == "A")
        self.assertTrue(any(item.関係名 == 因果演算作用.名称 for item in a_row.寄与))

    def test_模型核への因果作用追加は一度だけ(self):
        first = 因果演算模型核(標準模型核())
        second = 因果演算模型核(first)
        count = sum(1 for item in second.能力作用群 if getattr(item, "名称", "") == 因果演算作用.名称)
        self.assertEqual(count, 1)


if __name__ == "__main__":
    unittest.main()
