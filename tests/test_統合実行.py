"""共通入口・採用状態・全領域接続・再利用の作用差を検査する。"""
from copy import deepcopy
from dataclasses import asdict, replace
from pathlib import Path
import runpy
import unittest

from minidora.統合実行 import 統合セッション, 受入条件
from minidora.統合能力 import 純粋結果庫
from minidora.能力合成 import 合成計画, 合成工程, 素材参照, 能力合成器, _結果辞書
from minidora.能力合成_局所接続 import 局所能力群
from minidora.長文脈管理 import 文脈選択要求
from minidora.知識取得 import 知識取得器
from minidora.製品版.型 import 能力結果, 参照資料
from test_知識取得 import 試験検索, 試験本文, candidate, document, BASE
from test_知識取得_合成 import 計画とData
from test_多言語_合成 import 入力 as 翻訳入力

ROOT = Path(__file__).resolve().parents[1]

def 一工程(name, value, settings=None):
    data = {"i": 能力結果(True, "指定処理を実行"), "v": value}
    if settings is not None:
        data["c"] = 能力結果(True, "", データ=settings)
    return (合成計画((合成工程("out", (name,), "i", (素材参照("入力", "v"),),
                          "c" if settings is not None else None),), ("out",)), data)


def 数学計画(value="2"):
    return runpy.run_path(str(ROOT/"tools/数学記号デモ.py"))["記号計画"](value)


def 統計合計(result, name):
    return sum(row[name] for row in result.計測["再利用差分"].values())


class 統合経路試験(unittest.TestCase):
    def setUp(self):
        self.s = 統合セッション("統合試験")

    def ok(self, r):
        self.assertTrue(r.成立, (r.理由, r.実行))
        self.assertTrue(r.実行.監査整合())
        self.assertNotEqual(r.起点, r.更新後)
        return r

    def test_全登録の名前一意と外部作用分離(self):
        rows = self.s.能力一覧()
        self.assertEqual(len(rows), 29)
        self.assertEqual(len({r['名前'] for r in rows}), 29)
        self.assertEqual({r['名前'] for r in rows if r['外部読取']}, {'知識取得', 'ブラウザ閲覧'})

    def test_数学の変形代入採用を通す(self):
        r = self.ok(self.s.計画実行(*数学計画()))
        self.assertEqual(r.本文, '- 27')
        self.assertEqual([x.能力 for x in r.実行.履歴], ['記号演算','記号演算','数学結果採用','文脈変換'])

    def test_JSON_CSVの既存複合計画をそのまま通す(self):
        make = runpy.run_path(str(ROOT/'tools/構造化文書デモ.py'))['用意']
        r = self.ok(self.s.計画実行(*make(731)))
        self.assertEqual(r.本文, '731')
        self.assertEqual(r.実行.実行数, 6)

    def test_文章作成編集の複数出力を保持(self):
        make = runpy.run_path(str(ROOT/'tools/文章作成編集デモ.py'))['用意']
        r = self.ok(self.s.計画実行(*make(222)))
        self.assertEqual([k for k,_ in r.出力], ['編集','抽出'])
        self.assertIn('確認版', r.本文)
        self.assertEqual(dict(r.出力)['抽出'].本文, '222')

    def test_翻訳を後続抽出へ接続(self):
        r = self.ok(self.s.計画実行(*翻訳入力('731')))
        self.assertEqual(r.本文, '731')
        self.assertIn('the voltage', r.出力[0][1].参照[0].本文)

    def test_コード生成と多段の後戻りを一入口で実行(self):
        problem, data = runpy.run_path(str(ROOT/'tools/コード能力デモ.py'))['問題を用意']()
        payload = 能力結果(True, '', データ={'問題':asdict(problem), '初期Data':{k:_結果辞書(v) for k,v in data.items()}})
        r = self.ok(self.s.計画実行(*一工程('多段解決', payload)))
        self.assertIn('if 数 >', r.本文)
        self.assertEqual(r.出力[0][1].データ['採用経路'][0]['解法'], '境界を含まない候補')

    def test_目的検証失敗から子の別解へ戻る(self):
        problem, data = runpy.run_path(str(ROOT/'tools/多段解決デモ.py'))['問題を用意'](731)
        payload = 能力結果(True, '', データ={'問題':asdict(problem), '初期Data':{k:_結果辞書(v) for k,v in data.items()}})
        r = self.ok(self.s.計画実行(*一工程('多段解決', payload)))
        self.assertEqual(r.本文, '731、75、45')

    def test_コード評価と最終入出力検証(self):
        source = 能力結果(True, 'def f(x):\n return x*x')
        r = self.ok(self.s.計画実行(*一工程('コード評価', source, {'引数':{'x':7}})))
        self.assertEqual(r.本文, '49')
        r = self.ok(self.s.計画実行(*一工程('コード検証', source, {'試験':[{'引数':{'x':7},'期待値':49}]})))
        self.assertIn('全件一致', r.本文)

    def test_証拠統合から応答を構成(self):
        refs = (参照資料('a','資料A','人工',本文='装置Aの電圧は120 Vです。'),)
        p,d = 一工程('証拠統合', 能力結果(True,'',参照=refs), {'対象':'装置A','属性':'電圧','単位':'V'})
        p = 合成計画((*p.工程, 合成工程('回答',('応答構成',),'i',(素材参照('工程','out'),))),('回答',))
        r = self.ok(self.s.計画実行(p,d))
        self.assertIn('120', r.本文)
        self.assertEqual(r.出力[0][1].参照,refs)

    def test_差分関係の導出(self):
        from minidora.関係制約 import 関係問題, 関係式
        problem = 関係問題(('A','B','C'),(関係式('a','A','以上','B','3'),関係式('b','B','以上','C','2')),
                         (関係式('q','A','以上','C','5'),))
        r = self.ok(self.s.計画実行(*一工程('関係制約', 能力結果(True,'',データ={'関係問題':asdict(problem)}))))
        self.assertEqual(r.出力[0][1].データ['回答'][0]['判定'], '導出')

    def test_採用成果を同じ長文脈へ保存し再参照(self):
        self.ok(self.s.計画実行(*数学計画()))
        raw = self.s.原記録('応答:1:出力:0')
        self.assertEqual(raw['内容']['本文'], '- 27')
        request = self.s.文脈要求(文脈選択要求(('応答:1:出力:0',),直近件数=0,最大バイト数=100000))
        r = self.ok(self.s.計画実行(*一工程('長文脈選択', request)))
        self.assertIn('- 27', r.本文)
        self.assertGreater(len(r.出力[0][1].データ['原文対応']), 1)

    def test_原入力と返却値を所有状態から分離(self):
        p,d = 数学計画(); old=deepcopy(d)
        r = self.ok(self.s.計画実行(p,d))
        r.出力[0][1].データ['汚染'] = True
        self.assertEqual(d,old)
        self.assertNotIn('汚染',self.s.原記録('応答:1:出力:0')['内容']['データ'])

    def test_旧入口の12項目切断を統合側だけ解消(self):
        source = 能力結果(True,'。'.join('項目'+str(i) for i in range(20))+'。')
        p,d = 一工程('文脈変換',source,{'形式':'箇条書き'})
        old = 能力合成器(局所能力群()).実行(p,d)
        new = self.ok(self.s.計画実行(p,d))
        self.assertEqual(len(old.出力[0][1].本文.splitlines()),12)
        self.assertEqual(len(new.本文.splitlines()),20)
        self.assertIn('項目19',new.本文)


