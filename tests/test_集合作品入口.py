"""集合会話を標準製品・CLI・実localhost HTTPへ接続する。外部取得は使わない。"""
import json
from pathlib import Path
import subprocess
import sys
import unittest
from minidora.製品版.製品チャット import 製品ミニドラ

登録文=('資料「A」を登録:{"売上":75,"費用":50}',
        '資料「B」を登録:{"売上":60,"費用":40}',
        '資料「C」を登録:{"実績":{"売上":95,"費用":65}}')
集合要求='この3つの売上の合計と平均を円で教えて。表で'

class 集合作品入口試験(unittest.TestCase):
    def app(self):
        app=製品ミニドラ(汎用会話=True)
        for text in 登録文:self.assertEqual(app.応答(text,セッションID='集合').状態,'合格')
        return app
    def test_標準製品が集合を計画し監査台帳へ採用する(self):
        app=self.app();r=app.応答(集合要求,セッションID='集合')
        self.assertEqual(r.状態,'合格');self.assertIn('230/3円',r.本文)
        self.assertEqual(r.経路,'汎用会話');self.assertTrue(app.監査台帳.検証(r.追跡ID))
        json.dumps(r.辞書化(),ensure_ascii=False,allow_nan=False)
    def test_標準製品の訂正が集合目的を再実行する(self):
        app=self.app();self.assertEqual(app.応答(集合要求,セッションID='集合').状態,'合格')
        r=app.応答('訂正:属性は費用です',セッションID='集合')
        self.assertEqual(r.状態,'合格');self.assertIn('155/3円',r.本文)
    def test_標準製品でも別セッションへ資料を漏らさない(self):
        r=self.app().応答(集合要求,セッションID='別')
        self.assertEqual(r.状態,'保留');self.assertNotIn('230/3',r.本文)
    def run_cli(self,command,input=None):
        root=Path(__file__).resolve().parents[1]
        return subprocess.run([sys.executable,*command],input=input,encoding='utf-8',
                              capture_output=True,cwd=root,timeout=20)
    def test_製品CLIで登録から確認再開して集合を回答する(self):
        text='\n'.join((*登録文,集合要求.replace('を円で','を'),'単位は円です','/終了'))+'\n'
        r=self.run_cli(['-m','minidora.製品版','--汎用'],text)
        self.assertEqual(r.returncode,0,r.stderr);self.assertIn('230/3円',r.stdout)
    def test_集合デモが再計画訂正失効を通して完走する(self):
        r=self.run_cli(['tools/集合会話デモ.py','--json'])
        self.assertEqual(r.returncode,0,r.stderr)
        rows=json.loads(r.stdout)['会話']
        self.assertTrue(any(row['再計画'] for row in rows))
        self.assertTrue(any(row['状態']=='保留' and '失効' in row['本文'] for row in rows))
        self.assertIn('差は45円',rows[-1]['本文'])
    def test_汎用CLIのJSONが集合と試行履歴を保持する(self):
        r=self.run_cli(['tools/汎用チャット.py','--json'],'\n'.join((*登録文,集合要求,'/終了'))+'\n')
        self.assertEqual(r.returncode,0,r.stderr)
        row=json.loads(r.stdout.splitlines()[-1]);self.assertEqual(row['状態'],'合格')
        self.assertEqual(len(row['追跡']['再計画']),1)

class 集合作品HTTP試験(unittest.TestCase):
    def test_実localhostの会話登録集合説明を同一セッションで処理(self):
        from http.server import ThreadingHTTPServer
        from http.client import HTTPConnection
        from threading import Thread
        from minidora.製品版.api import APIHandler
        class 静音Handler(APIHandler):
            def log_message(self,*args):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),静音Handler)
        server.app=製品ミニドラ(汎用会話=True);server.同一生成元限定=True
        thread=Thread(target=server.serve_forever,kwargs={'poll_interval':0.01},daemon=True)
        thread.start()
        try:
            for text in (*登録文,集合要求,'それの計算過程も説明して'):
                conn=HTTPConnection('127.0.0.1',server.server_address[1],timeout=10)
                try:
                    conn.request('POST','/api/chat',body=json.dumps({'message':text,'session_id':'http-集合'},ensure_ascii=False).encode('utf-8'))
                    response=conn.getresponse();raw=response.read();value=json.loads(raw)
                    self.assertEqual(response.status,200);self.assertEqual(value['status'],'合格',value)
                    self.assertIsNone(response.getheader('Access-Control-Allow-Origin'))
                finally:conn.close()
            self.assertIn('平均 = 合計 / 3',value['response'])
        finally:
            server.shutdown();server.server_close();thread.join(timeout=5)

if __name__=='__main__':unittest.main()
