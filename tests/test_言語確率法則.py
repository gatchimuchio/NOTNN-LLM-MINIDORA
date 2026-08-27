import json
import unittest
from fractions import Fraction

from minidora.言語確率法則 import (
    EOS記号,
    UNK記号,
    MINIDORA厳密言語模型,
    最小厳密言語模型,
)


class 厳密言語模型試験(unittest.TestCase):
    def test_各条件分布は厳密に1へ正規化(self):
        lm = MINIDORA厳密言語模型.形成(("猫。", "猫です。", "犬。"), 次数=3)
        for prefix in ("", "猫", "猫で", "未知"):
            dist = lm.次記号分布(prefix)
            self.assertEqual(sum(dist.辞書().values(), Fraction(0, 1)), Fraction(1, 1))
            self.assertGreater(dist.確率_of(EOS記号), 0)

    def test_系列確率はchain_ruleとEOSで正(self):
        lm = MINIDORA厳密言語模型.形成(("猫。", "猫です。", "犬。"), 次数=3)
        self.assertGreater(lm.系列確率("猫。"), 0)
        self.assertGreater(lm.系列確率("未観測文字列"), 0)

    def test_観測系列は対応する異系列より高くなり得る(self):
        lm = MINIDORA厳密言語模型.形成(("猫。",) * 20 + ("犬。",), 次数=2)
        self.assertGreater(lm.系列確率("猫。"), lm.系列確率("犬。"))

    def test_EOS下限が正で可変長質量が閉じる(self):
        lm = MINIDORA厳密言語模型.形成(("abc", "abd", "ab"), 次数=4)
        audit = lm.正規化監査()
        self.assertTrue(audit.合格, audit.理由)
        self.assertGreater(audit.終端確率下限, 0)

    def test_形成順序で模型状態が変わらない(self):
        a = MINIDORA厳密言語模型.形成(("甲乙", "乙丙", "甲丙"), 次数=3)
        b = MINIDORA厳密言語模型.形成(("甲丙", "甲乙", "乙丙"), 次数=3)
        self.assertEqual(a.状態sha256, b.状態sha256)
        self.assertEqual(a.辞書化(), b.辞書化())

    def test_模型状態はJSON往復で同一(self):
        lm = MINIDORA厳密言語模型.形成(("日本語。", "ミニドラ。"), 次数=3)
        payload = json.loads(json.dumps(lm.辞書化(), ensure_ascii=False))
        restored = MINIDORA厳密言語模型.復元(payload)
        self.assertEqual(restored.状態sha256, lm.状態sha256)
        self.assertEqual(restored.系列確率("日本語。"), lm.系列確率("日本語。"))

    def test_最小模型も厳密LM法則を持つ(self):
        lm = 最小厳密言語模型()
        dist = lm.次記号分布("任意")
        self.assertEqual(set(dist.辞書()), {UNK記号, EOS記号})
        self.assertEqual(sum(dist.辞書().values(), Fraction(0, 1)), Fraction(1, 1))
        self.assertTrue(lm.正規化監査().合格)

    def test_決定論でsampling依存を持たない(self):
        lm = MINIDORA厳密言語模型.形成(("ああ", "あい"), 次数=2)
        self.assertEqual(lm.最尤次記号("あ"), lm.最尤次記号("あ"))


if __name__ == "__main__":
    unittest.main()