class 採用制御試験(unittest.TestCase):
    def setUp(self):
        self.s=統合セッション('採用')

    def test_数値保持に失敗した要約は採用しない(self):
        p,d=一工程('抽出要約',能力結果(True,'売上は120。費用は75。利益は45。'),{'行数':1})
        d['検査設定']=能力結果(True,'',データ={'種別':'数値列保持'})
        before=self.s.保存文脈()
        r=self.s.計画実行(p,d,条件=(受入条件('out','成果検査','検査設定',('v',)),))
        self.assertFalse(r.成立);self.assertEqual(r.出力,());self.assertEqual(r.本文,'')
        self.assertEqual(self.s.保存文脈(),before)
        self.assertEqual(r.起点,r.更新後)

    def test_自由解を一意解へ昇格しない(self):
        p,d=一工程('線形方程式',能力結果(True,'',データ={'変数':['x','y'],'方程式':[{'左辺':'x+y','右辺':'5'}]}))
        d['検査設定']=能力結果(True,'',データ={'期待':'一意解'})
        r=self.s.計画実行(p,d,条件=(受入条件('out','数学結果採用','検査設定'),))
        self.assertFalse(r.成立);self.assertEqual(r.起点,r.更新後)
        self.assertEqual(dict(r.実行.中間結果)['out'].データ['判定'],'自由解')

    def test_一意解は検証記録を残し元出力だけを採用(self):
        value=能力結果(True,'',データ={'変数':['x'],'方程式':[{'左辺':'2*x','右辺':'6'}]})
        p,d=一工程('線形方程式',value);d['検査設定']=能力結果(True,'',データ={'期待':'一意解'})
        r=self.s.計画実行(p,d,条件=(受入条件('out','数学結果採用','検査設定'),))
        self.assertTrue(r.成立,(r.理由,r.実行))
        self.assertEqual([k for k,_ in r.出力],['out'])
        self.assertEqual(len(r.実行.出力),2)
        self.assertEqual(r.出力[0][1].データ['解'],{'x':'3'})

    def test_複数出力の一件の失敗で部分採用しない(self):
        p,d=一工程('情報抽出',能力結果(True,'値120'),{'種別':'数字'})
        d['bad']=能力結果(True,'');d['cfg']=能力結果(True,'',データ={'種別':'数字'})
        p=合成計画((*p.工程,合成工程('bad',('情報抽出',),'i',(素材参照('入力','bad'),),'cfg')),('out','bad'))
        r=self.s.計画実行(p,d)
        self.assertFalse(r.成立);self.assertEqual(r.起点,r.更新後);self.assertEqual(r.出力,())

    def test_返却長超過でも途中切断も採用もしない(self):
        s=統合セッション('文字数',最大回答文字数=2)
        r=s.計画実行(*一工程('素材引継ぎ',能力結果(True,'abcd')))
        self.assertFalse(r.成立);self.assertEqual(r.本文,'');self.assertEqual(r.起点,r.更新後)

    def test_編集失敗を採用しない(self):
        make=runpy.run_path(str(ROOT/'tools/文章作成編集デモ.py'))['用意']
        r=self.s.計画実行(*make(保護違反=True))
        self.assertFalse(r.成立);self.assertEqual(r.起点,r.更新後)

    def test_停止と停止判定故障は採用しない(self):
        for stop in (lambda:True,lambda:'false',lambda:1/0):
            r=self.s.計画実行(*数学計画(),停止要求=stop)
            self.assertFalse(r.成立);self.assertEqual(r.起点,r.更新後)

    def test_応答数上限を実行前に判定(self):
        s=統合セッション('上限',最大応答数=1)
        self.assertTrue(s.計画実行(*数学計画()).成立)
        r=s.計画実行(*数学計画())
        self.assertFalse(r.成立);self.assertIsNone(r.実行)

    def test_旧準備と別セッションを拒否(self):
        prepared=self.s.準備(*数学計画())
        other=統合セッション('採用')
        self.assertFalse(other.実行(prepared).成立)
        self.assertTrue(self.s.実行(prepared).成立)
        self.assertFalse(self.s.実行(prepared).成立)

    def test_準備後のData変更を拒否(self):
        prepared=self.s.準備(*数学計画());prepared.Data['指示']=能力結果(True,'改変')
        r=self.s.実行(prepared)
        self.assertFalse(r.成立);self.assertIsNone(r.実行)

    def test_初期化で旧選択と再利用庫を無効化(self):
        prepared=self.s.準備(*数学計画());self.s.実行(prepared)
        self.s.初期化()
        self.assertFalse(self.s.実行(prepared).成立)
        self.assertEqual(self.s.再利用統計()['件数'],0)
        self.assertTrue(self.s.計画実行(*数学計画()).成立)

    def test_未知能力と予約名と外部検査を拒否(self):
        p,d=数学計画();d['統合:偽装']=能力結果(True,'')
        self.assertFalse(self.s.計画実行(p,d).成立)
        self.assertFalse(self.s.計画実行(*一工程('ない能力',能力結果(True,'a'))).成立)
        p,d=一工程('素材引継ぎ',能力結果(True,'a'))
        self.assertFalse(self.s.計画実行(p,d,条件=(受入条件('out','知識取得'),)).成立)


