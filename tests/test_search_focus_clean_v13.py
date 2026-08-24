from __future__ import annotations

import unittest

from minidora import 公開HDSコンパイラ
from minidora.hds_reference import HDS参照問合せ候補
from minidora.言語基底_英日意味 import 英日意味フレーム抽出


class 検索焦点接続V13試験(unittest.TestCase):
    def setUp(self) -> None:
        self.compiler = 公開HDSコンパイラ()

    def _lang_focus(self, ir):
        return [coord for coord in ir.座標 if coord.座標ID.startswith("lang-sem:search") and str(coord.種別) == "目的.検索焦点"]

    def test_英語正規化表層を目的検索焦点として保持する(self) -> None:
        question = "Which of the following statements best describes cellular respiration?"
        ir = self.compiler.問題IR(question, ("Choice A", "Choice B", "Choice C", "Choice D"))
        focus = self._lang_focus(ir)
        self.assertEqual(len(focus), 1)
        self.assertEqual(str(focus[0].内容), "cellular respiration")
        self.assertFalse(any(str(coord.種別) == "検索.英語正規化" for coord in ir.座標))

    def test_検索焦点内容は英日意味フレームの外部検索語と一致する(self) -> None:
        question = "Which mechanism best explains signal propagation through the system?"
        frame = 英日意味フレーム抽出(question)
        expected = " ".join(token for token in frame.外部検索語 if not token.startswith("rel:"))
        ir = self.compiler.コンパイル(question)
        focus = self._lang_focus(ir)
        self.assertEqual(len(focus), 1)
        self.assertEqual(str(focus[0].内容), expected)

    def test_一般質問では正規化検索焦点がprimary_queryへ入る(self) -> None:
        question = "Which of the following statements best describes cellular respiration?"
        ir = self.compiler.問題IR(question, ("Choice A", "Choice B", "Choice C", "Choice D"))
        queries = tuple(query.casefold() for query in HDS参照問合せ候補(ir))
        self.assertGreaterEqual(len(queries), 2)
        self.assertTrue(any("cellular respiration" in query for query in queries[:2]), queries[:2])

    def test_関係質問の候補queryは既存の不足スロット経路を維持する(self) -> None:
        ir = self.compiler.問題IR("Which molecule inhibits Enzyme X?", ("Compound A", "Compound B", "Compound C", "Compound D"))
        queries = tuple(query.casefold() for query in HDS参照問合せ候補(ir))
        for candidate in ("compound a", "compound b", "compound c", "compound d"):
            self.assertTrue(any(candidate in query and "inhibit" in query and "enzyme x" in query for query in queries), queries)


if __name__ == "__main__":
    unittest.main()
