"""回復契約による監督を、固有名を持たない別能力系で接続確認する。"""
from dataclasses import replace
from copy import deepcopy
from unittest.mock import patch
import unittest
from minidora.実行回復 import 回復規則,失敗を分類
from minidora.役割計画 import 役割作用,役割計画器
from minidora.会話意味 import 意味目的
from minidora.会話実行監督 import 会話実行監督
from minidora.会話作用契約 import 会話作用群
from minidora.汎用会話 import 汎用会話セッション
from minidora.統合実行 import 統合セッション
from minidora.能力合成 import 登録能力
from minidora.製品版.型 import 能力結果
from minidora.会話回答 import 回答記録整合
from minidora.会話数量 import 比較記録整合
from minidora.応答構成 import 能力結果を復元

class _部品:
    版='回復試験-v1';優先度=0
    def __init__(self,name,result): self.名前=name;self.result=result;self.calls=0
    def 判定(self,context): return 1.0
    def 実行(self,context):
        self.calls+=1
        return self.result(context) if callable(self.result) else deepcopy(self.result)


def setup(code='検証失敗',recovery=True):
    bad=_部品('試行部品',能力結果(False,'',保留理由='会話失敗:'+code+':入力候補が目的条件を満たさない'))
    good=_部品('代替部品',能力結果(True,'7'))
    root=統合セッション('独立回復',追加能力=(登録能力(bad),登録能力(good)))
    rules=(役割作用('初期候補','試行部品','成果',lambda p:(),lambda p:{},lambda p:True,
                  回復=(回復規則(code),) if recovery else ()),
           役割作用('代替候補','代替部品','成果',lambda p:(),lambda p:{},lambda p:True,費用=2))
    planner=役割計画器(rules,root.能力一覧())
    return root,planner,bad,good

