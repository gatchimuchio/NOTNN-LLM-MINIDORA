"""第18バッチの会話入口。資料・外部読取権限はCLI引数から明示する。"""
from pathlib import Path
import argparse,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from minidora.汎用会話 import 汎用会話セッション
from minidora.製品版.型 import 能力結果


def main():
    for stream in (sys.stdin,sys.stdout,sys.stderr):
        if hasattr(stream,'reconfigure'): stream.reconfigure(encoding='utf-8',errors='strict')
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('発話',nargs='?');p.add_argument('--資料',action='append',default=[],metavar='名前=パス')
    p.add_argument('--外部読取',action='store_true');p.add_argument('--json',action='store_true')
    args=p.parse_args();materials={}
    try:
        for spec in args.資料:
            name,path=spec.split('=',1)
            if not name or name in materials or len(materials)>=32: raise ValueError('資料名の空値・重複・上限')
            with Path(path).open('rb') as f: raw=f.read(262145)
            if len(raw)>262144: raise ValueError('資料は256KiB以内')
            materials[name]=能力結果(True,raw.decode('utf-8-sig'))
        session=汎用会話セッション('汎用CLI',外部読取許可=args.外部読取)
    except (ValueError,OSError,UnicodeError) as exc:
        print('入力不成立:'+str(exc),file=sys.stderr);return 2
    first=True
    def respond(text):
        nonlocal first
        r=session.応答(text,materials if first else None,外部読取許可=args.外部読取);first=False
        if args.json:
            from minidora.要求解釈 import _正規値
            print(json.dumps(_正規値(r.辞書化()),ensure_ascii=False,allow_nan=False))
        else: print(r.本文)
        return 0 if r.成立 or r.状態=='確認待ち' else 2
    if args.発話 is not None: return respond(args.発話)
    if sys.stdin.isatty(): print('日本語で入力。/終了 で終了。資料の貼付は単発引数又は--資料を利用してください。')
    while True:
        try: line=sys.stdin.readline(8194)
        except UnicodeError:
            print('標準入力はUTF-8で指定してください。後続を実行せず終了します。',file=sys.stderr);return 2
        if not line: return 0
        if len(line.rstrip('\r\n'))>8192:
            print('入力上限超過。後続を実行せず終了します。',file=sys.stderr);return 2
        text=line.strip()
        if text=='/終了': return 0
        if text: respond(text)

if __name__=='__main__': raise SystemExit(main())
