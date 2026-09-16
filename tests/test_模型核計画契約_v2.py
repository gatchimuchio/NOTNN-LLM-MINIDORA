from __future__ import annotations
from dataclasses import replace
from types import SimpleNamespace
import unittest

from minidora.製品版.型 import 能力結果
from minidora.汎用要求IR import 汎用要求IR, 目的指定, 要求IR版
from minidora.会話意味 import 意味目的
from minidora.役割計画 import 役割作用, 役割計画器, 役割計画版
from minidora.実行回復 import 回復規則
from minidora.会話実行監督 import 会話実行監督


def _要求():
    text='Aを変換して、その結果を出力する'
    return 汎用要求IR(
        text, {'A':能力結果(True,'x')}, {'A':'原型'},
        (目的指定('g1','A','中間','p1',(0,5)), 目的指定('g2','g1','終端','p2',(6,len(text)))),
        {'p1':{},'p2':{}}, ('g2',))


class 模型核要求被覆試験(unittest.TestCase):
    def test_RequestIR_v2は明示要素の被覆台帳を返す(self):
        self.assertEqual(要求IR版,'MINIDORA-汎用要求IR-v0.2')
        ledger=_要求().被覆台帳()
        self.assertEqual([x.種別 for x in ledger],['素材','目的','目的','引数','引数','出力'])
        self.assertEqual(ledger[0].参照先,('g1',))
        self.assertEqual(ledger[-1].識別子,'g2')

    def test_出力へ接続しない目的をRequestIR境界で拒否(self):
        r=_要求();extra=目的指定('孤立','A','中間','p3',(0,5))
        with self.assertRaisesRegex(ValueError,'出力に接続していない目的'):
            replace(r,目的=(*r.目的,extra),引数資料={**r.引数資料,'p3':{}}).固定複製()

    def test_目的循環をRequestIR境界で拒否(self):
        r=_要求();first=replace(r.目的[0],対象='g2')
        with self.assertRaisesRegex(ValueError,'目的依存の循環'):
            replace(r,目的=(first,r.目的[1])).固定複製()


class 模型核作用契約試験(unittest.TestCase):
    def setUp(self):
        self.登録簿=({'名前':'合成','版':'v1','外部読取':False},{'名前':'代替','版':'v1','外部読取':False})
        def raw(name): return 意味目的('原資料',{'資料':name})
        self.rule=役割作用('二資料合成','合成','比較結果',
            lambda p:(('左',raw(p['左'])),('右',raw(p['右']))),
            lambda p:{'方式':'比較','左':p['左'],'右':p['右']},lambda p:True,
            不成立条件=('入力不足',),保持事項=('対象','由来'))
        self.goal=意味目的('比較結果',{'左':'A','右':'B'})
        self.materials={'A':能力結果(True,'a'),'B':能力結果(True,'b')}

    def test_作用契約_v2は複数素材と実体契約を被覆する(self):
        self.assertEqual(役割計画版,'MINIDORA-役割計画-v0.3')
        結果=役割計画器((self.rule,),self.登録簿).計画する(self.goal,self.materials)
        self.assertEqual({x.素材 for x in 結果.要求被覆 if x.解決=='素材'},{'A','B'})
        root=next(x for x in 結果.要求被覆 if x.目的鍵==self.goal.鍵())
        self.assertEqual(tuple(n for n,_ in root.入力役割),('左','右'))
        self.assertTrue(root.契約印);self.assertTrue(結果.作用契約印)

    def test_設定関数を探索後に再評価しない(self):
        calls={'n':0}
        def settings(p): calls['n']+=1;return {'呼出':calls['n']}
        結果=役割計画器((replace(self.rule,設定=settings),),self.登録簿).計画する(self.goal,self.materials)
        self.assertEqual(calls['n'],1)
        config=next(v for k,v in 結果.資料.items() if k.startswith('設定:'))
        self.assertEqual(config.データ,{'呼出':1})

    def test_同一入力は同一の被覆と作用契約印(self):
        p=役割計画器((self.rule,),self.登録簿)
        a=p.計画する(self.goal,self.materials);b=p.計画する(self.goal,self.materials)
        self.assertEqual(a.要求被覆,b.要求被覆);self.assertEqual(a.作用契約印,b.作用契約印)

    def test_保持事項の重複を契約登録時に拒否(self):
        with self.assertRaisesRegex(ValueError,'保持事項'):
            役割計画器((replace(self.rule,保持事項=('対象','対象')),),self.登録簿)


