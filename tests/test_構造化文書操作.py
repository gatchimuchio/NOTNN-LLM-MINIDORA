"""型検査・部分選択・形式変換の情報落ち境界と来歴再構成。"""
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import json
import unittest

from minidora.構造化文書 import 構造化文書を読む
from minidora.構造化文書操作 import 文書を処理, 文書記録整合, _符号
from minidora.製品版.型 import 能力結果


class 文書操作試験(unittest.TestCase):
    def setUp(self):
        self.j=構造化文書を読む('{"items":[{"id":"001","n":120},{"id":"002","n":999}],"注記":"未確認"}','JSON')
        self.c=構造化文書を読む('品目,金額,備考\r\n甲,120,"改行\n留保"\r\n乙,999,別件\r\n','CSV')

    def op(self,r,kind,options):
        out=文書を処理(r,kind,options)
        self.assertTrue(out.成立,(out.保留理由,out.データ))
        self.assertTrue(文書記録整合(out))
        return out

    def test_JSONの階層を指定して選択(self):
        r=self.op(self.j,'JSON選択',{'位置':'/items/0/n'})
        self.assertEqual(r.本文,'120')
        self.assertFalse(r.データ['全原値保持'])
        self.assertIn('/注記',r.データ['未選択位置'])
        self.assertEqual(r.データ['文書']['対応']['']['原位置'],'/items/0/n')

    def test_特殊文字と空キーのポインター(self):
        r=構造化文書を読む('{"a/b":{"~key":{"":7}},"01":9}','JSON')
        self.assertEqual(self.op(r,'JSON選択',{'位置':'/a~1b/~0key/'}).本文,'7')
        self.assertEqual(self.op(r,'JSON選択',{'位置':'/01'}).本文,'9')

    def test_存在しないキー不正な配列添字を拒否(self):
        for path in ('/items/9','/missing','/items/00','/items/-','/items/-1','/items/1.0','items','/a~2b','#/items'):
            self.assertFalse(文書を処理(self.j,'JSON選択',{'位置':path}).成立)

    def test_nullと欠落を混同しない(self):
        r=構造化文書を読む('{"x":null}','JSON')
        self.assertEqual(self.op(r,'JSON選択',{'位置':'/x'}).本文,'null')
        self.assertFalse(文書を処理(r,'JSON選択',{'位置':'/y'}).成立)

    def test_複数段階選択が最初の原文に対応(self):
        a=self.op(self.j,'JSON選択',{'位置':'/items'})
        b=self.op(a,'JSON選択',{'位置':'/1/id'})
        c=self.op(b,'値取出',{'型':'文字列'})
        self.assertEqual(c.本文,'002')
        span=c.データ['文書']['対応']['']
        text=c.データ['原本']['原文']
        self.assertEqual(text[span['開始']:span['終了']],'"002"')
        self.assertEqual(span['原位置'],'/items/1/id')

    def test_CSVの列名行番号と選択順を保持(self):
        r=self.op(self.c,'CSV選択',{'列':['金額','品目'],'行':[1,0]})
        self.assertEqual(r.本文,'金額,品目\r\n999,乙\r\n120,甲\r\n')
        self.assertEqual(r.データ['文書']['対応']['/0/0']['原位置'],'/1/1')
        self.assertEqual(r.データ['未選択位置'],['/0/2','/1/2'])

    def test_CSVの行列重複欠落を拒否(self):
        for opts in ({'列':['missing'],'行':None},{'列':[True],'行':None},{'列':['品目',0],'行':None},
                     {'列':[0],'行':[0,0]},{'列':[0],'行':[2]},{'列':[0],'行':[True]},{'列':[],'行':None}):
            self.assertFalse(文書を処理(self.c,'CSV選択',opts).成立)

    def test_空行選択は空データとして明記(self):
        r=self.op(self.c,'CSV選択',{'列':['品目'],'行':[]})
        self.assertEqual(r.本文,'品目\r\n')
        self.assertFalse(r.データ['全原値保持'])
        self.assertEqual(len(r.データ['未選択位置']),6)

    def test_見出しなしは列番号で選択(self):
        r=構造化文書を読む('a,b\n1,2','CSV',見出し=False)
        self.assertEqual(self.op(r,'CSV選択',{'列':[1],'行':[0]}).本文,'b\r\n')
        self.assertFalse(文書を処理(r,'CSV選択',{'列':['a'],'行':None}).成立)

    def test_型検査で数値文字列真偽を区別(self):
        for path,good in (('/items/0/n','数値'),('/items/0/id','文字列')):
            for kind in ('数値','文字列','真偽'):
                opts={'規則':[{'位置':path,'型':kind,'必須':True}],'未指定許可':True}
                self.assertEqual(文書を処理(self.j,'型検査',opts).成立,kind==good)

    def test_型検査の必須任意と未指定欄(self):
        def settings(required,allow):
            return {'規則':[{'位置':'/missing','型':'文字列','必須':required}],'未指定許可':allow}
        self.op(self.j,'型検査',settings(False,True))
        self.assertFalse(文書を処理(self.j,'型検査',settings(True,True)).成立)
        self.assertFalse(文書を処理(self.j,'型検査',settings(False,False)).成立)
        self.op(self.j,'型検査',{'規則':[{'位置':'','型':'対象','必須':True}],'未指定許可':False})

    def test_任意項目でも不正ポインターは無視しない(self):
        r=文書を処理(self.j,'型検査',{'規則':[{'位置':'/items/00','型':'対象','必須':False}],'未指定許可':True})
        self.assertFalse(r.成立)

    def test_余剰フィールドを型検査で指摘(self):
        rules=[{'位置':'/items','型':'配列','必須':True}]
        self.assertFalse(文書を処理(self.j,'型検査',{'規則':rules,'未指定許可':False}).成立)
        rules.append({'位置':'/注記','型':'文字列','必須':True})
        self.op(self.j,'型検査',{'規則':rules,'未指定許可':False})

    def test_CSVからJSONは文字列のまま(self):
        r=self.op(self.c,'形式変換',{'出力':'JSON','行表現':'対象'})
        self.assertEqual(json.loads(r.本文)[0]['金額'],'120')
        self.assertEqual(r.データ['文書']['対応']['/0/金額']['原位置'],'/0/1')
        key=r.データ['文書']['キー対応']['/0/金額']
        self.assertEqual(r.データ['原本']['原文'][key['開始']:key['終了']],'金額')
        self.assertTrue(r.データ['全原値保持'])

    def test_CSVから配列形式のJSONへ(self):
        r=self.op(self.c,'形式変換',{'出力':'JSON','行表現':'配列'})
        self.assertEqual(json.loads(r.本文)[1],['乙','999','別件'])

    def test_JSON文字列の表をCSVへ往復(self):
        r=構造化文書を読む('[{"番号":"001","値":"甲,乙"},{"番号":"002","値":"引用\\\""}]','JSON')
        c=self.op(r,'形式変換',{'出力':'CSV','列名':['番号','値']})
        back=self.op(c,'形式変換',{'出力':'JSON','行表現':'対象'})
        self.assertEqual(json.loads(back.本文),json.loads(r.本文))
        self.assertTrue(back.データ['全原値保持'])

    def test_JSONの数値やnullをCSV文字列にしない(self):
        for value in ('1','true','null','[]','{}'):
            r=構造化文書を読む('[{"x":'+value+'}]','JSON')
            self.assertFalse(文書を処理(r,'形式変換',{'出力':'CSV','列名':['x']}).成立)

    def test_JSON表の不揃いなキーを補完削除しない(self):
        for text in ('[{"x":"1","y":"2"}]','[{"x":"1"},{}]','["x"]'):
            r=構造化文書を読む(text,'JSON')
            self.assertFalse(文書を処理(r,'形式変換',{'出力':'CSV','列名':['x']}).成立)

    def test_空配列は明示列名でCSV見出しだけ出す(self):
        r=構造化文書を読む('[]','JSON')
        self.assertEqual(self.op(r,'形式変換',{'出力':'CSV','列名':['甲','乙']}).本文,'甲,乙\r\n')

    def test_CSV式解釈リスクを引用符だけで通さない(self):
        for value in ('=1+1','+cmd','-1','@SUM(A1)','  =x','\tfoo'):
            r=構造化文書を読む(json.dumps([{'x':value}]),'JSON')
            out=文書を処理(r,'形式変換',{'出力':'CSV','列名':['x']})
            self.assertFalse(out.成立)
            self.assertEqual(out.本文,'')
            self.assertIn('式解釈リスク',out.データ['診断'])

    def test_選択で落とす値は原本と省略記録に残る(self):
        r=self.op(self.c,'CSV選択',{'列':['金額'],'行':[0]})
        self.assertIn('999',r.データ['原本']['原文'])
        self.assertNotIn('999',r.本文)
        self.assertEqual(len(r.データ['未選択位置']),5)

    def test_値取出は型を明示する(self):
        r=self.op(self.j,'JSON選択',{'位置':'/items/0/id'})
        self.assertEqual(self.op(r,'値取出',{'型':'文字列'}).本文,'001')
        self.assertFalse(文書を処理(r,'値取出',{'型':'数値'}).成立)
        self.assertFalse(文書を処理(self.j,'値取出',{'型':'対象'}).成立)

    def test_空文字と空値の本文を混同しない(self):
        a=構造化文書を読む('""','JSON');b=構造化文書を読む('null','JSON')
        self.assertEqual(self.op(a,'値取出',{'型':'文字列'}).本文,'')
        self.assertEqual(self.op(b,'値取出',{'型':'空値'}).本文,'null')

    def test_操作で原本を変更しない(self):
        before=deepcopy(self.j)
        r=self.op(self.j,'JSON選択',{'位置':'/items'})
        r.データ['原本']['原文']='変更'
        self.assertEqual(self.j,before)
        self.assertFalse(文書記録整合(r))

    def test_構造値とハッシュの偽装を再読で検出(self):
        r=deepcopy(self.j)
        r.データ['文書']['構造']['値']['items']['値'][0]['値']['n']['値']='731'
        r.データ.pop('記録SHA256')
        r.データ['記録SHA256']=sha256(_符号({'本文':r.本文,'データ':r.データ})).hexdigest()
        self.assertFalse(文書記録整合(r))
        self.assertFalse(文書を処理(r,'JSON選択',{'位置':'/items'}).成立)

    def test_省略と対応位置と本文の改変を検出(self):
        selected=self.op(self.j,'JSON選択',{'位置':'/items/0/n'})
        a=deepcopy(selected);a.データ['未選択位置']=[]
        b=deepcopy(selected);b.データ['文書']['対応']['']['開始']+=1
        for r in (a,b,replace(selected,本文='999')): self.assertFalse(文書記録整合(r))

    def test_操作列上限は履歴を捨てて通さない(self):
        r=self.j
        for _ in range(8): r=self.op(r,'JSON選択',{'位置':''})
        self.assertFalse(文書を処理(r,'JSON選択',{'位置':''}).成立)

    def test_未知設定と通常の能力結果を文書へ昇格しない(self):
        for value in (None,{},能力結果(True,'{"x":1}'),replace(self.j,成立=False)):
            self.assertFalse(文書記録整合(value))
        for op,opts in (('削除',{}),('JSON選択',{'位置':'','追加':True}),('CSV選択',{'列':[0],'行':None})):
            self.assertFalse(文書を処理(self.j,op,opts).成立)

    def test_ヘッダーの変換損失も別途明示(self):
        source=構造化文書を読む('a,b\n','CSV')
        r=self.op(source,'形式変換',{'出力':'JSON','行表現':'配列'})
        self.assertEqual(r.データ['未選択見出し'],['a','b'])
        r=self.op(self.c,'CSV選択',{'列':['金額'],'行':[0]})
        self.assertEqual(r.データ['未選択見出し'],['品目','備考'])
        r=self.op(r,'形式変換',{'出力':'JSON','行表現':'対象'})
        self.assertEqual(r.データ['未選択見出し'],['品目','備考'])

    def test_見出しなし空表の非可逆な出力を保留(self):
        source=構造化文書を読む('1,2','CSV',見出し=False)
        r=文書を処理(source,'CSV選択',{'列':[0],'行':[]})
        self.assertFalse(r.成立)
        self.assertEqual(r.本文,'')

    def test_同じ操作と原文で同じ結果(self):
        a=self.op(self.j,'JSON選択',{'位置':'/items'})
        b=self.op(self.j,'JSON選択',{'位置':'/items'})
        self.assertEqual(a,b)


if __name__=='__main__':
    unittest.main()
