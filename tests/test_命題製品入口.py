"""実CLI、標準監査台帳、実localhost HTTPを通す。公開Web・実ブラウザの試験ではない。"""
import json
from pathlib import Path
import subprocess
import sys
import unittest
from minidora.製品版.製品チャット import 製品ミニドラ


class 命題製品入口試験(unittest.TestCase):
    def test_標準CLIで命題登録から推論と説明まで完了(self):
        text='資料「規則」を登録:P。PならばQ。\n資料「規則」から「Q」は言える？\n根拠を説明して\nexit\n'
        root=Path(__file__).resolve().parents[1]
        r=subprocess.run([sys.executable,'-m','minidora.製品版','--汎用'],input=text,encoding='utf-8',capture_output=True,cwd=root,timeout=20)
        self.assertEqual(r.returncode,0,r.stderr);self.assertIn('支持されます',r.stdout);self.assertIn('条件適用',r.stdout)
    def test_命題会話デモが訂正失効意味候補を通す(self):
        root=Path(__file__).resolve().parents[1]
        r=subprocess.run([sys.executable,'tools/命題会話デモ.py','--json'],encoding='utf-8',capture_output=True,cwd=root,timeout=20)
        self.assertEqual(r.returncode,0,r.stderr)
        rows=json.loads(r.stdout)['会話'];self.assertEqual(len(rows),12)
        self.assertTrue(any(x['判定']=='矛盾' for x in rows));self.assertEqual(rows[-1]['判定'],'未確定')
    def test_標準監査台帳と命題追跡が対応(self):
        app=製品ミニドラ(汎用会話=True)
        app.応答('資料「規則」を登録:P。PならばQ。',セッションID='命題')
        result=app.応答('資料「規則」から「Q」は言える？',セッションID='命題')
        self.assertTrue(app.監査台帳.検証(result.追跡ID));self.assertEqual(result.経路,'汎用会話')
    def test_実HTTPで意味候補から確認再開し根拠を返す(self):
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
            steps=(('資料「規則」を登録:太郎は猫である。太郎は鳥ではない。','合格'),
                   ('資料「規則」から「すべての猫は鳥ではない」は言える？','確認待ち'),
                   ('解釈は2です','合格'),('根拠を説明して','合格'))
            for text,state in steps:
                conn=HTTPConnection('127.0.0.1',server.server_address[1],timeout=10)
                try:
                    conn.request('POST','/api/chat',body=json.dumps({'message':text,'session_id':'http-命題'},ensure_ascii=False).encode('utf-8'))
                    response=conn.getresponse();value=json.loads(response.read())
                    self.assertEqual(response.status,200);self.assertEqual(value['status'],state,value)
                    self.assertIsNone(response.getheader('Access-Control-Allow-Origin'))
                finally:conn.close()
            self.assertIn('存在証拠',value['response'])
        finally:server.shutdown();server.server_close();thread.join(timeout=5)

if __name__=='__main__':unittest.main()
