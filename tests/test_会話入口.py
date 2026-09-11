"""追加CLIと製品の明示汎用モードを、実クラスで通す。既定の製品経路は変えない。"""
from pathlib import Path
from unittest.mock import patch
import json,os,subprocess,sys,tempfile,unittest
from minidora.製品版.製品チャット import 製品ミニドラ
from minidora.汎用会話 import 汎用会話セッション

class 会話入口試験(unittest.TestCase):
    def test_製品の明示汎用モードで計画実行する(self):
        app=製品ミニドラ(汎用会話=True)
        r=app.応答('「x**2」をxで微分した結果は？',セッションID='demo')
        self.assertEqual(r.状態,'合格');self.assertEqual(r.経路,'汎用会話');self.assertIn('2*x',r.本文)
        self.assertTrue(app.監査台帳.検証(r.追跡ID))
        json.dumps(r.辞書化(),ensure_ascii=False,allow_nan=False)
    def test_製品でも確認返答を継続する(self):
        app=製品ミニドラ(汎用会話=True)
        for name,n in [('A',75),('B',60)]:
            r=app.応答('資料「'+name+'」を登録:{"売上":'+str(n)+'}',セッションID='a')
            self.assertEqual(r.状態,'合格')
        r=app.応答('資料「A」と資料「B」の売上を比較して',セッションID='a');self.assertEqual(r.状態,'確認待ち')
        r=app.応答('単位は円です',セッションID='a');self.assertEqual(r.状態,'合格');self.assertIn('-15円',r.本文)
    def test_失敗や保留をCoreへ透過させない(self):
        class 禁止Core:
            def 応答(self,text):raise AssertionError('Coreへ透過した')
        app=製品ミニドラ(汎用会話=True,基礎ミニドラ=禁止Core())
        r=app.応答('架空の答えを作って');self.assertEqual(r.状態,'保留');self.assertEqual(r.経路,'汎用会話')
    def test_既定の製品入口は旧経路を維持する(self):
        app=製品ミニドラ();r=app.応答('2+3');self.assertNotEqual(r.経路,'汎用会話');self.assertIn('5',r.本文)
    def test_製品のセッションは混線しない(self):
        app=製品ミニドラ(汎用会話=True)
        app.応答('「2+3」を計算して',セッションID='a')
        self.assertEqual(app.応答('それを詳しく説明して',セッションID='b').状態,'保留')
    def test_発話上限に達しても初期化で回復できる(self):
        app=汎用会話セッション('reset',最大発話=1)
        self.assertTrue(app.応答('こんにちは').成立)
        self.assertFalse(app.応答('こんにちは').成立)
        self.assertTrue(app.応答('/初期化').成立)
        self.assertTrue(app.応答('こんにちは').成立)
    def test_下位統合の初期化後に古い成果を使わない(self):
        s=汎用会話セッション('reset');s.応答('「2+3」を計算して');s.統合.初期化()
        self.assertFalse(s.応答('それを詳しく説明して').成立)
    def test_製品設定はboolのみ(self):
        with self.assertRaises(ValueError):製品ミニドラ(汎用会話=1)
    def run_cli(self,*args,input=None,product=False,env=None):
        root=Path(__file__).resolve().parents[1]
        command=[sys.executable,'-m','minidora.製品版','--汎用'] if product else [sys.executable,str(root/'tools/汎用チャット.py')]
        return subprocess.run(command+list(args),input=input,encoding='utf-8',capture_output=True,timeout=20,cwd=root,env=env)
    def test_追加CLIの単発(self):
        r=self.run_cli('「2+3」を計算して');self.assertEqual(r.returncode,0,r.stderr);self.assertIn('5',r.stdout)
    def test_結果質問の追加CLI(self):
        r=self.run_cli('x**2をxで微分した結果は？');self.assertEqual(r.returncode,0,r.stderr);self.assertIn('2*x',r.stdout)
    def test_JSON追跡をシリアライズできる(self):
        r=self.run_cli('--json','「x**2」をxで微分した結果は？');self.assertEqual(r.returncode,0,r.stderr)
        obj=json.loads(r.stdout);self.assertEqual(obj['状態'],'合格');self.assertIn('HDS保持',obj['追跡'])
    def test_継続CLIで再参照する(self):
        r=self.run_cli(input='「x**3」をxで微分して\nそれをxで微分して\n/終了\n')
        self.assertEqual(r.returncode,0,r.stderr);self.assertIn('6*x',r.stdout)
    def test_標準入力の既定文字コードへ依存しない(self):
        r=self.run_cli(input='「2+3」を計算して\n/終了\n',env={**os.environ,'PYTHONIOENCODING':'cp1252'})
        self.assertEqual(r.returncode,0,r.stderr);self.assertIn('5',r.stdout)
    def test_不正UTF8は追跡例外なく終了する(self):
        root=Path(__file__).resolve().parents[1]
        r=subprocess.run([sys.executable,str(root/'tools/汎用チャット.py')],input=b'\xff\n',capture_output=True,cwd=root,timeout=20)
        self.assertEqual(r.returncode,2);self.assertNotIn(b'Traceback',r.stderr)
    def test_入力超過は後続を実行しない(self):
        r=self.run_cli(input='あ'*8193+'\n「2+3」を計算して\n')
        self.assertEqual(r.returncode,2);self.assertNotIn('処理結果',r.stdout)
    def test_二つの明示ファイルを読む(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/'a.json';b=Path(d)/'b.json'
            a.write_text('{"売上":75,"単位":"円"}',encoding='utf-8');b.write_text('{"売上":60,"単位":"円"}',encoding='utf-8')
            r=self.run_cli('--資料','A='+str(a),'--資料','B='+str(b),'資料「A」と資料「B」の売上を比較して')
            self.assertEqual(r.returncode,0,r.stderr);self.assertIn('-15円',r.stdout)
    def test_未知ファイルを自動探索しない(self):
        r=self.run_cli('--資料','A=/a/nonexistent.json','資料「A」と資料「B」の売上を比較して')
        self.assertEqual(r.returncode,2)
    def test_同名資料を黙って上書きしない(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/'a.txt';a.write_text('1',encoding='utf-8')
            r=self.run_cli('--資料','A='+str(a),'--資料','A='+str(a),'「2+3」を計算して')
            self.assertEqual(r.returncode,2)
    def test_製品CLIの不正UTF8は追跡例外なく終了(self):
        root=Path(__file__).resolve().parents[1]
        r=subprocess.run([sys.executable,'-m','minidora.製品版','--汎用'],input=b'\xff\n',capture_output=True,cwd=root,timeout=20)
        self.assertEqual(r.returncode,2);self.assertNotIn(b'Traceback',r.stderr)
    def test_製品CLIの明示モード(self):
        r=self.run_cli('「x**2」をxで微分して',product=True)
        self.assertEqual(r.returncode,0,r.stderr);self.assertIn('2*x',r.stdout)

class 会話HTTP試験(unittest.TestCase):
    def setUp(self):
        from http.server import ThreadingHTTPServer
        from threading import Thread
        from minidora.製品版.api import APIHandler
        class 静音Handler(APIHandler):
            def log_message(self, *args): pass
        self.server=ThreadingHTTPServer(('127.0.0.1',0),静音Handler)
        self.server.app=製品ミニドラ(汎用会話=True)
        self.server.同一生成元限定=True
        self.thread=Thread(target=self.server.serve_forever,kwargs={'poll_interval':0.01},daemon=True)
        self.thread.start()
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join(timeout=5)
    def request(self,method,path,body=None,headers=None):
        from http.client import HTTPConnection
        c=HTTPConnection('127.0.0.1',self.server.server_address[1],timeout=10)
        try:
            raw=json.dumps(body,ensure_ascii=False).encode('utf-8') if body is not None else None
            c.request(method,path,body=raw,headers=headers or {})
            r=c.getresponse();return r.status,dict(r.headers),r.read()
        finally:c.close()
    def test_HTTPの標準入口から同じ会話を処理(self):
        code,headers,raw=self.request('POST','/api/chat',{'message':'x**2をxで微分した結果は？','session_id':'http'})
        r=json.loads(raw);self.assertEqual(code,200);self.assertEqual(r['status'],'合格');self.assertIn('2*x',r['response'])
        self.assertNotIn('Access-Control-Allow-Origin',headers)
    def test_既存画面を配信する(self):
        code,_,raw=self.request('GET','/');self.assertEqual(code,200);self.assertIn(b'<html',raw.lower())
    def test_汎用モードで未対応の旧能力を広告しない(self):
        code,_,raw=self.request('GET','/api/capabilities');self.assertEqual(code,200)
        caps=json.loads(raw)['capabilities'];self.assertNotIn('ニュース',caps);self.assertTrue(any('二資料' in x for x in caps))
    def test_別サイトの生成元は拒否(self):
        code,_,_=self.request('POST','/api/chat',{'message':'こんにちは'},headers={'Origin':'https://untrusted.example'})
        self.assertEqual(code,403)
    def test_別ホスト名への書換は拒否(self):
        code,_,_=self.request('GET','/health',headers={'Host':'untrusted.example'})
        self.assertEqual(code,403)
    def test_同一生成元の操作は許可(self):
        origin='http://127.0.0.1:'+str(self.server.server_address[1])
        code,_,_=self.request('POST','/api/chat',{'message':'こんにちは'},headers={'Origin':origin})
        self.assertEqual(code,200)

if __name__=='__main__':unittest.main()
