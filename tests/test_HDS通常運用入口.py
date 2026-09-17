"""CLI・HTTPの実入口と、科学・仮説等の共通能力接続。"""
from __future__ import annotations
import http.client
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from threading import Thread
import unittest

from minidora.HDS運用 import HDS運用セッション
from minidora.HDS運用.製品 import HDS運用製品
from minidora.HDS運用.HTTP入口 import サーバを構成
from minidora.製品版.型 import 能力結果

ROOT=Path(__file__).resolve().parents[1]


class HDS通常HTTP試験(unittest.TestCase):
    def setUp(self):
        self.app=HDS運用製品()
        self.server=サーバを構成(self.app,ポート=0)
        self.thread=Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.port=self.server.server_address[1]
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join(5)
    def call(self, path, value=None, origin=None, raw=None):
        conn=http.client.HTTPConnection('127.0.0.1',self.port,timeout=30)
        headers={'Content-Type':'application/json'}
        if origin is not None:headers['Origin']=origin
        body=raw if raw is not None else json.dumps(value,ensure_ascii=False).encode() if value is not None else None
        conn.request('POST' if body is not None else 'GET',path,body,headers)
        r=conn.getresponse();status=r.status;通信値=r.read();conn.close()
        return status,json.loads(通信値)
    def test_HTTP回答と実HDS監査(self):
        status,d=self.call('/api/chat',{'message':'2+3','session_id':'A'})
        self.assertEqual(status,200);self.assertEqual(d['status'],'COMMIT')
        self.assertEqual(d['経路'],'HDS通常運用')
        status,t=self.call('/api/trace/'+d['追跡_id'])
        self.assertEqual(status,200);self.assertTrue(t['valid'])
        追跡値=t['追跡']['イベント'][0]['出力']['HDS']
        self.assertIn('HDS運用/能力/記号演算',[x['作用ID'] for x in 追跡値['作用履歴']])
    def test_HTTP同一セッションの継続(self):
        self.call('/api/chat',{'message':'「x**3」をxで微分して','session_id':'A'})
        status,d=self.call('/api/chat',{'message':'それをxで微分して','session_id':'A'})
        self.assertEqual(status,200);self.assertEqual(d['status'],'COMMIT');self.assertIn('6*x',d['response'])
    def test_HTTP別セッションの隔離(self):
        self.call('/api/chat',{'message':'2+3','session_id':'A'})
        _,d=self.call('/api/chat',{'message':'それから数字を抽出して','session_id':'B'})
        self.assertEqual(d['status'],'SUSPEND')
    def test_HTTP外部生成元を拒否(self):
        status,_=self.call('/api/chat',{'message':'2+3'},origin='https://example.com')
        self.assertEqual(status,403)
    def test_HTTP異型と未知欄と重複を拒否(self):
        for value in ([],{'message':[]},{'message':'2+3','session_id':[]},{'message':'2+3','外部許可':True}):
            with self.subTest(value=value):self.assertEqual(self.call('/api/chat',value)[0],400)
        self.assertEqual(self.call('/api/chat',raw=b'{"message":"a","message":"b"}')[0],400)
    def test_HTTP能力一覧でセッションを作らない(self):
        status,d=self.call('/api/capabilities')
        self.assertEqual(status,200);self.assertEqual(len(d['capabilities']),48)
        self.assertEqual(self.app._セッション,{})
    def test_画面が現在と従来の通信鍵を読む(self):
        script=(ROOT/'src/minidora/製品版/web/app.js').read_text()
        self.assertIn("d['追跡_id']??d.trace_id",script)
        self.assertIn('d["追跡"]||d.trace',script)


