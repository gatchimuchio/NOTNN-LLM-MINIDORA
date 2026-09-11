"""共通JSON入口・独立CLI・明示権限の契約。"""
import json
from pathlib import Path
import subprocess
import sys
import unittest
from minidora.統合実行 import 統合セッション
from minidora.統合入出力 import JSON要求を読む, 統合要求を実行

ROOT=Path(__file__).resolve().parents[1]


def math_request():
    return {'種別':'能力','能力':'記号演算','入力':{'データ':{'式':'(x+1)**3','変数':['x']}},
            '設定':{'操作':'微分','対象変数':'x'}}


class 統合通信試験(unittest.TestCase):
    def test_単一能力の共通スキーマ(self):
        r=統合要求を実行(統合セッション('通信'),math_request())
        self.assertEqual(r['状態'],'合格',r)
        self.assertEqual(r['本文'],'3*x**2 + 6*x + 3')

    def test_未知項目を無視しない(self):
        req=math_request();req['推測で通す']=True
        s=統合セッション('通信');start=s.起点();r=統合要求を実行(s,req)
        self.assertEqual(r['状態'],'失敗');self.assertEqual(start,s.起点())

    def test_JSONの重複キーと非有限数値を拒否(self):
        for raw in ('{"x":1,"x":2}','{"x":NaN}','{"x":Infinity}'):
            with self.assertRaises(ValueError):JSON要求を読む(raw)

    def test_無効な素材を空Dataにしない(self):
        req=math_request();req['入力']={'本文':None}
        self.assertEqual(統合要求を実行(統合セッション('s'),req)['状態'],'失敗')

    def test_一覧と初期化を明示操作にする(self):
        s=統合セッション('s')
        self.assertEqual(len(統合要求を実行(s,{'種別':'一覧'})['能力']),29)
        start=s.起点();統合要求を実行(s,{'種別':'初期化'})
        self.assertNotEqual(start,s.起点())

    def test_CLIの連続要求で再利用する(self):
        req=math_request()
        r=subprocess.run([sys.executable,str(ROOT/'tools/統合チャット.py')],
                         input=json.dumps(req)+'\n'+json.dumps(req)+'\n',capture_output=True,encoding='utf-8',timeout=15)
        self.assertEqual(r.returncode,0,r.stderr)
        rows=[json.loads(x) for x in r.stdout.splitlines()]
        self.assertEqual(rows[0]['本文'],rows[1]['本文'])
        self.assertEqual(rows[1]['計測']['再利用差分']['記号演算']['再利用'],1)

    def test_CLIの不正JSONは非零終了(self):
        r=subprocess.run([sys.executable,str(ROOT/'tools/統合チャット.py')],input='{"種別":"一覧","種別":"初期化"}\n',
                         capture_output=True,encoding='utf-8',timeout=15)
        self.assertNotEqual(r.returncode,0)
        self.assertEqual(json.loads(r.stdout)['状態'],'失敗')


class 巨大行境界試験(unittest.TestCase):
    def test_巨大行の後半を独立要求にしない(self):
        r=subprocess.run([sys.executable,str(ROOT/'tools/統合チャット.py')],
            input=' '*2000001+'{"種別":"初期化"}\n',capture_output=True,encoding='utf-8',timeout=15)
        self.assertEqual(r.returncode,1)
        self.assertEqual(len(r.stdout.splitlines()),1)
        self.assertEqual(json.loads(r.stdout)['理由'],'入力行上限')
