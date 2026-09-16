from __future__ import annotations

import unittest

from minidora import 公開HDSコンパイラ
from minidora.HDS参照 import HDS参照問合せ候補
from minidora.言語基底_英日意味 import 英日意味フレーム抽出


def _条件値(関係, key: str) -> str:
    prefix = key + "="
    for raw in 関係.条件:
        value = str(raw)
        if value.startswith(prefix):
            return value[len(prefix):]
    return ""


def _意味関係(ir):
    return next(
        関係
        for 関係 in ir.関係
        if _条件値(関係, "英日意味射影") == "v0.5"
    )


class 英日意味コンパイル試験(unittest.TestCase):
    def setUp(self) -> None:
        self.構文化器 = 公開HDSコンパイラ()

    def test_least_likelyを日本語正本の反転関係質問へ落とす(self) -> None:
        text = "Which molecule is least likely to inhibit enzyme X?"
        frame = 英日意味フレーム抽出(text)
        self.assertIsNotNone(frame.関係質問)
        assert frame.関係質問 is not None
        self.assertEqual(frame.関係質問.種別, "阻害")
        self.assertEqual(frame.関係質問.未知位置, "始点")
        self.assertEqual(frame.関係質問.要求型, "molecule")
        self.assertEqual(frame.関係質問.既知端点, "enzyme X")
        self.assertTrue(frame.関係質問.反転)
        self.assertEqual(frame.関係質問.修飾, ())

        ir = self.構文化器.コンパイル(text)
        関係 = _意味関係(ir)
        self.assertEqual(関係.種別, "阻害")
        self.assertEqual(_条件値(関係, "不足位置"), "始点")
        self.assertEqual(_条件値(関係, "検索述語"), "inhibit")
        self.assertTrue(any(coord.種別 == "制御.選択意図" and coord.内容 == "反転" for coord in ir.座標))
        self.assertTrue(any("関係:阻害" in op.変換 and "蓋然性:最小" in op.変換 for op in ir.意味作用履歴))

    def test_背景文の否定を最終質問の制御へ伝染させない(self) -> None:
        text = (
            "Prior experiments did not show inhibition under condition A. "
            "Which molecule is most likely to inhibit enzyme X?"
        )
        frame = 英日意味フレーム抽出(text)
        self.assertIsNotNone(frame.関係質問)
        assert frame.関係質問 is not None
        self.assertEqual(frame.関係質問.種別, "阻害")
        self.assertFalse(frame.関係質問.反転)
        self.assertEqual(frame.関係質問.修飾, ())
        self.assertNotIn("否定:否定", frame.正本意味)
        self.assertIn("蓋然性:最大", frame.正本意味)

    def test_背景文のmodalを最終質問関係へ伝染させない(self) -> None:
        text = "Prior work may be incomplete. Which molecule inhibits enzyme X?"
        frame = 英日意味フレーム抽出(text)
        self.assertIsNotNone(frame.関係質問)
        assert frame.関係質問 is not None
        self.assertEqual(frame.関係質問.修飾, ())

    def test_型なし選択肢質問とmodalも未知始点へ落とす(self) -> None:
        text = "Which of the following could inhibit enzyme X?"
        frame = 英日意味フレーム抽出(text)
        self.assertIsNotNone(frame.関係質問)
        assert frame.関係質問 is not None
        self.assertEqual(frame.関係質問.種別, "阻害")
        self.assertEqual(frame.関係質問.未知位置, "始点")
        self.assertEqual(frame.関係質問.要求型, "選択肢")
        self.assertEqual(frame.関係質問.既知端点, "enzyme X")
        self.assertIn("様相:可能", frame.正本意味)
        self.assertEqual(frame.関係質問.修飾, (("様相", "可能"),))

        関係 = _意味関係(self.構文化器.コンパイル(text))
        self.assertEqual(_条件値(関係, "様相"), "可能")

    def test_mustを必要範囲として質問関係へ結ぶ(self) -> None:
        text = "Which compound must inhibit enzyme X?"
        frame = 英日意味フレーム抽出(text)
        self.assertIsNotNone(frame.関係質問)
        assert frame.関係質問 is not None
        self.assertEqual(frame.関係質問.修飾, (("様相", "必要"),))
        関係 = _意味関係(self.構文化器.コンパイル(text))
        self.assertEqual(_条件値(関係, "様相"), "必要")

    def test_受動態は意味方向へ反転して未知終点を保持する(self) -> None:
        ir = self.構文化器.コンパイル("Which protein is inhibited by compound X?")
        関係 = _意味関係(ir)
        coords = ir.座標辞書()
        self.assertEqual(関係.種別, "阻害")
        self.assertEqual(_条件値(関係, "不足位置"), "終点")
        self.assertEqual(_条件値(関係, "検索述語"), "inhibit")
        start = coords[関係.始点[0]]
        end = coords[関係.終点[0]]
        self.assertEqual(start.内容, "compound X")
        self.assertEqual(end.種別, "目的.未知終点")
        self.assertEqual(end.内容, "protein")

    def test_modal受動態も意味方向と範囲を保持する(self) -> None:
        text = "Which protein could be inhibited by compound X?"
        frame = 英日意味フレーム抽出(text)
        self.assertIsNotNone(frame.関係質問)
        assert frame.関係質問 is not None
        self.assertTrue(frame.関係質問.受動)
        self.assertEqual(frame.関係質問.未知位置, "終点")
        self.assertEqual(frame.関係質問.既知端点, "compound X")
        self.assertEqual(frame.関係質問.修飾, (("様相", "可能"),))
        関係 = _意味関係(self.構文化器.コンパイル(text))
        self.assertEqual(_条件値(関係, "様相"), "可能")

    def test_先頭条件範囲を質問本体から分離して関係へ戻す(self) -> None:
        text = "Under low pH, which compound may inhibit enzyme X?"
        frame = 英日意味フレーム抽出(text)
        self.assertIsNotNone(frame.関係質問)
        assert frame.関係質問 is not None
        self.assertEqual(frame.関係質問.種別, "阻害")
        self.assertEqual(frame.関係質問.既知端点, "enzyme X")
        self.assertIn(("様相", "可能"), frame.関係質問.修飾)
        self.assertIn(('条件範囲', "Under low pH"), frame.関係質問.修飾)

        関係 = _意味関係(self.構文化器.コンパイル(text))
        self.assertEqual(_条件値(関係, "様相"), "可能")
        self.assertEqual(_条件値(関係, '条件範囲'), "Under low pH")

    def test_量化を質問関係の修飾へ結ぶ(self) -> None:
        text = "Which enzyme inhibits all targets?"
        frame = 英日意味フレーム抽出(text)
        self.assertIsNotNone(frame.関係質問)
        assert frame.関係質問 is not None
        self.assertIn(("量化", "全称"), frame.関係質問.修飾)
        関係 = _意味関係(self.構文化器.コンパイル(text))
        self.assertEqual(_条件値(関係, "量化"), "全称")

    def test_目的語質問も未知終点へ落とす(self) -> None:
        ir = self.構文化器.コンパイル("What molecule does enzyme X produce?")
        関係 = _意味関係(ir)
        coords = ir.座標辞書()
        self.assertEqual(関係.種別, "生成")
        self.assertEqual(_条件値(関係, "不足位置"), "終点")
        self.assertEqual(coords[関係.始点[0]].内容, "enzyme X")
        self.assertEqual(coords[関係.終点[0]].内容, "molecule")

    def test_候補検索は意味関係から直接外部英語へ戻す(self) -> None:
        ir = self.構文化器.問題IR(
            "Which molecule is least likely to inhibit enzyme X?",
            ("Compound A", "Compound B", "Compound C", "Compound D"),
        )
        queries = HDS参照問合せ候補(ir)
        lowered = tuple(query.casefold() for query in queries)
        for 候補 in ("compound a", "compound b", "compound c", "compound d"):
            self.assertTrue(any(候補 in query and "inhibit" in query and "enzyme x" in query for query in lowered))
        self.assertTrue(any(coord.種別 == "検索.英語正規化" for coord in ir.座標))

    def test_命題選択は世界事実を捏造せず問い適合関係として保持する(self) -> None:
        ir = self.構文化器.コンパイル("Which statement is most likely correct regarding entropy?")
        意味 = [関係 for 関係 in ir.関係 if _条件値(関係, "英日意味射影")]
        self.assertEqual(len(意味), 1)
        self.assertEqual(str(意味[0].種別), "命題適合")
        self.assertEqual(_条件値(意味[0], "検索述語"), "proposition_match")

    def test_世界知識を意味フレームへ格納しない(self) -> None:
        frame = 英日意味フレーム抽出("Which protein inhibits kinase X?")
        self.assertNotIn("protein", frame.正本意味)
        self.assertNotIn("kinase", frame.正本意味)
        self.assertIn("protein", frame.外部検索語)
        self.assertIn("kinase", frame.外部検索語)


if __name__ == "__main__":
    unittest.main()
