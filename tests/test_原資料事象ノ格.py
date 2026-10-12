"""原事象のノ格NP境界に限る有限開発対照。"""
import unittest
from minidora.会話字句 import 会話字句を観測
from minidora.HDS運用.資料作用射影 import _自己事象節


class 原資料事象ノ格試験(unittest.TestCase):
    def 読む(self, 前句, 起点=0):
        全句 = 前句 + "ための機能"
        字句 = 会話字句を観測(全句)
        self.assertFalse(any(字.未知語 for 字 in 字句))
        前字句 = [字 for 字 in 字句 if 字.終了 <= len(前句)]
        self.assertEqual("".join(字.表層 for 字 in 前字句), 前句)
        return _自己事象節(全句, 前字句, 起点)

    def test_ノ格目的語は全名詞句のまま原範囲を保持し主体を補わない(self):
        前句 = "機械の部品を検査する"
        読み = self.読む(前句, 23)
        self.assertEqual(len(読み), 1)
        事象 = 読み[0]
        self.assertEqual(事象["明示格"]["を"]["原文"], "機械の部品")
        self.assertEqual([事象["明示格"]["を"]["開始"], 事象["明示格"]["を"]["終了"]], [23, 23 + len("機械の部品")])
        self.assertEqual(事象["原文"], 前句)
        self.assertEqual(事象["用言原文"], "検査する")
        self.assertIsNone(事象["明示主体"])
        self.assertEqual(事象["主体状態"], "未明示")

    def test_主体と目的語それぞれのノ格を別の明示格へ保持する(self):
        読み = self.読む("工場の作業員が研究室の記録を確認する")
        事象 = 読み[0]
        self.assertEqual(set(事象["明示格"]), {"が", "を"})
        self.assertEqual(事象["明示主体"]["原文"], "工場の作業員")
        self.assertEqual(事象["明示格"]["を"]["原文"], "研究室の記録")
        self.assertEqual(事象["用言原文"], "確認する")
        self.assertEqual(事象["肯否"], "肯定")
        self.assertEqual(事象["時制"], "非過去")

    def test_ノ格以外の接続や否定照応を名詞句へ変換しない(self):
        for 前句 in ("機械の部品と記録を検査する", "機械の部品を検査しない", "それの部品を検査する"):
            with self.subTest(前句=前句):
                self.assertIsNone(self.読む(前句))

    def test_既存の単純目的語は同じ原格と未明示主体を保つ(self):
        事象 = self.読む("部品を検査する")[0]
        self.assertEqual(set(事象["明示格"]), {"を"})
        self.assertEqual(事象["明示格"]["を"]["原文"], "部品")
        self.assertIsNone(事象["明示主体"])
        self.assertEqual(事象["原文"], "部品を検査する")


if __name__ == "__main__":
    unittest.main()
