from unittest import TestCase
from pathlib import Path
from dataclasses import replace
from types import SimpleNamespace
import ast,tempfile
from minidora.コア.構文化再利用 import 構文化再利用
from minidora.駆動系.契約 import 関係項,関係節,関係変換契約,関係要求,関係証拠
from minidora.駆動系.学習 import (変換を合成,関係形成,_形成を保持,関係形成を隔離,
    有効形成を取得,実行経験を形成,関係学習状態)
from minidora.駆動系.取得 import 関係を取得
from minidora.駆動系.変換 import 関係を変換
from minidora.駆動系.射影 import 関係結果を射影
from minidora.駆動系.目的不足 import 関係不足
from minidora.入力系.不足観測 import 不足観測内容
from minidora.HDS駆動コア import HDS駆動コア
from minidora.HDS実行主体 import HDS実行主体,HDS実行状態,HDS関数作用,HDS作用結果,HDS作用状態
from minidora.統合駆動_v2.政策 import HDS運用政策
from minidora.統合駆動_v2.自動形成 import 自動経験形成作用
from minidora.統合駆動_v2.形成 import HDS形成採用状態

class キャッシュ契約試験(TestCase):
    def test_文脈宣言のない状態依存器を再利用しない(self):
        class 解析器:
            def __init__(self): self.n=0
            def コンパイル(self,x):self.n+=1;return self.n
        再利用=構文化再利用(解析器())
        self.assertEqual((再利用('x'),再利用('x')),(1,2))
    def test_返却値の変更を保持成果へ逆流させない(self):
        class 解析器:
            構文化文脈署名='v1'
            def コンパイル(self,x):return {'値':[x]}
        再利用=構文化再利用(解析器());初回=再利用('x');初回['値'].append('changed')
        次回=再利用('x');次回['値'].append('changed')
        self.assertEqual(再利用('x'),{'値':['x']});self.assertEqual(再利用.実行数,1)
    def test_文脈の版変更を再評価する(self):
        class 解析器:
            構文化文脈署名='v1'
            def コンパイル(self,x):return self.構文化文脈署名
        本体=解析器();再利用=構文化再利用(本体);self.assertEqual(再利用('x'),'v1')
        本体.構文化文脈署名='v2';self.assertEqual(再利用('x'),'v2');self.assertEqual(再利用.実行数,2)
    def test_実行中に文脈が変わる結果をキャッシュしない(self):
        class 解析器:
            構文化文脈署名=0
            def コンパイル(self,x):self.構文化文脈署名+=1;return self.構文化文脈署名
        再利用=構文化再利用(解析器());再利用('x');再利用('x')
        self.assertEqual(再利用.再利用数,0);self.assertEqual(len(再利用._保持),0)

class 非純粋形成試験(TestCase):
    def test_外部作用を再実行せず未検証形成へ保持(self):
        呼出=[]
        def 作用(状態):
            呼出.append(1)
            return HDS作用結果(HDS作用状態.成立,追加状態=frozenset({'観測済'}))
        操作=HDS関数作用('観測',作用,出力状態=('観測済',))
        初期=HDS実行状態(目的=('観測する',),要求状態=frozenset({'観測済'}))
        結果=HDS実行主体((操作,),政策=HDS運用政策(自動形成=False)).実行(初期)
        形成器=自動経験形成作用(初期,結果.履歴,(操作,))
        self.assertIsNotNone(形成器._経験(結果.状態))
        形成結果=形成器.実行(結果.状態)
        self.assertEqual(呼出,[1]);self.assertEqual(形成器.再現回数,0)
        self.assertEqual(形成結果.形成更新[0].採用状態,HDS形成採用状態.試行)

def 節(述語,項):return 関係節(述語,(('対象',項),))
def 形成組(番号):
    x=関係項('x',変数=True,束縛域='rule')
    a=関係変換契約('一次:'+str(番号),(節('始',x),),節('中',x),('定義:一次',))
    b=関係変換契約('二次:'+str(番号),(節('中',x),),節('終',x),('定義:二次',))
    c=変換を合成(a,b,0)
    return 関係形成(c.ID,c,a,b,0,('観測',),('経験',)),(a,b)

