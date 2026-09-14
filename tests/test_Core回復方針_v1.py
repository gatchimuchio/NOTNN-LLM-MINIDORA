from __future__ import annotations
from dataclasses import replace
from types import SimpleNamespace
import unittest

from minidora.製品版.型 import 能力結果
from minidora.会話意味 import 意味目的
from minidora.役割計画 import 役割作用, 役割計画器, 役割計画版
from minidora.実行回復 import (
    回復規則, 回復方針を決定, 実行回復版,
)
from minidora.会話実行監督 import 会話実行監督, 会話実行監督版
from minidora.会話作用契約 import 会話作用群


def _registry(*names):
    return tuple({'名前':n,'版':'v1','外部読取':False} for n in names)


class _Integration:
    def __init__(self, registry, outcomes):
        self.registry=registry
        self.outcomes=list(outcomes)
        self.calls=0
        self.state=('s',0)
    def 起点(self): return self.state
    def 能力一覧(self): return self.registry
    def _停止(self,stop):
        if stop and stop(): raise InterruptedError()
    def 準備(self,plan,data,依頼文=''):
        return SimpleNamespace(起点=self.state,ハッシュ='plan-'+str(self.calls+1))
    def 実行(self,packed,外部読取許可=False,停止要求=None):
        self.calls+=1
        row=self.outcomes[min(self.calls-1,len(self.outcomes)-1)]
        if row.get('ok'):
            hist=(SimpleNamespace(理由='',状態='合格',工程=row.get('step','役割工程:0001'),入力ハッシュ='ok-'+str(self.calls)),)
            run=SimpleNamespace(履歴=hist,中間結果=(),ルートハッシュ='run-'+str(self.calls))
            return SimpleNamespace(成立=True,状態='合格',理由='',実行=run)
        reason=row.get('reason','会話失敗:検証失敗:不成立')
        hist=(SimpleNamespace(理由=reason,状態=row.get('state','保留'),工程=row.get('step','役割工程:0001'),
                              入力ハッシュ=row.get('input','in-'+str(self.calls))),)
        run=SimpleNamespace(履歴=hist,中間結果=(),ルートハッシュ='run-'+str(self.calls))
        return SimpleNamespace(成立=False,状態=row.get('response_state','保留'),理由=reason,実行=run)


class 回復方針単体試験(unittest.TestCase):
    def test_版を更新(self):
        self.assertEqual(実行回復版,'MINIDORA-実行回復-v0.2')
        self.assertEqual(役割計画版,'MINIDORA-役割計画-v0.3')
        self.assertEqual(会話実行監督版,'MINIDORA-会話実行監督-v0.2')

    def test_既存回復ABIは自己を代替_入力役割を再取得へ写す(self):
        self.assertEqual(回復規則('検証失敗').動作(),'代替作用')
        self.assertEqual(回復規則('取得不足','入力役割','報告',('主題取得',)).動作(),'入力再取得')
        for rule in 会話作用群():
            for recovery in rule.回復:
                recovery.検証()

    def test_意味未確定と入力不足は利用者確認_その他の無契約は停止(self):
        for kind in ('意味未確定','入力不足'):
            p=回復方針を決定(種別=kind,分類=kind,発生目的='g',発生作用='a',規則=None,再開放=None)
            self.assertEqual(p.動作,'利用者確認');self.assertFalse(p.自動実行)
        p=回復方針を決定(種別='前提矛盾',分類='前提矛盾',発生目的='g',発生作用='a',規則=None,再開放=None)
        self.assertEqual(p.動作,'停止');self.assertFalse(p.自動実行)
        # 既存会話の確認契約を勝手に拡張しない。分類が意味未確定でも、
        # 個別の未解釈注記は明示確認契約がない限り停止する。
        p=回復方針を決定(種別='未解釈注記',分類='意味未確定',発生目的='g',発生作用='a',規則=None,再開放=None)
        self.assertEqual(p.動作,'停止')

    def test_失敗種別と分類の不一致を方針入力で拒否(self):
        with self.assertRaisesRegex(ValueError,'分類が不一致'):
            回復方針を決定(種別='検証失敗',分類='情報不足',発生目的='g',発生作用='a',規則=None,再開放=None)

    def test_同一作用再試行は実行環境系かつ有限回数だけ(self):
        with self.assertRaises(ValueError): 回復規則('検証失敗',方式='同一作用再試行',最大再試行=1).検証()
        with self.assertRaises(ValueError): 回復規則('実行環境',方式='同一作用再試行').検証()
        with self.assertRaises(ValueError): 回復規則('実行環境',方式='同一作用再試行',最大再試行=3).検証()
        good=回復規則('実行環境',方式='同一作用再試行',最大再試行=2).検証()
        p1=回復方針を決定(種別='実行環境',分類='実行環境',発生目的='g',発生作用='a',規則=good,再開放=('g','a'),契約='c',再試行済=0)
        p2=回復方針を決定(種別='実行環境',分類='実行環境',発生目的='g',発生作用='a',規則=good,再開放=('g','a'),契約='c',再試行済=2)
        self.assertEqual((p1.動作,p1.再試行番号,p1.禁止),('同一作用再試行',1,()))
        self.assertEqual(p2.動作,'停止')

    def test_回復方式は独立した回復方針契約印へ入る(self):
        alt=役割作用('x','A','成果',lambda p:(),lambda p:{},lambda p:True,
                     回復=(回復規則('実行環境'),))
        retry=replace(alt,回復=(回復規則('実行環境',方式='同一作用再試行',最大再試行=1),))
        reg=_registry('A')
        a=会話実行監督(役割計画器((alt,),reg),_Integration(reg,({'ok':True},)))
        b=会話実行監督(役割計画器((retry,),reg),_Integration(reg,({'ok':True},)))
        self.assertNotEqual(a._回復契約印(),b._回復契約印())




