import unittest
from fractions import Fraction

from minidora import ミニドラ
from minidora.言語確率法則 import MINIDORA厳密言語模型


class MINIDORAv05統合試験(unittest.TestCase):
    def test_runtimeは厳密LM核と能力核を分離する(self):
        body = ミニドラ()
        self.assertIsInstance(body.言語模型核, MINIDORA厳密言語模型)
        self.assertIs(body.模型核, body.能力模型核)
        self.assertIsNot(body.言語模型核, body.能力模型核)
        self.assertTrue(body.言語模型監査().合格)

    def test_候補scoreはLM確率として流用されない(self):
        body = ミニドラ()
        probability = body.言語確率("任意")
        ability_result = body.言語評価("未知", ("候補A", "候補B"))
        self.assertIsInstance(probability, Fraction)
        self.assertGreater(probability, 0)
        self.assertTrue(hasattr(ability_result, "候補差"))

    def test_形成済み厳密LMを注入できる(self):
        lm = MINIDORA厳密言語模型.形成(("猫。",) * 10 + ("犬。",), 次数=2)
        body = ミニドラ(言語模型核_=lm)
        self.assertGreater(body.言語確率("猫。"), body.言語確率("犬。"))


if __name__ == "__main__":
    unittest.main()
