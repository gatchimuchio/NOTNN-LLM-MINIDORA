"""実統合器の採用・失効・版固定・最終照合。失敗注入は検査対象データだけ。"""
import ast
import json
import unittest
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from minidora.統合実行 import 統合セッション
from minidora.能力合成 import _結果辞書, _符号化, 合成計画, 合成工程, 素材参照
from minidora.製品版.型 import 能力結果, 参照資料
from minidora.製品版.能力契約 import 能力文脈
from minidora.監査改善計画 import 改善目的を計画, 改善統合能力群, 改善回答照合Module
from minidora.監査改善接続 import 拡張命題を検討, 改善回答を構成, 改善回答を検査
from minidora.会話意味 import 意味指紋
from minidora.能力結果復元 import 能力結果を復元
from minidora.長文脈管理 import 長文脈庫, 文脈登録, 文脈選択要求
from minidora.純粋結果庫 import 純粋結果庫


def request(query='Q'):
    return {'資料':[{'名前':'A','本文':'P。PならばQ。'}],'問い':query}


def original(query='Q'):
    ref=参照資料('src','A','利用者提供資料',本文='P。PならばQ。')
    return 能力結果(True,'資料から判定する',根拠=('src',),参照=(ref,),データ=request(query))


def answer(query='Q',detail=True):
    d=改善回答を構成(拡張命題を検討(request(query)),詳細=detail)
    return 能力結果(True,d['本文'],根拠=('原データ:'+意味指紋(d['報告']),),参照=original().参照,データ=d)


def gate(a, o, settings=None):
    rows=tuple({'参照':{'領域':'入力','識別子':str(i)},'結果':_結果辞書(v)} for i,v in enumerate((a,o)))
    return 改善回答照合Module().実行(能力文脈('照合','試験',補助={'合成入力':rows,'合成設定':
        {'種類':'命題','詳細':True} if settings is None else settings}))


class 最終照合試験(unittest.TestCase):
    def test_正常な回答と原要求を採用する(self):
        self.assertTrue(gate(answer(),original()).成立)

    def test_自己整合しても別の問いの回答を拒否する(self):
        a=answer('P');self.assertTrue(改善回答を検査(a.データ))
        self.assertFalse(gate(a,original('Q')).成立)

    def test_表示の本文改変を拒否(self):
        self.assertFalse(gate(replace(answer(),本文='別の回答'),original()).成立)

    def test_根拠削除を拒否(self):
        self.assertFalse(gate(replace(answer(),根拠=()),original()).成立)

    def test_参照削除を拒否(self):
        self.assertFalse(gate(replace(answer(),参照=()),original()).成立)

    def test_同名参照の内容変更を拒否(self):
        self.assertFalse(gate(replace(answer(),参照=(replace(original().参照[0],本文='R。'),)),original()).成立)

    def test_種類のすり替えを拒否(self):
        self.assertFalse(gate(answer(),original(),{'種類':'仮説','詳細':True}).成立)

    def test_表示詳細の不一致を拒否(self):
        self.assertFalse(gate(answer(detail=False),original()).成立)

    def test_bool代わりの整数や未知設定を拒否(self):
        for settings in ({'種類':'命題','詳細':1},{'種類':'命題','詳細':True,'ignore':True}):
            with self.subTest(settings=settings):self.assertFalse(gate(answer(),original(),settings).成立)

    def test_出典一致だけで別要求の数値を通さない(self):
        o=original();o.データ['照応距離']=2
        self.assertFalse(gate(answer(),o).成立)

    def test_最終照合失敗では原記録へ採用しない(self):
        s=統合セッション('検査',基底能力=改善統合能力群());start=s.起点()
        p=合成計画((合成工程('照合',('監査改善回答照合',),'i',
           (素材参照('入力','a'),素材参照('入力','o')),'c'),),('照合',))
        d={'i':能力結果(True,'照合する'),'a':answer('P'),'o':original('Q'),
           'c':能力結果(True,'',データ={'種類':'命題','詳細':True})}
        r=s.計画実行(p,d)
        self.assertFalse(r.成立);self.assertEqual(s.起点(),start)
        self.assertEqual(s.採用履歴スナップショット()[1],());self.assertEqual(r.採用記録ID,())
        self.assertTrue(r.実行.監査整合())  # 整合記録と意味的採用は別。


