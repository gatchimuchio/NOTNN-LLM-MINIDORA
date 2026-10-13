"""人工二題材だけの局所時間事象・原外側・不足診断有限群。"""
from copy import deepcopy
import unittest

from minidora.HDS運用.意味資料 import 資料意味を選ぶ
from minidora.HDS運用.資料回答 import (
    記載関係を読む, 回答意味を構成, 資料内容不足, 資料内容不足を読む, _条件を結ぶ,
)
from minidora.HDS運用.資料作用射影 import (
    _時間事象名詞化を読む, _自己事象節, 条件作用を結ぶ, 資料作用成果, 資料作用版,
)
from minidora.会話字句 import 会話字句を観測
from minidora.製品版.型 import 能力結果


明示 = "装置が停止するときに操作者が端末から信号を受信することは、以下の試験により確認できる。"
省略 = "部品が変形するときに外部から力を受けることは、以下の測定により確認できる。"


def 構造(本文, 対象="装置", 焦点="停止する", *, 資料=None):
    要求 = {"版": "HDS一般会話要求-v2", "対象": [], "主題": [対象], "操作": ["理由"],
        "形式": "文章", "範囲": "自動", "最大文字数": 24000, "問い": "なぜ" + 対象 + "が" + 焦点 + "のですか",
        "比較対象": [], "観点": [], "詳細": "標準", "提示本文": "", "関係焦点": [焦点], "肯否": "未指定"}
    return 資料意味を選ぶ(資料 or {"人工原資料": 能力結果(True, 本文)}, 要求)


def 読む(本文):
    return 記載関係を読む(構造(本文))


