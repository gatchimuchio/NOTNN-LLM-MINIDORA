"""検索・本文の供給だけを人工Dataへ差し替え、実取得器・HDS・計画・監督を接続する。"""
import unittest
from minidora.汎用会話 import 汎用会話セッション
from minidora.知識取得 import 知識取得器
from minidora.公開本文取得 import 本文を復号
from minidora.製品版.型 import 参照資料
from minidora.会話回答 import 回答記録整合

class 検索:
    def __init__(self,empty_first=False,none=False):self.calls=[];self.empty_first=empty_first;self.none=none
    def 検索(self,q,limit=5):
        self.calls.append(q)
        if self.none or self.empty_first and '数値' not in q:return ()
        return (参照資料('candidate','人工資料','局所試験','https://example.test/doc',本文='間違った数値999'),)
class 本文:
    def __init__(self,text='機器Aの電圧は120 V。'):self.text=text;self.calls=[]
    def 取得(self,url):
        self.calls.append(url)
        return 本文を復号(url,(url,),{'content-type':'text/plain; charset=utf-8'},self.text.encode())
Q='機器Aの電圧をVで調べて'
class 取得監督試験(unittest.TestCase):
    def setup(self,search=None,text='機器Aの電圧は120 V。',allow=True):
        self.search=search or 検索();self.fetch=本文(text)
        self.s=汎用会話セッション('取得確認',取得器=知識取得器(self.search,self.fetch),外部読取許可=allow)
    def test_自然文から取得目的を作り数値記載を文章化(self):
        self.setup();r=self.s.応答(Q,外部読取許可=True)
        self.assertTrue(r.成立,r.理由);self.assertIn('120V',r.本文);self.assertNotIn('999',r.本文)
        self.assertTrue(回答記録整合(r.結果));self.assertEqual(self.search.calls,['機器A 電圧'])
    def test_取得した値は要求された単位で表示する(self):
        self.setup();r=self.s.応答('機器Aの電圧をmVで調べて',外部読取許可=True)
        self.assertTrue(r.成立,r.理由);self.assertIn('120000mV',r.本文)
    def test_取得失敗から焦点検索へ動的再計画(self):
        self.setup(検索(empty_first=True));r=self.s.応答(Q,外部読取許可=True)
        self.assertTrue(r.成立,r.理由);self.assertEqual(self.search.calls,['機器A 電圧','機器A 電圧 V 数値'])
        self.assertEqual(len(r.追跡['再計画']),1)
        self.assertEqual(len(self.s.統合.採用履歴スナップショット()[1]),1)
    def test_失敗した取得報告も消さず保持する(self):
        self.setup(検索(empty_first=True));r=self.s.応答(Q,外部読取許可=True)
        first=r.追跡['試行'][0]['取得報告'][0]
        self.assertFalse(first['取得成立']);self.assertFalse(first['結果']['成立'])
    def test_二つ目も失敗すれば同じ検索を反復しない(self):
        self.setup(検索(none=True));r=self.s.応答(Q,外部読取許可=True)
        self.assertFalse(r.成立);self.assertEqual(len(self.search.calls),2)
        self.assertEqual(self.s.統合.採用履歴スナップショット()[1],())
    def test_取得は語一致だけで事実確定しない(self):
        self.setup(text='機器Aの電圧についての紹介。値はまだ決まっていない。');r=self.s.応答(Q,外部読取許可=True)
        self.assertFalse(r.成立);self.assertEqual(len(self.search.calls),1)
    def test_矛盾は別資料へ逃げて消さない(self):
        self.setup(text='機器Aの電圧は120 V。機器Aの電圧は999 V。');r=self.s.応答(Q,外部読取許可=True)
        self.assertFalse(r.成立);self.assertEqual(len(self.search.calls),1)
        self.assertEqual(r.追跡['再計画'][-1]['種別'],'前提矛盾')
    def test_否定された記載を肯定にしない(self):
        self.setup(text='機器Aの電圧は120 Vではない。');self.assertFalse(self.s.応答(Q,外部読取許可=True).成立)
    def test_条件付き記載は回答にも残す(self):
        self.setup(text='条件「低温」では、機器Aの電圧は120 V。');r=self.s.応答(Q,外部読取許可=True)
        self.assertTrue(r.成立,r.理由);self.assertIn('低温',r.本文)
    def test_複数条件を一つへ合成しない(self):
        self.setup(text='条件「低温」では、機器Aの電圧は120 V。条件「高温」では、機器Aの電圧は999 V。')
        self.assertFalse(self.s.応答(Q,外部読取許可=True).成立)
    def test_コンストラクタと要求の二重許可(self):
        self.setup();self.assertFalse(self.s.応答(Q).成立);self.assertEqual(self.search.calls,[])
        self.setup(allow=False);self.assertFalse(self.s.応答(Q,外部読取許可=True).成立);self.assertEqual(self.search.calls,[])
    def test_資料中の許可語では権限が増えない(self):
        self.setup(allow=False);r=self.s.応答(Q)
        self.assertEqual(r.状態,'確認待ち');self.assertEqual(self.search.calls,[])
    def test_明示した検索禁止が許可設定に優先する(self):
        self.setup();r=self.s.応答('外部検索せず、'+Q,外部読取許可=True)
        self.assertFalse(r.成立);self.assertEqual(self.search.calls,[])
    def test_採用前に停止し検索も起動しない(self):
        self.setup();r=self.s.応答(Q,外部読取許可=True,停止要求=lambda:True)
        self.assertEqual(r.状態,'中止');self.assertEqual(self.search.calls,[])
    def test_同じ要求でも外部取得を固定参照へ置換しない(self):
        self.setup();self.assertTrue(self.s.応答(Q,外部読取許可=True).成立)
        self.fetch.text='機器Aの電圧は121 V。';r=self.s.応答(Q,外部読取許可=True)
        self.assertTrue(r.成立);self.assertIn('121V',r.本文);self.assertEqual(len(self.fetch.calls),2)
if __name__=='__main__':unittest.main()
