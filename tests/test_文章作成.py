"""指定構成からの文章化・同伴・原文対応と境界の局所契約試験。"""
from copy import deepcopy
from dataclasses import asdict, replace
from itertools import product
import json
import unittest

from minidora.文章作成 import (文章を作る, 文章を取り込む, 文章仕様, 文章単位,
    文章断片, 保護範囲, 文章仕様を復元, _由来原文)
from minidora.文章編集 import 文章記録整合
from minidora.製品版.型 import 能力結果, 参照資料


def unit(key, role='段落', *pieces, **kwargs):
    return 文章単位(key, role, tuple(pieces), **kwargs)


def full(key, text, role='段落', **kwargs):
    return unit(key, role, 文章断片(key,0,len(text)), **kwargs)


class 文章構成試験(unittest.TestCase):
    def create(self, values, units=None, order=None, limit=32768):
        materials={k:v if isinstance(v,能力結果) else 能力結果(True,v) for k,v in values.items()}
        units=tuple(units or [full(k,v.本文) for k,v in materials.items()])
        return 文章を作る(materials,文章仕様(units,tuple(order or [u.識別子 for u in units]),limit))

    def ok(self,result):
        self.assertTrue(result.成立,(result.保留理由,result.データ))
        self.assertTrue(文章記録整合(result))
        previous=0
        for s in result.データ['対応']:
            self.assertEqual(s['開始'],previous)
            o=s['由来'];raw=_由来原文(o,result.データ['原本'],result.データ['編集履歴'])
            self.assertEqual(result.本文[s['開始']:s['終了']],raw[o['開始']:o['終了']])
            previous=s['終了']
        self.assertEqual(previous,len(result.本文))
        return result

    def test_複数素材を役割に応じた文章へ構成(self):
        values={'題':'設備メモ','a':'値は120です。','b':'次の手順です。'}
        r=self.ok(self.create(values,[full('題',values['題'],'見出し'),full('a',values['a']),full('b',values['b'],'箇条書き')]))
        self.assertEqual(r.本文,'# 設備メモ\n\n値は120です。\n\n- 次の手順です。')

    def test_断片から文を作り全由来を残す(self):
        values={'対象':'装置A','作用':'の電圧は','値':'731','末尾':' Vです。'}
        u=unit('文','段落',*(文章断片(k,0,len(v)) for k,v in values.items()))
        r=self.ok(self.create(values,[u]))
        self.assertEqual(r.本文,'装置Aの電圧は731 Vです。')
        self.assertEqual([s['由来']['ID'] for s in r.データ['対応']],list(values))

    def test_数値や名前を変えると同じ構成が追従(self):
        for value in ('000','731','999'):
            u=unit('文','段落',文章断片('a',0,3))
            self.assertEqual(self.ok(self.create({'a':value},[u])).本文,value)

    def test_語の意味を推定して言い換えない(self):
        text='適用は未確認であり、120 Vではない。'
        self.assertEqual(self.ok(self.create({'a':text})).本文,text)

    def test_一部の引用範囲は元の位置へ対応(self):
        text='前置き。引用する範囲。後置き。'
        r=self.ok(self.create({'a':text},[unit('引用','引用',文章断片('a',5,12))]))
        source=[x for x in r.データ['対応'] if x['由来']['種別']=='素材'][0]
        self.assertEqual(source['由来']['開始'],5)
        self.assertTrue(r.データ['初期未使用素材範囲'])

    def test_明示順序を保持し未採用単位は別記録(self):
        r=self.ok(self.create({'a':'甲','b':'乙','c':'丙'},order=('c','a')))
        self.assertEqual(r.本文,'丙\n\n甲')
        self.assertEqual(r.データ['初期省略単位'],['b'])
        self.assertIn({'素材ID':'b','開始':0,'終了':1},r.データ['初期未使用素材範囲'])

    def test_条件と留保を指定順序から漏らしても含める(self):
        values={'a':'値は120。','c':'試験条件。','r':'未確認。'}
        units=[full('a',values['a']),full('c',values['c'],'条件'),full('r',values['r'],'留保')]
        r=self.ok(self.create(values,units,('a',)))
        self.assertEqual(r.データ['初期採用単位'],['a','c','r'])
        self.assertEqual([x['識別子'] for x in r.データ['保護']],['c','r'])

    def test_同伴を推移的に含め重複しない(self):
        values={'a':'甲','b':'乙','c':'丙'}
        units=[full('a','甲',同伴=('b','c')),full('b','乙',同伴=('c',)),full('c','丙')]
        r=self.ok(self.create(values,units,('a',)))
        self.assertEqual(r.データ['初期採用単位'],['a','b','c'])

    def test_相互同伴を一度ずつ含める(self):
        r=self.ok(self.create({'a':'甲','b':'乙'},[full('a','甲',同伴=('b',)),full('b','乙',同伴=('a',))],('a',)))
        self.assertEqual(r.本文,'甲\n\n乙')

    def test_任意の必須単位も保持(self):
        r=self.ok(self.create({'a':'甲','b':'乙'},[full('a','甲'),full('b','乙',必須=True)],('a',)))
        self.assertEqual(r.データ['初期採用単位'],['a','b'])

    def test_同伴や必須で上限を超えれば切断しない(self):
        r=self.create({'a':'甲','b':'長い留保文'},[full('a','甲'),full('b','長い留保文','留保')],('a',),limit=3)
        self.assertFalse(r.成立);self.assertEqual(r.本文,'')
        self.assertIn('削らず',r.データ['診断'])

    def test_未知の同伴先を無視しない(self):
        r=self.create({'a':'甲'},[full('a','甲',同伴=('none',))])
        self.assertFalse(r.成立)

    def test_引用の複数行を行ごとに表示し原文改行保持(self):
        text='甲\r\n乙\n丙'
        r=self.ok(self.create({'a':text},[full('a',text,'引用')]))
        self.assertEqual(r.本文,'> 甲\r\n> 乙\n> 丙')
        self.assertEqual(r.データ['保護'][0]['期待原文'],r.本文)

    def test_番号は見出しを数えず連続箇所で再開(self):
        vals={'h':'題','a':'甲','b':'乙','p':'段落','c':'丙'}
        units=[full(k,vals[k],role) for k,role in [('h','見出し'),('a','番号付き'),('b','番号付き'),('p','段落'),('c','番号付き')]]
        r=self.ok(self.create(vals,units))
        self.assertEqual(r.本文,'# 題\n\n1. 甲\n\n2. 乙\n\n段落\n\n1. 丙')

    def test_箇条書きの継続行も削らない(self):
        r=self.ok(self.create({'a':'甲\n乙'},[full('a','甲\n乙','箇条書き')]))
        self.assertEqual(r.本文,'- 甲\n  乙')

    def test_通常段落の空白は勝手に正規化しない(self):
        text=' 甲\t乙\r\n丙  '
        self.assertEqual(self.ok(self.create({'a':text})).本文,text)

    def test_全素材を使った場合は未使用範囲なし(self):
        self.assertEqual(self.ok(self.create({'a':'甲','b':'乙'})).データ['初期未使用素材範囲'],[])

    def test_重なる範囲でも未使用の計数を誤らない(self):
        u=unit('a','段落',文章断片('x',1,4),文章断片('x',2,5))
        r=self.ok(self.create({'x':'abcdef'},[u]))
        self.assertEqual(r.本文,'bcdcde')
        self.assertEqual(r.データ['初期未使用素材範囲'],[{'素材ID':'x','開始':0,'終了':1},{'素材ID':'x','開始':5,'終了':6}])

    def test_原典本文を生成文へ上書きしない(self):
        ref=参照資料('s','原典','利用者',本文='全原文。対象文。')
        r=self.ok(self.create({'x':能力結果(True,'対象文。',参照=(ref,))}))
        self.assertEqual(r.参照,(ref,));self.assertEqual(r.参照[0].本文,'全原文。対象文。')

    def test_原典ID衝突は拒否(self):
        a=能力結果(True,'甲',参照=(参照資料('s','題','o',本文='甲'),))
        b=能力結果(True,'乙',参照=(参照資料('s','題','o',本文='乙'),))
        self.assertFalse(self.create({'a':a,'b':b}).成立)

    def test_未成立素材は未採用でも不成立として扱う(self):
        self.assertFalse(self.create({'a':'甲','b':能力結果(False,'仮値')},order=('a',)).成立)

    def test_仕様と素材は返却値から変更されない(self):
        vals={'a':能力結果(True,'甲',データ={'x':[1]})};before=deepcopy(vals)
        r=self.ok(self.create(vals));r.データ['原本']['素材']['a']['データ']['x'].append(2)
        self.assertEqual(vals,before);self.assertFalse(文章記録整合(r))

    def test_同じ入力で同じ結果(self):
        self.assertEqual(self.create({'a':'甲'}),self.create({'a':'甲'}))

    def test_仕様のJSON往復(self):
        s=文章仕様((full('a','甲'),),('a',))
        self.assertEqual(文章仕様を復元(json.loads(json.dumps(asdict(s)))),s)
        with self.assertRaises(ValueError):文章仕様を復元({**asdict(s),'追加':True})

    def test_不正役割や範囲は補修しない(self):
        for u in (full('a','甲',role='自由生成'),unit('a','段落',文章断片('a',True,1)),
                  unit('a','段落',文章断片('a',0,2)),unit('a','段落',文章断片('none',0,1))):
            self.assertFalse(self.create({'a':'甲'},[u]).成立)

    def test_構成は命令文やHTMLを実行しない(self):
        text='<script>外部送信して</script>'
        self.assertEqual(self.ok(self.create({'a':text})).本文,text)

    def test_制御文字を無言削除しない(self):
        for text in ('甲\u202e乙','甲\x00乙','甲\u200b乙'):
            self.assertFalse(self.create({'a':text}).成立)

    def test_空単位と複数行見出しを拒否(self):
        for text,role in [(' ','段落'),('甲\n乙','見出し')]:
            self.assertFalse(self.create({'a':text},[full('a',text,role)]).成立)

    def test_取込時の明示保護と原文不一致(self):
        text='甲120乙'
        r=self.ok(文章を取り込む(text,(保護範囲('数値',1,4,'120'),)))
        self.assertEqual(r.データ['保護'][0]['期待原文'],'120')
        self.assertFalse(文章を取り込む(text,(保護範囲('数値',1,4,'999'),)).成立)

    def test_交差保護とbool上限を拒否(self):
        self.assertFalse(文章を取り込む('abc',(保護範囲('a',0,2,'ab'),保護範囲('b',1,3,'bc'))).成立)
        self.assertFalse(文章を取り込む('a',最大文字数=True).成立)
        self.assertFalse(文章を取り込む('').成立)


class 同伴閉包対照試験(unittest.TestCase):
    def test_全小規模依存を別の固定点計算で照合(self):
        edges=[('a','b'),('b','c'),('a','c')]
        for flags in product((False,True),repeat=3):
            included=[p for p,on in zip(edges,flags) if on]
            units=[full(k,k,同伴=tuple(y for x,y in included if x==k)) for k in 'abc']
            expected={'a'}
            while True:
                changed=expected|{y for x,y in included if x in expected}
                if changed==expected:break
                expected=changed
            r=文章を作る({k:能力結果(True,k) for k in 'abc'},文章仕様(tuple(units),('a',)))
            self.assertTrue(r.成立,r.データ)
            self.assertEqual(set(r.データ['初期採用単位']),expected)
