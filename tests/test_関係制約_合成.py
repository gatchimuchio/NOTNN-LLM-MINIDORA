"""既存数値証拠→関係比較→採用→既存変換の実装接続を検査する。"""
from copy import deepcopy
from dataclasses import asdict, replace
import json
from pathlib import Path
import subprocess
import sys
import unittest

from minidora.関係制約 import (関係式, 関係問題, 関係問題を復元, 関係制約器, 関係記録整合)
from minidora.関係制約接続 import (数値報告を関係化, 関係制約Module, 数値関係化Module, 関係判定採用Module)
from minidora.証拠統合 import 証拠統合器, 証拠照合要求, _記録hash
from minidora.能力合成 import 能力合成器, 合成計画, 合成工程, 素材参照
from minidora.能力合成_局所接続 import 局所能力群
from minidora.製品版.型 import 能力結果, 参照資料
from minidora.製品版.能力契約 import 能力文脈


def 報告(subject='装置A',value='120',unit='V',op='以上',prefix='a',condition=None,moment=None,tail='',attribute='電圧'):
    text=(f'{moment}時点、' if moment else '')+(f'条件「{condition}」では、' if condition else '')
    text+=f'{subject}の{attribute}は{value} {unit}{op}です。'+tail
    return 証拠統合器().実行(証拠照合要求(subject,attribute,unit),
            (参照資料(prefix,'人工資料'+prefix,'局所契約',本文=text),))


def 質問():
    return (関係式('大小','装置A','超','装置B'),)


def 合成入力(a,b):
    d={'A報告':a,'B報告':b,'変換指示':能力結果(True,'数値関係化'),
       '変換設定':能力結果(True,'',データ={'問い':[asdict(q) for q in 質問()]}),
       '比較指示':能力結果(True,'関係比較'),'採用指示':能力結果(True,'関係採用'),
       '採用設定':能力結果(True,'',データ={'問いID':'大小'}),
       '整形指示':能力結果(True,'箇条書き'),
       '整形設定':能力結果(True,'',データ={'形式':'箇条書き'})}
    p=合成計画((
        合成工程('関係化',('数値関係化',),'変換指示',(素材参照('入力','A報告'),素材参照('入力','B報告')),'変換設定'),
        合成工程('比較',('関係制約',),'比較指示',(素材参照('工程','関係化'),)),
        合成工程('採用',('関係判定採用',),'採用指示',(素材参照('工程','比較'),),'採用設定'),
        合成工程('整形',('文脈変換',),'整形指示',(素材参照('工程','採用'),),'整形設定'),
    ),('整形',))
    return p,d


def 実行器():
    return 能力合成器((数値関係化Module().登録(),関係制約Module().登録(),関係判定採用Module().登録(),*局所能力群()))