class 原資料時間事象名詞化試験(unittest.TestCase):
    def test_B01_二題材の原事象と格範囲だけを保持(self):
        for 本文 in (明示, 省略):
            with self.subTest(本文=本文):
                群 = 読む(本文); 型 = 群[0]["資料作用"]["局所範囲"]
                self.assertEqual(型["種別"], "時間事象の名詞化内部帰属")
                self.assertEqual(資料作用版, "HDS原資料作用-v10")
                self.assertFalse(型["時間事象帰属証明"]["因果認定"])
                self.assertFalse(型["時間事象帰属証明"]["外部条件競合除外"])
                self.assertFalse(群[0]["資料作用"]["条件候補"])
                self.assertIsNone(群[0]["命題"])
                self.assertTrue(all(x is None for x in 群[0]["関係"].values()))
                self.assertEqual(型["内部事象"][1]["明示格"]["から"]["標識"], "から")
                for 項 in 型["字句"] + 型["範囲"]:
                    self.assertEqual(本文[項["開始"]:項["終了"]], 項.get("原文", 項.get("表層")))
                条件作用を結ぶ(群)

    def test_B02_省略主体と原可能用言と以下を補完しない(self):
        群 = 読む(省略); 型 = 群[0]["資料作用"]["局所範囲"]
        self.assertIsNone(型["内部帰結"]["明示主体"])
        self.assertEqual(型["内部帰結"]["辞書形"], "受ける")
        self.assertEqual(型["外側原述部"]["原文"], "確認できる")
        self.assertEqual(型["外側原述部"]["様相"], "未認定")
        self.assertFalse(型["外側原述部"]["基底動詞推測"])
        self.assertEqual(型["未解決参照"]["状態"], "未形成")
        self.assertIsNone(型["未解決参照"]["対応記載ID"])
        self.assertIsNone(型["外側主体"])
        self.assertIsNone(型["外側非動作証明"])
        self.assertEqual({項["種別"] for 項 in 群[0]["資料作用"]["残差"]},
            {"時間事象内部主体未明示", "原資料外側作用未読解", "原資料前方参照未形成"})
        self.assertEqual(資料作用成果(群)["版"], "HDS原資料作用-v10")

    def test_B03_引用未知多重否定と外側条件を局所化しない(self):
        for 本文 in ("「" + 明示[:-1] + "」", 明示.replace("装置", "ヌャリミグ"),
            明示.replace("ことは", "ことがあることは"), 明示.replace("受信する", "受信しない"),
            "ただし" + 明示, 明示.replace("以下の", "上記の"), 明示.replace("確認できる", "確認できない")):
            with self.subTest(本文=本文):
                self.assertIsNone(_時間事象名詞化を読む(本文.rstrip("。"), 0))

    def test_B04_明示原格追加は新callerのみで旧既定を維持(self):
        文 = "操作者が端末から信号を受信する"
        字句 = 会話字句を観測(文 + "こと")[:-1]
        self.assertIsNone(_自己事象節(文, 字句, 0))
        self.assertIsNotNone(_自己事象節(文, 字句, 0, 起点格=True))
        文 = "操作者が信号を受信する"; 字句 = 会話字句を観測(文 + "こと")[:-1]
        self.assertIsNotNone(_自己事象節(文, 字句, 0))
        self.assertEqual(_自己事象節(文, 字句, 0), _自己事象節(文, 字句, 0, 起点格=True))

    def test_B05_以下は後続や別ownerがあっても未解決(self):
        for 本文 in (明示, 明示 + "試験は実施しない。", 明示 + "試験は信号を記録する。試験は結果を報告する。"):
            with self.subTest(本文=本文):
                型 = 読む(本文)[0]["資料作用"]["局所範囲"]
                self.assertIsNone(型["未解決参照"]["対応記載ID"])
                self.assertFalse(型["時間事象帰属証明"]["確認実施認定"])
        束 = 構造(明示, 資料={"第一": 能力結果(True, 明示), "別所有": 能力結果(True, "試験は信号を記録する。")})
        self.assertIsNone(記載関係を読む(束)[0]["資料作用"]["局所範囲"]["未解決参照"]["対応記載ID"])

    def test_B06_外側未読採用禁止と競合は維持(self):
        群 = 読む("送信班は文書を送信する。" + 明示 + "ただし休業日は送信しない。")
        with self.assertRaisesRegex(ValueError, "未読外側作用"):
            _条件を結ぶ(群, {群[1]["ID"]})
        適用 = 条件作用を結ぶ(群)[群[-1]["ID"]]
        self.assertFalse(適用["確定"])
        self.assertIn(群[1]["ID"], 適用["未読解競合"])

    def test_B07_全HDS族とownerと版と原範囲の改変拒否(self):
        群 = 読む(省略)
        for 列 in ("座標", "関係", "残差"):
            for 操作 in ("欠落", "余分", "改変"):
                with self.subTest(列=列, 操作=操作):
                    改 = deepcopy(群); 値 = 改[0]["資料作用"][列]
                    if 操作 == "欠落": 値.pop()
                    elif 操作 == "余分": 値.append(deepcopy(値[-1]))
                    else: 値[-1]["由来" if 列 != "残差" else "理由"] = "改変"
                    with self.assertRaises(ValueError): 条件作用を結ぶ(改)
        for 改変 in (lambda x: x["原資料"].update(本文指紋="0" * 64),
            lambda x: x.update(版="HDS原資料作用-v8"),
            lambda x: x["局所範囲"]["時間事象帰属証明"].update(因果認定=True),
            lambda x: x["意味作用"].update(変換="改変")):
            with self.subTest(改変=改変):
                改 = deepcopy(群); 改変(改[0]["資料作用"])
                with self.assertRaises(ValueError): 条件作用を結ぶ(改)

    def test_B08_局所内容と全残差を不足診断へ原支持で接続(self):
        for 本文, 対象, 焦点 in ((明示, "装置", "停止する"), (省略, "部品", "変形する")):
            with self.subTest(対象=対象):
                束 = 構造(本文, 対象, 焦点)
                with self.assertRaises(資料内容不足) as 捕捉: 回答意味を構成(束)
                診断 = 捕捉.exception.診断
                self.assertEqual(診断["意味版"], "HDS資料回答内容-v21")
                self.assertTrue(診断["読解済み内容"])
                self.assertIn("名詞化の内側で結んで", 診断["読解済み内容"][0]["本文"])
                self.assertTrue(診断["実支持"])
                self.assertTrue(診断["局所支持"][0]["残差"])
                self.assertEqual(資料内容不足を読む(診断, 束), 診断)
                改 = deepcopy(診断); 改["局所支持"][0]["型"]["外側未読解"] = None
                with self.assertRaises(ValueError): 資料内容不足を読む(改, 束)
        for 対象, 焦点 in (("別装置", "停止する"), ("装置", "送信する"), ("部品", "受ける")):
            with self.subTest(対象=対象, 焦点=焦点):
                with self.assertRaises(ValueError) as 捕捉: 回答意味を構成(構造(省略 if 対象 == "部品" else 明示, 対象, 焦点))
                self.assertNotIsInstance(捕捉.exception, 資料内容不足)


if __name__ == "__main__":
    unittest.main()
