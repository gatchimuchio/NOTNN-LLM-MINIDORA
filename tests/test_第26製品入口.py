"""通常製品・実HDS・全能力factoryでの本文読解。未取得の部分構成は明示SKIP。"""
from pathlib import Path
import unittest

完全構成 = (Path(__file__).resolve().parents[1] / 'src/minidora/製品版/監査.py').is_file()
登録 = '本文資料「文」を登録：太郎は猫です。図を参照。すべての猫は哺乳類です。'
依頼 = '資料「文」から「太郎は哺乳類である」の根拠を説明して'


@unittest.skipUnless(完全構成, '完全製品依存未取得。完全リポジトリでは実行必須')
class 読解製品試験(unittest.TestCase):
    def setUp(self):
        from minidora.製品版.製品チャット import 製品ミニドラ
        self.factory = 製品ミニドラ
        self.p = 製品ミニドラ()
    def ok(self, text, session='default'):
        r = self.p.応答(text, セッションID=session)
        self.assertEqual(r.状態, '合格', r.本文)
        return r
    def test_既定入口から実HDSと採用境界へ接続(self):
        self.ok(登録); r = self.ok(依頼)
        self.assertEqual(r.経路, '汎用会話')
        trace = r.メタデータ['汎用追跡']
        self.assertEqual(trace['HDS原文'], 依頼)
        self.assertTrue(trace['監査改善']['合成監査整合'])
        self.assertEqual(len(trace['監査改善']['工程作用']), 3)
        self.assertIn('資料全体の判定ではありません', r.本文)
        self.assertIn('「支持」', r.本文)
        self.assertTrue(r.参照)
    def test_要約と短縮で未解釈の境界を保持(self):
        self.ok(登録); r = self.ok('資料「文」を要約して')
        self.assertIn('未解釈1記載', r.本文)
        self.assertIn('図を参照', self.ok('詳しく説明して').本文)
        self.assertIn('未解釈1記載', self.ok('短く説明して').本文)
    def test_資料更新で再説明を拒否して再検討(self):
        self.ok(登録); self.ok(依頼)
        self.ok('本文資料「文」を更新：太郎は猫です。')
        self.assertEqual(self.p.応答('短く説明して').状態, '保留')
        self.assertIn('「未確定」', self.ok('もう一度').本文)
    def test_普通の計算と別話題を維持(self):
        self.ok(登録); self.ok(依頼)
        self.assertNotEqual(self.ok('2+3').経路, '汎用会話')
        self.assertNotEqual(self.p.応答('短く説明して').経路, '汎用会話')
        self.assertIn('「支持」', self.ok(依頼).本文)
    def test_別セッションに資料を流用しない(self):
        self.ok(登録, 'one'); self.ok(依頼, 'one')
        other = self.p.応答(依頼, セッションID='two')
        self.assertNotEqual(other.経路, '汎用会話')
        self.assertNotIn('「支持」', other.本文)
    def test_不明条件をCoreへ逃がさない(self):
        class 禁止Core:
            def 応答(self, text): raise AssertionError('Core透過は禁止')
        self.p = self.factory(基礎ミニドラ=禁止Core())
        self.ok(登録)
        r = self.p.応答('資料「文」を要約して、根拠は隠して')
        self.assertEqual(r.状態, '保留')
        self.assertEqual(r.経路, '汎用会話')
    def test_初期化して旧成果へ戻らない(self):
        self.ok(登録); self.ok(依頼); self.ok('/初期化')
        self.assertNotEqual(self.p.応答(依頼).経路, '汎用会話')
    def test_無効化した経路を再開しない(self):
        self.p = self.factory(監査改善=False)
        self.assertNotEqual(self.p.応答(登録).経路, '汎用会話')
    def test_汎用会話モードと能力案内(self):
        self.p = self.factory(汎用会話=True)
        self.ok(登録); self.assertIn('「支持」', self.ok(依頼).本文)
        self.assertIn('本文読解', self.ok('できることを教えて').本文)

if __name__ == '__main__': unittest.main()
