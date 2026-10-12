"""時間節の名詞化内部帰属。外部取得・製品・記事生成は実行しない。"""
from copy import deepcopy
import unittest
from test_原資料条件作用 import 読む
from minidora.HDS運用.資料作用射影 import 条件作用を結ぶ, _時間条件名詞化を読む
from minidora.HDS運用.資料回答 import _条件を結ぶ


class 時間条件名詞化試験(unittest.TestCase):
    布 = "布が乾くときにも変化が大きいことは、湿気のときと比べると少し見分けにくい。"
    装置 = "装置が作動する場合にも電力が必要なことが、停止のときと比べると少し理解しにくい。"

    def test_別二題材の内部時間節と名詞化と標準の範囲を保持(self):
        for 本文 in (self.布, self.装置):
            with self.subTest(本文=本文):
                記載 = 読む(本文)
                局所 = 記載[0]["資料作用"]["局所範囲"]
                self.assertIsNotNone(局所)
                self.assertEqual(局所["種別"], "時間条件の名詞化内部帰属")
                self.assertFalse(記載[0]["資料作用"]["条件候補"])
                self.assertEqual(局所["内部帰属証明"]["読了候補数"], 1)
                self.assertFalse(局所["内部帰属証明"]["外部条件競合除外"])
                self.assertEqual(局所["内部事象"][0]["主体状態"], "明示")
                self.assertEqual(局所["内部帰結"]["肯否"], "肯定")
                self.assertIsNone(局所["外側非動作証明"])
                self.assertTrue(局所["外側未読解"])
                for 項 in 局所["範囲"] + 局所["字句"]:
                    self.assertEqual(本文[項["開始"]:項["終了"]], 項.get("原文", 項.get("表層")))
                条件作用を結ぶ(記載)

    def test_係助詞はと格助詞がを区別し外側主体を補完しない(self):
        for 文, 標識, 種別 in ((self.布, "は", "外側係助詞"), (self.装置, "が", "外側格助詞")):
            with self.subTest(標識=標識):
                局所 = 読む(文)[0]["資料作用"]["局所範囲"]
                self.assertEqual(局所["外側標識"], 標識)
                self.assertTrue(any(項["種別"] == 種別 for 項 in 局所["範囲"]))
                self.assertFalse(局所["内部帰属証明"]["外側主体補完"])
                self.assertTrue(any(項["種別"] == "原資料外側作用未読解" for 項 in 読む(文)[0]["資料作用"]["残差"]))

    def test_接続詞と原起点を全文証拠に保持(self):
        本文 = "送信班は文書を送信する。一方、" + self.布
        局所 = 読む(本文)[1]["資料作用"]["局所範囲"]
        self.assertGreater(局所["開始"], 0)
        self.assertEqual(局所["範囲"][0]["種別"], "談話接続")
        self.assertEqual(局所["範囲"][0]["原文"], "一方、")
        for 項 in 局所["範囲"] + 局所["字句"]:
            self.assertEqual(本文[項["開始"]:項["終了"]], 項.get("原文", 項.get("表層")))

    def test_別条件の全競合で未読外側を非サ変記載にしない(self):
        記載 = 読む("送信班は文書を送信する。" + self.布 + "ただし休業日は送信しない。")
        self.assertEqual(記載[1]["資料作用"]["動作核候補"], [])
        # 旧関係が非サ変叙述を持っていても、未読外側の新型を除外しない。
        記載[1]["関係"]["叙述"] = {"対象": "布", "述部": "変化"}
        適用 = 条件作用を結ぶ(記載)[記載[-1]["ID"]]
        self.assertFalse(適用["確定"])
        self.assertIn(記載[1]["ID"], 適用["未読解競合"])
        self.assertFalse(any(項["記載ID"] == 記載[1]["ID"] for 項 in 適用["除外"]))

    def test_新局所は採用根拠に使わず独立記載へ時間条件を移さない(self):
        記載 = 読む(self.装置 + "担当者は機器を点検する。")
        with self.assertRaisesRegex(ValueError, "未読外側作用"):
            _条件を結ぶ(記載, {記載[0]["ID"]})
        self.assertEqual(_条件を結ぶ(記載, {記載[1]["ID"]}), {})

    def test_外側追加条件と広域引用撤回を局所帰属で消さない(self):
        for 文 in ("ただし" + self.布, "上記の" + self.布,
                self.布.replace("湿気のとき", "雨が降るとき"),
                self.布.replace("少し", "晴れる場合は少し"),
                self.布.replace("変化が大きい", "変化が大きいが誤りな"),
                "「" + self.布[:-1] + "」", self.布.replace("ときにも", "ときには、")):
            with self.subTest(文=文):
                self.assertIsNone(_時間条件名詞化を読む(文.rstrip("。"), 0))

    def test_未知と内部省略主体と複数名詞化を拒否(self):
        for 文 in (self.布.replace("布が", ""), self.布.replace("変化", "ヌャリミグ"),
                self.布.replace("ことは", "ことがあることは"),
                self.布.replace("大きい", "大きくない")):
            with self.subTest(文=文):
                self.assertIsNone(_時間条件名詞化を読む(文.rstrip("。"), 0))

    def test_不在形容詞を肯定帰結に置かず該当肯定枝を保全(self):
        for 述部 in ("ない", "無い"):
            with self.subTest(述部=述部):
                文 = self.布.replace("大きい", 述部).rstrip("。")
                self.assertIsNone(_時間条件名詞化を読む(文, 0))
        self.assertIsNotNone(_時間条件名詞化を読む(self.布.rstrip("。"), 0))

    def test_原文範囲と外側残差の改変を最終照合で拒否(self):
        記載 = 読む(self.装置)
        for 改変 in (lambda 型: 型["内部帰属証明"].update(外側主体補完=True),
                lambda 型: 型.update(外側未読解=None),
                lambda 型: 型["内部帰結"].update(原文="別の文")):
            with self.subTest(改変=改変):
                改 = deepcopy(記載)
                改変(改[0]["資料作用"]["局所範囲"])
                with self.assertRaises(ValueError):
                    条件作用を結ぶ(改)


if __name__ == "__main__":
    unittest.main()