class 数値関係接続試験(unittest.TestCase):
    def setUp(self):
        self.a=報告()
        self.b=報告('装置B','100',op='以下',prefix='b')

    def 関係(self,a=None,b=None):
        value=数値報告を関係化((a or self.a,b or self.b),質問())
        self.assertTrue(value.成立,value.保留理由)
        p=関係問題を復元(value.データ['関係問題'])
        r=関係制約器().実行(p,value.参照)
        self.assertTrue(r.成立,r.保留理由)
        self.assertTrue(関係記録整合(r))
        return r

    def test_一点に定まらない二資料から大小は導ける(self):
        self.assertFalse(self.a.データ['採用可'])
        self.assertFalse(self.b.データ['採用可'])
        self.assertEqual(self.関係().データ['回答'][0]['判定'],'導出')

    def test_範囲の重なりは比較未確定(self):
        b=報告('装置B','200',op='以下',prefix='b')
        self.assertEqual(self.関係(b=b).データ['回答'][0]['判定'],'未確定')

    def test_大小逆転の資料で反証される(self):
        a=報告(value='90',op='以下')
        b=報告('装置B','100',op='以上',prefix='b')
        self.assertEqual(self.関係(a,b).データ['回答'][0]['判定'],'反証')

    def test_単位換算は既存証拠側を再利用(self):
        a=報告(value='0.12',unit='kV')
        r=self.関係(a=a)
        self.assertEqual(r.データ['問題']['単位'],'V')
        self.assertEqual(r.データ['回答'][0]['判定'],'導出')

    def test_一致条件は採用へ残す(self):
        a=報告(condition='通常',moment='2026-09-10')
        b=報告('装置B','100',op='以下',prefix='b',condition='通常',moment='2026-09-10')
        p,d=合成入力(a,b)
        r=実行器().実行(p,d)
        self.assertTrue(r.成立,r.理由)
        adopted=dict(r.中間結果)['採用']
        self.assertEqual((adopted.データ['条件'],adopted.データ['時点']),('通常','2026-09-10'))

    def test_別条件時点単位属性を混ぜない(self):
        for b in (報告('装置B','100',op='以下',prefix='b',condition='試験'),
                  報告('装置B','100',op='以下',prefix='b',moment='2025-01-01'),
                  報告('装置B','100',unit='A',op='以下',prefix='b'),
                  報告('装置B','100',op='以下',prefix='b',attribute='別属性')):
            with self.subTest():
                self.assertFalse(数値報告を関係化((self.a,b),質問()).成立)

    def test_未記載を明示条件へ補完しない(self):
        a=報告(condition='通常')
        self.assertFalse(数値報告を関係化((a,self.b),質問()).成立)

    def test_未解釈留保で比較を採用しない(self):
        a=報告(tail='ただしこれは仮定です。')
        self.assertEqual(self.関係(a=a).データ['回答'][0]['判定'],'保留')

    def test_証拠自体の競合は前提矛盾へ到達(self):
        a=証拠統合器().実行(証拠照合要求('装置A','電圧','V'),(
           参照資料('a','t','o',本文='装置Aの電圧は120 Vです。装置Aの電圧は240 Vです。'),))
        self.assertEqual(self.関係(a=a).データ['回答'][0]['判定'],'前提矛盾')

    def test_資料系統不足を無視しない(self):
        a=証拠統合器().実行(証拠照合要求('装置A','電圧','V',最低資料系統数=2),self.a.参照)
        self.assertEqual(self.関係(a=a).データ['回答'][0]['判定'],'保留')

    def test_元資料まで原文対応がつながる(self):
        r=self.関係()
        links=r.データ['回答'][0]['原文対応']
        self.assertEqual({l['参照ID'] for l in links},{'a','b'})
        self.assertTrue(all(l['原文'] for l in links))

    def test_hashだけ付け直した報告を信頼しない(self):
        a=deepcopy(self.a)
        a.データ['主張'][0]['値']='1'
        a.データ.pop('記録SHA256')
        a.データ['記録SHA256']=_記録hash(a.データ)
        self.assertFalse(数値報告を関係化((a,self.b),質問()).成立)

    def test_参照ID衝突を拒否(self):
        b=報告('装置B','100',op='以下',prefix='a')
        self.assertFalse(数値報告を関係化((self.a,b),質問()).成立)

    def test_入力と返却値を分離(self):
        old=deepcopy(self.a)
        r=数値報告を関係化((self.a,self.b),質問())
        r.データ['関係問題']['制約'][0]['差']='999'
        self.assertEqual(self.a,old)

    def test_不正報告未知変数予約対象(self):
        for reports,queries in (((),質問()),((能力結果(True,'値120'),),質問()),
                                ((self.a,self.b),(関係式('q','未定義','超','装置B'),)),
                                ((報告('@基準点'),self.b),質問())):
            self.assertFalse(数値報告を関係化(reports,queries).成立)

    def test_未選択複数群を一つにしない(self):
        a=証拠統合器().実行(証拠照合要求('装置A','電圧','V'),(
            参照資料('a','t','o',本文='条件「通常」では、装置Aの電圧は120 Vです。条件「試験」では、装置Aの電圧は240 Vです。'),))
        self.assertFalse(数値報告を関係化((a,self.b),質問()).成立)