class 共通回復試験(unittest.TestCase):
    def test_別能力の検証失敗から同じ監督器で回復する(self):
        root,planner,bad,good=setup()
        r=会話実行監督(planner,root).実行(意味目的('成果',{}),{},原文='成果を得る')
        self.assertTrue(r.応答.成立);self.assertEqual(r.応答.本文,'7')
        self.assertEqual((bad.calls,good.calls),(1,1));self.assertEqual(len(r.失敗),1)
        self.assertEqual(r.失敗[0].分類,'検証失敗');self.assertTrue(r.失敗[0].回復契約)
    def test_能力や作用の名称を変えても監督器を変更しない(self):
        root,planner,bad,good=setup()
        planner=役割計画器(tuple(replace(r,識別子='別名'+str(i)) for i,r in enumerate(planner.作用)),root.能力一覧())
        r=会話実行監督(planner,root).実行(意味目的('成果',{}),{},原文='成果')
        self.assertTrue(r.応答.成立);self.assertEqual(r.失敗[0].作用,'別名0')
    def test_契約のない失敗は代替能力があっても再試行しない(self):
        root,planner,bad,good=setup(recovery=False)
        r=会話実行監督(planner,root).実行(意味目的('成果',{}),{},原文='成果')
        self.assertFalse(r.応答.成立);self.assertEqual(good.calls,0)
    def test_未知失敗は分類名を補完しない(self):
        root,planner,bad,good=setup('未知の失敗',False)
        r=会話実行監督(planner,root).実行(意味目的('成果',{}),{},原文='成果')
        self.assertFalse(r.応答.成立);self.assertEqual(r.失敗[0].分類,'未分類')
    def test_通常例外は実行環境として区別して止める(self):
        root,planner,bad,good=setup()
        def crash(ctx): raise RuntimeError('実装例外')
        bad.result=crash
        r=会話実行監督(planner,root).実行(意味目的('成果',{}),{},原文='成果')
        self.assertFalse(r.応答.成立);self.assertEqual(r.失敗[0].分類,'実行環境');self.assertEqual(good.calls,0)
    def test_再計画で解法が尽きても元の実行失敗を保持する(self):
        root,planner,bad,good=setup()
        planner=役割計画器((planner.作用[0],),root.能力一覧())
        r=会話実行監督(planner,root).実行(意味目的('成果',{}),{},原文='成果')
        self.assertFalse(r.応答.成立);self.assertEqual(r.試行[-1]['状態'],'計画保留')
        self.assertEqual(r.失敗[0].種別,'検証失敗')
    def test_停止要求で能力を起動しない(self):
        root,planner,bad,good=setup()
        with self.assertRaises(InterruptedError):
            会話実行監督(planner,root).実行(意味目的('成果',{}),{},原文='成果',停止要求=lambda:True)
        self.assertEqual((bad.calls,good.calls),(0,0))
    def test_試行上限で代替能力を無制限に呼ばない(self):
        root,planner,bad,good=setup()
        r=会話実行監督(planner,root,最大試行=1).実行(意味目的('成果',{}),{},原文='成果')
        self.assertFalse(r.応答.成立);self.assertEqual(good.calls,0)
    def test_途中で外部の可変目的が変わっても固定目的を維持(self):
        root,planner,bad,good=setup();goal=意味目的('成果',{'指定':'元'})
        old=bad.result
        def change(ctx): goal.引数['指定']='書換';return old
        bad.result=change
        initial=goal.鍵();r=会話実行監督(planner,root).実行(goal,{},原文='成果')
        self.assertTrue(r.応答.成立);self.assertTrue(all(x['目的印']==initial for x in r.試行))
    def test_途中で契約が差し替わったら止める(self):
        root,planner,bad,good=setup();old=bad.result
        def change(ctx): planner.作用=planner.作用[::-1];return old
        bad.result=change
        with self.assertRaises(ValueError):会話実行監督(planner,root).実行(意味目的('成果',{}),{},原文='成果')
        self.assertEqual(good.calls,0)
    def test_条件矛盾を回復契約にして逃がさない(self):
        with self.assertRaises(ValueError):回復規則('前提矛盾').検証()
    def test_権限不足を再計画で昇格させない(self):
        with self.assertRaises(ValueError):回復規則('権限不足').検証()
    def test_意味未確定には確認が必要で自動経路へ飛ばない(self):
        with self.assertRaises(ValueError):回復規則('意味未確定').検証()
    def test_停止は回復不能(self):
        with self.assertRaises(ValueError):回復規則('停止').検証()
    def test_未知の回復規則を登録しない(self):
        with self.assertRaises(ValueError):回復規則('架空').検証()
    def test_入力回復には明示された役割が必要(self):
        with self.assertRaises(ValueError):回復規則('取得不足','入力役割').検証()
    def test_自己回復に無関係な入力指定を混ぜない(self):
        with self.assertRaises(ValueError):回復規則('検証失敗','自己','入力').検証()
    def test_入力役割の回復先作用は登録されている必要がある(self):
        root,planner,bad,good=setup()
        rule=replace(planner.作用[0],回復=(回復規則('検証失敗','入力役割','子',('不在作用',)),))
        with self.assertRaises(ValueError):役割計画器((rule,),root.能力一覧())
    def test_回復規則の二重指定を拒否する(self):
        root,planner,bad,good=setup()
        rule=replace(planner.作用[0],回復=(回復規則('検証失敗'),回復規則('検証失敗')))
        with self.assertRaises(ValueError):役割計画器((rule,),root.能力一覧())
    def test_未知作用を禁止に混ぜて黙認しない(self):
        root,planner,bad,good=setup()
        with self.assertRaises(ValueError):planner.計画する(意味目的('成果',{}),{},禁止=(('key','不存在'),))
    def test_入力役割の回復は直接の名付けた依存だけ(self):
        report=_部品('空の報告',能力結果(True,'空'))
        improved=_部品('十分な報告',能力結果(True,'十分'))
        def adopt(ctx):
            return 能力結果(True,'完成') if ctx.直前応答=='十分' else 能力結果(False,'',保留理由='会話失敗:取得不足:資料が空')
        adopter=_部品('採用',adopt)
        root=統合セッション('入力回復',追加能力=tuple(登録能力(x) for x in (report,improved,adopter)))
        rules=(役割作用('採用作用','採用','成果',lambda p:(('報告',意味目的('報告',p)),),lambda p:{},lambda p:True,
                        回復=(回復規則('取得不足','入力役割','報告',('初期報告',)),)),
               役割作用('初期報告','空の報告','報告',lambda p:(),lambda p:{},lambda p:True),
               役割作用('別の報告','十分な報告','報告',lambda p:(),lambda p:{},lambda p:True,費用=2))
        planner=役割計画器(rules,root.能力一覧())
        r=会話実行監督(planner,root).実行(意味目的('成果',{}),{},原文='報告を採用')
        self.assertTrue(r.応答.成立);self.assertEqual(r.失敗[0].再開放[1],'初期報告')
        self.assertNotEqual(r.失敗[0].再開放[1],'採用作用')
    def test_入力役割の許可外作用は再開放しない(self):
        s=汎用会話セッション('役割名')
        rules=tuple(replace(r,回復=(回復規則('構造未到達','入力役割','存在しない役割',('構造文書読取',)),)) if r.識別子=='直下数量選択' else r for r in 会話作用群())
        p=役割計画器(rules,s.統合.能力一覧())
        a={'資料':'A','形式':'JSON','属性':'売上','単位':'円','行条件':{}}
        goal=意味目的('比較回答',{'左':a,'右':{**a,'資料':'B'},'時点差':False,'詳細':False})
        r=会話実行監督(p,s.統合).実行(goal,{'A':能力結果(True,'{"売上":2}'),'B':能力結果(True,'{"箱":{"売上":1}}')},原文='比較')
        self.assertFalse(r.応答.成立);self.assertIsNone(r.失敗[0].再開放)
    def test_未知分類を既知の意味へ昇格しない(self): self.assertEqual(失敗を分類('通信かもしれない'),'未分類')
    def test_分類は回復の許可そのものではない(self):
        root,planner,bad,good=setup('情報不足',False)
        r=会話実行監督(planner,root).実行(意味目的('成果',{}),{},原文='成果')
        self.assertEqual(r.失敗[0].分類,'情報不足');self.assertIsNone(r.失敗[0].再開放)

class 既存整合性修復試験(unittest.TestCase):
    def setUp(self):
        s=汎用会話セッション('参照監査')
        self.r=s.応答('資料「A」と資料「B」の売上を比較して',
            {'A':能力結果(True,'{"売上":75,"単位":"円"}'),'B':能力結果(True,'{"売上":60,"単位":"円"}')})
        self.assertTrue(self.r.成立)
    def test_既存二資料回答の参照削除を検出(self):
        self.assertFalse(回答記録整合(replace(self.r.結果,参照=())))
    def test_既存比較記録の参照削除を検出(self):
        value=能力結果を復元(self.r.結果.データ['元結果'][0])
        self.assertFalse(比較記録整合(replace(value,参照=())))
    def test_既存回答の出典URL改変を検出(self):
        altered=replace(self.r.結果.参照[0],URL='https://false.example')
        self.assertFalse(回答記録整合(replace(self.r.結果,参照=(altered,*self.r.結果.参照[1:]))))
    def test_成功判定にbool以外を許可しない(self):
        self.assertFalse(回答記録整合(replace(self.r.結果,成立='true')))
    def test_正しい既存成果はそのまま通す(self):self.assertTrue(回答記録整合(self.r.結果))

if __name__=='__main__':unittest.main()
