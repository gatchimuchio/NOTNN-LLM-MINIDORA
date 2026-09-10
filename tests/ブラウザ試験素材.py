"""試験・デモ専用。HTTP応答の供給だけを差し替え、描画とイベントは実Chromiumで行う。"""
from minidora.ブラウザ通信 import ブラウザ資源
from minidora.ブラウザ閲覧 import ブラウザ要求, ブラウザ工程

起点 = "https://browser-test.example/index"
詳細 = "https://browser-test.example/detail"
数値 = "https://browser-test.example/value"


def 画面HTML(value=731):
    return f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><title>描画試験</title></head><body>
<h1 id="heading">設備一覧</h1><div id="info">読込前</div>
<button id="expand" type="button">詳細表示</button>
<div id="hidden" hidden>未表示999</div><a id="next" href="{詳細}">次ページ</a>
<script>
(() => {{
const button=document.getElementById('expand');
button.addEventListener('click',()=>{{
 document.getElementById('info').innerHTML='<table id="table"><tr><th>番号</th><th>値</th></tr><tr><td>001</td><td>{value}</td></tr></table>';
 button.textContent='表示済み';
}});
}})();
</script></body></html>'''


def 供給器(value=731, initial=None):
    page = 画面HTML(value) if initial is None else initial
    rows = {起点: ("text/html; charset=utf-8", page.encode()),
            詳細: ("text/html; charset=utf-8", f'<html><head><meta charset="utf-8"></head><body><div id="answer">値は{value}です。</div></body></html>'.encode()),
            数値: ("application/json", ('{"value":'+str(value)+'}').encode())}
    calls = []
    def supply(url):
        calls.append(url)
        mime, body = rows[url]
        return ブラウザ資源(url, mime, body)
    supply.calls = calls
    return supply


def 表要求():
    return ブラウザ要求(起点, (起点, 詳細, 数値), (
        ブラウザ工程("表示待機", "expand", "詳細表示"),
        ブラウザ工程("表示操作", "expand", "詳細表示"),
        ブラウザ工程("表示待機", "table"),
        ブラウザ工程("表取得", "table")))
