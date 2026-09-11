"""第19バッチの数量集合・確認・訂正・再計画を実会話経路で実行する。

資料はこのデモの人工データであり、公開Webや利用者の実データを使わない。
HDS、役割計画、監督器、数量処理、回答生成、採用は製品の実コードを使用する。
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from minidora.汎用会話 import 汎用会話セッション
from minidora.会話回答 import 回答記録整合


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='strict')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json',action='store_true',help='会話と実行記録をJSONで表示する')
    args=parser.parse_args()
    session=汎用会話セッション('集合会話デモ')
    # Cだけ入れ子にし、直下取得の失敗が共通の回復契約へ戻ることも表示する。
    examples=(
        ('資料「A」を登録:{"売上":75,"費用":50}', '合格', None),
        ('資料「B」を登録:{"売上":60,"費用":40}', '合格', None),
        ('資料「C」を登録:{"実績":{"売上":95,"費用":65}}', '合格', None),
        ('この3つの売上の合計と平均を教えて。表で', '確認待ち', None),
        ('単位は円です', '合格', '230/3円'),
        ('それの計算過程も説明して', '合格', '平均 = 合計 / 3'),
        ('訂正:属性は費用です', '合格', '155/3円'),
        ('この3つの売上の合計を円で教えて。資料「B」を除いて', '合格', '170円'),
        ('資料「C」を更新:{"実績":{"売上":105,"費用":70}}', '合格', None),
        ('それを詳しく説明して', '保留', '失効'),
        ('この3つの売上を円で比較して。表で', '合格', '差は45円'),
    )
    records=[]
    for question,state,expected in examples:
        result=session.応答(question)
        if result.状態!=state or expected is not None and expected not in result.本文:
            print('デモの想定した動作と不一致:'+question+' / '+result.本文,file=sys.stderr)
            return 1
        if result.結果 is not None and not 回答記録整合(result.結果):
            print('デモの回答記録が不整合',file=sys.stderr)
            return 1
        trace=result.追跡 or {}
        row={'入力':question,'状態':result.状態,'本文':result.本文,
             '試行数':len(trace.get('試行',[])),'再計画':trace.get('再計画',[])}
        records.append(row)
        if not args.json:
            print('入力：'+question+'\n'+result.状態+'：'+result.本文)
            if row['試行数']:print('実行試行数：'+str(row['試行数']))
            print()
    if args.json:
        print(json.dumps({'人工資料':True,'会話':records,'最終状態':session.状態()},ensure_ascii=False,indent=2))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
