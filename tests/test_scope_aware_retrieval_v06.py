from __future__ import annotations

import unittest

from minidora import 公開HDSコンパイラ
from minidora.hds_reference import HDS参照問合せ候補


class Scope対応R検索V06試験(unittest.TestCase):
    def setUp(self) -> None:
        self.compiler = 公開HDSコンパイラ()
        self.choices = ("Compound A", "Compound B", "Compound C", "Compound D")

    def _queries(self, question: str) -> tuple[str, ...]:
        ir = self.compiler.問題IR(question, self.choices)
        return tuple(query.casefold() for query in HDS参照問合せ候補(ir))

    def test_明示否定質問を否定英語へ戻す(self) -> None:
        queries = self._queries("Which molecule does not inhibit enzyme X?")
        for candidate in ("compound a", "compound b", "compound c", "compound d"):
            self.assertTrue(any(candidate in q and "does not inhibit enzyme x" in q for q in queries), queries)

    def test_modal質問を原modal付き英語へ戻す(self) -> None:
        queries = self._queries("Which of the following could inhibit enzyme X?")
        for candidate in ("compound a", "compound b", "compound c", "compound d"):
            self.assertTrue(any(candidate in q and "could inhibit enzyme x" in q for q in queries), queries)

    def test_modal否定を語順付きで復号する(self) -> None:
        queries = self._queries("Which molecule could not inhibit enzyme X?")
        for candidate in ("compound a", "compound b", "compound c", "compound d"):
            self.assertTrue(any(candidate in q and "could not inhibit enzyme x" in q for q in queries), queries)

    def test_least_likelyは関係否定へ変換しない(self) -> None:
        queries = self._queries("Which molecule is least likely to inhibit enzyme X?")
        choice_queries = [q for q in queries if any(c in q for c in ("compound a", "compound b", "compound c", "compound d"))]
        self.assertTrue(choice_queries)
        self.assertTrue(any("compound a inhibit enzyme x" in q for q in choice_queries), choice_queries)
        self.assertFalse(any("not inhibit enzyme x" in q or "does not inhibit enzyme x" in q for q in choice_queries), choice_queries)

    def test_scope表層は日本語正本条件と分離して保持される(self) -> None:
        ir = self.compiler.コンパイル("Which molecule could not inhibit enzyme X?")
        relation = next(r for r in ir.関係 if any(str(c).startswith("不足位置=") for c in r.条件))
        conditions = {str(c) for c in relation.条件}
        self.assertIn("極性=否定", conditions)
        self.assertIn("様相=可能", conditions)
        self.assertIn("極性表層=not", conditions)
        self.assertIn("様相表層=could", conditions)


if __name__ == "__main__":
    unittest.main()