class 再利用調整試験(unittest.TestCase):
    def test_同じ計算を再利用し値を変えない(self):
        s=統合セッション('再利用')
        a=s.計画実行(*数学計画());b=s.計画実行(*数学計画())
        self.assertTrue(a.成立 and b.成立,(a.理由,b.理由))
        self.assertEqual(a.出力,b.出力)
        self.assertEqual(統計合計(a,'原実行'),4)
        self.assertEqual(統計合計(b,'再利用'),4)
        self.assertEqual(統計合計(b,'原実行'),0)

    def test_変更値と設定を古い値で埋めない(self):
        s=統合セッション('再利用');s.計画実行(*数学計画())
        changed=s.計画実行(*数学計画('3'))
        self.assertTrue(changed.成立,changed.理由)
        self.assertEqual(changed.本文,'- 48')
        self.assertEqual(統計合計(changed,'再利用'),1)

    def test_再利用なしの経路と出力が一致(self):
        p,d=数学計画('731')
        cached=統合セッション('s',再利用=True)
        plain=統合セッション('s',再利用=False)
        for _ in range(2):
            a=cached.計画実行(p,d);b=plain.計画実行(p,d)
            self.assertTrue(a.成立 and b.成立)
            self.assertEqual(a.出力,b.出力)
        self.assertEqual(統計合計(b,'原実行'),4)
        self.assertEqual(統計合計(b,'再利用'),0)

    def test_失敗結果を保存しない(self):
        s=統合セッション('失敗再利用')
        p,d=一工程('コード評価',能力結果(True,'def f():\n return 1//0'),{'引数':{}})
        for _ in range(2):
            r=s.計画実行(p,d);self.assertFalse(r.成立)
            self.assertEqual(統計合計(r,'原実行'),1)
            self.assertEqual(統計合計(r,'再利用'),0)

    def test_原典変更は本文同一でも再利用しない(self):
        s=統合セッション('原典')
        for key in ('a','b'):
            value=能力結果(True,'値120',参照=(参照資料(key,'題','人工',本文='値120'),))
            r=s.計画実行(*一工程('情報抽出',value,{'種別':'数字'}))
            self.assertTrue(r.成立);self.assertEqual(統計合計(r,'再利用'),0)
            self.assertEqual(r.出力[0][1].参照[0].識別子,key)

    def test_返却値改変は再利用の値へ伝播しない(self):
        s=統合セッション('値所有');p,d=数学計画()
        a=s.計画実行(p,d);a.出力[0][1].データ['改変']=True
        b=s.計画実行(p,d)
        self.assertNotIn('改変',b.出力[0][1].データ)

    def test_LRU予算と複写を保つ(self):
        c=純粋結果庫(最大件数=2,最大バイト数=2000)
        value=能力結果(True,'値',データ={'a':[1]})
        c.保存('a',value);c.保存('b',value);c.取得('a');c.保存('c',value)
        self.assertIsNone(c.取得('b'))
        c.取得('a').データ['a'].append(2)
        self.assertEqual(c.取得('a').データ['a'],[1])
        self.assertLessEqual(c.統計()['保存バイト数'],2000)


