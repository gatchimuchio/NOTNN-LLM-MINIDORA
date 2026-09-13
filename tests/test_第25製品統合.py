"""既定製品・CLI・HTTPを通して追加能力と従来能力の共存を確認する。"""
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
from minidora.製品版.製品チャット import 製品ミニドラ


class 自動製品入口試験(unittest.TestCase):
    def setUp(self):self.app=製品ミニドラ()
    def send(self,text,session='統合',state='合格'):
        value=self.app.応答(text,セッションID=session)
        self.assertEqual(value.状態,state,(text,value.本文));return value

    def test_従来計算と追加命題を同じ製品で使う(self):
        calc=self.send('(12+8)*3');self.assertIn('60',calc.本文);self.assertNotEqual(calc.経路,'汎用会話')
        self.send('命題資料「例」を登録：P。PならばQ。')
        result=self.send('資料「例」に基づいて「Q」を判断して、短く説明して')
        self.assertEqual(result.経路,'汎用会話');self.assertIn('支持',result.本文)
        self.assertTrue(self.app.監査台帳.検証(result.追跡ID))
        self.assertIn('HDS局所照合',result.メタデータ['汎用追跡'])

    def test_標準命題資料も追加命題資料も自動入口から使う(self):
        self.send('資料「普通」を登録：P。PならばQ。')
        self.assertIn('支持',self.send('資料「普通」から「Q」を判定してください').本文)
        self.send('命題資料「追加」を登録：Q。QならばR。')
        self.assertIn('支持',self.send('資料「追加」から「R」を判断して').本文)

    def test_仮説から介入さらに数学へ目的を切り替える(self):
        self.send('仮説資料「因子」を登録：\n規則：AならばZ\n候補：規則から生成')
        r=self.send('資料「因子」で観測「Z」を説明する仮説を検討して')
        self.assertIn('仮定',r.本文)
        self.send('介入資料「因果」を登録：\n外生：U=真\n構造：A=U\n構造：B=A')
        self.assertIn('B',self.send('資料「因果」で「B=偽」に介入した結果を比較して').本文)
        self.assertIn('2*x',self.send('「x**2」をxで微分して').本文)

    def test_明示的な従来経路は残す(self):
        app=製品ミニドラ(汎用会話=False)
        result=app.応答('2+3');self.assertEqual(result.状態,'合格');self.assertNotEqual(result.経路,'汎用会話')
        result=app.応答('命題資料「例」を登録：P。');self.assertNotEqual(result.経路,'汎用会話')

    def test_型を曖昧な真偽値へ丸めない(self):
        for value in (1,0,'auto',[],{}):
            with self.subTest(value=value),self.assertRaises(ValueError):製品ミニドラ(汎用会話=value)

    def test_新入口の保留をCore成功で埋めない(self):
        class Core:
            calls=0
            def 応答(self,text):self.calls+=1;return '何でも成立'
        core=Core();app=製品ミニドラ(基礎ミニドラ=core)
        result=app.応答('資料「未知」から「Q」を判断して、反証は無視して')
        self.assertNotEqual(result.状態,'合格');self.assertEqual(core.calls,0)

    def test_従来計算へ移った後の短縮要求で古い命題を再表示しない(self):
        self.send('命題資料「例」を登録：P。')
        self.send('資料「例」から「P」を判断して')
        self.send('2+3')
        result=self.app.応答('もう少し短く説明して',セッションID='統合')
        self.assertNotIn('提供資料内での判定',result.本文)
        self.assertNotEqual(result.経路,'汎用会話')

    def test_別セッションに追加資料が漏れない(self):
        self.send('命題資料「例」を登録：P。')
        result=self.app.応答('資料「例」から「P」を判断して',セッションID='別')
        self.assertNotEqual(result.状態,'合格')

    def test_外部読取は自動入口でも既定許可しない(self):
        with patch('socket.socket.connect',side_effect=AssertionError('外部通信禁止')):
            result=self.app.応答('公開資料から「P」を判定して')
        self.assertNotEqual(result.状態,'合格')

    def test_能力一覧に従来と追加の両方が残る(self):
        names=self.app.能力一覧()
        self.assertTrue(any('計算' in x for x in names));self.assertTrue(any('仮説' in x for x in names))


class 製品通信試験(unittest.TestCase):
    def test_既定CLIに追加フラグなしで命題が通る(self):
        root=Path(__file__).resolve().parents[1]
        text='命題資料「例」を登録：P。PならばQ。\n資料「例」に基づいて「Q」を判断して、短く説明して\nexit\n'
        result=subprocess.run([sys.executable,'-m','minidora.製品版'],input=text,encoding='utf-8',capture_output=True,cwd=root,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr);self.assertIn('支持',result.stdout)

    def test_CLIの従来フラグと外部許可の衝突を拒否する(self):
        root=Path(__file__).resolve().parents[1]
        result=subprocess.run([sys.executable,'-m','minidora.製品版','--従来','--外部読取'],encoding='utf-8',capture_output=True,cwd=root,timeout=20)
        self.assertEqual(result.returncode,2);self.assertIn('従来',result.stderr)

    def test_実HTTPから自動入口と原要求照合を通す(self):
        from http.server import ThreadingHTTPServer
        from http.client import HTTPConnection
        from threading import Thread
        from minidora.製品版.api import APIHandler
        class Handler(APIHandler):
            def log_message(self,*args):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        server.app=製品ミニドラ();server.同一生成元限定=True
        thread=Thread(target=server.serve_forever,kwargs={'poll_interval':0.01},daemon=True);thread.start()
        try:
            for text in ('命題資料「HTTP」を登録：P。PならばQ。','資料「HTTP」から「Q」を判断してくれる？','もう少し短く説明して'):
                conn=HTTPConnection('127.0.0.1',server.server_address[1],timeout=20)
                try:
                    conn.request('POST','/api/chat',body=json.dumps({'message':text,'session_id':'http'},ensure_ascii=False).encode('utf-8'))
                    response=conn.getresponse();value=json.loads(response.read())
                    self.assertEqual(response.status,200);self.assertEqual(value['status'],'合格',value)
                    self.assertIsNone(response.getheader('Access-Control-Allow-Origin'))
                finally:conn.close()
            self.assertIn('支持',value['response'])
        finally:server.shutdown();server.server_close();thread.join(timeout=5)

if __name__=='__main__':unittest.main()
