"""自己述定を原主体・推量の限定として保持する資料内容接続。"""
from copy import deepcopy
import unittest

from test_資料内容不足 import 構造を作る
from minidora.HDS運用.資料回答 import 回答意味を構成, 記載関係を読む, _根拠主述
from minidora.HDS運用.意味資料 import 資料意味を選ぶ
from minidora.製品版.型 import 能力結果


class 自己述定内容接続試験(unittest.TestCase):
    定義 = "装置とは金属を削る機械である。"
    推量 = "ただし装置は、恐らく機器の記録に違いない。"

    def test_同主体の推量を原強度と支持範囲で保持(self):
        本文 = self.定義 + self.推量
        意味 = 回答意味を構成(構造を作る(本文, "装置"))
        局所行 = 意味["記載関係"][1]
        self.assertIsNone(局所行["命題"])
        self.assertTrue(all(値 is None for 値 in 局所行["関係"].values()))
        self.assertEqual(局所行["資料作用"]["局所範囲"]["内容状態"], "推定")
        限定 = next(項 for 項 in 意味["意味"]["命題"] if 項["種別"] == "限定記載")
        self.assertEqual(限定["本文"], "原資料の推量を含む記載：" + self.推量)
        self.assertIn(局所行["ID"], 限定["根拠"])
        定義命題 = next(項 for 項 in 意味["意味"]["命題"] if 項["種別"] == "定義")
        self.assertIn(限定["本文"], 定義命題["条件"])
        for 範囲 in 局所行["資料作用"]["局所範囲"]["モダリティ"]["範囲"]:
            self.assertEqual(本文[範囲["開始"]:範囲["終了"]], 範囲["原文"])

    def test_別主体の推量を対象の適用条件へ移植しない(self):
        別推量 = "ただし機器は、恐らく装置の記録に違いない。"
        意味 = 回答意味を構成(構造を作る(self.定義 + 別推量, "装置"))
        self.assertTrue(意味["記載関係"][1]["資料作用"]["局所範囲"]["自己述定証明"])
        self.assertIn(意味["記載関係"][1]["ID"], 意味["未使用記載"])
        self.assertFalse(any(別推量 in 項["本文"] for 項 in 意味["意味"]["命題"]))

    def test_存在分類は原主体の分類記載として内部主体未明示を保持(self):
        分類 = "装置が停止する場合は、故障して停止する場合と点検して停止する場合がある。"
        意味 = 回答意味を構成(構造を作る(self.定義 + 分類, "装置"))
        行 = 意味["記載関係"][1]
        self.assertIsNone(行["命題"])
        self.assertTrue(all(項["明示主体"] is None for 項 in 行["資料作用"]["局所範囲"]["内部事象"]))
        self.assertTrue(any(項["本文"] == "原資料の分類記載：" + 分類 for 項 in 意味["意味"]["命題"]))
        self.assertEqual(len([項 for 項 in 行["資料作用"]["残差"] if 項["種別"] == "自己述定内部主体未明示"]), 4)

    def test_自己分類だけから理由を構成しない(self):
        分類 = "装置が停止する場合は、故障して停止する場合と点検して停止する場合がある。"
        雛形 = 構造を作る(分類, "装置")
        要求 = deepcopy(雛形["要求"])
        要求.update({"操作": ["理由"], "問い": "装置が停止するのはなぜですか", "関係焦点": ["停止する"], "肯否": "肯定"})
        構造 = 資料意味を選ぶ({"分類原資料": 能力結果(True, 分類)}, 要求)
        with self.assertRaisesRegex(ValueError, "理由|因果"):
            回答意味を構成(構造)

    def test_自己述定から後続の省略主体を補完しない(self):
        記載 = 記載関係を読む(構造を作る(self.推量 + "それは停止する。", "装置"))
        self.assertIsNone(記載[0]["先行主語"])
        self.assertIsNone(記載[1]["先行主語"])
        self.assertIsNone(_根拠主述(記載[1]))

    def test_同主体の誤り記載を局所型だからと無視しない(self):
        with self.assertRaisesRegex(ValueError, "誤り|撤回|訂正"):
            回答意味を構成(構造を作る(self.定義 + "ただし装置は、恐らく誤りに違いない。", "装置"))


if __name__ == "__main__":
    unittest.main()
