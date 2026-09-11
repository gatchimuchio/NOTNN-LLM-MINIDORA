"""会話能力の日本語CLI。明示資料だけを読み、外部読取は利用者が選択する。"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
from .汎用会話 import 汎用会話セッション
from .製品版.型 import 能力結果


def _資料を読む(spec, materials):
    if type(spec) is not str or '=' not in spec: raise ValueError('資料指定は名前=パス')
    name, path = spec.split('=', 1)
    if not name or len(name) > 128 or name != name.strip() or not path:
        raise ValueError('資料名又はパス不正')
    if name not in materials and len(materials) >= 32: raise ValueError('資料は32件以内')
    with Path(path).open('rb') as source: raw = source.read(1000001)
    if len(raw) > 1000000: raise ValueError('資料は1MB以内')
    updated = {**materials, name: 能力結果(True, raw.decode('utf-8-sig'))}
    if sum(len(v.本文.encode('utf-8')) for v in updated.values()) > 1000000:
        raise ValueError('全資料本文は合計1MB以内')
    return updated


def main(argv=None) -> int:
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'): stream.reconfigure(encoding='utf-8', errors='strict')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('依頼', nargs='?')
    parser.add_argument('--資料', action='append', default=[], metavar='名前=パス')
    parser.add_argument('--外部読取', action='store_true', help='明示対象・属性・条件を検索先へ送ることを許可')
    parser.add_argument('--形式', choices=('段落', '箇条書き'), default='段落')
    parser.add_argument('--最大文字数', type=int, default=20000)
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--session', default='汎用チャット')
    args = parser.parse_args(argv)
    if not 1 <= args.最大文字数 <= 100000: parser.error('最大文字数は1〜100000')
    materials = {}
    try:
        for spec in args.資料:
            name = spec.split('=', 1)[0]
            if name in materials: raise ValueError('初期資料名が重複')
            materials = _資料を読む(spec, materials)
        session = 汎用会話セッション(args.session, 外部読取許可=args.外部読取)
    except (ValueError, TypeError, OSError, UnicodeError) as exc:
        print('初期化不成立:' + str(exc), file=sys.stderr)
        return 2

    def respond(text):
        result = session.応答(text, materials, 外部読取許可=args.外部読取,
            形式=args.形式, 最大文字数=args.最大文字数)
        print(json.dumps(result.辞書化(), ensure_ascii=False) if args.json else result.本文)
        return 0 if result.成立 else 2

    if args.依頼 is not None: return respond(args.依頼)
    if sys.stdin.isatty():
        print('日本語の依頼、/資料 名前=パス、/初期化、/終了。外部読取=' + str(args.外部読取))
    while True:
        try:
            line = sys.stdin.readline(8194)
            if not line: return 0
            if len(line.rstrip('\r\n')) > 8192:
                print('入力上限超過。後続を実行せず終了します。', file=sys.stderr)
                return 2
            text = line.strip()
            if text == '/終了': return 0
            if text == '/初期化':
                session.初期化(); materials = {}; print('会話と資料を初期化しました。')
            elif text.startswith('/資料 '):
                materials = _資料を読む(text[4:].strip(), materials)
                print('資料を更新しました。確認待ちの依頼は「再開して」で処理します。')
            elif text: respond(text)
        except UnicodeError:
            print('入力はUTF-8で指定してください。後続を実行せず終了します。', file=sys.stderr)
            return 2
        except (ValueError, OSError) as exc:
            print('入力不成立:' + str(exc), file=sys.stderr)
        except KeyboardInterrupt:
            return 130
