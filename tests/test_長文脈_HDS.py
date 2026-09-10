"""実公開HDS Compiler・既存会話セッションまで通す接続試験。"""
import unittest

from minidora.長文脈管理 import 長文脈庫, 文脈登録, 文脈選択要求
from minidora.文脈要求 import 文脈付き要求セッション
from minidora.製品版.型 import 能力結果, 参照資料


class 長文脈HDS接続試験(unittest.TestCase):
    def setUp(self):
        self.a = 長文脈庫('long-hds')
        value = 能力結果(True, '売上は731です。費用は75です。利益は45です。',
                        参照=(参照資料('元', '人工資料', '試験', 本文='売上は731です。費用は75です。利益は45です。'),))
        self.a.更新(self.a.起点(), (文脈登録('原文', value),
                     *(文脈登録(f'雑談:{i}', 能力結果(True, '関係のない話題。' * 20)) for i in range(100))))
        self.session = 文脈付き要求セッション('long-hds')

    def material(self):
        selected = self.a.選択(文脈選択要求(('原文',), 直近件数=0, 最大バイト数=4096))
        return selected, self.a.資料化(selected)

    def test_長文脈の原文選択から実HDSと抽出へ(self):
        selected, material = self.material()
        result = self.session.応答('本文から数字を抽出して', {'本文': material})
        self.assertTrue(result.成立, result.理由)
        self.assertEqual(result.出力[0][1].本文, '731、75、45')
        self.assertEqual(len(selected.省略ID), 100)
        self.assertEqual(result.出力[0][1].参照, material.参照)

    def test_抽出結果を既存の次ターン照応へ使う(self):
        _, material = self.material()
        first = self.session.応答('本文を1行で要約して', {'本文': material})
        self.assertTrue(first.成立, first.理由)
        second = self.session.応答('それから数字を抽出して')
        self.assertTrue(second.成立, second.理由)
        self.assertEqual(second.出力[0][1].本文, '731')

    def test_実HDSの成果を長文脈へ登録して再参照(self):
        selected, material = self.material()
        result = self.session.応答('本文から数字を抽出して', {'本文': material})
        self.assertTrue(result.成立, result.理由)
        self.a.成果登録(selected, '成果', result.出力[0][1])
        selected = self.a.選択(文脈選択要求(('成果',), 直近件数=0))
        self.assertEqual(selected.選択ID, ('原文', '成果'))
        self.assertEqual(self.a.原記録('成果')['依存'], ['原文'])

    def test_復元後も実Compiler経路が成立する(self):
        self.a = 長文脈庫.復元(self.a.保存文字列())
        _, material = self.material()
        result = self.session.応答('本文から数字を抽出して', {'本文': material})
        self.assertTrue(result.成立, result.理由)
        self.assertEqual(result.出力[0][1].本文, '731、75、45')

    def test_実HDS成果の依存元を改訂すると現行参照しない(self):
        selected, material = self.material()
        result = self.session.応答('本文を1行で要約して', {'本文': material})
        self.assertTrue(result.成立, result.理由)
        self.a.成果登録(selected, '成果', result.出力[0][1])
        self.a.更新(self.a.起点(), (文脈登録('新版', 能力結果(True, '売上は999です。')),),
                    失効ID=('原文',), 理由='明示改訂')
        self.assertFalse(self.a.選択(文脈選択要求(('成果',))).成立)
        current = self.a.選択(文脈選択要求(('新版',), 直近件数=0))
        result = self.session.応答('本文から数字を抽出して', {'本文': self.a.資料化(current)})
        self.assertTrue(result.成立, result.理由)
        self.assertEqual(result.出力[0][1].本文, '999')

    def test_過小予算の不成立資料を実行しない(self):
        selected = self.a.選択(文脈選択要求(('原文',), 最大バイト数=1))
        result = self.session.応答('本文から数字を抽出して', {'本文': self.a.資料化(selected)})
        self.assertFalse(result.成立)
        self.assertEqual(result.出力, ())


if __name__ == '__main__':
    unittest.main()
