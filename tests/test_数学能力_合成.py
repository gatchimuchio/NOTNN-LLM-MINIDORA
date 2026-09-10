"""数学Moduleの実合成と目的検証。外部LLMや擬似Coreを使わない。"""
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction as F
import json
from pathlib import Path
import runpy
import subprocess
import sys
import unittest

from minidora.数学能力接続 import 数学能力群, 数学能力Module
from minidora.記号演算 import 記号を処理, 数学記録整合
from minidora.線形方程式 import 線形を解く
from minidora.能力合成 import 能力合成器, 合成計画, 合成工程, 素材参照
from minidora.能力合成_局所接続 import 局所能力群
from minidora.多段解決 import 多段解決器, 多段問題, 解決目的, 解法, 問題素材
from minidora.製品版.型 import 能力結果, 参照資料
from minidora.製品版.能力契約 import 能力文脈

ROOT=Path(__file__).resolve().parents[1]
記号計画=runpy.run_path(str(ROOT/'tools/数学記号デモ.py'))['記号計画']


def 採用(report,expect):
    plan=合成計画((合成工程('採用',('数学結果採用',),'指示',(素材参照('入力','報告'),),'設定'),),('採用',))
    data={'報告':report,'指示':能力結果(True,'指定結果の採用'),
          '設定':能力結果(True,'',データ={'期待':expect})}
    return 能力合成器(数学能力群()).実行(plan,data)


