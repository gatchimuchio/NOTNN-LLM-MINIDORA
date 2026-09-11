"""1行1JSONで統合能力へ要求する。通常チャットやGUIの入口は変更しない。"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from minidora.統合実行 import 統合セッション
from minidora.統合入出力 import JSON要求を読む, 統合要求を実行


def main():
    if hasattr(sys.stdin, 'reconfigure'):
        sys.stdin.reconfigure(encoding='utf-8')
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--一覧', action='store_true')
    parser.add_argument('--外部読取許可', action='store_true')
    parser.add_argument('--再利用無効', action='store_true')
    args = parser.parse_args()
    session = 統合セッション('統合CLI', 外部読取許可=args.外部読取許可, 再利用=not args.再利用無効)
    if args.一覧:
        print(json.dumps(統合要求を実行(session, {'種別':'一覧'}), ensure_ascii=False, indent=2))
        return 0
    status = 0
    while True:
        line = sys.stdin.readline(2000001)
        if not line:
            break
        if len(line) > 2000000:
            print(json.dumps({'状態':'失敗','本文':'','理由':'入力行上限'},ensure_ascii=False),flush=True)
            return 1  # 同じ巨大行の後半を独立した要求として読まない。
        try:
            result = 統合要求を実行(session, JSON要求を読む(line))
        except Exception as exc:
            result = {'状態':'失敗','本文':'','理由':'JSON入力不成立:'+type(exc).__name__}
        print(json.dumps(result, ensure_ascii=False), flush=True)
        status = max(status, int(result['状態'] not in ('合格',)))
    return status


if __name__=='__main__':
    raise SystemExit(main())
