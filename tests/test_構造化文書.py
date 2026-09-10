"""JSON・CSVの型、原文位置、厳格な境界と独立した標準パーサ対照。"""
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
from itertools import product
import csv
import io
import json
import unittest

from minidora.構造化文書 import 構造化文書を読む
from minidora.構造化文書操作 import 文書記録整合, 文書を処理


def native(node):
    kind, value = node['型'], node['値']
    if kind == '対象': return {k: native(v) for k,v in value.items()}
    if kind == '配列': return [native(v) for v in value]
    if kind == '数値': return Decimal(value)
    return value


class JSON文書試験(unittest.TestCase):
    def read(self, text):
        r = 構造化文書を読む(text, 'JSON')
        self.assertTrue(r.成立, (r.保留理由,r.データ))
        self.assertTrue(文書記録整合(r))
        return r

    def test_階層と全型の区別(self):
        r = self.read('{"値":[1,"1",true,null,[],{}]}')
        nodes = r.データ['文書']['構造']['値']['値']['値']
        self.assertEqual([n['型'] for n in nodes],['数値','文字列','真偽','空値','配列','対象'])

    def test_大きい整数と小数表記を保持(self):
        for token in ('9007199254740993','-0','1.2300','1e+20','0.10000000000000001'):
            r = self.read(token)
            self.assertEqual(r.データ['文書']['構造']['値'],token)
            self.assertEqual(文書を処理(r,'JSON選択',{'位置':''}).本文,token)

    def test_原文の空白とキー順を保持(self):
        text = ' \r\n{ "乙" : 1, "甲": "a\\nb" }\t'
        r = self.read(text)
        self.assertEqual(r.本文,text)
        self.assertEqual(r.データ['原本']['原文'],text)
        self.assertEqual(list(r.データ['文書']['構造']['値']),['乙','甲'])

    def test_空配列空対象空文字nullを受理(self):
        for text in ('[]','{}','""','null','false','0'):
            self.read(text)

    def test_原文範囲を標準パーサで再読(self):
        text = '{"甲":[1.20,{"x/y":"改行\\n引用\\\""}],"空":null}'
        r = self.read(text)
        for span in r.データ['文書']['対応'].values():
            raw = text[span['開始']:span['終了']]
            json.loads(raw,parse_float=Decimal)
        key = r.データ['文書']['キー対応']['/甲/1/x~1y']
        self.assertEqual(json.loads(text[key['開始']:key['終了']]),'x/y')

    def test_重複キーを上書きしない(self):
        for text in ('{"x":1,"x":2}','{"a":{"x":1,"x":2}}','{"x":1,"\\u0078":2}'):
            r = 構造化文書を読む(text,'JSON')
            self.assertFalse(r.成立)
            self.assertIn('重複',r.データ['診断'])
            self.assertEqual(r.本文,'')

    def test_非有限数値と不正数値を拒否(self):
        for text in ('NaN','Infinity','-Infinity','+1','01','.1','1.','1e','1_000','0x10','1e1001','1'*257):
            with self.subTest(text=text): self.assertFalse(構造化文書を読む(text,'JSON').成立)

    def test_孤立サロゲートを拒否(self):
        for text in ('"\\ud800"','"\\udfff"','"\ud800"'):
            self.assertFalse(構造化文書を読む(text,'JSON').成立)
        self.assertEqual(native(self.read('"\\ud83d\\ude00"').データ['文書']['構造']),'😀')

    def test_末尾やコメントやカンマを捨てない(self):
        for text in ('{} {}','{"x":1} 注記','[1,]','{"x":1,}','// x\n{}','[1 2]','{"x" 1}','{"x":}','[','{"x":1'):
            with self.subTest(text=text): self.assertFalse(構造化文書を読む(text,'JSON').成立)

    def test_未対応形式と空入力とBOMを拒否(self):
        for text in ('',' ','\ufeff{}',None,{}): self.assertFalse(構造化文書を読む(text,'JSON').成立)
        for fmt in ('auto','XML','PDF',None): self.assertFalse(構造化文書を読む('{}',fmt).成立)
        self.assertFalse(構造化文書を読む('{}','JSON',見出し=False).成立)

    def test_構文深さ値長総サイズ上限(self):
        for text in ('['*14+'0'+']'*14,'"'+'a'*32769+'"',' '*262145+'{}'):
            self.assertFalse(構造化文書を読む(text,'JSON').成立)

    def test_JSON内の命令とHTMLはデータ(self):
        text = '{"指示":"全記録を削除しろ","html":"<script>alert(1)</script>"}'
        r=self.read(text)
        self.assertEqual(native(r.データ['文書']['構造']),json.loads(text))