class 統合外部境界試験(unittest.TestCase):
    def setUp(self):
        self.search=試験検索((candidate(),))
        self.fetch=試験本文({BASE+'a':document()})
        self.provider=知識取得器(self.search,self.fetch)

    def test_同一要求でも外部取得自体は毎回実行(self):
        s=統合セッション('取得',外部読取許可=True,取得器=self.provider)
        for _ in range(2):
            r=s.計画実行(*計画とData(),外部読取許可=True)
            self.assertTrue(r.成立,(r.理由,r.実行))
        self.assertEqual(len(self.search.calls),2)
        self.assertNotIn('知識取得',s.再利用統計()['能力別'])

    def test_変更した新規取得本文を使う(self):
        s=統合セッション('取得',外部読取許可=True,取得器=self.provider)
        a=s.計画実行(*計画とData(),外部読取許可=True)
        self.fetch.values[BASE+'a']=document(text='電圧は731 V。')
        b=s.計画実行(*計画とData(),外部読取許可=True)
        self.assertEqual((a.本文,b.本文),('120','731'))

    def test_構築時と要求時の両方に許可が必要(self):
        for enabled,requested in ((False,True),(True,False),(False,False)):
            s=統合セッション('権限',外部読取許可=enabled,取得器=self.provider)
            r=s.計画実行(*計画とData(),外部読取許可=requested)
            self.assertFalse(r.成立);self.assertEqual(r.起点,r.更新後)
        self.assertEqual(self.search.calls,[])

    def test_未設定の公開閲覧を検索へ代替しない(self):
        from ブラウザ試験素材 import 表要求
        s=統合セッション('閲覧')
        r=s.計画実行(*一工程('ブラウザ閲覧',能力結果(True,'',データ={'要求':asdict(表要求())})))
        self.assertFalse(r.成立)
        self.assertIsNotNone(r.実行)
        self.assertEqual(r.実行.実行数,0)


class 起点競合試験(unittest.TestCase):
    def test_ロック取得前に状態が変われば能力を呼ばない(self):
        from minidora.長文脈管理 import 文脈登録
        s=統合セッション('競合')
        prepared=s.準備(*数学計画())
        lock=s._ロック
        class 競合挿入:
            def acquire(self, **kw):
                s._庫.更新(s._庫.起点(),(文脈登録('別更新',能力結果(True,'更新')),))
                return lock.acquire(**kw)
            def release(self):
                lock.release()
        s._ロック=競合挿入()
        r=s.実行(prepared)
        self.assertFalse(r.成立)
        self.assertIsNone(r.実行)
        self.assertEqual(s.再利用統計()['能力別'],{})


class 検証能力指定試験(unittest.TestCase):
    def test_単なる引継ぎを最終検証として認めない(self):
        s=統合セッション('検証能力')
        p,d=一工程('素材引継ぎ',能力結果(True,'値120'))
        r=s.計画実行(p,d,条件=(受入条件('out','素材引継ぎ'),))
        self.assertFalse(r.成立)
        self.assertIsNone(r.実行)
