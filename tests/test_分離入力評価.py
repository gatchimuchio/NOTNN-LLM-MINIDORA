"""評価器の期待値分離と、保留を解答能力へ加算しない集計を検査する。"""
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from 独立入力評価 import ケースを読む, 評価する, JSON読取
from minidora.監査改善接続 import 改善計画を実行


def ケース(status='支持', *, content='P。', query='P'):
    return {'ID':'C1','区分':'開発生成','種類':'命題',
            '要求':{'資料':[{'名前':'甲','本文':content}],'問い':query},
            '期待':{'状態':'合格','判定':status}}


class 分離入力評価試験(unittest.TestCase):
    def read(self, rows):
        with TemporaryDirectory() as folder:
            p=Path(folder)/'cases.jsonl'
            p.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),encoding='utf-8')
            return ケースを読む(p)

    def test_識別子区分期待値を実行器へ渡さない(self):
        row=ケース();calls=[]
        def spy(kind,request,**settings):
            calls.append((kind,request,settings))
            return 改善計画を実行(kind,request,**settings)
        result=評価する([row],実行器=spy)
        self.assertEqual(result['集計']['期待一致'],1)
        self.assertEqual(calls,[('命題',row['要求'],{'詳細':False})])

    def test_正しい未確定を実質回答に数えない(self):
        result=評価する([ケース('未確定',query='Q')])['集計']
        self.assertEqual(result['期待一致'],1);self.assertEqual(result['実質回答数'],0)
        self.assertEqual(result['意味未確定数'],1)

    def test_正常な保留を実質回答に数えない(self):
        row=ケース(content='未知の動作をしてください。');row['期待']={'状態':'保留'}
        result=評価する([row])['集計']
        self.assertEqual(result['期待一致'],1);self.assertEqual(result['正常な保留数'],1)
        self.assertEqual(result['実質回答数'],0)

    def test_誤った意味結果を検出(self):
        result=評価する([ケース('反証')])['集計']
        self.assertEqual(result['期待一致'],0);self.assertEqual(result['期待不一致'],1)
        self.assertEqual(result['実質回答中の期待一致率'],0)

    def test_実行例外を保留へ変えない(self):
        row=ケース();row['期待']={'状態':'保留'}
        def fail(*args,**kwargs):raise RuntimeError('試験用例外')
        result=評価する([row],実行器=fail)['集計']
        self.assertEqual(result['実行例外'],1);self.assertEqual(result['正常な保留数'],0)
        self.assertEqual(result['期待不一致'],1)

    def test_入力区分別を別集計する(self):
        a=ケース();b=ケース('未確定',query='Q');b['ID']='C2';b['区分']='外部提供'
        report=評価する([a,b])
        self.assertEqual(report['区分別']['開発生成']['件数'],1)
        self.assertEqual(report['区分別']['外部提供']['実質回答数'],0)

    def test_無内容の成功期待を拒否(self):
        row=ケース();row['期待']={'状態':'合格'}
        with self.assertRaises(ValueError):self.read([row])

    def test_保留への意味期待を拒否(self):
        row=ケース();row['期待']['状態']='保留'
        with self.assertRaises(ValueError):self.read([row])

    def test_重複ケースを拒否(self):
        with self.assertRaises(ValueError):self.read([ケース(),ケース()])

    def test_空ケースを拒否(self):
        with self.assertRaises(ValueError):self.read([])

    def test_未知欄を拒否(self):
        row=ケース();row['答え']='P'
        with self.assertRaises(ValueError):self.read([row])

    def test_JSON重複キーを拒否(self):
        with self.assertRaises(ValueError):JSON読取('{"A":1,"A":2}')

    def test_JSON非有限数を拒否(self):
        for n in ('NaN','Infinity','-Infinity'):
            with self.subTest(n=n),self.assertRaises(ValueError):JSON読取('{"値":'+n+'}')

    def test_元バイトから入力指紋を返す(self):
        rows,digest=self.read([ケース()]);self.assertEqual(len(digest),64)
        self.assertEqual(rows,[ケース()])

if __name__=='__main__':unittest.main()
