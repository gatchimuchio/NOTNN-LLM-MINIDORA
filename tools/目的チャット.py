"""目的から能力経路を組み立てる日本語CLI。標準チャットとは独立した追加入口。"""
from pathlib import Path
import argparse
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from minidora.目的会話 import 目的会話セッション
from minidora.製品版.型 import 能力結果


def main():
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'): stream.reconfigure(encoding='utf-8', errors='strict')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('依頼', nargs='?')
    parser.add_argument('--資料', action='append', default=[], metavar='名前=パス')
    parser.add_argument('--json', action='store_true', help='追跡情報もJSONで表示')
    parser.add_argument('--一覧', action='store_true')
    options = parser.parse_args()
    session = 目的会話セッション('目的チャット')
    if options.一覧:
        from dataclasses import asdict
        print(json.dumps({'記述': [asdict(x) for x in session.カタログ.記述],
                          '作用': [asdict(x) for x in session.カタログ.作用]}, ensure_ascii=False, indent=2))
        return 0
    materials = {}
    try:
        for spec in options.資料:
            name, path = spec.split('=', 1)
            if not name or name in materials or len(materials) >= 32: raise ValueError('資料名の空値・重複・件数上限')
            with Path(path).open('rb') as source: raw = source.read(1000001)
            if len(raw) > 1000000: raise ValueError('資料は1MB以内')
            materials[name] = 能力結果(True, raw.decode('utf-8-sig'))
    except (ValueError, OSError, UnicodeError) as exc:
        print('資料入力不成立:' + str(exc), file=sys.stderr)
        return 2

    def respond(text):
        result = session.応答(text, materials)
        print(json.dumps(result.辞書化(), ensure_ascii=False) if options.json else
              result.本文 if result.成立 else result.状態 + ': ' + result.理由)
        return 0 if result.成立 else 2

    if options.依頼 is not None: return respond(options.依頼)
    if sys.stdin.isatty(): print('日本語の依頼を入力。/終了 で終了、/初期化 で履歴を消去します。')
    while True:
        try:
            line = sys.stdin.readline(8194)
        except UnicodeError:
            print('標準入力はUTF-8で指定してください。後続を実行せず終了します。', file=sys.stderr)
            return 2
        if not line: return 0
        if len(line.rstrip('\r\n')) > 8192:
            print('入力上限超過。後半を別の依頼として実行せず終了します。', file=sys.stderr)
            return 2
        text = line.strip()
        if text == '/終了': return 0
        if text == '/初期化':
            session.統合.初期化()
            print('初期化しました。')
        elif text: respond(text)


if __name__ == '__main__':
    raise SystemExit(main())
