"""製品CLI・台帳・実localhost HTTPで帰属/文脈/取得命題を確認する。"""
import json
from pathlib import Path
import subprocess
import sys
import unittest
from minidora.製品版.製品チャット import 製品ミニドラ
from minidora.会話意味 import 意味指紋


class 文脈製品入口試験(unittest.TestCase):
    def test_実CLIで帰属内容と現実を区別(self):
        root=Path(__file__).resolve().parents[1]
        script='資料「A」を登録:太郎は「私は猫である」と述べた。\n資料「A」から「太郎は「太郎は猫である」と述べた」は言える？\n資料「A」から「太郎は猫である」は言える？\nexit\n'
        r=subprocess.run([sys.executable,'-m','minidora.製品版','--汎用'],input=script,encoding='utf-8',capture_output=True,cwd=root,timeout=20)
        self.assertEqual(r.returncode,0,r.stderr);self.assertIn('支持されます',r.stdout);self.assertIn('偽であるとは判定しません',r.stdout)
    def test_デモで人工取得も含む17発話が完了(self):
        root=Path(__file__).resolve().parents[1]
        r=subprocess.run([sys.executable,'tools/文脈命題デモ.py','--json'],encoding='utf-8',capture_output=True,cwd=root,timeout=20)
        self.assertEqual(r.returncode,0,r.stderr);d=json.loads(r.stdout)
        self.assertEqual(len(d['会話']),14);self.assertEqual(len(d['人工取得']),3)
        self.assertEqual(d['人工取得'][-1]['供給回数'],{'検索':1,'本文取得':1})
    def test_監査ハッシュは内部文脈追跡と対応(self):
        s=製品ミニドラ(汎用会話=True);s.応答('資料「A」を登録:PまたはQかつR。',セッションID='audit21')
        r=s.応答('資料「A」から「PまたはQ」は言える？',セッションID='audit21')
        self.assertTrue(s.監査台帳.検証(r.追跡ID));self.assertEqual(r.経路,'汎用会話')
        self.assertTrue(r.メタデータ['汎用追跡']['資料解釈検討'])
    def test_能力一覧に帰属と局所照応を表示(self):
        s=製品ミニドラ(汎用会話=True);self.assertIn('局所照応',s.応答('できることを教えて').本文)
        self.assertTrue(any('帰属' in item for item in s.能力一覧()))
    def test_実HTTPで資料解釈を選択して説明(self):
        from http.server import ThreadingHTTPServer
        from http.client import HTTPConnection
        from threading import Thread
        from minidora.製品版.api import APIHandler
        class Handler(APIHandler):
            def log_message(self,*args):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        server.app=製品ミニドラ(汎用会話=True);server.同一生成元限定=True
        thread=Thread(target=server.serve_forever,kwargs={'poll_interval':0.01},daemon=True);thread.start()
        try:
            steps=(('資料「A」を登録:PまたはQかつR。','合格'),
                   ('資料「A」から「R」は言える？','確認待ち'),('資料解釈は2です','合格'),('根拠を説明して','合格'))
            for text,state in steps:
                conn=HTTPConnection('127.0.0.1',server.server_address[1],timeout=10)
                try:
                    conn.request('POST','/api/chat',body=json.dumps({'message':text,'session_id':'ctx-http'},ensure_ascii=False).encode())
                    response=conn.getresponse();data=json.loads(response.read())
                    self.assertEqual(response.status,200);self.assertEqual(data['status'],state,data)
                    self.assertIsNone(response.getheader('Access-Control-Allow-Origin'))
                finally:conn.close()
            self.assertIn('指定した資料解釈2',data['response']);self.assertIn('支持されます',data['response'])
        finally:server.shutdown();server.server_close();thread.join(timeout=5)

if __name__=='__main__':unittest.main()
