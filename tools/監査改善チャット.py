"""限定能力を日本語入力JSONLで動かす。ネットワークを利用しない。

入力1行は {"入力":"日本語発話"}。資料の改行はJSONの\\nで表す。
--保存/--復元は単独会話の純粋再生用。完全製品のバックアップではない。
通信入力不正時は終了値2とし、出力ファイル・保存状態を公開しない。
標準出力は逐次送信のため巻戻しできない。意味的保留は通信エラーとは別。
"""
from __future__ import annotations

import argparse
import io
from contextlib import ExitStack
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from minidora.監査改善会話 import 監査改善会話セッション, 契約版
from minidora.監査改善会話解釈 import JSONを厳格に読む
from minidora.能力合成 import _符号化
from minidora.標準入出力 import 標準入出力をUTF8にする
from minidora.原子的保存 import 原子的テキスト出力, 同じファイル


def 保存する(path: Path, text: str, overwrite: bool) -> None:
    if len(text.encode('utf-8')) > 2_000_000:
        raise ValueError('保存状態のサイズ上限')
    with 原子的テキスト出力(path, 上書き=overwrite) as stream:
        stream.write(text)


def _入出力を検査(args) -> None:
    readers = [p for p in (args.input, args.restore) if p is not None]
    if args.output is not None and any(同じファイル(args.output, p) for p in readers):
        raise ValueError('入出力ファイルの衝突')
    if args.save is not None:
        if args.output is not None and 同じファイル(args.save, args.output):
            raise ValueError('出力と保存状態の衝突')
        if args.input is not None and 同じファイル(args.save, args.input):
            raise ValueError('入力JSONLを保存状態で置換しない')
    for path in (args.output, args.save):
        if path is None:
            continue
        if path.is_symlink():
            raise ValueError('出力先のシンボリックリンクは使用しない')
        if path.exists() and not args.overwrite:
            raise ValueError('既存ファイルには--上書きを明示する')
        if path.exists() and not path.is_file():
            raise ValueError('出力先は通常ファイルを指定する')


def _応答を書き出す(session, source, target) -> bool:
    invalid = False
    first = True
    while True:
        line = source.readline(65_537)
        if not line:
            break
        if first:
            # UTF-8 BOMは通信先頭だけに許可する。本文内のBOMは除去しない。
            line = line.removeprefix('\ufeff')
            first = False
        if len(line) > 65_536:
            target.write(_符号化({'状態': '保留', '本文': '入力行サイズ上限',
                                  '理由': '通信入力不正'}).decode('utf-8') + '\n')
            return True
        if not line.strip():
            continue
        try:
            row = JSONを厳格に読む(line, 最大バイト数=196_608)
            if type(row) is not dict or set(row) != {'入力'} or type(row['入力']) is not str:
                raise ValueError('1行には文字列の入力欄だけが必要')
            response = session.応答(row['入力']).辞書化()
        except (ValueError, TypeError, UnicodeError) as exc:
            response = {'状態': '保留', '本文': '入力を受理しません。' + str(exc), '理由': '通信入力不正'}
            invalid = True
        target.write(_符号化(response).decode('utf-8') + '\n')
        target.flush()
    return invalid


def main(argv=None):
    # --helpとargparseの日本語エラーにも適用する。読書き後には移動しない。
    標準入出力をUTF8にする()
    ap = argparse.ArgumentParser(description=__doc__)
    entry = ap.add_mutually_exclusive_group()
    entry.add_argument('--入力', dest='input', type=Path, help='UTF-8 JSONL。省略時は標準入力')
    entry.add_argument('--発話', dest='utterances', action='append', help='日本語発話を直接指定。順に複数回指定できる')
    entry.add_argument('--契約', dest='contract', action='store_true', help='対応入口・上限・日本語入力例をJSON表示')
    ap.add_argument('--出力', dest='output', type=Path, help='UTF-8 JSONL。省略時は標準出力')
    ap.add_argument('--復元', dest='restore', type=Path)
    ap.add_argument('--保存', dest='save', type=Path)
    ap.add_argument('--セッション', dest='session')
    ap.add_argument('--上書き', dest='overwrite', action='store_true')
    args = ap.parse_args(argv)
    if args.contract:
        if any(p is not None for p in (args.output, args.restore, args.save, args.session)) or args.overwrite:
            ap.error('--契約は出力先・状態操作・セッション指定と併用しない')
        print(_符号化({
            '版': 'MINIDORA-会話CLI-v0.2', '意味契約': 契約版,
            '符号化': 'UTF-8/strict', '入力': {'JSONL': {'入力': '日本語発話'}, '直接指定': '--発話 を順に複数回指定'},
            '上限': {'発話文字数': 8192, '発話数': 128, 'JSONL行文字数': 65536},
            '例': ['命題資料「例」を登録：P。PならばQ。', '資料「例」から「Q」を判定して', '短く説明して'],
            '対応範囲': '登録資料上の有限命題・候補仮説・明示ブール介入。任意自然言語や一般常識の理解を意味しない',
            '不正通信': '終了値2。出力ファイルと保存状態を公開しない。標準出力は巻戻しできない',
            '保存': '各ファイル単独の原子的置換。複数ファイル一括の原子性はない'
        }).decode('utf-8'))
        return 0
    try:
        if args.utterances is not None and (len(args.utterances) > 128 or any(len(s) > 8192 for s in args.utterances)):
            raise ValueError('直接発話の数・文字数上限')
        _入出力を検査(args)
        if args.restore is not None:
            with args.restore.open('rb') as source:
                raw = source.read(2_000_001)
            if len(raw) > 2_000_000:
                raise ValueError('復元状態のサイズ上限')
            session = 監査改善会話セッション.復元(raw.decode('utf-8'), 期待セッションID=args.session)
        else:
            session = 監査改善会話セッション(args.session or 'default')
        with ExitStack() as stack:
            if args.utterances is not None:
                source = stack.enter_context(io.StringIO(''.join(
                    _符号化({'入力': text}).decode('utf-8') + '\n' for text in args.utterances)))
            else:
                source = stack.enter_context(args.input.open(encoding='utf-8-sig', errors='strict')) if args.input else sys.stdin
            target = stack.enter_context(原子的テキスト出力(args.output, 上書き=args.overwrite)) if args.output else sys.stdout
            invalid = _応答を書き出す(session, source, target)
            if invalid:
                # 正常行があっても破損通信を含むファイル・状態は公開しない。
                raise ValueError('通信入力不正のためファイル出力と保存を確定しません')
        if args.save is not None:
            保存する(args.save, session.保存文字列(), args.overwrite)
        return 0
    except (OSError, ValueError, TypeError, UnicodeError) as exc:
        print('監査改善チャットを完了できません。' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
