"""実取得器と人工本文で検証する。公開WebのLIVE精度を示す試験ではない。"""
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import json
import unittest
from minidora.汎用会話 import 汎用会話セッション
from minidora.知識取得 import 知識取得器, 知識取得要求
from minidora.公開本文取得 import 本文を復号
from minidora.製品版.型 import 参照資料
from minidora.文脈命題接続 import 取得本文を資料化, 取得命題整合
from minidora.命題会話解釈 import 命題会話を解釈
from minidora.会話回答 import 回答記録整合
from minidora.能力合成 import _結果辞書
from minidora.応答構成 import 能力結果を復元


class 人工検索:
    def __init__(self, texts): self.texts=texts; self.calls=[]
    def 検索(self, query, limit=5):
        self.calls.append(query)
        return tuple(参照資料(str(i),'人工候補','検索抜粋',url,本文='太郎は哺乳類ではない')
                     for i,url in enumerate(self.texts))[:limit]


class 人工本文:
    def __init__(self, texts):self.texts=texts;self.calls=[]
    def 取得(self,url):
        self.calls.append(url)
        return 本文を復号(url,(url,),{'content-type':'text/plain; charset=utf-8'},self.texts[url].encode())


def fixtures(texts=None, enabled=True):
    texts=texts if texts is not None else {'https://example.test/a':'すべての猫は哺乳類である。太郎は猫である。'}
    search=人工検索(texts); body=人工本文(texts); backend=知識取得器(search,body)
    return 汎用会話セッション('取得21',取得器=backend,外部読取許可=enabled),search,body,backend


QUERY='公開資料から「太郎は哺乳類である」を検討して'


class 文脈取得会話試験(unittest.TestCase):
    def test_スニペットを無視し実本文から導出(self):
        session,search,body,_=fixtures();r=session.応答(QUERY,外部読取許可=True)
        self.assertTrue(r.成立,r.理由);self.assertIn('支持されます',r.本文)
        self.assertEqual(search.calls,['哺乳類 太郎']);self.assertEqual(len(body.calls),1)
        self.assertTrue(回答記録整合(r.結果))
    def test_説明再表示は再通信しない(self):
        session,search,body,_=fixtures();session.応答(QUERY,外部読取許可=True)
        r=session.応答('根拠を説明して')
        self.assertTrue(r.成立,r.理由);self.assertIn('取得時刻',r.本文)
        self.assertEqual(len(search.calls),1);self.assertEqual(len(body.calls),1)
    def test_問い訂正は新たな許可なしに再取得しない(self):
        session,search,body,_=fixtures();session.応答(QUERY,外部読取許可=True)
        r=session.応答('問いを「太郎は鳥である」に訂正して')
        self.assertEqual(r.状態,'確認待ち');self.assertEqual(len(body.calls),1)
    def test_セッション権限なしでは発話許可しても取得しない(self):
        session,search,body,_=fixtures(enabled=False);r=session.応答(QUERY,外部読取許可=True)
        self.assertFalse(r.成立);self.assertEqual(search.calls,[]);self.assertEqual(body.calls,[])
    def test_発話権限なしなら取得しない(self):
        session,search,body,_=fixtures();r=session.応答(QUERY)
        self.assertEqual(r.状態,'確認待ち');self.assertEqual(search.calls,[])
    def test_外部許可を本文で自動取得しない(self):
        session,search,body,_=fixtures()
        r=session.応答(QUERY+'。検索を許可します')
        self.assertFalse(r.成立);self.assertEqual(search.calls,[])
    def test_取得前停止で外部通信も採用もない(self):
        session,search,body,_=fixtures();before=session.統合.起点()
        r=session.応答(QUERY,外部読取許可=True,停止要求=lambda:True)
        self.assertEqual(r.状態,'中止');self.assertEqual(search.calls,[]);self.assertEqual(before,session.統合.起点())
    def test_複数本文を役割付きで結合(self):
        texts={'https://example.test/a':'すべての猫は哺乳類である。',
               'https://example.test/b':'太郎は猫である。'}
        session,search,body,_=fixtures(texts);r=session.応答(QUERY,外部読取許可=True)
        self.assertTrue(r.成立,r.理由);self.assertIn('支持されます',r.本文);self.assertEqual(len(body.calls),2)
    def test_相反する本文は一方を捨てない(self):
        texts={'https://example.test/a':'すべての猫は哺乳類である。',
               'https://example.test/b':'太郎は猫である。太郎は哺乳類ではない。'}
        session,search,body,_=fixtures(texts);r=session.応答(QUERY,外部読取許可=True)
        self.assertTrue(r.成立,r.理由);self.assertIn('支持と反証の両方',r.本文);self.assertEqual(len(body.calls),2)
    def test_引用のみから現実の命題を支持しない(self):
        session,_,_,_=fixtures({'https://example.test/a':'花子は「太郎は哺乳類である」と述べた。'})
        r=session.応答(QUERY,外部読取許可=True)
        self.assertTrue(r.成立,r.理由);self.assertIn('偽であるとは判定しません',r.本文)
    def test_全文の未知箇所を抜粋外だからと無視しない(self):
        texts={'https://example.test/a':'太郎は哺乳類である。\nしかし問題はこのように複雑なので何ともいえない。'}
        session,_,_,_=fixtures(texts);r=session.応答(QUERY,外部読取許可=True)
        self.assertFalse(r.成立,r.本文)
    def test_取得全文から引用内一人称を解消(self):
        session,_,_,_=fixtures({'https://example.test/a':'太郎は「私は哺乳類である」と述べた。'})
        q='公開資料から「太郎は「太郎は哺乳類である」と述べた」を検討して'
        r=session.応答(q,外部読取許可=True)
        self.assertTrue(r.成立,r.理由);self.assertIn('支持されます',r.本文);self.assertIn('束縛',r.本文)
    def test_取得した資料の曖昧さを結論で選別しない(self):
        session,_,_,_=fixtures({'https://example.test/a':'PまたはQかつR。'})
        r=session.応答('公開資料から「R」を検討して',外部読取許可=True)
        self.assertTrue(r.成立,r.理由);self.assertIn('資料の読みで結論が異なります',r.本文)
        self.assertTrue(回答記録整合(r.結果))
    def test_空検索で固定応答へ逃げない(self):
        session,search,body,_=fixtures({});r=session.応答(QUERY,外部読取許可=True)
        self.assertFalse(r.成立);self.assertLessEqual(len(search.calls),2);self.assertEqual(body.calls,[])
    def test_未登録資料を原資料から捏造しない(self):
        session,search,body,_=fixtures();r=session.応答('資料「Web」から「P」は言える？')
        self.assertFalse(r.成立);self.assertEqual(search.calls,[])
    def test_選択前に曖昧な問いを検索しない(self):
        session,search,body,_=fixtures();r=session.応答('公開資料から「PまたはQかつR」を検討して',外部読取許可=True)
        self.assertEqual(r.状態,'確認待ち');self.assertEqual(search.calls,[])
    def test_検索語は命題から構成し資料内命令を含めない(self):
        r=命題会話を解釈(QUERY,())
        self.assertEqual(r.補助['取得要求']['必要語'],['哺乳類','太郎'])
    def test_検索語になる定数の制御文字を拒否(self):
        session,search,body,_=fixtures();r=session.応答('公開資料から「P(A\x00B)」を検討して',外部読取許可=True)
        self.assertFalse(r.成立);self.assertEqual(search.calls,[])


