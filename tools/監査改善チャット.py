"""第23バッチの限定能力を日本語入力JSONLで動かす。ネットワークを利用しない。

入力1行は {"入力":"日本語発話"}。登録資料の改行はJSONの\\nで表す。
--保存/--復元はこの単独会話の純粋再生用。完全製品の状態バックアップではない。
"""
from __future__ import annotations
import argparse
import os
from pathlib import Path
import sys
import tempfile
from contextlib import ExitStack

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from minidora.監査改善会話 import 監査改善会話セッション
from minidora.監査改善会話解釈 import JSONを厳格に読む
from minidora.能力合成 import _符号化


def 保存する(path: Path, text: str, overwrite: bool):
    """同ディレクトリへ書き切ってから公開する。既存ファイルの上書きは明示時のみ。"""
    raw=text.encode('utf-8')
    if len(raw)>2_000_000:
        raise ValueError('保存状態のサイズ上限')
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.minidora-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f:
            f.write(raw);f.flush();os.fsync(f.fileno())
        if overwrite:
            os.replace(tmp,path)
        else:
            # exists確認後の競合でも既存ファイルを上書きしない。
            os.link(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--入力',dest='input',type=Path,help='UTF-8 JSONL。省略時は標準入力')
    ap.add_argument('--出力',dest='output',type=Path,help='UTF-8 JSONL。省略時は標準出力')
    ap.add_argument('--復元',dest='restore',type=Path)
    ap.add_argument('--保存',dest='save',type=Path)
    ap.add_argument('--セッション',dest='session')
    ap.add_argument('--上書き',dest='overwrite',action='store_true')
    args=ap.parse_args(argv)
    for stream in (sys.stdin,sys.stdout,sys.stderr):
        if hasattr(stream,'reconfigure'):stream.reconfigure(encoding='utf-8')
    try:
        # 入力・状態と出力を同じファイルへ向けて切り詰めない。
        readers={p.resolve() for p in (args.input,args.restore) if p is not None}
        writers=[p.resolve() for p in (args.output,args.save) if p is not None]
        if len(set(writers))!=len(writers) or (args.output is not None and args.output.resolve() in readers):
            raise ValueError('入出力ファイルの衝突')
        if args.save is not None and args.input is not None and args.save.resolve()==args.input.resolve():
            raise ValueError('入力JSONLを保存状態で置換しない')
        if not args.overwrite and any(p.exists() for p in (args.output,args.save) if p is not None):
            raise ValueError('既存ファイルには--上書きを明示する')
        if args.restore is not None:
            with args.restore.open('rb') as f:raw=f.read(2_000_001)
            if len(raw)>2_000_000:raise ValueError('復元状態のサイズ上限')
            session=監査改善会話セッション.復元(raw.decode('utf-8'),期待セッションID=args.session)
        else:
            session=監査改善会話セッション(args.session or 'default')
        invalid=False
        with ExitStack() as stack:
            source=stack.enter_context(args.input.open(encoding='utf-8-sig')) if args.input else sys.stdin
            target=stack.enter_context(args.output.open('w' if args.overwrite else 'x',encoding='utf-8',newline='\n')) if args.output else sys.stdout
            while True:
                line=source.readline(65_537)
                if not line:break
                if len(line)>65_536:
                    target.write(_符号化({'状態':'保留','本文':'入力行サイズ上限','理由':'通信入力不正'}).decode()+'\n')
                    invalid=True;break
                if not line.strip():continue
                try:
                    row=JSONを厳格に読む(line,最大バイト数=196_608)
                    if type(row) is not dict or set(row)!={'入力'} or type(row['入力']) is not str:
                        raise ValueError('1行には文字列の入力欄だけが必要')
                    response=session.応答(row['入力']).辞書化()
                except (ValueError,TypeError,UnicodeError) as exc:
                    response={'状態':'保留','本文':'入力を受理しません。'+str(exc),'理由':'通信入力不正'}
                    invalid=True
                target.write(_符号化(response).decode('utf-8')+'\n');target.flush()
        if args.save is not None:保存する(args.save,session.保存文字列(),args.overwrite)
        return 2 if invalid else 0
    except (OSError,ValueError,TypeError,UnicodeError) as exc:
        print('監査改善チャットを完了できません。'+str(exc),file=sys.stderr)
        return 2

if __name__=='__main__':raise SystemExit(main())
