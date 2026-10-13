"""U+200B原字と局所診断・可視表示の同伴。語中や条件の無言除去は認めない。"""
from copy import deepcopy
import unittest
from test_基本チャット引用診断 import 会話構造
from test_基本チャット内容 import 実行, 要求
from minidora.HDS運用.意味資料 import 資料を区分, 意味資料を検査
from minidora.HDS運用.内容構成 import 資料文章を検査
from minidora.HDS運用.値 import 結果を復元


class 会話不可視診断試験(unittest.TestCase):
    本文 = "# 定義\n試料甲とは熱の移動を抑える容器である。\n# 書誌\n【報告】\u200b\n"

    def test_直接strictは拒否し会話原本は全節と原字を保持(self):
        with self.assertRaises(ValueError):
            資料を区分(self.本文, 会話本文=True)
        構造 = 会話構造(self.本文)
        行 = 構造["資料群"]["資料"]
        self.assertEqual(結果を復元(行["資料"]).本文, self.本文)
        self.assertEqual(行["未選択"], [])
        診断 = 行["全体構文診断"]["診断"][0]
        self.assertEqual(診断["種別"], "不可視文字")
        self.assertEqual(self.本文[診断["文字位置"]], "\u200b")
        self.assertEqual(self.本文[診断["開始"]:診断["終了"]], 診断["原文"])
        self.assertTrue(意味資料を検査(構造))

    def test_定義と交差しない診断を原文束縛の可視片で同伴(self):
        成果 = 実行(self.本文, 要求(主題=("試料甲",), 関係焦点=("定義",)))
        self.assertIn("熱の移動を抑える容器", 成果.本文)
        self.assertIn("【報告】〈U+200B〉", 成果.本文)
        self.assertNotIn("\u200b", 成果.本文)
        項 = 成果.データ["意味成果"]["未確定限定"][0]
        self.assertEqual(項["対応"]["原文"], "【報告】\u200b\n")
        素材 = 結果を復元(成果.データ["文章"]).データ["原本"]["素材"]["診断原行"+str(項["留保番号"])]
        self.assertEqual(素材["データ"]["原文"], 項["対応"]["原文"])
        self.assertEqual(素材["本文"], "【報告】〈U+200B〉\n")
        self.assertTrue(資料文章を検査(成果))
        改変 = deepcopy(成果)
        改変.データ["意味成果"]["未確定限定"][0]["対応"]["原文"] = "【報告】\n"
        self.assertFalse(資料文章を検査(改変))

    def test_語中条件と対象を分断する不可視文字は保留(self):
        for 原行 in ("試料\u200b甲は安全ではない。", "ただ\u200bし低温の場合に限る。",
                     "【報告】\u200b条件あり", "普通の記載\u200b", "「未閉鎖\n\u200b\n", "```\n\u200b\n```\n"):
            with self.subTest(原行=原行), self.assertRaises(ValueError):
                会話構造(self.本文.split("# 書誌")[0] + 原行)

    def test_条件同対象脚注又は支持に交差する行は限定採用しない(self):
        for 原行 in ("【ただし低温の場合】\u200b", "【試料甲は安全ではない】\u200b", "【注記[3]】\u200b"):
            本文 = self.本文.split("# 書誌")[0].replace("容器である。", "容器である[3]。") + 原行
            with self.subTest(原行=原行), self.assertRaises(ValueError):
                実行(本文, 要求(主題=("試料甲",), 関係焦点=("定義",)))

    def test_他制御文字と未閉鎖は境界を維持(self):
        for 原行 in ("【報告】\ufeff", "【報告】\u200c", "【報告】\x00", "【報告】\u200b\n「未閉鎖"):
            with self.subTest(原行=原行), self.assertRaises(ValueError):
                会話構造(self.本文.split("# 書誌")[0] + 原行)