class 回復監督試験(unittest.TestCase):
    def test_代替作用を局所再計画する(self):
        reg=_registry('A','B')
        first=役割作用('第一','A','成果',lambda p:(),lambda p:{},lambda p:True,
                       回復=(回復規則('検証失敗'),))
        second=役割作用('第二','B','成果',lambda p:(),lambda p:{},lambda p:True,費用=2)
        planner=役割計画器((first,second),reg)
        root=_Integration(reg,({'reason':'会話失敗:検証失敗:候補不適合'},{'ok':True}))
        r=会話実行監督(planner,root).実行(意味目的('成果',{}),{},原文='成果')
        self.assertTrue(r.応答.成立);self.assertEqual(root.calls,2)
        self.assertEqual(r.失敗[0].回復方針,'代替作用')
        self.assertEqual(r.試行[1]['回復方針'],'代替作用')
        self.assertEqual(r.失敗[0].再開放,(意味目的('成果',{}).鍵(),'第一'))

    def test_同一作用再試行は計画器を再評価せず同一計画を使う(self):
        reg=_registry('A')
        action=役割作用('一時失敗','A','成果',lambda p:(),lambda p:{},lambda p:True,
                         回復=(回復規則('実行環境',方式='同一作用再試行',最大再試行=1),))
        planner=役割計画器((action,),reg)
        original=planner.計画する;count={'n':0}
        def plan(*a,**k): count['n']+=1;return original(*a,**k)
        planner.計画する=plan
        root=_Integration(reg,({'state':'失敗','response_state':'失敗','reason':'実装例外'},{'ok':True}))
        r=会話実行監督(planner,root).実行(意味目的('成果',{}),{},原文='成果')
        self.assertTrue(r.応答.成立);self.assertEqual((root.calls,count['n']),(2,1))
        self.assertEqual(r.失敗[0].回復方針,'同一作用再試行')
        self.assertEqual(r.試行[1]['固定被覆数'],1)

    def test_同一作用再試行上限で停止(self):
        reg=_registry('A')
        action=役割作用('一時失敗','A','成果',lambda p:(),lambda p:{},lambda p:True,
                         回復=(回復規則('実行環境',方式='同一作用再試行',最大再試行=1),))
        planner=役割計画器((action,),reg)
        root=_Integration(reg,({'state':'失敗','response_state':'失敗','reason':'実装例外'},))
        r=会話実行監督(planner,root,最大試行=5).実行(意味目的('成果',{}),{},原文='成果')
        self.assertFalse(r.応答.成立);self.assertEqual(root.calls,2)
        self.assertEqual([x.回復方針 for x in r.失敗],['同一作用再試行','停止'])

    def test_入力役割回復は子作用だけを再取得へ開く(self):
        reg=_registry('採用','初期','代替')
        child=意味目的('報告',{})
        root_goal=意味目的('成果',{})
        adopt=役割作用('採用作用','採用','成果',lambda p:(('報告',child),),lambda p:{},lambda p:True,
                       回復=(回復規則('取得不足','入力役割','報告',('初期報告',)),))
        first=役割作用('初期報告','初期','報告',lambda p:(),lambda p:{},lambda p:True)
        second=役割作用('代替報告','代替','報告',lambda p:(),lambda p:{},lambda p:True,費用=2)
        planner=役割計画器((adopt,first,second),reg)
        root=_Integration(reg,({'step':'役割工程:0002','reason':'会話失敗:取得不足:空'}, {'ok':True,'step':'役割工程:0002'}))
        r=会話実行監督(planner,root).実行(root_goal,{},原文='報告を採用')
        self.assertTrue(r.応答.成立)
        self.assertEqual(r.失敗[0].回復方針,'入力再取得')
        self.assertEqual(r.失敗[0].再開放,(child.鍵(),'初期報告'))
        self.assertEqual(r.試行[1]['固定被覆数'],1)  # 親の採用作用は固定

    def test_局所再計画は対象外の兄弟作用変更を拒否(self):
        reg=_registry('ROOT','L1','L2','R1','R2')
        left=意味目的('左',{}); right=意味目的('右',{}); goal=意味目的('成果',{})
        root_rule=役割作用('根','ROOT','成果',lambda p:(('左',left),('右',right)),lambda p:{},lambda p:True)
        l1=役割作用('左初期','L1','左',lambda p:(),lambda p:{},lambda p:True,
                    回復=(回復規則('検証失敗'),))
        l2=役割作用('左代替','L2','左',lambda p:(),lambda p:{},lambda p:True,費用=2)
        calls={'right':0}
        def right1(_):
            calls['right']+=1
            return calls['right']==1
        r1=役割作用('右初期','R1','右',lambda p:(),lambda p:{},right1)
        r2=役割作用('右代替','R2','右',lambda p:(),lambda p:{},lambda p:True,費用=2)
        planner=役割計画器((root_rule,l1,l2,r1,r2),reg)
        integration=_Integration(reg,({'step':'役割工程:0001','reason':'会話失敗:検証失敗:左失敗'}, {'ok':True}))
        with self.assertRaisesRegex(ValueError,'回復対象外'):
            会話実行監督(planner,integration).実行(goal,{},原文='左右を統合')
        self.assertEqual(integration.calls,1)

    def test_局所再計画は失敗した左部分木だけ変更し親と右を固定(self):
        reg=_registry('ROOT','L1','L2','R1')
        left=意味目的('左',{}); right=意味目的('右',{}); goal=意味目的('成果',{})
        root_rule=役割作用('根','ROOT','成果',lambda p:(('左',left),('右',right)),lambda p:{},lambda p:True)
        l1=役割作用('左初期','L1','左',lambda p:(),lambda p:{},lambda p:True,
                    回復=(回復規則('検証失敗'),))
        l2=役割作用('左代替','L2','左',lambda p:(),lambda p:{},lambda p:True,費用=2)
        r1=役割作用('右固定','R1','右',lambda p:(),lambda p:{},lambda p:True)
        planner=役割計画器((root_rule,l1,l2,r1),reg)
        integration=_Integration(reg,({'step':'役割工程:0001','reason':'会話失敗:検証失敗:左失敗'}, {'ok':True,'step':'役割工程:0003'}))
        r=会話実行監督(planner,integration).実行(goal,{},原文='左右を統合')
        self.assertTrue(r.応答.成立)
        self.assertEqual(r.試行[1]['固定被覆数'],2)  # 根と右
        second=dict((key,act) for _,key,act in r.試行[1]['工程作用'])
        self.assertEqual(second[left.鍵()],'左代替')
        self.assertEqual(second[right.鍵()],'右固定')
        self.assertEqual(second[goal.鍵()],'根')

    def test_意味未確定は利用者確認方針を記録し自動再試行しない(self):
        reg=_registry('A','B')
        a=役割作用('第一','A','成果',lambda p:(),lambda p:{},lambda p:True)
        b=役割作用('第二','B','成果',lambda p:(),lambda p:{},lambda p:True,費用=2)
        planner=役割計画器((a,b),reg)
        root=_Integration(reg,({'reason':'会話失敗:意味未確定:対象曖昧'},))
        r=会話実行監督(planner,root).実行(意味目的('成果',{}),{},原文='成果')
        self.assertEqual(root.calls,1);self.assertFalse(r.応答.成立)
        self.assertEqual(r.失敗[0].回復方針,'利用者確認')
        self.assertIsNone(r.失敗[0].再開放)

if __name__=='__main__': unittest.main()
