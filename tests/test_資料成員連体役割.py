"""成員母集団の原目的・連体主体を分ける有限開発対照。"""
from copy import deepcopy
import unittest
from unittest.mock import patch

from minidora.HDS運用.資料回答 import (
    回答意味を構成, 資料内容不足, 資料内容不足を読む, 資料回答版,
    _成員修飾の内容を読む,
)
from minidora.HDS運用.内容構成 import _文章, _資料文章を照合, 資料文章を検査, 資料文章の版を検査
from test_資料内容不足 import 構造を作る


class 資料成員連体役割試験(unittest.TestCase):
    def 意味を得る(self, 述部):
        return 回答意味を構成(構造を作る("機構は" + 述部 + "の一つである。", "機構"))

    def 不足を得る(self, 述部):
        構造 = 構造を作る("機構は" + 述部 + "の一つである。", "機構")
        with self.assertRaises(資料内容不足) as 捕捉:
            回答意味を構成(構造)
        return 構造, 捕捉.exception.診断

    def 寄与を得る(self, 意味):
        return next(項["読解"] for 項 in 意味["演算"] if 項["種別"] == "成員定義の内容寄与")

    def 部分を得る(self, 診断):
        return 診断["不足役割"][0]["原役割読解"][0]

    def test_目的だけを一意主要部へ限定し実行因果手段を作らない(self):
        述部 = "部品を加工するための機能"
        意味 = self.意味を得る(述部)
        読み = self.寄与を得る(意味)
        self.assertTrue(読み["必要内容寄与"])
        self.assertIsNone(読み["目的"]["内部事象"][0]["明示主体"])
        self.assertIsNone(読み["目的"]["手段"])
        self.assertFalse(読み["目的"]["現実実行"])
        self.assertFalse(読み["目的"]["因果根拠"])
        self.assertEqual(len(読み["用途係り先候補"]), 1)
        self.assertFalse(意味["記載関係"][0]["関係"]["目的"])
        構造 = 構造を作る("機構は" + 述部 + "の一つである。", "機構")
        成果 = _資料文章を照合(構造, _文章(構造), 形式=None, 共有保存=False)
        self.assertIn(述部, 成果.本文)
        self.assertNotIn("機構が部品を加工", 成果.本文)
        self.assertTrue(資料文章を検査(成果))

    def test_所有側の部分読了dictだけでは内容成立しない(self):
        _, 診断 = self.不足を得る("機械が持つ機能")
        読み = self.部分を得る(診断)
        self.assertTrue(読み)
        self.assertFalse(読み["必要内容寄与"])
        self.assertIsNone(読み["目的"])
        self.assertEqual(読み["明示連体主体"]["明示主体"]["核"]["原文"], "機械")
        self.assertEqual(読み["明示連体主体"]["格空所"]["状態"], "未確定")
        self.assertTrue(読み["未解決役割"])

    def test_目的と連体主体の多候補を原空白括弧と共に保持(self):
        for 述部 in ("部品を加工するための、機械が持つ機能",
                     "部品を加工するための、機械 (装置) が持つ機能",
                     "部品を加工するための機械の機能"):
            with self.subTest(述部=述部):
                _, 診断 = self.不足を得る(述部)
                読み = self.部分を得る(診断)
                self.assertFalse(読み["必要内容寄与"])
                self.assertIsNone(読み["目的"]["内部事象"][0]["明示主体"])
                self.assertGreater(len(読み["用途係り先候補"]), 1)
                self.assertEqual(読み["原母集団"], 述部)
                self.assertEqual("".join(項["表層"] for 項 in 読み["原役割証拠"]["字句"]), 述部)
                for 項 in 読み["用途係り先候補"]:
                    self.assertEqual(述部[項["開始"]:項["終了"]], 項["原文"])

    def test_目的内部の明示actorを成員又は手段へ移さない(self):
        意味 = self.意味を得る("作業者が部品を加工するための機能")
        読み = self.寄与を得る(意味)
        self.assertTrue(読み["必要内容寄与"])
        self.assertEqual(読み["目的"]["内部事象"][0]["明示主体"]["原文"], "作業者")
        self.assertIsNone(読み["目的"]["手段"])
        self.assertNotIn("機構が部品を加工", 意味["意味"]["命題"][0]["本文"])

    def test_旧別主体の事象と未知修飾を新役割型で許可しない(self):
        for 述部 in ("作業者が金属を削る機械", "情報を移動するための、装置B（B）が持つ機能"):
            with self.subTest(述部=述部):
                _, 診断 = self.不足を得る(述部)
                self.assertEqual(診断["不足役割"][0]["原役割読解"], [])
                self.assertIn(述部, 診断["読解済み内容"][0]["本文"])

    def test_否定照応とためを肯定のためのへ変換しない(self):
        for 述部 in ("機械が持たない機能", "それが持つ機能", "部品を加工するため、機械が持つ機能"):
            with self.subTest(述部=述部):
                _, 診断 = self.不足を得る(述部)
                self.assertEqual(診断["不足役割"][0]["原役割読解"], [])
                self.assertIn(述部, 診断["読解済み内容"][0]["本文"])

    def test_原役割範囲部分boolと旧意味版の改変を最終消費者で拒否(self):
        構造, 診断 = self.不足を得る("部品を加工するための、機械が持つ機能")
        for 種別 in ("主体", "省略actor", "主要部", "部分bool"):
            改変 = deepcopy(診断)
            読み = self.部分を得る(改変)
            if 種別 == "主体": 読み["明示連体主体"]["明示主体"]["核"]["原文"] = "機構"
            elif 種別 == "省略actor": 読み["目的"]["内部事象"][0]["明示主体"] = {"原文": "機械"}
            elif 種別 == "主要部": 読み["原役割証拠"]["主要部"]["開始"] += 1
            else: 読み["必要内容寄与"] = True
            with self.subTest(種別=種別), self.assertRaises(ValueError) as 捕捉:
                資料内容不足を読む(改変, 構造)
            self.assertNotIsInstance(捕捉.exception, 資料内容不足)
        全構造 = 構造を作る("機構は部品を加工するための機能の一つである。", "機構")
        成果 = _資料文章を照合(全構造, _文章(全構造), 形式=None, 共有保存=False)
        改変 = deepcopy(成果)
        self.寄与を得る(改変.データ["意味成果"])["必要内容寄与"] = False
        self.assertFalse(資料文章を検査(改変))
        旧 = deepcopy(成果); 旧.データ["意味成果"]["版"] = "HDS資料回答内容-v13"
        with patch("minidora.HDS運用.内容構成._文章", side_effect=AssertionError("旧意味再生成")):
            with self.assertRaisesRegex(ValueError, "意味版|失効|版"):
                資料文章の版を検査(旧)
        self.assertEqual(資料回答版, "HDS資料回答内容-v21")


if __name__ == "__main__":
    unittest.main()
