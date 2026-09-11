"""複数主題の取得目的を実取得処理へ接続。供給Dataは人工、外部通信は行わない。"""
import unittest
from urllib.parse import unquote
from minidora.汎用会話 import 汎用会話セッション
from minidora.知識取得 import 知識取得器
from minidora.公開本文取得 import 本文を復号
from minidora.製品版.型 import 参照資料
from minidora.会話回答 import 回答記録整合

Q='主題「機器A」と主題「機器B」と主題「機器C」の電圧をVで調べて比較して'

class _検索:
    def __init__(self,missing=None):self.calls=[];self.missing=missing
    def 検索(self,q,limit=5):
        self.calls.append(q);name=q.split()[0]
        if name==self.missing and '数値' not in q:return ()
        return (参照資料('候補:'+name,'人工文書','人工検索','https://example.test/'+name,本文='推測値999'),)
class _本文:
    def __init__(self,conflict=False):self.calls=[];self.conflict=conflict
    def 取得(self,url):
        name=unquote(url.rsplit('/',1)[-1]);self.calls.append(name)
        n={'機器A':120,'機器B':150,'機器C':200}[name]
        text=name+'の電圧は'+str(n)+' V。'
        if self.conflict and name=='機器B':text+=name+'の電圧は999 V。'
        return 本文を復号(url,(url,),{'content-type':'text/plain; charset=utf-8'},text.encode())

class 集合取得試験(unittest.TestCase):
    def make(self,missing=None,conflict=False,allow=True):
        self.search=_検索(missing);self.fetch=_本文(conflict)
        return 汎用会話セッション('複数取得',取得器=知識取得器(self.search,self.fetch),外部読取許可=allow)
    def test_三主題の取得を役割ごとに計画して比較(self):
        s=self.make();r=s.応答(Q,外部読取許可=True)
        self.assertTrue(r.成立,(r.理由,r.追跡));self.assertTrue(回答記録整合(r.結果))
        self.assertIn('差は80V',r.本文);self.assertNotIn('999V',r.本文)
        self.assertEqual(self.search.calls,['機器A 電圧','機器B 電圧','機器C 電圧'])
    def test_複数主題の平均と表を同じ構成器から生成(self):
        r=self.make().応答('主題「機器A」と主題「機器B」の電圧の平均をVで調べて。表で',外部読取許可=True)
        self.assertTrue(r.成立,r.理由);self.assertIn('135V',r.本文);self.assertIn('| 資料',r.本文)
    def test_一主題だけの不足からその目的の取得経路を変更(self):
        s=self.make(missing='機器B');r=s.応答(Q,外部読取許可=True)
        self.assertTrue(r.成立,(r.理由,r.追跡));self.assertEqual(len(r.追跡['試行']),2)
        self.assertEqual(len(r.追跡['再計画']),1)
        self.assertIn('機器B 電圧 V 数値',self.search.calls)
        self.assertNotIn('機器A 電圧 V 数値',self.search.calls)
        self.assertEqual(r.追跡['再計画'][0]['分類'],'情報不足')
    def test_片方の矛盾を追加検索で消して平均しない(self):
        s=self.make(conflict=True);r=s.応答(Q,外部読取許可=True)
        self.assertFalse(r.成立);self.assertFalse(any('数値' in x for x in self.search.calls))
        self.assertEqual(r.追跡['再計画'][-1]['分類'],'前提矛盾')
        self.assertEqual(s.統合.採用履歴スナップショット()[1],())
    def test_要求側の外部許可がなければ検索しない(self):
        s=self.make();r=s.応答(Q)
        self.assertEqual(r.状態,'確認待ち');self.assertEqual(self.search.calls,[])
    def test_セッション側の外部許可がなければ検索しない(self):
        s=self.make(allow=False);r=s.応答(Q,外部読取許可=True)
        self.assertFalse(r.成立);self.assertEqual(self.search.calls,[])
    def test_検索禁止は全主題の取得より優先(self):
        s=self.make();r=s.応答('提供資料だけで、'+Q,外部読取許可=True)
        self.assertFalse(r.成立);self.assertEqual(self.search.calls,[])
    def test_未対応の付加要求があれば取得前に止める(self):
        s=self.make();r=s.応答(Q+'。原因を断定して',外部読取許可=True)
        self.assertFalse(r.成立);self.assertEqual(self.search.calls,[])
    def test_取得後の説明は採用済み成果から戻り再取得しない(self):
        s=self.make();r=s.応答(Q,外部読取許可=True);self.assertTrue(r.成立,r.理由)
        count=len(self.search.calls);r=s.応答('それを詳しく説明して')
        self.assertTrue(r.成立,r.理由);self.assertEqual(len(self.search.calls),count)
        self.assertIn('https://example.test/',r.本文)
    def test_単位訂正は新たな取得目的として実行する(self):
        s=self.make();self.assertTrue(s.応答(Q,外部読取許可=True).成立)
        r=s.応答('訂正:単位はmVです',外部読取許可=True)
        self.assertTrue(r.成立,r.理由);self.assertIn('120000mV',r.本文)
        self.assertEqual(len(self.search.calls),6)
    def test_対応していない時点指定を検索文へ混ぜない(self):
        s=self.make();r=s.応答(Q+'。2025年だけ',外部読取許可=True)
        self.assertFalse(r.成立);self.assertEqual(self.search.calls,[])

    def test_単位が不足する場合は検索前に確認し返答から再開(self):
        s=self.make();r=s.応答(Q.replace('をVで','を'),外部読取許可=True)
        self.assertEqual(r.状態,'確認待ち');self.assertEqual(self.search.calls,[])
        r=s.応答('単位はVです',外部読取許可=True)
        self.assertTrue(r.成立,r.理由);self.assertIn('差は80V',r.本文)
    def test_未対応の単位では無用な外部取得をしない(self):
        s=self.make();r=s.応答(Q.replace('Vで','未知単位で'),外部読取許可=True)
        self.assertEqual(r.状態,'確認待ち');self.assertEqual(self.search.calls,[])

if __name__=='__main__':unittest.main()