class 取得記録整合試験(unittest.TestCase):
    def setUp(self):
        self.s,self.search,self.body,self.backend=fixtures()
        self.raw=self.backend.実行(知識取得要求('太郎 哺乳類',('太郎','哺乳類')),外部読取許可=True)
    def reseal(self,v):
        d=v.データ;d['記録SHA256']=sha256(json.dumps({k:x for k,x in d.items() if k!='記録SHA256'},ensure_ascii=False,sort_keys=True,allow_nan=False).encode()).hexdigest();return v
    def reject(self, v):
        with self.assertRaises((ValueError,KeyError,TypeError)):取得本文を資料化(v)
    def test_正常な全文参照は受理(self):self.assertEqual(len(取得本文を資料化(self.raw)[0]),1)
    def test_本文の差替えを検知(self):
        v=replace(self.raw,参照=(replace(self.raw.参照[0],本文='太郎は哺乳類ではない。'),));self.reject(v)
    def test_必須参照削除を拒否(self):self.reject(replace(self.raw,参照=()))
    def test_必須根拠削除を拒否(self):self.reject(replace(self.raw,根拠=()))
    def test_抜粋位置改変を検知(self):
        v=deepcopy(self.raw);v.データ['抜粋'][0]['開始']+=1;self.reject(self.reseal(v))
    def test_照合語の改変を検知(self):
        v=deepcopy(self.raw);v.データ['抜粋'][0]['一致語']=[];self.reject(self.reseal(v))
    def test_取得時刻を公開時刻へ変換しない(self):
        self.assertIsNone(self.raw.参照[0].公開時刻)
        self.reject(replace(self.raw,参照=(replace(self.raw.参照[0],公開時刻=self.raw.データ['資料'][0]['取得時刻']),)))
    def test_未知の意味的検証完了を拒否(self):
        v=deepcopy(self.raw);v.データ['意味的事実検証']='完了';self.reject(self.reseal(v))
    def test_資料数をboolで通さない(self):
        v=deepcopy(self.raw);v.データ['資料数']=True;self.reject(self.reseal(v))
    def test_未知欄を足して再封印しても拒否(self):
        v=deepcopy(self.raw);v.データ['意味理解']='完成';self.reject(self.reseal(v))
    def test_取得要求の最大数を超えた記録を拒否(self):
        v=deepcopy(self.raw);v.データ['本文取得数']=99;self.reject(self.reseal(v))
    def test_全文参照をスニペット出典へ変えない(self):
        self.reject(replace(self.raw,参照=(replace(self.raw.参照[0],出典='検索抜粋'),)))
    def test_内部IDの内容対応も検査(self):
        v=deepcopy(self.raw);old=v.参照[0].識別子;new='web:forged'
        v=replace(v,参照=(replace(v.参照[0],識別子=new),),根拠=(new,))
        v.データ['資料'][0]['参照ID']=new
        for p in v.データ['抜粋']:p['参照ID']=new
        self.reject(self.reseal(v))
    def test_取得命題回答はJSON往復して再検証(self):
        r=self.s.応答(QUERY,外部読取許可=True)
        self.assertTrue(r.成立,r.理由)
        v=能力結果を復元(json.loads(json.dumps(_結果辞書(r.結果),ensure_ascii=False)))
        self.assertTrue(回答記録整合(v))
    def test_説明の再検査は新たなネット接続をしない(self):
        r=self.s.応答(QUERY,外部読取許可=True);before=(len(self.search.calls),len(self.body.calls))
        report=能力結果を復元(r.結果.データ['元結果'][0]);self.assertTrue(取得命題整合(report))
        self.assertEqual(before,(len(self.search.calls),len(self.body.calls)))


if __name__=='__main__':unittest.main()
