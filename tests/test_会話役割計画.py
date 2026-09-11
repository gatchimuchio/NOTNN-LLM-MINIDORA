"""役割計画の必要条件、停止、未知作用への非外挿を検査する。"""
from dataclasses import replace
import unittest
from minidora.汎用会話 import 汎用会話セッション
from minidora.役割計画 import 役割計画器,役割作用
from minidora.会話作用契約 import 会話作用群
from minidora.会話意味 import 意味目的
from minidora.会話実行監督 import 会話実行監督
from minidora.製品版.型 import 能力結果

class 役割計画試験(unittest.TestCase):
    def setUp(self):
        self.s=汎用会話セッション('計画')
        self.rules=会話作用群();self.registry=self.s.統合.能力一覧()
        self.p=役割計画器(self.rules,self.registry)
        self.left={'資料':'A','形式':'JSON','属性':'売上','単位':'円','行条件':{}}
        self.right={**self.left,'資料':'B'}
        self.goal=意味目的('比較回答',{'左':self.left,'右':self.right,'時点差':False,'詳細':False})
        self.data={'A':能力結果(True,'{"売上":75}'),'B':能力結果(True,'{"売上":60}')}
    def test_左右の入力は別のDataに束縛される(self):
        p=self.p.計画する(self.goal,self.data)
        self.assertEqual({r.識別子 for s in p.計画.工程 for r in s.入力 if r.領域=='入力'},{'素材:A','素材:B'})
    def test_計画時に能力を実行しない(self):
        self.p.計画する(self.goal,self.data)
        self.assertEqual(self.s.統合.再利用統計()['能力別'],{})
        self.assertEqual(self.s.統合.採用履歴スナップショット()[1],())
    def test_資料が欠ければ架空の資料を作らない(self):
        with self.assertRaises(ValueError):self.p.計画する(self.goal,{'A':self.data['A']})
    def test_同順位の二作用は任意に選ばない(self):
        duplicate=replace(self.rules[0],識別子='同じ費用の別作用')
        p=役割計画器((*self.rules,duplicate),self.registry)
        with self.assertRaises(ValueError):p.計画する(self.goal,self.data)
    def test_存在しない能力は登録できない(self):
        with self.assertRaises(ValueError):役割計画器((replace(self.rules[0],能力='未知能力'),),self.registry)
    def test_外部作用を純粋作用に偽装しない(self):
        with self.assertRaises(ValueError):役割計画器((replace(self.rules[-1],外部読取=False),),self.registry)
    def test_費用ゼロを許さない(self):
        with self.assertRaises(ValueError):役割計画器((replace(self.rules[0],費用=0),),self.registry)
    def test_目的の循環で止まる(self):
        loop=役割作用('循環','数量比較','循環',lambda p:(('自己',意味目的('循環',p)),),lambda p:{},lambda p:True)
        p=役割計画器((loop,),self.registry)
        with self.assertRaises(ValueError):p.計画する(意味目的('循環',{}),{})
    def test_探索上限を合格にしない(self):
        p=役割計画器(self.rules,self.registry,最大展開数=1)
        with self.assertRaises(ValueError):p.計画する(self.goal,self.data)
    def test_再計画で対象全体を取り違えない(self):
        key=意味目的('数量',self.right).鍵();p=self.p.計画する(self.goal,self.data,禁止=((key,'直下数量選択'),))
        actions=[x[2] for x in p.工程作用]
        self.assertEqual(actions.count('直下数量選択'),1);self.assertEqual(actions.count('入れ子数量選択'),1)
    def test_原因という型名だけで解決しない(self):
        with self.assertRaises(ValueError):self.p.計画する(意味目的('売上低下の原因',{}),self.data)
    def test_無許可の検索経路は計画化しない(self):
        with self.assertRaises(ValueError):self.p.計画する(意味目的('取得回答',{'主題':'機器A','属性':'電圧','単位':'V','詳細':False}),{})
    def test_監督の試行上限を守る(self):
        supervisor=会話実行監督(self.p,self.s.統合,最大試行=1)
        self.data['B']=能力結果(True,'{"箱":{"売上":60}}')
        r=supervisor.実行(self.goal,self.data,原文='比較要求')
        self.assertFalse(r.応答.成立);self.assertEqual(len(r.試行),1)
    def test_版が変わった計画器を実行しない(self):
        supervisor=会話実行監督(self.p,self.s.統合);self.p.登録印='変更'
        with self.assertRaises(ValueError):supervisor.実行(self.goal,self.data,原文='比較要求')
if __name__=='__main__':unittest.main()