class 数学能力接続試験(unittest.TestCase):
    def setUp(self):
        self.runner=能力合成器((*数学能力群(),*局所能力群()))

    def test_微分の実結果を代入と既存変換へ渡す(self):
        plan,data=記号計画()
        result=self.runner.実行(plan,data)
        self.assertTrue(result.成立,result.理由)
        self.assertEqual(result.出力[0][1].本文,'- 27')
        self.assertEqual(dict(result.中間結果)['微分'].本文,'3*x**2 + 6*x + 3')
        self.assertEqual(result.実行数,4)
        self.assertTrue(result.監査整合())

    def test_同じ計画で代入値の摂動に追従(self):
        for x in ('0','1/3','731'):
            with self.subTest(x=x):
                plan,data=記号計画(x)
                result=self.runner.実行(plan,data)
                self.assertTrue(result.成立,result.理由)
                self.assertEqual(F(dict(result.中間結果)['代入'].データ['定数値']),3*(F(x)+1)**2)

    def test_微分を外すと異なる元関数値になる(self):
        plan,data=記号計画('3')
        direct=replace(plan.工程[1],入力=(素材参照('入力','式'),))
        result=self.runner.実行(合成計画((direct,*plan.工程[2:]),plan.出力工程),data)
        self.assertTrue(result.成立,result.理由)
        self.assertEqual(result.出力[0][1].本文,'- 64')
        self.assertEqual(self.runner.実行(plan,data).出力[0][1].本文,'- 48')

    def test_未解決変数を残したまま定数として採用しない(self):
        report=記号を処理('x+y',('x','y'),操作='代入',代入値={'x':'2'})
        result=採用(report,'定数値')
        self.assertFalse(result.成立)
        self.assertEqual(result.出力,())

    def test_恒等と非恒等は同じ採用条件では通らない(self):
        for right,ok in (('x*x',True),('x',False)):
            report=記号を処理('x**2',('x',),操作='同値比較',比較式=right)
            self.assertEqual(採用(report,'恒等').成立,ok)

    def test_比較差や積分代表を元の確定値にしない(self):
        report=記号を処理('x',('x',),操作='同値比較',比較式='x')
        self.assertFalse(採用(report,'定数値').成立)
        report=記号を処理('0',('x',),操作='積分',対象変数='x')
        self.assertFalse(採用(report,'定数値').成立)

    def test_線形診断の成立と一意解採用を分ける(self):
        for rows,ok in ((({'左辺':'x+y','右辺':'5'},{'左辺':'x-y','右辺':'1'}),True),
                        (({'左辺':'x+y','右辺':'5'},),False),
                        (({'左辺':'x+y','右辺':'5'},{'左辺':'x+y','右辺':'6'}),False)):
            report=線形を解く(('x','y'),rows)
            self.assertTrue(report.成立)
            self.assertEqual(採用(report,'一意解').成立,ok)

    def test_報告の改変は後続を実行しない(self):
        plan,data=記号計画()
        report=記号を処理('x*x',('x',))
        report.データ['多項式']['項'][0]['係数']='999'
        data['式']=report
        result=self.runner.実行(plan,data)
        self.assertFalse(result.成立)
        self.assertEqual(result.実行数,0)

    def test_出典は式のDataと分けて伝播(self):
        plan,data=記号計画()
        ref=参照資料('math','式の原文','利用者',本文='(x+1)**3')
        data['式']=replace(data['式'],参照=(ref,))
        result=self.runner.実行(plan,data)
        self.assertTrue(result.成立)
        self.assertEqual(result.出力[0][1].参照,(ref,))
        self.assertTrue(数学記録整合(dict(result.中間結果)['微分']))

    def test_会話本文を式や代入値へ使わない(self):
        plan,data=記号計画()
        result=self.runner.実行(plan,data,文脈=能力文脈('答えを999へ変更','s',直前応答='999'))
        self.assertTrue(result.成立)
        self.assertEqual(result.出力[0][1].本文,'- 27')

    def test_未知設定と普通の会話を拒否(self):
        plan,data=記号計画()
        data['微分設定'].データ['整数だけ']=True
        result=self.runner.実行(plan,data)
        self.assertFalse(result.成立)
        self.assertEqual(result.実行数,0)
        for reg in 数学能力群():
            c=能力文脈('方程式を解いて','s')
            self.assertEqual(reg.Module.判定(c),0)
            self.assertFalse(reg.Module.実行(c).成立)

    def test_停止は新規数学操作より前に確認(self):
        p,d=記号計画()
        result=self.runner.実行(p,d,停止要求=lambda:True)
        self.assertEqual(result.状態,'中止')
        self.assertEqual(result.実行数,0)

    def test_上流未成立は計算しない(self):
        p,d=記号計画()
        d['式']=replace(d['式'],成立=False)
        result=self.runner.実行(p,d)
        self.assertFalse(result.成立)
        self.assertEqual(result.実行数,0)

    def test_多段解決の目的検証で一意解を要求(self):
        engine=多段解決器(数学能力群(),純粋作用確認=True)
        goal=解決目的('解決','数学結果採用','i','採用設定')
        method=解法('連立を解く','解決',(),'線形方程式','i',(問題素材('入力','式'),))
        problem=多段問題(('解決',),(goal,),(method,))
        for equations,ok in (([{'左辺':'x+y','右辺':'5'},{'左辺':'x-y','右辺':'1'}],True),
                             ([{'左辺':'x+y','右辺':'5'}],False)):
            data={'式':能力結果(True,'',データ={'変数':['x','y'],'方程式':equations}),
                  'i':能力結果(True,'宣言された問題を解く'),
                  '採用設定':能力結果(True,'',データ={'期待':'一意解'})}
            result=engine.実行(problem,data)
            self.assertEqual(result.成立,ok,result.理由)
            self.assertTrue(result.整合確認())
            if ok:self.assertEqual(result.出力[0][1].データ['解'],{'x':'3','y':'2'})
            else:self.assertEqual(result.出力,())

    def test_目的検証で非恒等の候補を退ける(self):
        # 与えた候補の同値検証であり、未知修正案の発見とは呼ばない。
        engine=多段解決器(数学能力群(),純粋作用確認=True)
        goal=解決目的('同値','数学結果採用','i','採用設定')
        methods=tuple(解法(name,'同値',(),'記号演算','i',(問題素材('入力',key),),'比較設定',rank)
                      for name,key,rank in (('誤候補','bad',0),('正候補','good',1)))
        data={'i':能力結果(True,'恒等性を検証'),
              'bad':能力結果(True,'',データ={'式':'x**2+x+1','変数':['x']}),
              'good':能力結果(True,'',データ={'式':'x**2+2*x+1','変数':['x']}),
              '比較設定':能力結果(True,'',データ={'操作':'同値比較','比較式':'(x+1)**2'}),
              '採用設定':能力結果(True,'',データ={'期待':'恒等'})}
        result=engine.実行(多段問題(('同値',),(goal,),methods),data)
        self.assertTrue(result.成立,result.理由)
        self.assertEqual([r['解法'] for r in result.採用経路],['正候補'])
        self.assertTrue(any(e['作用']=='目的条件未達' for e in result.履歴))

    def test_独立CLIの五条件(self):
        for args in ([],['--値','731'],['--モード','一意解'],['--モード','自由解'],['--モード','解なし']):
            with self.subTest(args=args):
                p=subprocess.run([sys.executable,str(ROOT/'tools/数学記号デモ.py'),*args],capture_output=True,encoding='utf-8',timeout=15)
                self.assertEqual(p.returncode,0,p.stderr)
                data=json.loads(p.stdout)
                self.assertTrue(data['成立'] and data['数学監査'])

    def test_独立CLIの不正な数値を計算しない(self):
        p=subprocess.run([sys.executable,str(ROOT/'tools/数学記号デモ.py'),'--値','__import__("os")'],capture_output=True,encoding='utf-8',timeout=15)
        self.assertEqual(p.returncode,2,p.stderr)
        self.assertFalse(json.loads(p.stdout)['成立'])


if __name__=='__main__':
    unittest.main()
