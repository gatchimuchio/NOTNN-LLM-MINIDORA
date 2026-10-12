"""談話付きの並列定義を全文・明示対象・原役割へ結ぶ有限開発対照。"""
from copy import deepcopy
import unittest
from unittest.mock import patch
from minidora.HDS運用.意味資料 import 資料意味を選ぶ
from minidora.HDS運用.資料回答 import (
    回答意味を構成, 資料内容不足, 資料内容不足を読む,
    _定義文を読む, _定義談話を読む, _並列目的定義を読む, 資料回答版,
)
from minidora.HDS運用.内容構成 import _文章, _資料文章を照合, 資料文章を検査, 資料文章の版を検査
from minidora.HDS運用.資料回答共有保存 import 資料回答意味を読む
from minidora.製品版.型 import 能力結果


def 構造を作る(本文, 対象):
    要求 = {"版": "HDS一般会話要求-v2", "対象": [], "主題": [対象], "操作": ["説明"],
            "形式": "文章", "範囲": "自動", "最大文字数": 24000, "問い": 対象 + "の定義",
            "比較対象": [], "観点": [], "詳細": "標準", "提示本文": "", "関係焦点": ["定義"], "肯否": "未指定"}
    return 資料意味を選ぶ({"人工原資料": 能力結果(True, 本文)}, 要求)


