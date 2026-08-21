import unittest

from minidora import ミニドラ, 要求, 参照記録, 固定参照供給器, 実行状態


class 自然言語閉路試験(unittest.TestCase):
    def test_手順なし要求を実行できる(self):
        result = ミニドラ().実行(要求("2+2は？"))
        self.assertEqual(result.値, 4)
        self.assertEqual(result.採否.状態, 実行状態.合格)
        self.assertEqual(result.言語計画, "算術")

    def test_自然言語応答は演算優先順位を保持する(self):
        self.assertEqual(ミニドラ().応答("2+3*4は？"), "14です。")

    def test_括弧付き数式を実行できる(self):
        self.assertEqual(ミニドラ().応答("(2+3)*4は？"), "20です。")

    def test_日本語算術をPへ縮約する(self):
        self.assertEqual(ミニドラ().応答("10から3を引いて"), "7です。")

    def test_比較を自然言語で返す(self):
        self.assertEqual(ミニドラ().応答("10 > 3 ?"), "はい。")

    def test_文字数を数えられる(self):
        self.assertEqual(ミニドラ().応答("「ミニドラ」の文字数を数えて"), "4です。")

    def test_日本語空白なしでも参照できる(self):
        provider = 固定参照供給器((
            参照記録("1", "東京", "日本の首都", "fixture://1", "固定"),
        ))
        self.assertEqual(ミニドラ(provider).応答("東京の首都は？"), "日本の首都。")

    def test_未知は推測せず停止する(self):
        body = ミニドラ(固定参照供給器(()))
        result = body.実行(要求("未知の対象は？"))
        self.assertIsNone(result.値)
        self.assertEqual(result.採否.状態, 実行状態.保留)
        self.assertEqual(body.応答("未知の対象は？"), "分かりません。確認できる根拠がありません。")

    def test_同一入力は決定的に同一応答となる(self):
        body = ミニドラ()
        self.assertEqual({body.応答("123+456は？") for _ in range(100)}, {"579です。"})

    def test_不正演算はクラッシュせず失敗として閉じる(self):
        result = ミニドラ().実行(要求("10/0は？"))
        self.assertEqual(result.採否.状態, 実行状態.失敗)
        self.assertEqual(ミニドラ().応答("10/0は？"), "処理できません。")


if __name__ == "__main__":
    unittest.main()
