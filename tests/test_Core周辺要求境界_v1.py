from __future__ import annotations
from types import SimpleNamespace
import unittest

from minidora.会話意味 import 意味目的
from minidora.役割計画 import 役割作用, 役割計画器
from minidora.会話実行監督 import 会話実行監督

class _統合Stub:
    def __init__(self, registry, plan_hash='plan-hash'):
        self.registry=registry; self.plan_hash=plan_hash; self.state=('s',0)
    def 起点(self): return self.state
    def 能力一覧(self): return self.registry
    def _停止(self, stop):
        if stop and stop(): raise InterruptedError()
    def 準備(self, plan, data, 依頼文=''):
        return SimpleNamespace(起点=self.state, ハッシュ=self.plan_hash)
    def 実行(self, packed, 外部読取許可=False, 停止要求=None):
        run=SimpleNamespace(履歴=(), 中間結果=(), ルートハッシュ='run')
        return SimpleNamespace(成立=True, 状態='合格', 理由='', 実行=run)

class Core周辺要求境界試験(unittest.TestCase):
    def setUp(self):
        self.registry=({'名前':'A','版':'v1','外部読取':False},)
        self.action=役割作用('作用','A','成果',lambda p:(),lambda p:{},lambda p:True)
        self.goal=意味目的('成果',{})

    def test_要求被覆と準備済み計画を一つの境界契約へ結合(self):
        result=会話実行監督(役割計画器((self.action,),self.registry),_統合Stub(self.registry)).実行(
            self.goal,{},原文='現在の依頼')
        self.assertTrue(result.応答.成立)
        self.assertEqual(len(result.試行[0]['要求境界契約印']),64)

    def test_同一要求でも準備済み計画印の差を同一視しない(self):
        planner=役割計画器((self.action,),self.registry)
        a=会話実行監督(planner,_統合Stub(self.registry,'plan-a')).実行(self.goal,{},原文='現在の依頼').試行[0]
        b=会話実行監督(planner,_統合Stub(self.registry,'plan-b')).実行(self.goal,{},原文='現在の依頼').試行[0]
        self.assertNotEqual(a['要求境界契約印'],b['要求境界契約印'])
        self.assertEqual(a['要求被覆印'],b['要求被覆印'])

if __name__=='__main__': unittest.main()