class 形成保持補強試験(TestCase):
    def setUp(self):
        self.組=tuple(形成組(i) for i in range(129))
        self.状態=_形成を保持({x.ID:x for x,_ in self.組},())
    def test_128件を超えても129番目の形成は保持される(self):
        self.assertEqual(len(self.状態.形成),128);self.assertEqual(len(self.状態.保管形成),1)
        self.assertEqual(len(self.状態.全形成),129)
    def test_保管された形成も有効規則から再取得できる(self):
        規則=tuple(r for _,規 in self.組 for r in 規)
        self.assertEqual(len(有効形成を取得(self.状態,規則)),129)
    def test_保管形成の反証隔離も他形成を消さない(self):
        対象=self.状態.保管形成[0].ID
        後=関係形成を隔離(self.状態,対象,'反証')
        self.assertEqual(len(後.全形成),129)
        self.assertEqual(next(x for x in 後.全形成 if x.ID==対象).採用状態,HDS形成採用状態.隔離)
    def test_全形成をチェックポイントから復元する(self):
        核=HDS駆動コア();核._関係学習状態=self.状態
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'state.json';核.継続状態を保存(p,リポジトリ版='r1')
            新=HDS駆動コア();新.継続状態を復元(p,リポジトリ版='r1')
            self.assertEqual(新.関係学習状態,self.状態)
    def test_256件を超えた新しい使用経験を捨てない(self):
        形成,規則=self.組[0]
        形成=replace(形成,支持経験=tuple('既存:'+str(i) for i in range(256)))
        状態=関係学習状態((形成,))
        項=関係項('新対象')
        要求=関係要求('照会','終を知る','世界',節('終',項),
            (関係証拠('新観測',節('始',項),('新しい出典',)),),規則)
        追加=有効形成を取得(状態,規則)
        取得=関係を取得(要求,追加);変換=関係を変換(要求,取得);出力=関係結果を射影(要求,変換,追加)
        self.assertIn(形成.ID,出力.使用形成)
        後=実行経験を形成(状態,要求,変換,出力)
        self.assertGreaterEqual(len(next(x for x in 後.全形成 if x.ID==形成.ID).支持経験),257)

class 不足観測補強試験(TestCase):
    def 不足(self,肯定=True):
        return 関係不足('r','p',関係節('activate',(('始点',関係項('["alpha"]','意味端点')),
            ('終点',関係項('["beta"]','意味端点'))),肯定,('温度=高',)),('回答:B',),('中間規則',))
    def test_中間関係が既存の選択観測形式へ接続する(self):
        r=不足観測内容(self.不足(),候補ラベル='B',言語='en')
        self.assertEqual(r['外部検索表層'],'alpha beta activate')
        self.assertIn('目的:p',r['provenance']);self.assertIn('利用先:回答:B',r['provenance'])
        self.assertIn(('意味条件','温度=高'),r['条件範囲'])
    def test_反対極性を検索要求の条件へ残す(self):
        r=不足観測内容(self.不足(False),候補ラベル='B',言語='en')
        self.assertIn(('極性','否定'),r['条件範囲'])
    def test_未完了計画から観測を捏造しない(self):
        with self.assertRaises(ValueError):不足観測内容(replace(self.不足(),状態='予算未完了'),候補ラベル='B',言語='en')

class 監査検索言語試験(TestCase):
    def test_G06証拠probeは入力言語で翻訳せず正本表層を保持する(self):
        # G06は会話表現ではなくHDS観測演算子。英語入力でも旧43能力の検索表層を変えない。
        p=Path(__file__).resolve().parents[2]/'src/minidora/HDS構文化失敗.py'
        tree=ast.parse(p.read_text(encoding='utf-8'))
        fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='HDS監査参照候補生成')
        構文木=ast.Module(body=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0),fn],type_ignores=[])
        env={'HDS監査参照候補':lambda *a:a}
        exec(compile(ast.fix_missing_locations(構文木),str(p),'exec'),env)
        for 言語 in ('ja','en'):
            ir=SimpleNamespace(座標=(),座標辞書=lambda:{},正規化文='対象',原文='対象',入力言語=言語)
            r=env['HDS監査参照候補生成'](ir,(SimpleNamespace(関門対応=('G06',)),))
            self.assertTrue(r[0][0].endswith('証拠'));self.assertEqual(r[0][1],'証拠')