class 資料談話並列定義試験(unittest.TestCase):
    倉庫 = "より厳密に定義すれば、備蓄庫は器具の集まりであり、物資の保管/管理のために建設されたものである。"
    検査 = "検査機は部品の集まりであり、金属の加工、研磨のために設置された装置である。"
    成員 = "備蓄庫は物資の保管を確認するための、管理者が持つ機能の一つである。"

    def test_別二題材の全文分類目的受動と元明示主体を保持(self):
        for 文, 対象 in ((self.倉庫, "備蓄庫"), (self.検査, "検査機")):
            with self.subTest(対象=対象):
                意味 = 回答意味を構成(構造を作る(文, 対象))
                行 = next(行 for 行 in 意味["記載関係"] if 行["関係"]["定義"])
                定義 = 行["関係"]["定義"]; 型 = 定義["並列定義型"]
                self.assertEqual(定義["対象"], 対象)
                self.assertIsNone(行["関係"]["目的"])
                self.assertEqual(行["対応"]["原文"], 文)
                self.assertEqual(型["原述部"], 定義["述部"])
                self.assertEqual(型["受動修飾"]["態"], "受動")
                self.assertIsNone(型["受動修飾"]["行為者"])
                self.assertEqual(型["受動修飾"]["行為者状態"], "未明示")
                for 項 in [型["分類"], 型["結合"], 型["原目的列"], 型["目的標識"], 型["受動修飾"], 型["主要部"], *型["名詞列の原区間"]]:
                    self.assertEqual(型["原述部"][項["開始"]:項["終了"]], 項["原文"])
                self.assertEqual("".join(字["表層"] for 字 in 型["字句"]), 定義["述部"])
                self.assertEqual(意味["使用記載"], [行["ID"]])
                self.assertIn(型["原目的列"]["原文"], 意味["意味"]["命題"][0]["本文"])
                if 定義.get("定義談話"):
                    self.assertTrue(意味["意味"]["命題"][0]["本文"].startswith(定義["定義談話"]["原文"]))

    def test_具体定義共存でも成員多候補と未明示actorをFalseのまま保持(self):
        本文 = self.成員 + "\n# 構造\n" + self.倉庫
        意味 = 回答意味を構成(構造を作る(本文, "備蓄庫"))
        部分 = next(項["読解"] for 項 in 意味["演算"] if 項["種別"] == "成員定義の内容寄与")
        self.assertFalse(部分["必要内容寄与"])
        self.assertIsNone(部分["目的"]["内部事象"][0]["明示主体"])
        self.assertEqual(部分["目的"]["内部事象"][0]["明示格"]["を"]["原文"], "物資の保管")
        self.assertEqual(len(部分["用途係り先候補"]), 2)
        自己定義 = [行 for 行 in 意味["記載関係"] if 行["関係"]["定義"]]
        self.assertEqual(len(自己定義), 2)
        self.assertEqual(len(意味["使用記載"]), 2)
        for 行 in 自己定義:
            self.assertEqual(本文[行["対応"]["開始"]:行["対応"]["終了"]], 行["対応"]["原文"])

    def test_世界条件と仮定を精度談話として分離しない(self):
        for 接頭 in ("物資を保管すれば、", "仮に定義すれば、", "安全に定義すれば、"):
            with self.subTest(接頭=接頭):
                文 = 接頭 + self.検査
                self.assertIsNone(_定義談話を読む(文))
                定義 = _定義文を読む(文)
                self.assertFalse(定義 and 定義.get("並列定義型"))

    def test_否定未知引用別主体と後置条件を新並列型で通さない(self):
        述部 = "部品の集まりであり、金属の加工、研磨のために設置された装置"
        for 原 in (述部.replace("設置された", "設置されなかった"), 述部.replace("金属", "ヌャリミグ"),
                   "「" + 述部 + "」", 述部.replace("金属の加工、研磨", "作業者が金属を加工する"),
                   述部 + "ただし雨天の場合に限る", 述部.replace("加工、研磨", "加工、、研磨")):
            with self.subTest(原=原):
                self.assertIsNone(_並列目的定義を読む(原))

    def test_別対象具体定義と未知括弧注記で不足を完成にしない(self):
        for 本文 in (self.成員 + self.倉庫.replace("備蓄庫", "検査機"),
                     self.成員.replace("管理者", "管理者（ヌャリミグ）")):
            with self.subTest(本文=本文), self.assertRaises(資料内容不足) as 捕捉:
                回答意味を構成(構造を作る(本文, "備蓄庫"))
            診断 = 捕捉.exception.診断
            self.assertIn(self.成員.split("は", 1)[1].split("、", 1)[0], 診断["読解済み内容"][0]["本文"])
            self.assertEqual(診断["不足役割"][0]["対象"], ["備蓄庫"])

    def test_全源再導出と共有保存同値を確認し原役割と旧版改変を拒否(self):
        構造 = 構造を作る(self.倉庫, "備蓄庫")
        文章 = _文章(構造)
        成果 = _資料文章を照合(構造, 文章, 形式=None, 共有保存=False)
        共有 = _資料文章を照合(構造, 文章, 形式=None, 共有保存="HDS資料回答共有保存-v3")
        self.assertEqual(資料回答意味を読む(共有.データ["意味成果"], 意味版=資料回答版), 成果.データ["意味成果"])
        self.assertTrue(資料文章を検査(共有))
        for 種別 in ("actor", "range", "talk"):
            改変 = deepcopy(成果)
            定義 = next(行["関係"]["定義"] for 行 in 改変.データ["意味成果"]["記載関係"] if 行["関係"]["定義"])
            if 種別 == "actor": 定義["並列定義型"]["受動修飾"]["行為者"] = "備蓄庫"
            elif 種別 == "range": 定義["並列定義型"]["分類"]["終了"] += 1
            else: 定義["定義談話"]["原文"] = "仮に定義すれば、"
            with self.subTest(種別=種別):
                self.assertFalse(資料文章を検査(改変))
        旧 = deepcopy(成果); 旧.データ["意味成果"]["版"] = "HDS資料回答内容-v15"
        with patch("minidora.HDS運用.内容構成._文章", side_effect=AssertionError("旧v15再生成")):
            with self.assertRaises(ValueError): 資料文章の版を検査(旧)
        self.assertEqual(資料回答版, "HDS資料回答内容-v19")


if __name__ == "__main__":
    unittest.main()