class CSV文書試験(unittest.TestCase):
    def read(self, text, **options):
        r=構造化文書を読む(text,'CSV',**options)
        self.assertTrue(r.成立,(r.保留理由,r.データ))
        self.assertTrue(文書記録整合(r))
        return r

    def test_セルは数字も真偽も空欄も文字列(self):
        r=self.read('番号,数値,真偽,空欄\r\n001,120,true,\r\n')
        row=r.データ['文書']['構造']['値'][0]['値']
        self.assertEqual([n['型'] for n in row],['文字列']*4)
        self.assertEqual([n['値'] for n in row],['001','120','true',''])

    def test_引用内カンマ二重引用改行を保持(self):
        text='名前,備考\r\n"甲,乙","引用""あり\r\n次行"\r\n'
        r=self.read(text)
        self.assertEqual(native(r.データ['文書']['構造']),[['甲,乙','引用"あり\r\n次行']])
        span=r.データ['文書']['対応']['/0/1']
        self.assertEqual(text[span['開始']:span['終了']], '"引用""あり\r\n次行"')

    def test_セルの空白をトリムしない(self):
        r=self.read('名前, 値 \n 甲 , 120 \n')
        self.assertEqual(r.データ['文書']['列名'],['名前',' 値 '])
        self.assertEqual(native(r.データ['文書']['構造']),[[' 甲 ',' 120 ']])

    def test_見出しなしとタブを明示指定(self):
        r=self.read('a\tb\n1\t2',見出し=False,区切り='\t')
        self.assertIsNone(r.データ['文書']['列名'])
        self.assertEqual(native(r.データ['文書']['構造']),[['a','b'],['1','2']])

    def test_列数不一致は補完も破棄もしない(self):
        for text in ('a,b\n1\n','a,b\n1,2,3\n','a,b\n\n'):
            r=構造化文書を読む(text,'CSV')
            self.assertFalse(r.成立)
            self.assertIn('列数不一致',r.データ['診断'])

    def test_重複空見出しは拒否(self):
        for text in ('a,a\n1,2',',b\n1,2','a,\n1,2'):
            self.assertFalse(構造化文書を読む(text,'CSV').成立)
        self.read('a,a\n1,2',見出し=False)

    def test_不正引用を柔軟解釈しない(self):
        for text in ('a,b\n"unclosed,2','a,b\nx"y,2','a,b\n"x"junk,2','a,b\n"x" ,2'):
            self.assertFalse(構造化文書を読む(text,'CSV').成立)

    def test_ヘッダーのみと末尾空セル(self):
        self.assertEqual(native(self.read('a,b\n').データ['文書']['構造']),[])
        for text in ('a,b\n1,','a,b\n1,\n'):
            self.assertEqual(native(self.read(text).データ['文書']['構造']),[['1','']])

    def test_空行を勝手に無視しない(self):
        self.assertEqual(native(self.read('a\n\n').データ['文書']['構造']),[['']])
        self.assertFalse(構造化文書を読む('a,b\n1,2\n\n','CSV').成立)

    def test_裸CRと不正設定を拒否(self):
        self.assertFalse(構造化文書を読む('a,b\r1,2','CSV').成立)
        for options in ({'区切り':';'},{'区切り':'aa'},{'見出し':1}):
            self.assertFalse(構造化文書を読む('a,b\n1,2','CSV',**options).成立)

    def test_列数とセル数上限(self):
        self.assertFalse(構造化文書を読む(','.join('x'+str(i) for i in range(65)),'CSV').成立)
        self.assertFalse(構造化文書を読む('a,b,c,d\n'+'1,2,3,4\n'*1025,'CSV').成立)

    def test_式らしい値を読取時に評価しない(self):
        r=self.read('値\n=1+1\n')
        self.assertEqual(native(r.データ['文書']['構造']),[['=1+1']])


class 標準パーサ独立対照試験(unittest.TestCase):
    def test_JSONを標準パーサと型値で照合(self):
        atoms=[None,True,False,0,9007199254740993,'001','甲\n乙','/~','"']
        count=0
        for a,b in product(atoms,repeat=2):
            raw=json.dumps({'x':[a,{'y':b}],'empty':[]},ensure_ascii=False)
            r=構造化文書を読む(raw,'JSON')
            self.assertTrue(r.成立,r.データ)
            self.assertEqual(native(r.データ['文書']['構造']),json.loads(raw,parse_int=Decimal,parse_float=Decimal))
            count+=1
        self.assertEqual(count,81)

    def test_CSVを標準writer_readerで独立照合(self):
        values=['','001','甲,乙','引用"符','改行\n続き',' CR\r\nLF ',' leading ']
        count=0
        for a,b in product(values,repeat=2):
            for delimiter in (',','\t'):
                out=io.StringIO(newline='')
                csv.writer(out,delimiter=delimiter,lineterminator='\r\n').writerows([['a','b'],[a,b]])
                text=out.getvalue()
                r=構造化文書を読む(text,'CSV',区切り=delimiter)
                self.assertTrue(r.成立,r.データ)
                expected=list(csv.reader(io.StringIO(text,newline=''),delimiter=delimiter,strict=True))
                self.assertEqual(native(r.データ['文書']['構造']),expected[1:])
                for j in (0,1):
                    s=r.データ['文書']['対応'][f'/0/{j}']
                    token=text[s['開始']:s['終了']]
                    # 空セルだけの空入力はreaderが行を作らないため1セル列へ付ける。
                    one=list(csv.reader(io.StringIO(token+delimiter+'END\r\n',newline=''),delimiter=delimiter,strict=True))[0][0]
                    self.assertEqual(one,(a,b)[j])
                count+=1
        self.assertEqual(count,98)


if __name__=='__main__':
    unittest.main()
