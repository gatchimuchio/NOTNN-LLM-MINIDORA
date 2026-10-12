"""辞書の名詞区分と原連体境界を保持する。固有名から一般概念を補わない。"""
from copy import deepcopy
import unittest

from minidora.HDS運用.資料回答 import _種別を読む, 記載関係を読む
from minidora.HDS運用.意味資料 import 資料意味を選ぶ
from minidora.HDS運用.内容構成 import _文章, 資料文章を照合, 資料文章を検査
from minidora.製品版.型 import 能力結果
from test_資料定義種別 import 定義要求
from minidora.会話字句 import 会話字句を観測


class 資料定義固有主要部試験(unittest.TestCase):
    def test_既知の固有名と普通名詞連接を原主要部として保持する(self):
        for 文, 主要部 in (("人を運ぶ日本航空", "日本航空"),
                           ("客が待つ東京駅", "東京駅")):
            with self.subTest(文=文):
                読み = _種別を読む(文)
                self.assertEqual(読み["種別"], 主要部)
                証拠 = 読み["連体型証拠"]
                self.assertEqual(文[slice(*証拠["主要部範囲"])], 主要部)
                self.assertEqual("".join(項["表層"] for 項 in 証拠["字句"]), 文)
                self.assertTrue(any(項["品詞"][:2] == ["名詞", "固有名詞"]
                                    for 項 in 証拠["字句"]
                                    if 項["開始"] >= 証拠["主要部範囲"][0]))
                self.assertFalse(any(項["未知語"] for 項 in 証拠["字句"]))

    def test_裸の名詞と連用形と未知語と代名詞を新連体型にしない(self):
        self.assertTrue(any(項.未知語 for 項 in 会話字句を観測("人を運ぶヌャリミグ")))
        for 文 in ("日本航空", "人を運び日本航空", "人を運ぶヌャリミグ", "人を運ぶ彼"):
            with self.subTest(文=文):
                self.assertIsNone(_種別を読む(文))

    def test_所属の後の同明示対象の具体名詞定義を失わない(self):
        本文 = "案内先は施設の一つである。\n\n案内先は客が待つ東京駅である。"
        構造 = 資料意味を選ぶ({"人工資料": 能力結果(True, 本文)}, 定義要求("案内先"))
        成果 = 資料文章を照合(構造, _文章(構造))
        self.assertTrue(資料文章を検査(成果))
        self.assertIn("施設の一つ", 成果.本文)
        self.assertIn("客が待つ東京駅", 成果.本文)
        self.assertNotIn("種別・所属関係です", 成果.本文)
        記載 = 記載関係を読む(構造)
        行 = next(行 for 行 in 記載 if "東京駅" in 行["対応"]["原文"])
        self.assertEqual(行["関係"]["定義"]["種別"], "東京駅")
        self.assertEqual(本文[行["対応"]["開始"]:行["対応"]["終了"]], 行["対応"]["原文"])

    def test_原語の品詞証拠を後付けで普通名詞へ変える成果を拒否する(self):
        本文 = "案内先は客が待つ東京駅である。"
        構造 = 資料意味を選ぶ({"人工資料": 能力結果(True, 本文)}, 定義要求("案内先"))
        成果 = 資料文章を照合(構造, _文章(構造))
        改変 = deepcopy(成果)
        行 = next(行 for 行 in 改変.データ["意味成果"]["記載関係"] if 行["関係"]["定義"])
        証拠 = 行["関係"]["定義"]["連体型証拠"]
        字 = next(項 for 項 in 証拠["字句"] if 項["開始"] >= 証拠["主要部範囲"][0]
                  and 項["品詞"][:2] == ["名詞", "固有名詞"])
        字["品詞"][1] = "普通名詞"
        self.assertFalse(資料文章を検査(改変))


if __name__ == "__main__":
    unittest.main()
