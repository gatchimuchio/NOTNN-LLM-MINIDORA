"""原記載を使わない実導出と、支持・反証がない未導出を区別する回帰試験。"""
from copy import deepcopy
import unittest
from minidora.資料読解 import 資料を読解
from minidora.監査改善接続 import 拡張命題を検討, 改善回答を構成, 改善回答を検査
from minidora.監査改善会話 import 監査改善会話セッション


def _要求(問い, 本文='R。'):
    return {'資料': [{'名前': '例', '本文': 本文}], '問い': 問い}


class 導出分類試験(unittest.TestCase):
    def test_原記載なしの含意導出を未導出と表示しない(self):
        for 詳細 in (True, False):
            with self.subTest(詳細=詳細):
                回答 = 改善回答を構成(拡張命題を検討(_要求('PならばP')), 詳細=詳細)
                self.assertEqual(回答['報告']['状態'], '支持')
                self.assertNotIn('未導出', [節['役割'] for 節 in 回答['節']])
                self.assertIn('原記載を使わず', 回答['本文'])
                self.assertIn('事実認定ではありません', 回答['本文'])
                self.assertTrue(改善回答を検査(回答))

    def test_全称と連言の論理導出でも原記載を補作しない(self):
        for 問い in ('すべての猫は猫である', 'PかつQならばP'):
            with self.subTest(問い=問い):
                回答 = 改善回答を構成(拡張命題を検討(_要求(問い)))
                self.assertEqual(回答['報告']['状態'], '支持')
                self.assertIn('原記載を使わず', 回答['本文'])
                self.assertFalse(any(節['役割'] == '使用記載' for 節 in 回答['節']))
                self.assertIn('局所仮定', [節['役割'] for 節 in 回答['節']])

    def test_真の未導出は未確定と未導出を保持(self):
        回答 = 改善回答を構成(拡張命題を検討(_要求('P')))
        self.assertEqual(回答['報告']['状態'], '未確定')
        self.assertIn('未導出', [節['役割'] for 節 in 回答['節']])
        self.assertNotIn('原記載を使わず', 回答['本文'])

    def test_原記載からの支持反証矛盾を論理だけの結論にしない(self):
        for 本文, 判定 in (('P。', '支持'), ('否定(P)。', '反証'), ('P。否定(P)。', '矛盾')):
            with self.subTest(判定=判定):
                回答 = 改善回答を構成(拡張命題を検討(_要求('P', 本文)))
                self.assertEqual(回答['報告']['状態'], 判定)
                self.assertIn('使用記載', [節['役割'] for 節 in 回答['節']])
                self.assertNotIn('原記載を使わず', 回答['本文'])

    def test_部分読解でも論理導出と文書根拠を区別(self):
        for 詳細 in (True, False):
            with self.subTest(詳細=詳細):
                回答 = 改善回答を構成(資料を読解(_要求('PならばP', 'R。図を参照。')), 詳細=詳細)
                self.assertEqual(回答['報告']['局所判定']['判定'], '支持')
                self.assertEqual(回答['報告']['選択記載'], [])
                self.assertIn('原記載を使わず', 回答['本文'])
                self.assertIn('未解釈1記載', 回答['本文'])
                self.assertIn('資料全体の判定ではありません', 回答['本文'])

    def test_説明分類を改変した回答は再検査で拒否(self):
        回答 = 改善回答を構成(拡張命題を検討(_要求('PならばP')))
        改変 = deepcopy(回答)
        節 = next(節 for 節 in 改変['節'] if 節['役割'] == '導出範囲')
        節['本文'] = '資料により実世界の事実として認定しました。'
        改変['本文'] = '\n'.join(節['本文'] for 節 in 改変['節'])
        self.assertFalse(改善回答を検査(改変))

    def test_会話の短縮と保存復元でも分類を保持(self):
        会話 = 監査改善会話セッション('説明分類')
        self.assertEqual(会話.応答('命題資料「例」を登録：R。').状態, '合格')
        結果 = 会話.応答('資料「例」から「PならばP」を判定して')
        self.assertEqual(結果.状態, '合格')
        self.assertIn('原記載を使わず', 結果.本文)
        短縮 = 会話.応答('短く説明して')
        self.assertEqual(短縮.状態, '合格')
        self.assertIn('原記載を使わず', 短縮.本文)
        復元 = 監査改善会話セッション.復元(会話.保存文字列(), 期待セッションID='説明分類')
        self.assertEqual(復元.保存文字列(), 会話.保存文字列())
        self.assertIn('原記載を使わず', 復元.応答('詳しく説明して').本文)

    def test_既定製品で実HDSから論理導出を説明(self):
        from minidora.製品版.製品チャット import 製品ミニドラ
        製品 = 製品ミニドラ()
        self.assertEqual(製品.応答('命題資料「例」を登録：R。').状態, '合格')
        for 入力 in ('資料「例」から「PならばP」を判定して', '短く説明して'):
            結果 = 製品.応答(入力)
            self.assertEqual(結果.状態, '合格', 結果.本文)
            self.assertEqual(結果.経路, '汎用会話')
            self.assertIn('原記載を使わず', 結果.本文)

if __name__ == '__main__':
    unittest.main()