class 統合採用試験(unittest.TestCase):
    def setUp(self):
        self.s=統合セッション('統合',基底能力=改善統合能力群())

    def plan(self,**kwargs):
        p=改善目的を計画('命題',original(),self.s.能力一覧())
        return self.s.準備(p.計画,p.Data,**kwargs)

    def test_三工程を実行し採用IDを返す(self):
        p=self.plan();r=self.s.実行(p)
        self.assertTrue(r.成立,r.理由);self.assertEqual(len(r.実行.履歴),3)
        self.assertEqual(r.採用記録ID,('応答:1:出力:0',))
        self.assertEqual(r.辞書化()['採用記録ID'],['応答:1:出力:0'])
        self.assertEqual(len(self.s.採用履歴スナップショット()[1]),1)

    def test_準備後のData改変を拒否(self):
        p=self.plan();p.Data['素材:原要求'].データ['問い']='P'
        before=self.s.起点();self.assertFalse(self.s.実行(p).成立)
        self.assertEqual(before,self.s.起点())

    def test_別所有者の計画を拒否する(self):
        p=self.plan();other=統合セッション('統合',基底能力=改善統合能力群())
        self.assertFalse(other.実行(p).成立)

    def test_二度の採用を許さない(self):
        p=self.plan();self.assertTrue(self.s.実行(p).成立)
        self.assertFalse(self.s.実行(p).成立);self.assertEqual(len(self.s._履歴),1)

    def test_初期化した旧計画を使わない(self):
        p=self.plan();self.s.初期化();self.assertFalse(self.s.実行(p).成立)

    def test_失効は歴史を保持し現行参照だけ除外する(self):
        r=self.s.実行(self.plan());key=r.採用記録ID[0]
        history=deepcopy(self.s._履歴)
        self.s.記録を失効(self.s.起点(),(key,),理由='訂正')
        self.assertEqual(history,self.s._履歴)
        self.assertFalse(self.s.原記録(key)['現行'])
        self.assertEqual(self.s.採用履歴スナップショット()[1],())

    def test_依存する後続成果にも推移失効する(self):
        a=self.s.実行(self.plan());id1=a.採用記録ID[0]
        b=self.s.実行(self.plan(依存記録=(id1,)));id2=b.採用記録ID[0]
        self.assertIn(id1,self.s.原記録(id2)['依存'])
        self.s.記録を失効(self.s.起点(),(id1,),理由='訂正')
        self.assertFalse(self.s.原記録(id2)['現行'])
        self.assertEqual(self.s.採用履歴スナップショット()[1],())

    def test_失効済み記録を新計画の依存にしない(self):
        a=self.s.実行(self.plan());key=a.採用記録ID[0]
        self.s.記録を失効(self.s.起点(),(key,),理由='訂正')
        with self.assertRaises(ValueError):self.plan(依存記録=(key,))

    def test_未存在や重複の依存を拒否(self):
        for ids in (('missing',),['missing'],('a','a'),(1,)):
            with self.subTest(ids=ids),self.assertRaises(ValueError):self.plan(依存記録=ids)

    def test_失効を古い起点で行わない(self):
        old=self.s.起点();r=self.s.実行(self.plan())
        with self.assertRaises(ValueError):self.s.記録を失効(old,r.採用記録ID,理由='訂正')
        self.assertTrue(self.s.原記録(r.採用記録ID[0])['現行'])

    def test_失効に失敗したら一部だけ変更しない(self):
        r=self.s.実行(self.plan());before=self.s.保存文脈()
        with self.assertRaises(ValueError):self.s.記録を失効(self.s.起点(),(r.採用記録ID[0],'missing'),理由='訂正')
        self.assertEqual(before,self.s.保存文脈())

    def test_最終回答上限で採用しない(self):
        s=統合セッション('small',基底能力=改善統合能力群(),最大回答文字数=1)
        p=改善目的を計画('命題',original(),s.能力一覧());start=s.起点()
        r=s.計画実行(p.計画,p.Data)
        self.assertFalse(r.成立);self.assertEqual(start,s.起点())

    def test_能力版変更で旧計画を止める(self):
        p=self.plan();module=self.s._能力[-1].Module
        module.版='changed'
        self.assertFalse(self.s.実行(p).成立)

    def test_停止で採用を行わない(self):
        before=self.s.起点();r=self.s.実行(self.plan(),停止要求=lambda:True)
        self.assertEqual(r.状態,'中止');self.assertEqual(before,self.s.起点())

    def test_型不正の停止を受理しない(self):
        before=self.s.起点();r=self.s.実行(self.plan(),停止要求=lambda:'false')
        self.assertFalse(r.成立);self.assertEqual(before,self.s.起点())

    def test_外部許可の昇格を拒否する(self):
        r=self.s.実行(self.plan(),外部読取許可=True)
        self.assertFalse(r.成立)

    def test_基底の未取得機能を暗黙偽装しない(self):
        self.assertEqual(len(self.s.能力一覧()),5)
        with self.assertRaises(ValueError):統合セッション('x',基底能力=[])
        with self.assertRaises(ValueError):統合セッション('x',基底能力=改善統合能力群(),追加能力=改善統合能力群())

    def test_能力を消すと計画も失敗する(self):
        with self.assertRaises(ValueError):改善目的を計画('命題',original(),self.s.能力一覧()[:-1])


