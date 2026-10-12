"""取得→終端採用→採用原本再利用の接続契約。人工通信を知識性能に数えない。"""
from hashlib import sha256
import unittest

from minidora.HDS運用.製品 import HDS製品ミニドラ
from minidora.HDS運用.セッション import HDS運用セッション
from minidora.HDS運用.値 import 結果を復元
from minidora.公開本文取得 import 本文を復号
from minidora.知識取得 import 知識取得器
from minidora.製品版.型 import 参照資料
from minidora.製品版.検索 import 固定Web検索供給器


class 人工本文:
    本文 = '試料甲とは熱の移動を抑える容器である。試料甲の方式は断熱収納。'
    URL = 'https://example.com/source'

    def __init__(self):
        self.取得回数 = 0

    def 取得(self, url):
        self.取得回数 += 1
        return 本文を復号(url, (url,), {'content-type': 'text/plain; charset=utf-8'}, self.本文.encode())


class 取得採用試験(unittest.TestCase):
    def test_実型取得記録を照合して同会話だけで原本を再利用する(self):
        本文 = 人工本文()
        検索 = 固定Web検索供給器((参照資料('候補甲', '試料甲', '契約試験', 本文.URL),))
        取得 = 知識取得器(検索, 本文)
        製品 = HDS製品ミニドラ(基本チャット=True, 公開取得方針="auto", 取得器=取得, 手順形成=False)
        応答 = 製品.応答('試料甲とは何ですか', セッションID='取得')
        self.assertEqual(応答.状態, 'APPROVE', 応答.本文)
        self.assertIn('熱の移動を抑える容器', 応答.本文)
        self.assertEqual(本文.取得回数, 1)
        self.assertTrue(製品.監査台帳.検証(応答.追跡ID))
        会話 = 製品.セッション('取得')
        前回 = 結果を復元(会話._前回結果)
        記録 = 前回.データ['構造']['取得記録'][0]
        self.assertEqual(記録['資料'][0]['本文SHA256'], sha256(本文.本文.encode()).hexdigest())
        復元 = HDS運用セッション.復元(会話.保存(), 外部読取許可=True, 取得器=取得)
        self.assertTrue(復元.状態()['前回有効'])
        追問 = 復元.応答('試料甲の方式を説明して')
        self.assertTrue(追問.成立, 追問.本文)
        self.assertIn('断熱収納', 追問.本文)
        self.assertEqual(本文.取得回数, 1)
        self.assertEqual(追問.結果.データ['構造']['取得記録'], 前回.データ['構造']['取得記録'])
        別 = 製品.応答('試料甲とは何ですか', セッションID='別', 外部読取許可=False)
        self.assertEqual(別.状態, 'SUSPEND')
        self.assertEqual(本文.取得回数, 1)


if __name__ == '__main__':
    unittest.main()
