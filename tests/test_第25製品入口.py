"""完全リポジトリの実製品・実HDS・実能力factoryを通す。部分配布では明示SKIP。"""
from pathlib import Path
import unittest

完全構成 = (Path(__file__).resolve().parents[1] / 'src/minidora/製品版/監査.py').is_file()
登録 = '命題資料「例」を登録：P。PならばQ。'
問い = '資料「例」に基づいて「Q」を判断して、短く説明して'


@unittest.skipUnless(完全構成, '完全製品依存の未取得。部分構成を全製品PASSとは扱わない')
class 製品接続試験(unittest.TestCase):
    def setUp(self):
        # 完全構成がある環境ではimport失敗をSKIPしない。
        from minidora.製品版.製品チャット import 製品ミニドラ
        self.factory = 製品ミニドラ
        self.product = 製品ミニドラ()

    def send(self, text, session='default'):
        結果 = self.product.応答(text, セッションID=session)
        self.assertEqual(結果.状態, '合格', 結果.本文)
        return 結果

    def test_既定製品から有限命題へ到達(self):
        self.send(登録)
        結果 = self.send(問い)
        self.assertEqual(結果.経路, '汎用会話')
        self.assertIn('「支持」', 結果.本文)
        追跡 = 結果.メタデータ['汎用追跡']
        self.assertEqual(追跡['HDS原文'], 問い)
        self.assertTrue(追跡['監査改善']['合成監査整合'])
        self.assertEqual(追跡['監査改善']['要求']['問い'], 'Q')
        self.assertTrue(結果.参照)

    def test_既定製品から有限仮説と確認継続へ到達(self):
        self.send('仮説資料「仮」を登録：\n規則：AならばB\n候補：A')
        pending = self.product.応答('資料「仮」で仮説を検討して、短く説明して')
        self.assertEqual(pending.状態, '確認待ち')
        結果 = self.send('観測を「B」にして')
        self.assertIn('Aを仮定', 結果.本文)
        self.assertIn('事実ではありません', 結果.本文)

    def test_既定製品から有限介入へ到達(self):
        self.send('介入資料「因」を登録：\n外生：U=真\n構造：A=U\n構造：B=A')
        結果 = self.send('資料「因」で「B=偽」に介入した結果を比較して、短く説明して')
        self.assertIn('Bは真から偽', 結果.本文)
        self.assertIn('モデル内', 結果.本文)

    def test_従来の計算経路を保持(self):
        結果 = self.send('2+3')
        self.assertNotEqual(結果.経路, '汎用会話')
        self.assertIn('5', 結果.本文)

    def test_明示無効化と型検査(self):
        disabled = self.factory(監査改善=False)
        self.assertNotEqual(disabled.応答(登録).経路, '汎用会話')
        for value in (None, 0, 1, 'true'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.factory(監査改善=value)

    def test_セッション間の資料と焦点を隔離(self):
        self.send(登録, 'one'); self.send(問い, 'one')
        other = self.product.応答(問い, セッションID='two')
        self.assertNotEqual(other.経路, '汎用会話')
        self.assertNotIn('「支持」', other.本文)
        self.assertIn('「支持」', self.send(問い, 'one').本文)

    def test_別話題の短縮を旧命題成果へ結び付けない(self):
        self.send(登録); self.send(問い); self.send('2+3')
        結果 = self.product.応答('もう少し短く説明して')
        self.assertNotEqual(結果.経路, '汎用会話')
        self.assertNotIn('「支持」', 結果.本文)
        self.assertIn('「支持」', self.send(問い).本文)

    def test_保留した要求を模型核の自由回答へ落とさない(self):
        class 通過禁止:
            def 応答(self, text):
                raise AssertionError('改善会話の不成立から模型核へ透過してはいけない')
        self.product = self.factory(基礎ミニドラ=通過禁止())
        self.send(登録)
        結果 = self.product.応答('資料「例」から「Q」を判断して、根拠を捨てて')
        self.assertEqual(結果.状態, '保留')
        self.assertEqual(結果.経路, '汎用会話')

    def test_資料訂正と再説明失効を製品から実行(self):
        self.send(登録); self.send(問い)
        self.send('命題資料「例」を更新：P。')
        結果 = self.product.応答('詳しく説明して')
        self.assertEqual(結果.状態, '保留')
        self.assertIn('失効', 結果.本文)
        self.assertIn('「未確定」', self.send('もう一度').本文)

    def test_製品初期化後に旧資料を使わない(self):
        self.send(登録); self.send(問い)
        self.send('/初期化')
        結果 = self.product.応答(問い)
        self.assertNotIn('「支持」', 結果.本文)

    def test_汎用モードにも新能力が接続される(self):
        self.product = self.factory(汎用会話=True)
        self.send(登録)
        self.assertIn('「支持」', self.send(問い).本文)

    def test_述語別名を製品の現在目的へ適用する(self):
        self.send('命題資料「例」を登録：太郎はネコである。すべての猫は哺乳類である。')
        self.send('資料「例」から「太郎は哺乳類である」を判断して')
        結果 = self.send('述語別名を「ネコ/1=猫」にして')
        self.assertIn('「支持」', 結果.本文)
        self.assertIn('明示定義', 結果.本文)


if __name__ == '__main__':
    unittest.main()