class _統合Stub:
    def __init__(self,登録簿): self.登録簿=登録簿;self.calls=0;self.状態=('s',0)
    def 起点(self): return self.状態
    def 能力一覧(self): return self.登録簿
    def _停止(self,stop):
        if stop and stop(): raise InterruptedError()
    def 準備(self,plan,資料,依頼文=''): return SimpleNamespace(起点=self.状態,ハッシュ='plan-'+str(self.calls+1))
    def 実行(self,packed,外部読取許可=False,停止要求=None):
        self.calls+=1
        if self.calls==1:
            history=(SimpleNamespace(理由='会話失敗:検証失敗:候補不適合',状態='保留',工程='役割工程:0001',入力ハッシュ='input-1'),)
            run=SimpleNamespace(履歴=history,中間結果=(),ルートハッシュ='run-1')
            return SimpleNamespace(成立=False,状態='保留',理由='候補不適合',実行=run)
        history=(SimpleNamespace(理由='',状態='合格',工程='役割工程:0001',入力ハッシュ='input-2'),)
        run=SimpleNamespace(履歴=history,中間結果=(),ルートハッシュ='run-2')
        return SimpleNamespace(成立=True,状態='合格',理由='',実行=run)


class 模型核失敗駆動再計画試験(unittest.TestCase):
    def setUp(self):
        self.登録簿=({'名前':'A','版':'v1','外部読取':False},{'名前':'B','版':'v1','外部読取':False})
        self.first=役割作用('第一','A','成果',lambda p:(),lambda p:{},lambda p:True,回復=(回復規則('検証失敗'),))
        self.second=役割作用('第二','B','成果',lambda p:(),lambda p:{},lambda p:True,費用=2)
        self.goal=意味目的('成果',{})

    def test_再計画ごとに被覆と実体契約を監査する(self):
        planner=役割計画器((self.first,self.second),self.登録簿);root=_統合Stub(self.登録簿)
        結果=会話実行監督(planner,root).実行(self.goal,{},原文='成果')
        self.assertTrue(結果.応答.成立);self.assertEqual(len(結果.試行),2)
        self.assertTrue(all(x['要求被覆印'] and x['作用契約印'] for x in 結果.試行))
        self.assertNotEqual(結果.試行[0]['作用契約印'],結果.試行[1]['作用契約印'])
        self.assertEqual(結果.失敗[0].再開放,(self.goal.鍵(),'第一'))

    def test_被覆欠落計画を実行前に拒否する(self):
        planner=役割計画器((self.second,),self.登録簿);original=planner.計画する
        planner.計画する=lambda *a,**k: replace(original(*a,**k),要求被覆=())
        root=_統合Stub(self.登録簿)
        with self.assertRaisesRegex(ValueError,'要求被覆'):
            会話実行監督(planner,root).実行(self.goal,{},原文='成果')
        self.assertEqual(root.calls,0)

    def test_再計画で失敗していない同一作用の契約を横滑りさせない(self):
        calls={'n':0}
        leaf_a=役割作用('第一','A','中間',lambda p:(),lambda p:{},lambda p:True,回復=(回復規則('検証失敗'),))
        leaf_b=役割作用('第二','B','中間',lambda p:(),lambda p:{},lambda p:True,費用=2)
        def root_settings(p):
            calls['n']+=1
            return {'世代':calls['n']}
        root_rule=役割作用('終端','A','成果',lambda p:(('子',意味目的('中間',{})),),root_settings,lambda p:True)
        planner=役割計画器((root_rule,leaf_a,leaf_b),self.登録簿)
        統合=_統合Stub(self.登録簿)
        # 最初の失敗工程を子工程へ合わせる。親「終端」は失敗していないのに、
        # 再計画で同じ作用の設定だけが変わるなら実行前に停止する。
        original_execute=統合.実行
        def execute(packed,外部読取許可=False,停止要求=None):
            統合.calls+=1
            if 統合.calls==1:
                history=(SimpleNamespace(理由='会話失敗:検証失敗:候補不適合',状態='保留',工程='役割工程:0001',入力ハッシュ='input-1'),)
                run=SimpleNamespace(履歴=history,中間結果=(),ルートハッシュ='run-1')
                return SimpleNamespace(成立=False,状態='保留',理由='候補不適合',実行=run)
            raise AssertionError('契約横滑りを検出する前に二回目を実行した')
        統合.実行=execute
        with self.assertRaisesRegex(ValueError,'既存作用契約'):
            会話実行監督(planner,統合).実行(意味目的('成果',{}),{},原文='成果')
        self.assertEqual(統合.calls,1)

if __name__=='__main__': unittest.main()
