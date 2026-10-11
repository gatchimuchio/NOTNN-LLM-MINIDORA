"""原本引用診断の有限配送契約。回答の意味採否は資料回答側で検査する。"""
from copy import deepcopy
from hashlib import sha256
import json
import unittest

from minidora.HDS運用.一般依頼 import 一般依頼を読む
from minidora.HDS運用.意味資料 import 資料を区分, 資料意味を選ぶ, 意味資料を検査, 会話引用診断版
from minidora.HDS運用.値 import 結果を復元
from minidora.製品版.型 import 能力結果


def 会話要求():
    return {"版": "HDS一般会話要求-v2", "対象": [], "主題": ["試料甲"], "操作": ["説明"],
            "形式": "文章", "範囲": "自動", "最大文字数": 24000, "問い": "契約試験の定義",
            "比較対象": [], "観点": [], "詳細": "標準", "提示本文": "", "関係焦点": ["定義"], "肯否": "未指定"}


def 会話構造(本文):
    return 資料意味を選ぶ({"資料": 能力結果(True, 本文)}, 会話要求())


class 会話引用診断試験(unittest.TestCase):
    本文 = "# 定義\n試料甲とは熱の移動を抑える容器である。\n# 出典\n著者,論文名」『雑誌』\n"

    def test_有効v2は診断欄なしで従来交換形を維持(self):
        本文 = self.本文.replace("論文名」", "「論文名」")
        構造 = 会話構造(本文)
        行 = 構造["資料群"]["資料"]
        self.assertEqual(set(行), {"資料", "節", "選択", "未選択"})
        self.assertEqual(行["節"], 資料を区分(本文, 会話本文=True))
        self.assertEqual(行["選択"], [0, 1])
        self.assertEqual(行["未選択"], [])
        self.assertEqual(結果を復元(行["資料"]).本文, 本文)
        self.assertTrue(意味資料を検査(構造))

    def test_有効v1の選択と交換形を変えない(self):
        要求 = 一般依頼を読む({"原文": "資料「A」の保守について要点を整理して"})["要求"]
        構造 = 資料意味を選ぶ({"A": 能力結果(True, "# 保守\n対象は屋内で点検する。\n# 色\n青い。")}, 要求)
        行 = 構造["資料群"]["A"]
        self.assertNotIn("全体構文診断", 行)
        self.assertEqual(行["選択"], [0])
        self.assertEqual(行["未選択"], [1])
        self.assertTrue(意味資料を検査(構造))

    def test_直接strictと旧v1は孤立閉じを拒否(self):
        for 会話指定 in (False, True):
            with self.subTest(会話指定=会話指定), self.assertRaises(ValueError):
                資料を区分(self.本文, 会話本文=会話指定)
        要求 = 一般依頼を読む({"原文": "資料「A」の定義について説明して"})["要求"]
        with self.assertRaises(ValueError):
            資料意味を選ぶ({"A": 能力結果(True, self.本文)}, 要求)

    def test_孤立閉じは全文原座標本文印と未確定作用域を同伴(self):
        構造 = 会話構造(self.本文)
        行 = 構造["資料群"]["資料"]
        注記 = 行["全体構文診断"]
        self.assertEqual(注記["版"], 会話引用診断版)
        self.assertEqual(注記["本文SHA256"], sha256(self.本文.encode()).hexdigest())
        self.assertEqual(len(注記["診断"]), 1)
        診断 = 注記["診断"][0]
        self.assertEqual(self.本文[診断["文字位置"]], "」")
        self.assertEqual(self.本文[診断["開始"]:診断["終了"]], "著者,論文名」『雑誌』\n")
        self.assertEqual(診断["原文"], self.本文[診断["開始"]:診断["終了"]])
        self.assertEqual(診断["種別"], "孤立閉じ")
        self.assertIn("未確定", 診断["作用域"])
        self.assertIn("撤回", 診断["必要資料"])
        self.assertIn("命題採用", 注記["境界"])
        self.assertEqual(結果を復元(行["資料"]).本文, self.本文)
        self.assertTrue(意味資料を検査(構造))

    def test_診断後も既存見出し階層と全節を原文ごと保持(self):
        行 = 会話構造(self.本文)["資料群"]["資料"]
        self.assertEqual([節["階層"][0]["見出し"] for 節 in 行["節"]], ["定義", "出典"])
        self.assertEqual("".join(self.本文[節["開始"]:節["終了"]] for 節 in 行["節"]), self.本文)
        self.assertEqual(行["選択"], [0, 1])
        self.assertEqual(行["未選択"], [])

    def test_閉じ引用の種と混在丸括弧の原字を保つ(self):
        for 字 in ("」", "』", ")", "）"):
            本文 = "試料甲(型式1）は容器である。\n出典" + 字 + "\n"
            with self.subTest(字=字):
                行 = 会話構造(本文)["資料群"]["資料"]
                self.assertEqual(結果を復元(行["資料"]).本文, 本文)
                self.assertEqual(len(行["全体構文診断"]["診断"]), 1)
                self.assertEqual(本文[行["全体構文診断"]["診断"][0]["文字位置"]], 字)

    def test_開いた引用や内部不整合を局所診断で解除しない(self):
        for 本文 in ('「先行\n試料甲とは容器である。\n',
                     '試料甲とは容器である。\n注記」\n「後続',
                     '注記」\n「先行）\n試料甲とは容器である。」',
                     '注記」\n(先行』\n試料甲とは容器である。)'):
            with self.subTest(本文=本文), self.assertRaises(ValueError):
                会話構造(本文)

    def test_未閉鎖コードや制御字を診断へ迂回しない(self):
        for 本文 in ('試料甲とは容器である。\n出典」\n```\n後続',
                     '試料甲とは容器である。\n出典」\u200b',
                     '試料甲とは容器である。\n出典」\u202e',
                     '試料甲とは容器である。\n出典」\x00'):
            with self.subTest(本文=本文), self.assertRaises(ValueError):
                会話構造(本文)

    def test_コード囲いの中の引用は従来の原文区間に保つ(self):
        本文 = "試料甲とは容器である。\n```\n「文字列の例\n```\n出典」\n"
        行 = 会話構造(本文)["資料群"]["資料"]
        self.assertEqual(len(行["全体構文診断"]["診断"]), 1)
        self.assertEqual(行["全体構文診断"]["診断"][0]["原文"], "出典」\n")
        self.assertIn("「文字列の例", 結果を復元(行["資料"]).本文)

    def test_否定撤回条件を収集から削らず採否を判定しない(self):
        for 原行 in ("試料甲は容器ではない」", "この定義は撤回された」", "ただし屋外では使用しない」",
                     "上記の定義は誤りである」", "この説明の適用は未確認である」"):
            本文 = "試料甲とは容器である。\n" + 原行 + "\n"
            with self.subTest(原行=原行):
                行 = 会話構造(本文)["資料群"]["資料"]
                self.assertEqual(行["全体構文診断"]["診断"][0]["原文"], 原行 + "\n")
                self.assertEqual(結果を復元(行["資料"]).本文, 本文)
                self.assertEqual(行["未選択"], [])

    def test_診断数原行量節数の上限で原本を切断しない(self):
        for 本文 in ("試料甲とは容器である。\n" + "」" * 65,
                     "試料甲とは容器である。\n" + "名" * 11000 + "」",
                     "\n".join("# 章" + str(番号) + "\n記載。" for 番号 in range(129)) + "\n出典」"):
            with self.subTest(文字数=len(本文)), self.assertRaises(ValueError):
                会話構造(本文)

    def test_保存交換後は全文から診断を再構成(self):
        構造 = 会話構造(self.本文)
        復元 = json.loads(json.dumps(構造, ensure_ascii=False))
        self.assertTrue(意味資料を検査(復元))
        self.assertEqual(復元, 構造)

    def test_診断原行座標印及び診断欠落の改変を拒否(self):
        元 = 会話構造(self.本文)
        for 欄, 値 in (("開始", 0), ("終了", 1), ("文字位置", 0), ("原文", "正常な書誌"),
                       ("種別", "確定資料"), ("理由", "無関係"), ("必要資料", "確認不要"), ("作用域", "非適用")):
            with self.subTest(欄=欄):
                改変 = deepcopy(元)
                改変["資料群"]["資料"]["全体構文診断"]["診断"][0][欄] = 値
                self.assertFalse(意味資料を検査(改変))
        for 欄, 値 in (("版", "旧版"), ("本文SHA256", "0" * 64), ("診断", [])):
            with self.subTest(欄=欄):
                改変 = deepcopy(元)
                改変["資料群"]["資料"]["全体構文診断"][欄] = 値
                self.assertFalse(意味資料を検査(改変))
        改変 = deepcopy(元)
        del 改変["資料群"]["資料"]["全体構文診断"]
        self.assertFalse(意味資料を検査(改変))

    def test_本文改変と有効原本への診断後付けを拒否(self):
        元 = 会話構造(self.本文)
        改変 = deepcopy(元)
        改変["資料群"]["資料"]["資料"]["本文"] = self.本文.replace("容器", "熱源")
        self.assertFalse(意味資料を検査(改変))
        有効 = 会話構造(self.本文.replace("論文名」", "「論文名」"))
        有効["資料群"]["資料"]["全体構文診断"] = 元["資料群"]["資料"]["全体構文診断"]
        self.assertFalse(意味資料を検査(有効))


if __name__ == "__main__":
    unittest.main()
