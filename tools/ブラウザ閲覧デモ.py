"""実ブラウザの局所描画対照、または明示JSON要求による公開ページ閲覧。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from minidora.ブラウザ閲覧 import ブラウザ閲覧器, 描画を観測, 表示操作を行う, 表を配列, _要素
from minidora.ブラウザ接続 import ブラウザ要求を復元
from minidora.構造化文書 import 構造化文書を読む
from minidora.構造化文書操作 import 文書を処理
from minidora.製品版.抽出 import 情報抽出Module


def 描画試験(value: int, executable: str | None):
    from playwright.sync_api import sync_playwright
    # 外部知識ではなく人工HTML。URL移動をしない描画試験として表示する。
    html=f'''<html><body><button id="show" type="button">表を表示</button><div id="root"></div>
    <script>document.getElementById('show').onclick=()=>{{
    document.getElementById('root').innerHTML='<table id="t"><tr><th>番号</th><th>値</th></tr><tr><td>001</td><td>{value}</td></tr></table>';
    }};</script></body></html>'''
    with sync_playwright() as p:
        b=p.chromium.launch(headless=True, executable_path=executable)
        try:
            c=b.new_context(offline=True,service_workers='block');page=c.new_page()
            page.set_content(html);before=描画を観測(page)
            表示操作を行う(page,before,'show','表を表示')
            after=描画を観測(page);rows=表を配列(_要素(after,'t'));version=b.version
        finally:b.close()
    doc=構造化文書を読む(json.dumps(rows,ensure_ascii=False),'JSON')
    doc=文書を処理(doc,'JSON選択',{'位置':'/1/1'})
    doc=文書を処理(doc,'値取出',{'型':'文字列'})
    result=情報抽出Module().実行('数字',doc.本文)
    return {'範囲':'人工HTMLの実Chromium描画。URL移動・公開Web取得の実証ではない。',
            'ブラウザ版':version,'操作前に表あり':any(r['ID']=='t' for r in before['要素']),
            '操作後の表':rows,'後続抽出':result.本文,
            '状態変化':before['観測SHA256']!=after['観測SHA256'],
            '成立':result.成立 and result.本文==str(value)}


def main():
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--描画試験',action='store_true')
    mode.add_argument('--要求',type=Path)
    parser.add_argument('--値',type=int,default=731)
    parser.add_argument('--実行ファイル')
    parser.add_argument('--外部読取許可',action='store_true')
    args=parser.parse_args()
    if not 0<=args.値<=1000000:parser.error('--値は0〜1000000')
    if args.要求 and not args.外部読取許可:parser.error('公開閲覧には--外部読取許可が必要')
    try:
        if args.描画試験:
            data=描画試験(args.値,args.実行ファイル)
        else:
            raw=json.loads(args.要求.read_text(encoding='utf-8'))
            r=ブラウザ閲覧器(実行ファイル=args.実行ファイル).実行(ブラウザ要求を復元(raw),外部読取許可=True)
            data={'成立':r.成立,'本文':r.本文,'理由':r.保留理由,'記録':r.データ}
        print(json.dumps(data,ensure_ascii=False,indent=2))
        return 0 if data['成立'] else 1
    except Exception as exc:
        print(json.dumps({'成立':False,'診断':type(exc).__name__},ensure_ascii=False))
        return 1


if __name__=='__main__':raise SystemExit(main())
