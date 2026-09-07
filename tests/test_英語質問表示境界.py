from __future__ import annotations

from dataclasses import replace
import unittest

from minidora.hds_choice_runtime import HDS選択推論実行
from minidora.hds_compiler_v1 import 公開HDSコンパイラ
from minidora.hds_ir import HDS残差
from minidora.hds_language_semantic_bridge import HDS英日意味射影
from minidora.hds_model_projection import HDS内部言語状態
from minidora.hds_runtime_projection import HDSKData射影
from minidora.参照 import 参照記録
from minidora.能力状態差循環 import 標準能力模型核
from minidora.言語基底_英日意味 import 英語質問境界解析, 英語質問表示, 英日意味フレーム抽出 as 基礎抽出
from minidora.言語基底_英日意味強化 import 英日意味フレーム抽出 as 強化抽出
from minidora.言語構造 import _意味集合


_中立文 = "The archive contains routine records."
_宣言群 = (
    "The device which monitors the window uses a sensor.",
    "The operator who monitors the window uses a sensor.",
    "The room where the operator works contains a sensor.",
    "When the gate is open, blue widgets activate gamma.",
    "The report explains how the device works.",
    "The report identifies which device works.",
    "The operator knows who activates gamma.",
    "The report explains why the gate opens.",
    "The operator knows where the switch is stored.",
    "The operator knows when the switch activates gamma.",
    "The word 'which' appears in the report.",
    "The report contains 'Which?'.",
    'The report quotes "Which object activates gamma?".',
    '"Which object activates gamma?"',
    "The report quotes 'Why can't the device work?'.",
    "What a remarkable device!",
    "How remarkable the device is!",
)


def _前後追加(本文: str) -> tuple[str, ...]:
    区切り = "" if 本文.endswith((".", "?", "!", '"')) else "."
    return (本文, _中立文 + " " + 本文, 本文 + 区切り + " " + _中立文)


