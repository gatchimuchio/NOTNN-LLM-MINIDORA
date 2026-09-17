"""実画面→ローカルHTTP→既存HDS→能力→回答・監査を通す試験。"""
from __future__ import annotations
import os
from threading import Thread
import unittest
from minidora.HDS運用.製品 import HDS運用製品
from minidora.HDS運用.HTTP入口 import サーバを構成


@unittest.skipUnless(os.getenv('MINIDORA_BROWSER_NAV_TEST') == '1', '別構成で実ブラウザ接続を検証')
class HDS通常運用画面試験(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.driver = sync_playwright().start()
        cls.browser = cls.driver.chromium.launch(headless=True,
            executable_path=os.getenv('MINIDORA_BROWSER_EXECUTABLE'))

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.driver.stop()

    def setUp(self):
        self.server = サーバを構成(HDS運用製品(), ポート=0)
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.thread.join, timeout=5)
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.base = 'http://127.0.0.1:' + str(self.server.server_address[1])
        self.文脈 = self.browser.new_context(service_workers='block')
        self.addCleanup(self.文脈.close)
        self.文脈.route('**/*', lambda r: r.continue_() if r.request.url.startswith(self.base + '/') else r.abort())
        self.page = self.文脈.new_page()
        self.page.set_default_timeout(30000)
        self.page.goto(self.base + '/')
        self.page.wait_for_function("document.title === 'HDS-MINIDORA'")

    def 送信(self, 依頼):
        数 = self.page.locator('.msg.assistant').count()
        self.page.locator('#input').fill(依頼)
        self.page.locator('#send').click()
        self.page.wait_for_function("n => document.querySelectorAll('.msg.assistant').length > n", arg=数)
        self.page.wait_for_function("!document.querySelector('#send').disabled")
        return self.page.locator('.msg.assistant .bubble').last.inner_text()

    def test_数学回答とHDSの実行追跡を表示する(self):
        self.assertIn('5', self.送信('2+3'))
        self.page.wait_for_function("document.querySelector('#traceBody').textContent.includes('HDS運用/能力/記号演算')")
        self.assertIn('hash chain valid', self.page.locator('#traceBody').inner_text())
        self.assertNotIn('Trace取得失敗', self.page.locator('#traceBody').inner_text())

    def test_同じ画面で複合依頼と次ターンを処理する(self):
        self.assertIn('3*x**2', self.送信('「x**3」をxで微分して'))
        self.assertIn('6*x', self.送信('それをxで微分して'))
        self.assertIn('HDS通常運用', self.page.locator('.meta').last.inner_text())

    def test_新しい会話へ旧成果を持ち込まない(self):
        self.送信('「x**3」をxで微分して')
        self.page.locator('#newSession').click()
        self.assertIn('HDS-MINIDORA', self.page.locator('.welcome').inner_text())
        self.assertIn('完了できません', self.送信('それをxで微分して'))


@unittest.skipUnless(os.getenv('MINIDORA_BROWSER_DOM_TEST') == '1', '別構成で実DOMを検証')
class HDS通常運用表示試験(unittest.TestCase):
    """移動禁止環境でも実JSを検査する。fetchは実製品応答の再生であり通信試験ではない。"""
    @classmethod
    def setUpClass(cls):
        from pathlib import Path
        from playwright.sync_api import sync_playwright
        cls.driver = sync_playwright().start()
        cls.browser = cls.driver.chromium.launch(headless=True,
            executable_path=os.getenv('MINIDORA_BROWSER_EXECUTABLE'))
        cls.root = Path(__file__).resolve().parents[1] / 'src/minidora/製品版/web'
        製品 = HDS運用製品()
        cls.実応答 = 製品.応答('2+3').辞書化()
        記録 = 製品.監査台帳.取得(cls.実応答['追跡_id'])
        cls.実追跡 = {'追跡': 記録.辞書化(), 'valid': 製品.監査台帳.検証(記録.追跡ID)}

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.driver.stop()

    def setUp(self):
        self.文脈 = self.browser.new_context(offline=True, service_workers='block')
        self.addCleanup(self.文脈.close)
        self.page = self.文脈.new_page()
        self.page.set_default_timeout(10000)
        html = (self.root/'index.html').read_text(encoding='utf-8')
        html = html.replace('<script type="module" src="/static/app.js"></script>', '')
        html = html.replace('<link rel="stylesheet" href="/static/styles.css" />', '')
        self.page.set_content(html)
        self.page.evaluate("""([response, trace]) => {
          Object.defineProperty(window, 'localStorage', {value:{getItem:()=>null,setItem:()=>{}}});
          Object.defineProperty(window.crypto, 'randomUUID', {value:()=> '00000000-0000-4000-8000-000000000000'});
          window.fetch = async (url) => ({ok:true, json:async()=>
            url==='/health'? {'実行方式':'HDS-FIRST'} : url==='/api/chat'? response : trace});
        }""", [self.実応答, self.実追跡])
        self.page.add_script_tag(content=(self.root/'app.js').read_text(encoding='utf-8'))
        self.page.wait_for_function("document.title === 'HDS-MINIDORA'")

    def test_HDS用の利用例を表示(self):
        self.assertIn('HDS-MINIDORA', self.page.locator('.welcome').inner_text())
        self.assertNotIn('今日のニュース', self.page.locator('.chips').inner_text())
        self.assertIn('微分', self.page.locator('.hint').inner_text())

    def test_実HDSの応答と監査を現在通信鍵で表示(self):
        self.page.locator('#input').fill('2+3')
        self.page.locator('#send').click()
        self.page.wait_for_function("document.querySelector('#traceBody').textContent.includes('HDS運用/能力/記号演算')")
        self.assertIn('5', self.page.locator('.msg.assistant .bubble').inner_text())
        self.assertIn('hash chain valid', self.page.locator('#traceBody').inner_text())
        self.assertIn('HDS通常運用', self.page.locator('.meta').inner_text())


if __name__ == '__main__':
    unittest.main()