class HDS運用CLI試験(unittest.TestCase):
    def run_cli(self, *args, text=None):
        return subprocess.run([sys.executable,'-m','minidora.HDS運用',*args],input=text,
            encoding='utf-8',capture_output=True,timeout=60,cwd=ROOT,env={**os.environ,'PYTHONPATH':str(ROOT/'src')})
    def test_通常CLI起動(self):
        r=self.run_cli('2+3');self.assertEqual(r.returncode,0,r.stderr);self.assertIn('5',r.stdout)
    def test_製品CLIのHDS指定(self):
        r=subprocess.run([sys.executable,'-m','minidora.製品版','--HDS','2+3'],capture_output=True,
            encoding='utf-8',timeout=60,cwd=ROOT,env={**os.environ,'PYTHONPATH':str(ROOT/'src')})
        self.assertEqual(r.returncode,0,r.stderr);self.assertIn('5',r.stdout)
    def test_JSONLが同じセッションで動く(self):
        r=self.run_cli('--JSONL',text='{"依頼":"2+3"}\n{"依頼":"それから数字を抽出して"}\n')
        self.assertEqual(r.returncode,0,r.stderr)
        rows=[json.loads(x) for x in r.stdout.splitlines()]
        self.assertEqual([x['状態'] for x in rows],['COMMIT','COMMIT'])
        self.assertIn('5',rows[-1]['本文'])
    def test_JSONL未知欄を拒否(self):
        r=self.run_cli('--JSONL',text='{"依頼":"2+3","外部許可":true}\n')
        self.assertEqual(r.returncode,2)
    def test_保存ファイルから再開(self):
        with tempfile.TemporaryDirectory() as d:
            p=str(Path(d)/'state.json')
            r=self.run_cli('--保存',p,'「x**3」をxで微分して');self.assertEqual(r.returncode,0,r.stderr)
            r=self.run_cli('--読込',p,'それをxで微分して');self.assertEqual(r.returncode,0,r.stderr);self.assertIn('6*x',r.stdout)
    def test_明示ファイルを資料として読む(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'input.txt';p.write_text('費用123。',encoding='utf-8')
            r=self.run_cli('--資料','本文='+str(p),'本文から数字を抽出して')
            self.assertEqual(r.returncode,0,r.stderr);self.assertIn('123',r.stdout)


class HDS既存専門能力接続試験(unittest.TestCase):
    def test_科学能力を候補報告として実行(self):
        q='The spin state is 1 |up> + 1 |down>. Evaluate 2 sigma_z + 3 sigma_x.'
        s=HDS運用セッション(資料={'問題':能力結果(True,'',データ={'問題':q,'選択肢':['0','1','2','3']})})
        r=s.応答('資料「問題」の科学候補を検討して')
        self.assertTrue(r.成立,r.理由)
        self.assertIn('4番「3」',r.本文);self.assertIn('候補生成の報告',r.本文)
        self.assertIn('HDS運用/能力/科学候補報告',[h.作用ID for h in r.実行.履歴])
    def test_科学能力の正解情報を拒否(self):
        q=json.dumps({'問題':'unknown','選択肢':['a','b'],'正解':1})
        r=HDS運用セッション(資料={'問題':q}).応答('資料「問題」の科学候補を検討して')
        self.assertFalse(r.成立)
    def test_科学候補未取得を正答にしない(self):
        q=json.dumps({'問題':'unknown','選択肢':['a','b']})
        r=HDS運用セッション(資料={'問題':q}).応答('資料「問題」の科学候補を検討して')
        self.assertTrue(r.成立,r.理由);self.assertIn('得られませんでした',r.本文)
    def test_有限仮説を通常HDSから検討する(self):
        s=HDS運用セッション()
        資料定義={'事実':[], '規則':[{'識別子':'r1','前件':['太郎は猫である'], '後件':'太郎は動物である','出典':'提供規則'}],
                '仮説候補':['太郎は猫である'],'観測':['太郎は動物である']}
        r=s.応答('仮説資料「規則」を登録：'+json.dumps(資料定義,ensure_ascii=False))
        self.assertTrue(r.成立,r.理由)
        r=s.応答('資料「規則」で仮説を検討して')
        self.assertTrue(r.成立,r.理由)
        self.assertIn('HDS運用/能力/有限仮説検討',[h.作用ID for h in r.実行.履歴])
    def test_有限介入比較を通常HDSから呼ぶ(self):
        s=HDS運用セッション()
        r=s.応答('介入資料「系」を登録：外生:X=true\n構造:Y=X\n介入:Y=false')
        self.assertTrue(r.成立,r.理由)
        r=s.応答('資料「系」で介入を比較して')
        self.assertTrue(r.成立,r.理由)
        self.assertIn('HDS運用/能力/有限介入比較',[h.作用ID for h in r.実行.履歴])

    def test_外生変数への不正な介入を拒否する(self):
        s=HDS運用セッション()
        self.assertTrue(s.応答('介入資料「系」を登録：外生:X=true\n構造:Y=X\n介入:X=false').成立)
        r=s.応答('資料「系」で介入を比較して')
        self.assertFalse(r.成立)
        self.assertIn('内生変数',r.理由[-1])


if __name__=='__main__':unittest.main()