class 長文脈と復元試験(unittest.TestCase):
    def test_成果の原記録と依存失効が往復する(self):
        store=長文脈庫('ctx')
        store.更新(store.起点(),(文脈登録('d',original()),文脈登録('o',answer(),'成果',('d',))))
        store.更新(store.起点(),失効ID=('d',),理由='訂正')
        restored=長文脈庫.復元(store.保存文字列())
        self.assertEqual(_符号化(store.原記録('o')),_符号化(restored.原記録('o')))
        self.assertFalse(restored.原記録('o')['現行'])
        self.assertFalse(restored.選択(文脈選択要求(必須ID=('o',))).成立)

    def test_原記録の返り値から内部を変えられない(self):
        store=長文脈庫('ctx');store.更新(store.起点(),(文脈登録('d',original()),))
        row=store.原記録('d');row['内容']['本文']='改変'
        self.assertNotEqual(store.原記録('d')['内容']['本文'],'改変')

    def test_結果JSON往復で参照時点と型を保つ(self):
        from datetime import datetime,timezone
        v=replace(original(),参照=(replace(original().参照[0],公開時刻=datetime(2026,9,12,tzinfo=timezone.utc)),))
        self.assertEqual(v,能力結果を復元(json.loads(_符号化(_結果辞書(v)))))

    def test_不正な結果を復元時に拒否する(self):
        for updates in ({'成立':1},{'保留理由':'未確定'},{'unknown':1}):
            with self.subTest(updates=updates),self.assertRaises(ValueError):能力結果を復元({**_結果辞書(original()),**updates})

    def test_純粋結果庫は複製とLRU上限を保つ(self):
        c=純粋結果庫(最大件数=1);o=original();c.保存('a',o);o.データ['問い']='R'
        self.assertEqual(c.取得('a').データ['問い'],'Q')
        c.保存('b',original());self.assertIsNone(c.取得('a'))
        self.assertEqual(c.統計()['件数'],1);c.消去();self.assertEqual(c.統計()['件数'],0)

    def test_第25標準接続は既定有効化と明示無効化を区別する(self):
        # 第25バッチで既定接続へ変更。HDS・共有統合器と明示無効化は維持する。
        source=(Path(__file__).parents[1]/'src/minidora/汎用会話.py').read_text(encoding='utf-8')
        tree=ast.parse(source)
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='汎用会話セッション')
        init=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='__init__')
        argmap={a.arg:v for a,v in zip(init.args.kwonlyargs,init.args.kw_defaults)}
        self.assertIs(argmap['監査改善'].value,True)
        from minidora.汎用会話 import 汎用会話セッション
        self.assertIsNotNone(汎用会話セッション('既定')._監査改善)
        self.assertIsNone(汎用会話セッション('無効',監査改善=False)._監査改善)
        self.assertIn('統合=self.統合',source);self.assertIn('公開HDSコンパイラ().コンパイル(原文)',source)
        self.assertIn('継続許可=self._監査改善焦点',source)

if __name__=='__main__':unittest.main()