class 英語質問表示境界試験(unittest.TestCase):
    def setUp(self) -> None:
        self.コンパイラ = 公開HDSコンパイラ()

    def _活性化質問を確認(self, 本文: str, 条件: tuple[str, ...] = ()) -> None:
        self.assertTrue(英語質問表示(本文))
        for 抽出 in (基礎抽出, 強化抽出):
            質問 = 抽出(本文).関係質問
            self.assertIsNotNone(質問)
            assert 質問 is not None
            self.assertEqual((質問.種別, 質問.未知位置, 質問.要求型, 質問.既知端点, 質問.検索述語),
                             ("活性化", "始点", "switch", "lamp", "activate"))
            self.assertEqual(tuple(値 for 鍵, 値 in 質問.修飾 if 鍵 == "条件scope"), 条件)
        ir = self.コンパイラ.意味コンパイル(本文)
        関係群 = [関係 for 関係 in ir.関係 if "英日意味射影=v0.5" in 関係.条件
                  and "不足位置=始点" in 関係.条件]
        self.assertEqual(len(関係群), 1)
        self.assertEqual(関係群[0].種別, "活性化")
        座標 = ir.座標辞書()
        self.assertEqual(tuple(座標[端点].内容 for 端点 in 関係群[0].終点), ("lamp",))
        self.assertEqual(tuple(値.removeprefix("条件scope=") for 値 in 関係群[0].条件
                               if 値.startswith("条件scope=")), 条件)
        self.assertFalse(any(残差.種別 == "semantic_loss" for 残差 in ir.残差))

    def test_全文括弧と句点と疑問符を端点へ混ぜない(self) -> None:
        for 本文 in (
            "Which switch activates lamp", "(Which switch activates lamp)",
            "[Which switch activates lamp]", "[(Which switch activates lamp)].",
            "(Which switch activates lamp).", "(Which switch activates lamp?).",
            "(Which switch activates lamp)?", "(Which switch activates lamp? )",
            "(Which switch activates lamp)?!",
            "（Which switch activates lamp？）。",
        ):
            for 変形 in _前後追加(本文):
                with self.subTest(本文=変形):
                    self._活性化質問を確認(変形)

    def test_全文括弧の回復で感嘆や引用や埋込を質問へ昇格しない(self) -> None:
        for 本文 in (
            "(What a remarkable switch)!", "[How remarkable the switch is!].",
            '("Which switch activates lamp?").',
            'The report quotes "(Which switch activates lamp?)".',
            "The report includes (which switch activates lamp).",
        ):
            with self.subTest(本文=本文):
                self.assertFalse(英語質問表示(本文))
                self.assertIsNone(基礎抽出(本文).関係質問)
                self.assertIsNone(強化抽出(本文).関係質問)
        本文 = "The report includes (which switch activates lamp?)."
        self.assertTrue(英語質問表示(本文))
        self.assertIsNone(基礎抽出(本文).関係質問)
        質問 = 強化抽出(本文).関係質問
        self.assertIsNotNone(質問)
        assert 質問 is not None
        self.assertEqual(質問.種別, "問い適合")
        self.assertIn("The report includes", 質問.既知端点)

    def test_複数条件と引用括弧内区切りを全条件一件として保持する(self) -> None:
        for 条件 in (
            "If the seal is open, and the fuse is intact",
            'If the label reads "open, please"',
            'If the label reads "open; please"',
            'If the label reads "open, which?"',
            "If the label (open, checked) is present",
            "If the label [open; checked] is present",
        ):
            for 区切り in (",", ";"):
                for 終端 in ("", "?"):
                    本文 = f"{条件}{区切り} which switch activates lamp{終端}"
                    with self.subTest(本文=本文):
                        self._活性化質問を確認(本文, (条件,))

    def test_後置条件は先頭一文字へ短縮せず全文を保持する(self) -> None:
        for 条件 in ("under condition delta", "when the seal is open", "unless the fuse is broken"):
            for 終端 in ("", "?", "."):
                本文 = f"Which switch activates lamp {条件}{終端}"
                with self.subTest(本文=本文):
                    self._活性化質問を確認(本文, (条件,))
        引用内条件 = 英語質問境界解析('Which object has the label "under condition delta"?')
        self.assertEqual(引用内条件.条件scope, ())

    def test_単独改行は直接疑問を切らず間接疑問を主節へ昇格しない(self) -> None:
        裸 = "Which switch activates lamp"
        for 本文 in ("Which switch\nactivates lamp", "Which\nswitch activates lamp",
                    "Which switch\r\nactivates lamp"):
            with self.subTest(本文=本文):
                for 抽出 in (基礎抽出, 強化抽出):
                    self.assertEqual(抽出(本文), 抽出(裸))
                self._活性化質問を確認(本文)
        for 本文 in ("The report identifies\nwhich switch activates lamp.",
                    "When the seal is open,\ncopper switch activates lamp."):
            with self.subTest(本文=本文):
                self.assertFalse(英語質問表示(本文))
                self.assertIsNone(強化抽出(本文).関係質問)
                ir = self.コンパイラ.意味コンパイル(本文)
                self.assertFalse(any(残差.種別 == "semantic_loss" for 残差 in ir.残差))

    def test_直接when疑問は前半を条件へ変換せず全文を保持する(self) -> None:
        for 主節 in ("does the switch activate lamp", "has the switch activated lamp",
                    "is the switch active", "could the switch activate lamp"):
            for 終端 in ("", "?"):
                本体 = f"When {主節}, under condition delta"
                for 本文 in _前後追加(本体 + 終端):
                    with self.subTest(本文=本文):
                        境界 = 英語質問境界解析(本文)
                        self.assertTrue(境界.質問表示)
                        self.assertEqual(境界.本体, 本体)
                        self.assertEqual(境界.条件scope, ())
                        self.assertIsNone(基礎抽出(本文).関係質問)
                        質問 = 強化抽出(本文).関係質問
                        self.assertIsNotNone(質問)
                        assert 質問 is not None
                        self.assertEqual((質問.種別, 質問.既知端点), ("問い適合", 本体))
                        self.assertFalse(any(鍵 == "条件scope" for 鍵, _ in 質問.修飾))
        self._活性化質問を確認("When the seal is open, which switch activates lamp",
                                 ("When the seal is open",))

    def test_複数のWH境界は短い条件や部分質問へ確定しない(self) -> None:
        for 本体 in (
            "If the label, which contains copper, is present, which switch activates lamp",
            "If the label, which contains copper, is present and the " + "very " * 45
            + "long fuse is intact, which switch activates lamp",
        ):
            for 終端 in ("", "?"):
                with self.subTest(本体=本体, 終端=終端):
                    境界 = 英語質問境界解析(本体 + 終端)
                    self.assertTrue(境界.質問表示)
                    self.assertEqual(境界.境界状態, "条件境界未確定")
                    self.assertEqual((境界.本体, 境界.条件scope), (本体, ()))
                    self.assertIsNone(基礎抽出(本体 + 終端).関係質問)
                    質問 = 強化抽出(本体 + 終端).関係質問
                    self.assertIsNotNone(質問)
                    assert 質問 is not None
                    self.assertEqual((質問.種別, 質問.既知端点), ("問い適合", 本体))
                    self.assertFalse(any(鍵 == "条件scope" for 鍵, _ in 質問.修飾))

    def test_副詞と前置詞句を伴う直接疑問を条件節へ落とさない(self) -> None:
        for 主節 in (
            "When exactly does the switch activate lamp",
            "When in the cycle does the switch activate lamp",
            "Under which condition does the switch activate lamp",
            "To which device does the switch send pulses",
        ):
            for 終端 in ("", "?"):
                for 本文 in _前後追加(主節 + 終端):
                    with self.subTest(本文=本文):
                        境界 = 英語質問境界解析(本文)
                        self.assertTrue(境界.質問表示)
                        self.assertEqual((境界.本体, 境界.条件scope), (主節, ()))
                        質問 = 強化抽出(本文).関係質問
                        self.assertIsNotNone(質問)
                        assert 質問 is not None
                        self.assertEqual((質問.種別, 質問.既知端点), ("問い適合", 主節))

    def test_条件付きの倒置疑問と前置疑問句は条件scopeを保持する(self) -> None:
        条件 = "If the seal is open"
        for 主節 in (
            "does the switch activate lamp",
            "is the lamp active",
            "to which device does the switch send pulses",
            "under which condition does the switch activate lamp",
            "when exactly does the switch activate lamp",
        ):
            # 倒置だけでは省略条件・命令と区別できないため、明示疑問符を要求する。
            for 終端 in (("?",) if 主節.startswith(("does ", "is ")) else ("", "?")):
                本文 = f"{条件}, {主節}{終端}"
                with self.subTest(本文=本文):
                    境界 = 英語質問境界解析(本文)
                    self.assertTrue(境界.質問表示)
                    self.assertEqual((境界.本体, 境界.条件scope), (主節, (条件,)))
                    質問 = 強化抽出(本文).関係質問
                    self.assertIsNotNone(質問)
                    assert 質問 is not None
                    self.assertEqual(質問.既知端点, 主節)
                    self.assertIn(("条件scope", 条件), 質問.修飾)
                    ir = self.コンパイラ.意味コンパイル(本文)
                    関係群 = [関係 for 関係 in ir.関係 if "英日意味射影=v0.5" in 関係.条件]
                    self.assertEqual(len(関係群), 1)
                    self.assertIn(f"条件scope={条件}", 関係群[0].条件)

    def test_倒置疑問の認定で条件節と埋込と引用を主節へ昇格しない(self) -> None:
        for 本文 in (
            "When the switch is active, the test ends.",
            "When exactly the switch activates lamp is unknown.",
            "When in the cycle the switch does activate lamp, the test ends.",
            "Had the gate been open, the lamp would have activated.",
            "Were the seal intact, the lamp would activate.",
            "Should the switch fail, the lamp remains off.",
            "Do not activate the lamp.",
            "Have the operator activate the lamp.",
            "Under the condition in which the switch activates lamp, the test ends.",
            "The report identifies to which device the switch sends pulses.",
            'If the label says "does the switch activate lamp?", the test ends.',
            'The report quotes "When exactly does the switch activate lamp?".',
        ):
            with self.subTest(本文=本文):
                self.assertFalse(英語質問表示(本文))
                self.assertIsNone(強化抽出(本文).関係質問)

    def test_when前置詞句の後の主語を直接疑問の修飾へ吸収しない(self) -> None:
        for 条件 in (
            "When during testing sensors are active",
            "When in winter it is cold",
            "When during testing Nora is present",
        ):
            for 終端 in ("", "?"):
                with self.subTest(条件=条件, 終端=終端):
                    self._活性化質問を確認(f"{条件}, which switch activates lamp{終端}", (条件,))
            for 主節 in ("when does the switch activate lamp", "under which condition does the switch activate lamp"):
                本文 = f"{条件}, {主節}?"
                境界 = 英語質問境界解析(本文)
                self.assertEqual((境界.本体, 境界.条件scope), (主節, (条件,)))
                self.assertIn(("条件scope", 条件), 強化抽出(本文).関係質問.修飾)
        for 終端 in ("", "?"):
            本体 = "When in the cycle does the switch activate lamp, under condition delta"
            境界 = 英語質問境界解析(本体 + 終端)
            self.assertEqual(境界.質問表示, bool(終端))
            self.assertEqual((境界.本体, 境界.条件scope), (本体, ()))
            self.assertEqual(境界.境界状態, "when前置句境界未確定")

    def test_未確定のwhen境界は平叙事実として利用しない(self) -> None:
        for 本体 in (
            "When during testing sensors are active, under normal conditions the lamp glows.",
            "When in the cycle does the switch activate lamp, under condition delta",
        ):
            for 本文 in _前後追加(本体):
                with self.subTest(本文=本文):
                    self.assertFalse(英語質問表示(本文))
                    self.assertIsNone(強化抽出(本文).関係質問)
                    ir = self.コンパイラ.意味コンパイル(本文)
                    self.assertTrue(any(残差.残差ID == "lang-sem:question-boundary-unresolved" for 残差 in ir.残差))
                    self.assertFalse(HDS内部言語状態(HDSKData射影(ir), 証拠境界=True).証拠利用可)

    def test_不整合括弧は端点stripで修復せず未確定の全文を保持する(self) -> None:
        for 本文 in ("(Which switch activates lamp?", "([Which switch activates lamp)]?"):
            with self.subTest(本文=本文):
                境界 = 英語質問境界解析(本文)
                self.assertTrue(境界.質問表示)
                self.assertEqual(境界.境界状態, "括弧境界未確定")
                self.assertIsNone(基礎抽出(本文).関係質問)
                質問 = 強化抽出(本文).関係質問
                self.assertIsNotNone(質問)
                assert 質問 is not None
                self.assertEqual((質問.種別, 質問.既知端点), ("問い適合", 本文.rstrip("?")))

    def test_正式Runtimeで裸と全文括弧の支持差と無根拠停止が一致する(self) -> None:
        問い群 = ("Which switch activates lamp", "(Which switch activates lamp)",
                  "[(Which switch activates lamp)].", "(Which switch activates lamp? )")
        参照条件 = (
            ("明示支持", "Copper switch activates lamp. Silver switch does not activate lamp.", "APPROVE"),
            ("参照なし", None, "SUSPEND"),
            ("逆方向だけ", "Lamp activates copper switch.", "SUSPEND"),
            ("異なる条件だけ", "Under condition delta, copper switch activates lamp.", "SUSPEND"),
        )
        for 名前, 本文, 期待状態 in 参照条件:
            裸の結果 = None
            for 問い本文 in 問い群:
                with self.subTest(参照=名前, 問い=問い本文):
                    問い = self.コンパイラ.問題IR(問い本文, ("Copper switch", "Silver switch"))
                    参照 = (参照記録("artificial", "artificial", 本文, "test", "test"),) if 本文 else ()
                    結果 = HDS選択推論実行(
                        問い, 参照, コンパイル=self.コンパイラ.意味コンパイル,
                        基礎能力核=None, 模型核=標準能力模型核(), 正式模型評価=True, 局所再照合=False,
                    )
                    self.assertEqual(結果.状態, 期待状態)
                    self.assertIsNotNone(結果.MINIDORA模型結果)
                    assert 結果.MINIDORA模型結果 is not None
                    観測 = (結果.状態, 結果.回答内容, 結果.MINIDORA模型結果.参照候補辞書())
                    if 裸の結果 is None:
                        裸の結果 = 観測
                    self.assertEqual(観測, 裸の結果)
                    if 期待状態 == "APPROVE":
                        self.assertEqual(結果.回答内容, "Copper switch")
                        self.assertEqual(観測[2], {"A": 3, "B": -2})
                    else:
                        self.assertIsNone(結果.回答内容)

    def test_宣言内の疑問語と引用を質問残差へ昇格しない(self) -> None:
        for 宣言 in _宣言群:
            for 本文 in _前後追加(宣言):
                with self.subTest(本文=本文):
                    self.assertFalse(英語質問表示(本文))
                    self.assertIsNone(基礎抽出(本文).関係質問)
                    self.assertIsNone(強化抽出(本文).関係質問)
                    ir = self.コンパイラ.意味コンパイル(本文)
                    self.assertFalse(any("不足位置=" in 条件 for 関係 in ir.関係 for 条件 in 関係.条件))
                    self.assertFalse(any(残差.種別 == "semantic_loss" for 残差 in ir.残差))
                    self.assertTrue(HDS内部言語状態(HDSKData射影(ir), 証拠境界=True).証拠利用可)

    def test_疑問符なしの問いに前後文を足しても意味フレームを変えない(self) -> None:
        for 問い in ("Which widgets activate gamma", "What activates gamma", "Who activates gamma"):
            for 本文 in (*_前後追加(問い), 問い + ". The archive does not contain unusual records."):
                with self.subTest(本文=本文):
                    self.assertTrue(英語質問表示(本文))
                    self.assertIsNotNone(強化抽出(本文).関係質問)
                    for 抽出 in (基礎抽出, 強化抽出):
                        self.assertEqual(抽出(本文), 抽出(問い))

    def test_未解質問は前後文があっても証拠利用を遮断する(self) -> None:
        for 本文 in _前後追加("Which?"):
            with self.subTest(本文=本文):
                self.assertTrue(英語質問表示(本文))
                self.assertIsNone(強化抽出(本文).関係質問)
                ir = self.コンパイラ.意味コンパイル(本文)
                self.assertTrue(any(残差.残差ID == "lang-sem:question-loss" for 残差 in ir.残差))
                self.assertFalse(HDS内部言語状態(HDSKData射影(ir), 証拠境界=True).証拠利用可)

    def test_条件whenの主節が平叙文か問いかを区別する(self) -> None:
        self.assertFalse(英語質問表示("When the gate is open, blue widgets activate gamma."))
        for 主節 in ("who activates gamma", "why does gamma activate", "where is the switch"):
            問い = "When the gate is open, " + 主節
            for 本文 in (*_前後追加(問い), *_前後追加(問い + "?")):
                with self.subTest(本文=本文):
                    self.assertTrue(英語質問表示(本文))
                    質問 = 強化抽出(本文).関係質問
                    self.assertIsNotNone(質問)
                    assert 質問 is not None
                    self.assertIn(("条件scope", "When the gate is open"), 質問.修飾)

    def test_引用疑問符は実質問の焦点を奪わない(self) -> None:
        for 問い in ("Which widgets activate gamma", "Which widgets activate gamma?"):
            本文 = 問い + (". " if not 問い.endswith("?") else " ") + "The report contains 'Which?'."
            self.assertEqual(強化抽出(本文), 強化抽出(問い))

    def test_引用外の疑問符と単語内部apostropheを保持する(self) -> None:
        for 本文 in (
            "Which object is labeled 'which'?",
            "Which object is labeled 'Which?'?",
            "When does the device activate gamma?",
            "Under which condition does the device activate gamma?",
            "The device activates which target?",
        ):
            with self.subTest(本文=本文):
                self.assertTrue(英語質問表示(本文))
                self.assertIsNotNone(強化抽出(本文).関係質問)
        本文 = "Which object can't activate gamma?"
        質問 = 強化抽出(本文).関係質問
        self.assertIsNotNone(質問)
        assert 質問 is not None
        self.assertEqual(質問.種別, "活性化")
        self.assertEqual(質問.既知端点, "gamma")
        self.assertIn(("極性", "否定"), 質問.修飾)
        self.assertEqual(強化抽出(本文 + " The archive can't contain unusual records."), 強化抽出(本文))

    def test_質問表示を持たない宣言でも既存の意味損失を免除しない(self) -> None:
        元 = self.コンパイラ.意味コンパイル("The report identifies which device works.")
        残差 = HDS残差("test:unresolved", "semantic_loss", 元.原文, "別の未解関係")
        結果 = HDS英日意味射影(replace(元, 残差=(残差,)))
        self.assertEqual(結果.残差, (残差,))
        self.assertFalse(HDS内部言語状態(HDSKData射影(結果), 証拠境界=True).証拠利用可)

    def test_独立明示関係の否定条件を中立追加で失わない(self) -> None:
        否定条件 = "Under condition delta, blue widgets do not activate gamma."
        for 本文 in (否定条件, _宣言群[1] + " " + 否定条件, 否定条件 + " " + _宣言群[1] + " " + _中立文):
            with self.subTest(本文=本文):
                ir = self.コンパイラ.意味コンパイル(本文)
                状態 = HDS内部言語状態(HDSKData射影(ir), 証拠境界=True)
                self.assertTrue(状態.証拠利用可)
                対象 = [関係 for 関係 in 状態.関係構造 if 関係.種別 == "活性化"
                        and 関係.始点 == _意味集合("blue widgets") and 関係.終点 == _意味集合("gamma")]
                self.assertTrue(対象)
                self.assertFalse(any(関係.肯定 for 関係 in 対象))
                self.assertTrue(any({"condition", "delta"}.issubset(frozenset().union(*関係.条件)) for 関係 in 対象))

    def test_正式Runtimeで関係詞や間接疑問の中立追加後も明示支持を利用する(self) -> None:
        問い = self.コンパイラ.問題IR("Which object activates gamma?", ("Blue widgets", "Red widgets"))
        for 宣言 in _宣言群[:11]:
            for 本文 in _前後追加("Blue widgets activate gamma. " + 宣言):
                with self.subTest(本文=本文):
                    結果 = HDS選択推論実行(
                        問い,
                        (参照記録("artificial", "artificial", 本文, "test", "test"),),
                        コンパイル=self.コンパイラ.意味コンパイル,
                        基礎能力核=None,
                        模型核=標準能力模型核(),
                        正式模型評価=True,
                        局所再照合=False,
                    )
                    self.assertEqual(結果.状態, "APPROVE")
                    self.assertEqual(結果.回答内容, "Blue widgets")
                    self.assertIsNotNone(結果.MINIDORA模型結果)
                    assert 結果.MINIDORA模型結果 is not None
                    self.assertEqual(結果.MINIDORA模型結果.参照候補辞書(), {"A": 3, "B": 0})


if __name__ == "__main__":
    unittest.main()
