"""実HDS採用原本の保存・依存失効・再表現を検査する。品質率の受入ではない。"""
from copy import deepcopy
import json
import unittest

from minidora.HDS運用 import HDS運用セッション
from minidora.HDS運用.値 import 開封, 封緘, 結果を復元


class 会話状態試験(unittest.TestCase):
    本文 = '試作器甲の方式は個別交換。試作器乙の方式は一括交換。'

    def 会話(self, 名前='状態試験'):
        return HDS運用セッション(名前, 手順形成=False)

    def 採用(self, 会話, 文):
        応答 = 会話.応答(文)
        self.assertTrue(応答.成立, 応答.本文)
        return 応答

    def 提示(self, 会話):
        return self.採用(会話, '次の文章を要約して:\n' + self.本文)

    def test_提示原本は保存復元後の新比較目的にも渡る(self):
        会話 = self.会話(); 初回 = self.提示(会話)
        復元 = HDS運用セッション.復元(会話.保存())
        比較 = self.採用(復元, '試作器甲と試作器乙を方式で比較して')
        self.assertIn('個別交換', 比較.本文)
        self.assertIn('一括交換', 比較.本文)
        self.assertEqual(初回.結果.参照, 比較.結果.参照)
        self.assertEqual(結果を復元(比較.結果.データ['構造']['資料群']['提示本文']['資料']).本文, self.本文)

    def test_形式のみの再表現は原本を保持し終端で照合する(self):
        会話 = self.会話(); 初回 = self.提示(会話)
        応答 = self.採用(会話, '引用形式にして')
        self.assertEqual(初回.結果.データ['構造'], 応答.結果.データ['構造'])
        self.assertEqual(初回.結果.参照, 応答.結果.参照)
        self.assertEqual({行['能力'] for 行 in 応答.追跡['能力試行']}, {'資料文章再表現'})
        self.assertTrue(HDS運用セッション.復元(会話.保存()).状態()['前回有効'])

    def test_保存原本だけの書換えは再封緘しても復元されない(self):
        会話 = self.会話(); self.提示(会話)
        状態 = 開封(json.loads(会話.保存()))
        変更 = deepcopy(状態)
        変更['前回結果']['内容']['データ']['構造']['資料群']['提示本文']['資料']['内容']['本文'] = '試作器甲の方式は不明。'
        with self.assertRaises(ValueError):
            HDS運用セッション.復元(json.dumps(封緘(変更), ensure_ascii=False))

    def test_別会話へ採用結果だけ移植しても復元されない(self):
        元 = self.会話('元'); self.提示(元)
        元状態 = 開封(json.loads(元.保存()))
        別状態 = 開封(json.loads(self.会話('別').保存()))
        for 欄 in ('前回目的', '前回結果', '前回依存', '焦点有効'):
            別状態[欄] = deepcopy(元状態[欄])
        with self.assertRaisesRegex(ValueError, '同セッションの採用原記録'):
            HDS運用セッション.復元(json.dumps(封緘(別状態), ensure_ascii=False))

    def test_登録原本を変更すると旧回答が失効し新原本を読む(self):
        会話 = self.会話()
        self.assertTrue(会話.資料を登録('仕様', self.本文).成立)
        初回 = self.採用(会話, '試作器甲と試作器乙を方式で比較して')
        self.assertEqual(set(会話._前回依存), {'仕様'})
        self.assertTrue(会話.資料を登録('仕様', self.本文.replace('個別交換', '部品修理'), 更新=True).成立)
        self.assertFalse(会話.状態()['前回有効'])
        self.assertFalse(会話.応答('引用形式にして').成立)
        新 = self.採用(会話, '試作器甲と試作器乙を方式で比較して')
        self.assertIn('部品修理', 新.本文)
        self.assertNotIn('個別交換', 新.本文)
        self.assertNotEqual(初回.結果.参照, 新.結果.参照)

    def test_新話題の不成立を旧話題の採用へ読み替えない(self):
        会話 = self.会話(); self.提示(会話)
        新話題 = 会話.応答('別の話です。未提示物とは何ですか')
        self.assertFalse(新話題.成立)
        self.assertFalse(会話.状態()['前回有効'])
        続き = 会話.応答('それを詳しく説明して')
        self.assertFalse(続き.成立)
        self.assertNotIn('個別交換', 続き.本文)

    def test_別セッションには提示根拠と焦点を引き継がない(self):
        元, 別 = self.会話('元'), self.会話('別')
        self.提示(元)
        応答 = 別.応答('それを詳しく説明して')
        self.assertFalse(応答.成立)
        self.assertIsNone(別._前回結果)
        self.assertNotIn('個別交換', 応答.本文)


if __name__ == '__main__':
    unittest.main()
