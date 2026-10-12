"""正準本体の独立複製に限定した新人工6群。実資料・性能・製品評価は含まない。"""
import json
import math
import unittest
from unittest.mock import patch
from minidora.HDS運用 import 資料回答共有保存 as 保存


class 正準本体独立複製試験(unittest.TestCase):
    def 複製(self, 値, *, 上限=保存._圧縮展開上限):
        原 = 保存._バイト(値, 上限=上限)
        長さ, 深さ = 保存._JSON情報(値, 上限=上限)
        return 保存._正準本体を複製(値, 原, 元長=長さ, 元深さ=深さ, 上限=上限), 原

    def 形を比較(self, 左, 右):
        self.assertIs(type(左), type(右))
        if type(左) is dict:
            self.assertEqual(list(左), list(右))
            for 鍵 in 左: self.形を比較(左[鍵], 右[鍵])
        elif type(左) is list:
            self.assertEqual(len(左), len(右))
            for 甲, 乙 in zip(左, 右): self.形を比較(甲, 乙)
        else:
            self.assertEqual(左, 右)
            if type(左) is float and 左 == 0.0:
                self.assertEqual(math.copysign(1, 左), math.copysign(1, 右))

    def test_正準形順序型と浮動符号を保持(self):
        値 = {"終": [None, True, False, 17, 3.0, -0.0], "先": {"え": "e\u0301", "あ": "日本語😀\x00\"\\"}, "中": [{"z": 1, "a": 2}]}
        元順 = list(値)
        本体, 原 = self.複製(値)
        self.形を比較(本体, json.loads(原))
        self.assertEqual(保存._バイト(本体, 上限=保存._圧縮展開上限), 原)
        self.assertEqual(list(値), 元順)
        self.assertTrue(all(type(子) is not tuple for 子 in 本体["終"]))
        self.assertEqual(本体["先"]["え"], "e\u0301")

    def test_各可変値の出現を独立し不変値を再使用(self):
        文字列 = "原Unicode断片" * 17
        共通 = {"文字列": 文字列, "列": [文字列, 1]}
        値 = {"B": 共通, "A": 共通, "列": [共通, 共通]}
        本体, 原 = self.複製(値)
        for 部分 in (本体["A"], 本体["B"], *本体["列"]):
            self.assertIsNot(部分, 共通)
            self.assertIsNot(部分["列"], 共通["列"])
            self.assertIs(部分["文字列"], 文字列)
        全部分 = [本体["A"], 本体["B"], *本体["列"]]
        self.assertEqual(len({id(部分) for 部分 in 全部分}), 4)
        self.assertEqual(len({id(部分["列"]) for 部分 in 全部分}), 4)
        本体["A"]["列"].append("後変異")
        self.assertEqual(共通["列"], [文字列, 1])
        self.assertEqual(本体["B"]["列"], [文字列, 1])
        self.assertEqual(保存._バイト(値, 上限=保存._圧縮展開上限), 原)

    def test_型循環と既存有限JSON拒否を緩めない(self):
        class 文字列派生(str): pass
        class 偽型(type):
            def __eq__(self, 他): return 他 is str
            __hash__ = type.__hash__
        class 偽文字列(str, metaclass=偽型): pass
        循環 = []; 循環.append(循環)
        過深 = 0
        for _ in range(保存._意味深さ上限 + 1): 過深 = [過深]
        不正 = [(1,), 文字列派生("x"), {1: "x"}, math.nan, math.inf, -math.inf, "\ud800", 循環, 過深]
        for 値 in 不正:
            with self.subTest(種別=type(値).__name__):
                with self.assertRaises(ValueError):
                    保存._正準本体を複製(値, b"null", 元長=4, 元深さ=0, 上限=1024)
        for 値, 上限 in [("あ", 4), ("x" * 21, 20), ([0] * 21, 20)]:
            with self.subTest(上限=上限):
                with self.assertRaises(ValueError):
                    保存._正準本体を複製(値, b"null", 元長=4, 元深さ=0, 上限=上限)
        偽 = 偽文字列("x")
        原 = json.dumps(偽, ensure_ascii=False).encode("utf-8")
        with self.assertRaisesRegex(ValueError, "複製の厳密型"):
            保存._正準本体を複製(偽, 原, 元長=len(原), 元深さ=0, 上限=1024)

    def test_clone中のcycle型深さ節点を有限に拒否(self):
        def 過深挿入(値):
            深い = 0
            for _ in range(保存._意味深さ上限 + 1): 深い = [深い]
            値.append(深い)
        対照 = [(lambda: [], lambda 値: 値.append(値), 1024, "循環"),
                (lambda: [], 過深挿入, 1024, "深さ・節点"),
                (lambda: [], lambda 値: 値.extend([0] * 21), 20, "深さ・節点"),
                (lambda: [], lambda 値: 値.append(object()), 1024, "厳密型"),
                (lambda: {}, lambda 値: 値.update({1: "未知鍵"}), 1024, "辞書鍵型"),
                (lambda: [], lambda 値: 値.append(math.nan), 1024, "非有限数"),
                (lambda: [], lambda 値: 値.append("x" * 21), 20, "文字数")]
        正規情報 = 保存._JSON情報
        for 作る, 変更, 上限, 理由 in 対照:
            値 = 作る(); 原 = 保存._バイト(値, 上限=上限)
            長さ, 深さ = 正規情報(値, 上限=上限)
            発火 = []
            def 途中変異(項, **kwargs):
                情報 = 正規情報(項, **kwargs)
                if 項 is 値 and not 発火:
                    発火.append(True); 変更(値)
                return 情報
            with self.subTest(理由=理由), patch.object(保存, "_JSON情報", side_effect=途中変異), \
                 patch.object(保存, "_バイト", side_effect=AssertionError("clone guardより後へ到達")) as 符号化:
                with self.assertRaisesRegex(ValueError, 理由):
                    保存._正準本体を複製(値, 原, 元長=長さ, 元深さ=深さ, 上限=上限)
                self.assertTrue(発火)
                self.assertEqual(符号化.call_count, 0)

    def test_原正準保存宣言と途中同型変異を直接照合(self):
        値 = {"A": 1, "B": 2}
        原 = 保存._バイト(値, 上限=1024)
        長さ, 深さ = 保存._JSON情報(値, 上限=1024)
        対照 = [(bytearray(原), 長さ, 深さ), (原, True, 深さ), (原, 長さ, False),
                (原, float(長さ), 深さ), (原, 長さ + 1, 深さ), (原, 長さ, 深さ + 1),
                (b'{"B":2,"A":1}', 長さ, 深さ), (b'{"A":2,"B":2}', 長さ, 深さ)]
        for 原対照, 長対照, 深対照 in 対照:
            with self.subTest(宣言=(長対照, 深対照), 原型=type(原対照).__name__):
                with self.assertRaises(ValueError):
                    保存._正準本体を複製(値, 原対照, 元長=長対照, 元深さ=深対照, 上限=1024)
        情報を読む = 保存._JSON情報
        発火 = []
        def 途中変異(項, **kwargs):
            情報 = 情報を読む(項, **kwargs)
            if 項 is 値 and not 発火:
                発火.append(True); 値["A"] = 2
            return 情報
        with patch.object(保存, "_JSON情報", side_effect=途中変異), \
             patch.object(保存, "_バイト", wraps=保存._バイト) as 符号化:
            with self.assertRaisesRegex(ValueError, "原正準保存が不一致"):
                保存._正準本体を複製(値, 原, 元長=長さ, 元深さ=深さ, 上限=1024)
            self.assertTrue(発火)
            self.assertEqual(符号化.call_count, 1)
        self.assertEqual(原, b'{"A":1,"B":2}')

    def test_人工v3共有writerreaderの全byte同値と入力不変(self):
        所有 = {"資料ID": "人工資料", "保存指紋": "a" * 64, "本文": "原文字列の共通部分。" * 12000}
        座標 = {"座標ID": "人工座標", "開始": 0, "終了": 3}
        意味 = {"版": "人工正準意味-v1", "記載関係": [
                    {"資料作用": {"原資料": 所有, "座標": [座標]}},
                    {"資料作用": {"原資料": 所有, "座標": [座標]}}],
                "資料作用成果": {"原資料": [所有], "座標": [座標], "適用": {"人工適用": {"原資料": 所有}}},
                "未読": {"原文": "採用しない未知句", "残差": ["保持"]}}
        元 = 保存._バイト(意味, 上限=保存._圧縮展開上限)
        self.assertGreater(len(元), 保存._共有境界)
        旧本体 = lambda 値, 原, **kwargs: json.loads(原)
        with patch.object(保存, "_正準本体を複製", side_effect=旧本体):
            旧保存 = 保存.資料回答意味を保存(意味, 意味版=意味["版"])
            旧読取 = 保存.資料回答意味を読む(旧保存, 意味版=意味["版"])
            旧共有 = 保存._共有表を保存(意味, 意味版=意味["版"], 保存版=保存.資料回答共有保存版, 上限=保存._圧縮展開上限)
        新保存 = 保存.資料回答意味を保存(意味, 意味版=意味["版"])
        新読取 = 保存.資料回答意味を読む(新保存, 意味版=意味["版"])
        新共有 = 保存._共有表を保存(意味, 意味版=意味["版"], 保存版=保存.資料回答共有保存版, 上限=保存._圧縮展開上限)
        長さ, 深さ = 保存._JSON情報(意味, 上限=保存._圧縮展開上限)
        元供与共有 = 保存._共有表を保存(意味, 意味版=意味["版"], 保存版=保存.資料回答共有保存版,
                              上限=保存._圧縮展開上限, 原情報=(元, 長さ, 深さ))
        self.assertEqual(新保存["版"], 保存.資料回答共有保存版)
        self.assertEqual(新保存["圧縮対象"], "閉共有JSON-v1")
        self.assertEqual(保存._バイト(新保存), 保存._バイト(旧保存))
        self.assertEqual(保存._バイト(新読取, 上限=保存._圧縮展開上限), 元)
        self.assertEqual(保存._バイト(旧読取, 上限=保存._圧縮展開上限), 元)
        self.assertEqual(保存._バイト(新共有, 上限=保存._圧縮展開上限), 保存._バイト(旧共有, 上限=保存._圧縮展開上限))
        self.assertEqual(保存._バイト(元供与共有, 上限=保存._圧縮展開上限), 保存._バイト(新共有, 上限=保存._圧縮展開上限))
        self.assertEqual(保存._バイト(意味, 上限=保存._圧縮展開上限), 元)
        self.assertIs(意味["記載関係"][0]["資料作用"]["原資料"], 所有)


if __name__ == "__main__":
    unittest.main()
