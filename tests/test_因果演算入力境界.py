from __future__ import annotations

import unittest

from minidora.因果演算 import 因果演算作用, 因果演算模型核
from minidora.模型 import 言語状態, 標準模型核
from minidora.言語構造 import 言語関係構造


def rel(kind: str, start: str, end: str, *, predicate=()) -> 言語関係構造:
    return 言語関係構造(
        kind,
        frozenset({start}),
        frozenset({end}),
        True,
        (),
        frozenset(predicate),
    )


def value(result, start: str, end: str):
    for item in result.導出群:
        if item.始点 == frozenset({start}) and item.終点 == frozenset({end}):
            return item.値
    return None


class 因果演算入力境界試験(unittest.TestCase):
    def test_問題文中の事実関係を参照Dataと連鎖できる(self):
        core = 因果演算模型核(標準模型核())
        action = next(item for item in core.能力作用群 if isinstance(item, 因果演算作用))
        context = core.文脈化(
            言語状態(
                "given fact",
                関係構造=(rel("増加", "alpha", "beta"),),
            ),
            参照状態=(
                言語状態(
                    "reference fact",
                    識別子="r1",
                    関係構造=(rel("減少", "beta", "gamma"),),
                ),
            ),
        )
        result = action.演算(context)
        self.assertEqual(value(result, "alpha", "gamma"), -1)

    def test_問い関係そのものを因果前提へ昇格しない(self):
        core = 因果演算模型核(標準模型核())
        action = next(item for item in core.能力作用群 if isinstance(item, 因果演算作用))
        context = core.文脈化(
            言語状態(
                "question",
                関係構造=(rel("問い適合", "alpha", "beta", predicate=("rel:増加",)),),
            ),
            参照状態=(
                言語状態(
                    "reference fact",
                    識別子="r1",
                    関係構造=(rel("減少", "beta", "gamma"),),
                ),
            ),
        )
        result = action.演算(context)
        self.assertIsNone(value(result, "alpha", "gamma"))


if __name__ == "__main__":
    unittest.main()
