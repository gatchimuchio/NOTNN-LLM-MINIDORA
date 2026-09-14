from __future__ import annotations
from types import SimpleNamespace
import unittest

from minidora.製品版.型 import 能力結果
from minidora.会話意味 import 意味目的
from minidora.役割計画 import 役割作用, 役割計画器
from minidora.実行回復 import 回復規則
from minidora.実行トランザクション import (
    実行トランザクション版, 実行トランザクション台帳,
    台帳を更新, 台帳を失効, 再開投影を作る,
)
from minidora.会話実行監督 import 会話実行監督, 会話実行監督版, 会話実行Transaction監督版


def _reg(*rows):
    return tuple({'名前': n, '版': 'v1', '外部読取': ext} for n, ext in rows)


def _rec(step, state, reason='', out=''):
    return SimpleNamespace(工程=step, 状態=state, 理由=reason, 入力ハッシュ='in:'+step, 出力ハッシュ=out)


def _run(history, middle=()):
    return SimpleNamespace(履歴=tuple(history), 中間結果=tuple(middle), ルートハッシュ='run', 監査整合=lambda: True)


class Transaction単体試験(unittest.TestCase):
    def test_固定再開と失効(self):
        child, goal = 意味目的('子', {}), 意味目的('成果', {})
        reg = _reg(('CHILD', False), ('ROOT', False))
        rules = (
            役割作用('根', 'ROOT', '成果', lambda p:(('子',child),), lambda p:{}, lambda p:True),
            役割作用('子', 'CHILD', '子', lambda p:(), lambda p:{}, lambda p:True),
        )
        plan = 役割計画器(rules, reg).計画する(goal,{})
        steps = {key:sid for sid,key,_ in plan.工程作用}
        value = 能力結果(True,'fixed')
        response = SimpleNamespace(実行=_run((_rec(steps[child.鍵()],'合格'),), ((steps[child.鍵()],value),)))
        ledger = 台帳を更新(実行トランザクション台帳('tx'), plan, response)
        projected = 再開投影を作る(ledger, plan, 再実行目的={goal.鍵()})
        self.assertEqual(projected.固定工程,(steps[child.鍵()],))
        self.assertEqual(tuple(s.識別子 for s in projected.計画.工程),(steps[goal.鍵()],))
        self.assertEqual(projected.計画.工程[0].入力[0].領域,'入力')
        self.assertEqual(台帳を失効(ledger,{child.鍵()}).固定成果,())
        self.assertEqual(実行トランザクション版,'MINIDORA-実行トランザクション-v0.1')
        self.assertEqual(会話実行監督版,'MINIDORA-会話実行監督-v0.2')
        self.assertEqual(会話実行Transaction監督版,'MINIDORA-会話実行監督-Transaction-v0.1')


class _RetryIntegration:
    def __init__(self, reg, child_step, root_step):
        self.reg, self.child_step, self.root_step = reg, child_step, root_step
        self.state=('s',0); self.calls=0; self.prepared=[]
    def 起点(self): return self.state
    def 能力一覧(self): return self.reg
    def _停止(self, stop):
        if stop and stop(): raise InterruptedError()
    def 準備(self, plan, data, 依頼文=''):
        self.prepared.append((plan,data)); return SimpleNamespace(起点=self.state,ハッシュ='p'+str(len(self.prepared)))
    def 実行(self, packed, 外部読取許可=False, 停止要求=None):
        self.calls += 1
        if self.calls == 1:
            hist=(_rec(self.child_step,'合格'), _rec(self.root_step,'失敗','能力呼出・結果契約違反:RuntimeError'))
            return SimpleNamespace(成立=False,状態='失敗',理由='実装例外',実行=_run(hist,((self.child_step,能力結果(True,'観測')),)))
        return SimpleNamespace(成立=True,状態='合格',理由='',実行=_run((_rec(self.root_step,'合格'),)))


