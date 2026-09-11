"""独立真理値計算との対照と追加境界。反復数を独立試験件数に水増ししない。"""
from itertools import product
from random import Random
from dataclasses import replace
from copy import deepcopy
import json
import unittest
from minidora.命題構造 import 原子, 結合, 反対, 命題記載, 命題項
from minidora.命題推論 import 命題推論器
from minidora.命題解釈 import 命題資料を読む, 命題を読む
from minidora.命題能力接続 import 命題資料を構成
from minidora.会話回答 import 回答記録整合
from minidora.汎用会話 import 汎用会話セッション
from minidora.製品版.型 import 能力結果
from minidora.能力合成 import _結果辞書
from minidora.応答構成 import 能力結果を復元


def 真理値(e, env):
    if e.種別=='原子':return env[e.述語]
    if e.種別=='否定':return not 真理値(e.子[0],env)
    if e.種別=='連言':return all(真理値(c,env) for c in e.子)
    if e.種別=='選言':return any(真理値(c,env) for c in e.子)
    if e.種別=='含意':return not 真理値(e.子[0],env) or 真理値(e.子[1],env)
    raise AssertionError('対照器に未対応の種別')


class 命題独立対照試験(unittest.TestCase):
    def test_整合する命題問題を独立真理値表で対照(self):
        rng=Random(20);atoms=[原子(s) for s in 'PQR'];literals=atoms+[反対(a) for a in atoms]
        formulas=literals+[結合(kind,a,b) for kind in ('連言','選言','含意') for a in literals for b in literals]
        valuations=[dict(zip('PQR',row)) for row in product((False,True),repeat=3)]
        checked=0
        for _ in range(300):
            premises=rng.sample(formulas,3);q=rng.choice(formulas)
            models=[v for v in valuations if all(真理値(e,v) for e in premises)]
            if not models:continue
            records=tuple(命題記載(str(i),e,'人工資料','有限論理式',(0,5)) for i,e in enumerate(premises))
            r=命題推論器(records).判定(q)
            if r['支持']:self.assertTrue(all(真理値(q,v) for v in models),(premises,q,r))
            if r['反証']:self.assertTrue(all(not 真理値(q,v) for v in models),(premises,q,r))
            checked+=1
        self.assertGreater(checked,100)
    def test_主体述語の一括改名で導出を維持(self):
        for entity,cls,parent in [('A','X','Y'),('甲','未知分類','上位分類'),('x17','分類_03','分類_91')]:
            src=f'すべての{cls}は{parent}である。{entity}は{cls}である。'
            r=命題推論器(命題資料を読む(src,'改名')).判定(命題を読む(f'{entity}は{parent}である')[0].式)
            self.assertEqual(r['判定'],'支持')
    def test_独立した存在証人で関係を合成しない(self):
        src='あるxについて(親(x,花子))。あるxについて(支援(x,花子))。'
        q='あるxについて(親(x,花子)かつ支援(x,花子))'
        r=命題推論器(命題資料を読む(src,'資料')).判定(命題を読む(q)[0].式)
        self.assertEqual(r['判定'],'未確定')
    def test_全称変数を同じ個体に潰さない(self):
        src='親(太郎,花子)。すべてのxについて(すべてのyについて(親(x,y)ならば支援(y,x)))。'
        e=命題推論器(命題資料を読む(src,'資料'))
        self.assertEqual(e.判定(命題を読む('支援(花子,太郎)')[0].式)['判定'],'支持')
        self.assertEqual(e.判定(命題を読む('支援(太郎,花子)')[0].式)['判定'],'未確定')
    def test_異なる時点を再帰条件でも混ぜない(self):
        src='2025年では(P)。2026年では(PならばQ)。2026年では(QならばR)。'
        r=命題推論器(命題資料を読む(src,'資料')).判定(命題を読む('2026年では(R)')[0].式)
        self.assertEqual(r['判定'],'未確定')
    def test_構造Dataにある条件を捨てない(self):
        with self.assertRaises(ValueError):命題資料を構成(能力結果(True,'P。',データ={'条件':'未解釈'}),'資料')
    def test_旧数値回答もJSON往復後に検証できる(self):
        s=汎用会話セッション('旧回答');r=s.応答('「2+3」を計算して')
        v=能力結果を復元(json.loads(json.dumps(_結果辞書(r.結果),ensure_ascii=False)))
        self.assertTrue(回答記録整合(v))
    def test_JSON往復後の本文改変は検知(self):
        s=汎用会話セッション('改変');r=s.応答('「2+3」を計算して')
        d=json.loads(json.dumps(_結果辞書(r.結果),ensure_ascii=False));d['本文']='999'
        self.assertFalse(回答記録整合(能力結果を復元(d)))
    def test_否定全称の二候補は異なる判定になり得る(self):
        src='太郎は猫である。太郎は鳥ではない。'
        e=命題推論器(命題資料を読む(src,'資料'));c=命題を読む('すべての猫は鳥ではない')
        self.assertEqual([e.判定(x.式)['判定'] for x in c],['未確定','支持'])
    def test_係り受け候補の確認が意味を実際に変える(self):
        s=汎用会話セッション('候補');s.応答('資料「資料」を登録:P。否定(R)。')
        a=s.応答('資料「資料」から「PまたはQかつR」は言える？')
        self.assertEqual(a.状態,'確認待ち')
        b=s.応答('解釈は1です');self.assertIn('支持されます',b.本文)
        s.応答('資料「資料」から「PまたはQかつR」は言える？')
        c=s.応答('解釈は2です');self.assertIn('反証',c.本文)

if __name__=='__main__':unittest.main()
