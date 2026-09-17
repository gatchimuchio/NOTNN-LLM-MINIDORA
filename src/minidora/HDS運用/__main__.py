"""HDS通常運用のCLI/JSONL/ローカル画面。すべて同じHDSセッションを呼ぶ。"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

from .契約 import JSONを読む, 計画を復元
from .セッション import HDS運用セッション
from ..会話意味 import 意味目的


def _保存する(セッション, 宛先):
    if 宛先 is None:
        return
    宛先 = Path(宛先)
    本文 = セッション.保存()
    # 同じディレクトリの一時ファイルをfsync後に置換。旧ファイルを途中まで上書きしない。
    fd, 仮 = tempfile.mkstemp(prefix='.hds-', dir=宛先.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as f:
            f.write(本文)
            f.flush()
            os.fsync(f.fileno())
        os.replace(仮, 宛先)
    finally:
        if os.path.exists(仮):
            os.unlink(仮)


def main(argv=None):
    p = argparse.ArgumentParser(description='HDSが能力群を直接駆動する通常運用')
    p.add_argument('--serve', action='store_true')
    p.add_argument('--ポート', type=int, default=8080)
    p.add_argument('--外部読取', action='store_true')
    p.add_argument('--session', default='cli')
    p.add_argument('--JSONL', action='store_true')
    p.add_argument('--一覧', action='store_true')
    p.add_argument('--資料', action='append', default=[], metavar='名前=ファイル')
    p.add_argument('--保存')
    p.add_argument('--読込')
    p.add_argument('message', nargs='*')
    a = p.parse_args(argv)
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='strict')
    if a.serve and (a.JSONL or a.保存 or a.読込 or a.message):
        p.error('--serveはJSONL・保存・読込・一回依頼と同時指定できません')
    if a.読込 and a.資料:
        p.error('--読込と--資料は同時指定できません')
    if a.JSONL and a.message:
        p.error('--JSONLは一回依頼と同時指定できません')
    資料 = {}
    try:
        for 項 in a.資料:
            if '=' not in 項:
                raise ValueError('--資料は名前=ファイルで指定')
            名, 経路 = 項.split('=', 1)
            if 名 in 資料:
                raise ValueError('資料名重複')
            with Path(経路).open('rb') as f:
                raw = f.read(2_000_001)
            if len(raw) > 2_000_000:
                raise ValueError('資料容量上限')
            資料[名] = raw.decode('utf-8-sig')
        if a.serve:
            from .製品 import HDS運用製品
            from .HTTP入口 import サーバを構成
            from ..製品版.監査 import 監査台帳
            app = HDS運用製品(資料=資料, 外部読取許可=a.外部読取,
                監査台帳_=監査台帳(os.getenv('MINIDORA_AUDIT_LOG') or None))
            with サーバを構成(app, ポート=a.ポート) as server:
                server.serve_forever()
            return 0
        if a.読込:
            with Path(a.読込).open('rb') as f:
                raw = f.read(8_000_001)
            s = HDS運用セッション.復元(raw.decode('utf-8'), 外部読取許可=a.外部読取)
        else:
            s = HDS運用セッション(a.session, 資料=資料, 外部読取許可=a.外部読取)
        if a.一覧:
            print(json.dumps(s.能力一覧(), ensure_ascii=False))
            return 0
        if a.message:
            結果 = s.応答(' '.join(a.message))
            _保存する(s, a.保存)
            print(結果.本文)
            return 0 if 結果.成立 else 1
        if a.JSONL:
            while True:
                行 = sys.stdin.readline(2_000_001)
                if not 行:
                    break
                if len(行) > 2_000_000:
                    raise ValueError('JSONL行上限。後半を別依頼として処理しない')
                値 = JSONを読む(行, 上限=2_000_000)
                if type(値) is not dict or not {'依頼'} <= set(値) <= {'依頼', '意味目的', '計画'}:
                    raise ValueError('JSONL要求の項目不正')
                目的 = 意味目的(**値['意味目的']) if '意味目的' in 値 else None
                計画, 素材 = 計画を復元(値['計画']) if '計画' in 値 else (None, None)
                結果 = s.応答(値['依頼'], 意味目的_=目的, 明示計画=計画, 計画資料=素材)
                _保存する(s, a.保存)
                print(json.dumps(結果.辞書化(), ensure_ascii=False, allow_nan=False), flush=True)
            return 0
        print('HDS-MINIDORA / exitで終了')
        while True:
            try:
                文 = input('> ')
            except EOFError:
                break
            if 文.strip().casefold() in ('exit', 'quit'):
                break
            if not 文.strip():
                continue
            結果 = s.応答(文)
            _保存する(s, a.保存)
            print(結果.本文)
        return 0
    except (ValueError, TypeError, OSError, UnicodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == '__main__':
    raise SystemExit(main())
