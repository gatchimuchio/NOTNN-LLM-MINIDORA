"""第22バッチの明示IRデモ。ネットワークやリポジトリの書込みは行わない。"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from 独立入力評価 import JSON読取
from minidora.監査改善接続 import 改善計画を実行


from minidora.標準入出力 import 標準入出力をUTF8にする

def main():
    標準入出力をUTF8にする()
    parser=argparse.ArgumentParser(description='明示IRから既存能力合成器で検討→回答を実行する')
    parser.add_argument('--種類',choices=('命題','仮説','介入'),required=True)
    parser.add_argument('--入力',type=Path,required=True)
    parser.add_argument('--簡略',action='store_true')
    args=parser.parse_args()
    try:
        if args.入力.stat().st_size>300000:raise ValueError('入力サイズ上限')
        request=JSON読取(args.入力.read_text(encoding='utf-8-sig'))
        result=改善計画を実行(args.種類,request,詳細=not args.簡略)
        print(json.dumps({'状態':result.状態,'理由':result.理由,'実行数':result.実行数,
            '監査整合':result.監査整合(),'回答':[value.本文 for _,value in result.出力]},ensure_ascii=False,indent=2))
        return 0 if result.成立 else 2
    except (OSError,ValueError,TypeError) as exc:
        print('デモ入力エラー：'+str(exc))
        return 2

if __name__=='__main__':raise SystemExit(main())