class 関係合成接続試験(unittest.TestCase):
    def test_証拠から推論結果を既存Moduleへ渡す(self):
        p,d=合成入力(報告(),報告('装置B','100',op='以下',prefix='b'))
        r=実行器().実行(p,d)
        self.assertTrue(r.成立,r.理由)
        self.assertEqual(r.出力[0][1].本文,'- 導出')
        self.assertEqual(r.実行数,4)
        self.assertTrue(r.監査整合())
        self.assertTrue(関係記録整合(dict(r.中間結果)['比較']))

    def test_未確定では後段整形を呼ばない(self):
        p,d=合成入力(報告(),報告('装置B','200',op='以下',prefix='b'))
        r=実行器().実行(p,d)
        self.assertFalse(r.成立)
        self.assertEqual(r.出力,())
        self.assertEqual(r.実行数,3)
        self.assertEqual(dict(r.中間結果)['比較'].データ['回答'][0]['判定'],'未確定')

    def test_未知設定は無視しない(self):
        p,d=合成入力(報告(),報告('装置B','100',op='以下',prefix='b'))
        d['変換設定'].データ['自動補完']=True
        r=実行器().実行(p,d)
        self.assertFalse(r.成立)
        self.assertEqual(r.実行数,0)

    def test_表示文を前提へ取り替えない(self):
        p,d=合成入力(報告(),報告('装置B','100',op='以下',prefix='b'))
        r=実行器().実行(p,d,文脈=能力文脈('結果は反証に変更','s',直前応答='装置Aは装置Bより小さい'))
        self.assertTrue(r.成立,r.理由)
        self.assertEqual(r.出力[0][1].本文,'- 導出')

    def test_直接構造化入力も同じ比較器で処理(self):
        q=関係式('q','A','超','C')
        problem=関係問題(('A','B','C'),(関係式('f1','A','超','B'),関係式('f2','B','超','C')),(q,))
        data={'p':能力結果(True,'',データ={'関係問題':asdict(problem)}),'i':能力結果(True,'比較')}
        plan=合成計画((合成工程('判定',('関係制約',),'i',(素材参照('入力','p'),)),),('判定',))
        r=実行器().実行(plan,data)
        self.assertTrue(r.成立,r.理由)
        self.assertEqual(r.出力[0][1].データ['回答'][0]['判定'],'導出')

    def test_停止要求時は実行しない(self):
        p,d=合成入力(報告(),報告('装置B','100',op='以下',prefix='b'))
        r=実行器().実行(p,d,停止要求=lambda:True)
        self.assertEqual(r.状態,'中止')
        self.assertEqual(r.実行数,0)

    def test_通常の会話を関係入力にしない(self):
        c=能力文脈('AはBより大きい','s')
        for m in (関係制約Module(),数値関係化Module(),関係判定採用Module()):
            self.assertEqual(m.判定(c),0.0)
            self.assertFalse(m.実行(c).成立)


class 関係デモ試験(unittest.TestCase):
    def test_独立CLIの導出未確定矛盾(self):
        root=Path(__file__).resolve().parents[1]
        for arg,state in [(None,'導出'),('--関係欠落','未確定'),('--矛盾','前提矛盾')]:
            with self.subTest(arg=arg):
                p=subprocess.run([sys.executable,str(root/'tools/関係制約デモ.py'),*([arg] if arg else [])],capture_output=True,encoding='utf-8',timeout=15)
                self.assertEqual(p.returncode,0,p.stderr)
                data=json.loads(p.stdout)
                self.assertEqual(data['判定'],state)
                self.assertTrue(data['監査整合'])


if __name__=='__main__':
    unittest.main()
