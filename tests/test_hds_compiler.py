import unittest

from minidora import HDSコンパイラ, ミニドラ, 要求, 実行状態


class HDSコンパイラ試験(unittest.TestCase):
    def test_同義表現を同一作用へ射影(self):
        c = HDSコンパイラ()
        for text in ("2と3を足して", "2足す3は？", "2と3の和は？"):
            ir = c.コンパイル(text)
            self.assertEqual(ir.実行核.作用, "加算")
            self.assertEqual(ir.初期状態["arg0"], 2)
            self.assertEqual(ir.初期状態["arg1"], 3)
            self.assertEqual(ir.残差, ())

    def test_HDS_IRが意味座標関係由来を保持(self):
        ir = HDSコンパイラ().コンパイル("2と3の和は？")
        types = {x.種別 for x in ir.座標}
        self.assertIn("対象.現在状態", types)
        self.assertIn("手段.作用", types)
        self.assertIn("目的.到達状態", types)
        self.assertTrue(ir.関係)
        self.assertTrue(ir.意味作用履歴)
        self.assertEqual(ir.保持状態, "FULL_FIELD_ACTIVE")

    def test_意味未分別は捨てず残差保持して保留(self):
        ir = HDSコンパイラ().コンパイル("1と2と3を足して")
        self.assertTrue(ir.残差)
        self.assertIsNone(ir.手順)
        result = ミニドラ().実行(要求("1と2と3を足して"))
        self.assertEqual(result.採否.状態, 実行状態.保留)
        self.assertIsNotNone(result.HDS_IR)
        self.assertTrue(result.HDS_IR.残差)

    def test_数式もHDS_IRを経由する(self):
        result = ミニドラ().実行(要求("2+3*4は？"))
        self.assertEqual(result.値, 14)
        self.assertIsNotNone(result.HDS_IR)
        self.assertEqual(result.HDS_IR.実行核.作用, "数式")
        self.assertTrue(result.HDS_IR.関係)

    def test_応答の同義語差を解消(self):
        body = ミニドラ()
        self.assertEqual(body.応答("2足す3は？"), "5です。")
        self.assertEqual(body.応答("2と3の和は？"), "5です。")


class HDS参照意味試験(unittest.TestCase):
    def test_意味スロットが同一で値が競合すると矛盾保留(self):
        from minidora import 参照記録, 固定参照供給器
        provider = 固定参照供給器((
            参照記録("a", "東京", "人口1400万人", "fixture://a", "固定", 意味=(("実体", "東京"), ("属性", "人口"), ("値", 1400), ("時点", 2026), ("範囲", "東京都"))),
            参照記録("b", "東京", "人口1300万人", "fixture://b", "固定", 意味=(("実体", "東京"), ("属性", "人口"), ("値", 1300), ("時点", 2026), ("範囲", "東京都"))),
        ))
        result = ミニドラ(provider).実行(要求("東京の人口は？"))
        self.assertEqual(result.採否.状態, 実行状態.保留)
        self.assertTrue(any(r.種別 == "contradiction" for r in result.HDS_IR.残差))

    def test_時点が違えば矛盾にしない(self):
        from minidora import 参照記録, 固定参照供給器
        provider = 固定参照供給器((
            参照記録("a", "東京", "人口1400万人", "fixture://a", "固定", 意味=(("実体", "東京"), ("属性", "人口"), ("値", 1400), ("時点", 2026), ("範囲", "東京都"))),
            参照記録("b", "東京", "人口1300万人", "fixture://b", "固定", 意味=(("実体", "東京"), ("属性", "人口"), ("値", 1300), ("時点", 2020), ("範囲", "東京都"))),
        ))
        result = ミニドラ(provider).実行(要求("東京の人口は？"))
        self.assertEqual(result.採否.状態, 実行状態.合格)
        self.assertFalse(any(r.種別 == "contradiction" for r in result.HDS_IR.残差))

    def test_意味なし文字列二件を勝手に矛盾扱いしない(self):
        from minidora import 参照記録, 固定参照供給器
        provider = 固定参照供給器((
            参照記録("a", "東京", "人口1400万人", "fixture://a", "固定"),
            参照記録("b", "東京", "人口1300万人", "fixture://b", "固定"),
        ))
        result = ミニドラ(provider).実行(要求("東京の人口は？"))
        self.assertNotEqual(result.採否.状態, 実行状態.失敗)
        self.assertFalse(any(r.種別 == "contradiction" for r in result.HDS_IR.残差))


if __name__ == "__main__":
    unittest.main()