class Transaction監督試験(unittest.TestCase):
    def test_成功済み外部観測を同一取引で二度実行しない(self):
        child, goal = 意味目的('取得結果',{}), 意味目的('成果',{})
        reg=_reg(('FETCH',True),('ROOT',False))
        rules=(
            役割作用('根','ROOT','成果',lambda p:(('取得',child),),lambda p:{},lambda p:True,
                     回復=(回復規則('実行環境',方式='同一作用再試行',最大再試行=1),)),
            役割作用('外部取得','FETCH','取得結果',lambda p:(),lambda p:{},lambda p:True,外部読取=True),
        )
        planner=役割計画器(rules,reg); plan=planner.計画する(goal,{},外部許可=True)
        steps={key:sid for sid,key,_ in plan.工程作用}; integration=_RetryIntegration(reg,steps[child.鍵()],steps[goal.鍵()])
        result=会話実行監督(planner,integration).実行(goal,{},原文='取得して処理',外部許可=True)
        self.assertTrue(result.応答.成立); self.assertEqual(integration.calls,2)
        self.assertEqual(len(integration.prepared[1][0].工程),1)
        self.assertEqual(result.試行[1]['外部固定工程'],(steps[child.鍵()],))
        self.assertEqual(result.試行[1]['外部工程'],())
        self.assertEqual(result.試行[0]['トランザクション印'],result.試行[1]['トランザクション印'])

    def test_局所再計画は兄弟を固定し対象と祖先だけ再実行する(self):
        left,right,goal=意味目的('左',{}),意味目的('右',{}),意味目的('成果',{})
        reg=_reg(('L1',False),('L2',False),('R',False),('ROOT',False))
        rules=(
            役割作用('根','ROOT','成果',lambda p:(('左',left),('右',right)),lambda p:{},lambda p:True,
                     回復=(回復規則('取得不足','入力役割','左',('左初期',)),)),
            役割作用('左初期','L1','左',lambda p:(),lambda p:{},lambda p:True),
            役割作用('左代替','L2','左',lambda p:(),lambda p:{},lambda p:True,費用=2),
            役割作用('右固定','R','右',lambda p:(),lambda p:{},lambda p:True),
        )
        planner=役割計画器(rules,reg); first=planner.計画する(goal,{})
        steps={key:sid for sid,key,_ in first.工程作用}
        class I:
            def __init__(self): self.state=('x',0); self.calls=0; self.prepared=[]
            def 起点(self): return self.state
            def 能力一覧(self): return reg
            def _停止(self, stop):
                if stop and stop(): raise InterruptedError()
            def 準備(self, plan, data, 依頼文=''):
                self.prepared.append((plan,data)); return SimpleNamespace(起点=self.state,ハッシュ='x'+str(len(self.prepared)))
            def 実行(self, packed, 外部読取許可=False, 停止要求=None):
                self.calls+=1
                if self.calls==1:
                    hist=(_rec(steps[left.鍵()],'合格'),_rec(steps[right.鍵()],'合格'),_rec(steps[goal.鍵()],'保留','会話失敗:取得不足:左'))
                    mid=((steps[left.鍵()],能力結果(True,'old')),(steps[right.鍵()],能力結果(True,'right')))
                    return SimpleNamespace(成立=False,状態='保留',理由='左',実行=_run(hist,mid))
                return SimpleNamespace(成立=True,状態='合格',理由='',実行=_run((_rec(steps[goal.鍵()],'合格'),)))
        integration=I(); result=会話実行監督(planner,integration).実行(goal,{},原文='左右')
        self.assertTrue(result.応答.成立)
        ids={s.識別子 for s in integration.prepared[1][0].工程}
        self.assertNotIn(steps[right.鍵()],ids); self.assertIn(steps[goal.鍵()],ids)
        self.assertEqual(result.試行[1]['再開固定目的'],(right.鍵(),))
        self.assertEqual(set(result.試行[1]['再実行目的']),{left.鍵(),goal.鍵()})
        actions={key:act for _,key,act in result.試行[1]['工程作用']}
        self.assertEqual(actions[left.鍵()],'左代替')


if __name__=='__main__': unittest.main()
