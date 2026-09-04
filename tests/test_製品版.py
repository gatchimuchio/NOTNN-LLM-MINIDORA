from __future__ import annotations
import json, threading, time
from datetime import datetime, timezone
from http.client import HTTPConnection
import unittest
from minidora.製品版 import 製品ミニドラ, 固定ニュース供給器, 固定知識供給器
from minidora.製品版.型 import 能力結果
from minidora.製品版.型 import 参照資料
from minidora.製品版.能力契約 import 能力文脈
from minidora.製品版.api import APIHandler
from http.server import ThreadingHTTPServer

class FakeCore:
    def 応答(self, text: str) -> str:
        return f"CORE:{text}"

KNOW=(参照資料("k1","富士山","Wikipedia","https://example.com/fuji",None,"富士山は日本にある山で、標高3776メートル。日本最高峰である。"),)

NEWS=(
    参照資料("n1","政府が新制度を発表","共同", "https://example.com/1", datetime.now(timezone.utc), "政府は新制度を発表した。対象は全国。開始は来月。"),
    参照資料("n2","企業が新製品を公開","技術紙", "https://example.com/2", datetime.now(timezone.utc), "企業は新製品を公開した。省電力が特徴。発売は今月。"),
    参照資料("n3","研究チームが成果を報告","科学紙", "https://example.com/3", datetime.now(timezone.utc), "研究チームは新しい成果を報告した。再現試験も実施された。"),
)

class ProductTests(unittest.TestCase):
    def setUp(self): self.app=製品ミニドラ(基礎ミニドラ=FakeCore(), ニュース供給器=固定ニュース供給器(NEWS), 知識供給器=固定知識供給器(KNOW))
    def test_news_then_summary(self):
        a=self.app.応答("今日のニュースは？",セッションID="s")
        self.assertEqual(a.経路,"ニュース"); self.assertEqual(len(a.参照),3)
        b=self.app.応答("3行で要約して",セッションID="s")
        self.assertEqual(b.経路,"要約"); self.assertTrue(b.本文); self.assertEqual(len(b.参照),3)
        self.assertTrue(self.app.監査台帳.検証(a.追跡ID)); self.assertTrue(self.app.監査台帳.検証(b.追跡ID))
        self.assertEqual(self.app.監査台帳.取得(b.追跡ID).前応答ハッシュ,a.監査ハッシュ)
    def test_explicit_summary(self):
        r=self.app.応答("要約して：猫は哺乳類です。猫は夜に活動することがあります。猫には多くの品種があります。",セッションID="x")
        self.assertEqual(r.経路,"要約"); self.assertIn("猫",r.本文)
    def test_bullet_transform(self):
        self.app.応答("要約して：Aです。Bです。Cです。",セッションID="t")
        r=self.app.応答("箇条書きにして",セッションID="t")
        self.assertEqual(r.経路,"文脈変換"); self.assertTrue(r.本文.startswith("- "))
    def test_extract_numbers(self):
        self.app.応答("これは売上100、利益20、成長率5%です",セッションID="e")
        r=self.app.応答("数字を抜いて",セッションID="e")
        self.assertEqual(r.経路,"情報抽出"); self.assertIn("100",r.本文)
    def test_calculation(self):
        r=self.app.応答("(12+8)*3",セッションID="c")
        self.assertEqual(r.経路,"計算"); self.assertIn("60",r.本文)
    def test_core_fallback(self):
        r=self.app.応答("自由意志について説明して",セッションID="g")
        self.assertEqual(r.経路,"基礎Core"); self.assertEqual(r.本文,"CORE:自由意志について説明して")
    def test_basic_chat(self):
        r=self.app.応答("何ができる？",セッションID="b")
        self.assertEqual(r.経路,"基本会話"); self.assertIn("ニュース",r.本文)
    def test_trace_contains_route_selection(self):
        r=self.app.応答("今日のニュースは？",セッションID="z")
        rec=self.app.監査台帳.取得(r.追跡ID)
        self.assertIn("能力選択",[e.段階 for e in rec.イベント])
    def test_knowledge_reference(self):
        r=self.app.応答("富士山とは？",セッションID="k")
        self.assertEqual(r.経路,"知識参照"); self.assertIn("富士山",r.本文); self.assertEqual(len(r.参照),1)
    def test_news_summary_uses_reference_body(self):
        self.app.応答("今日のニュースは？",セッションID="ground")
        r=self.app.応答("3行で要約して",セッションID="ground")
        self.assertTrue(any(x in r.本文 for x in ("全国","省電力","再現試験")))
    def test_session_isolation(self):
        self.app.応答("今日のニュースは？",セッションID="a")
        r=self.app.応答("3行で要約して",セッションID="b")
        self.assertNotEqual(r.経路,"要約")
    def test_dynamic_module_registration(self):
        class Echo:
            名前="動的Echo"; 版="echo-v1"; 優先度=999
            def 判定(self,c): return 1.0 if c.入力文.startswith("echo:") else 0.0
            def 実行(self,c): return 能力結果(True,c.入力文.split(":",1)[1],根拠=("echo",))
        self.app.Module登録(Echo())
        r=self.app.応答("echo:追加能力",セッションID="m")
        self.assertEqual(r.経路,"動的Echo"); self.assertEqual(r.本文,"追加能力")

class APITests(unittest.TestCase):
    def setUp(self):
        self.app=製品ミニドラ(基礎ミニドラ=FakeCore(), ニュース供給器=固定ニュース供給器(NEWS), 知識供給器=固定知識供給器(KNOW))
        self.server=ThreadingHTTPServer(("127.0.0.1",0),APIHandler); self.server.app=self.app
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True); self.thread.start()
        self.port=self.server.server_address[1]
    def tearDown(self): self.server.shutdown(); self.server.server_close()
    def call(self,method,path,body=None):
        c=HTTPConnection("127.0.0.1",self.port,timeout=3)
        data=json.dumps(body,ensure_ascii=False).encode() if body is not None else None
        headers={"Content-Type":"application/json"} if data else {}
        c.request(method,path,body=data,headers=headers); r=c.getresponse(); payload=json.loads(r.read().decode()); c.close(); return r.status,payload
    def test_health(self): self.assertEqual(self.call("GET","/health")[0],200)
    def test_static_ui(self):
        c=HTTPConnection("127.0.0.1",self.port,timeout=3); c.request("GET","/"); r=c.getresponse(); body=r.read().decode(); c.close(); self.assertEqual(r.status,200); self.assertIn("MINIDORA",body)
    def test_chat_and_trace(self):
        s,p=self.call("POST","/api/chat",{"session_id":"api","message":"今日のニュースは？"}); self.assertEqual(s,200)
        self.assertEqual(p["route"],"ニュース")
        s2,t=self.call("GET","/api/trace/"+p["trace_id"]); self.assertEqual(s2,200); self.assertTrue(t["valid"])
    def test_validation(self): self.assertEqual(self.call("POST","/api/chat",{"message":""})[0],400)

if __name__ == "__main__": unittest.main()
