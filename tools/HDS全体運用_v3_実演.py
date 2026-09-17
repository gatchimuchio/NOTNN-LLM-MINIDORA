"""人工資料の数量関係から計算・コード・説明・訂正・手順再利用を確認する。"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from minidora.HDS運用 import HDS運用セッション


def main():
    解析 = argparse.ArgumentParser(description='HDS全体運用v3の人工資料による連続実演')
    解析.add_argument('--output', type=Path)
    引数 = 解析.parse_args()
    for 流 in (sys.stdout, sys.stderr):
        if hasattr(流, 'reconfigure'):
            流.reconfigure(encoding='utf-8', errors='strict')
    記録 = []

    def 応答(会話, 入力, 必須=(), *, 成立=True, 期待値=None):
        始 = time.monotonic()
        結果 = 会話.応答(入力)
        if 結果.成立 != 成立 or any(語 not in 結果.本文 for 語 in 必須):
            raise RuntimeError('実演の期待状態・本文不一致:' + 入力 + '\n' + 結果.本文)
        if 期待値 is not None:
            実値 = {行['資料']:行['値'] for 行 in 結果.結果.データ['計算']['結果']}
            if 実値 != 期待値:
                raise RuntimeError('数量結果不一致:' + repr(実値))
        記録.append({'入力':入力, '期待成立':成立, '期待値':期待値, '検査合格':True,
                     '秒':time.monotonic()-始, **結果.辞書化()})
        print(f'[{結果.状態}] {入力}\n{結果.本文}\n', flush=True)
        return 結果

    会話 = HDS運用セッション('数量連続実演', 手順形成=False, 再利用=False)
    応答(会話, '資料「A」を登録:単価は120円/個。数量は3個。固定費は50円。')
    応答(会話, '資料「B」を登録:単価は90円/個。数量は3個。固定費は100円。')
    応答(会話, '資料「規則」を登録:費用は単価と数量の積に固定費を足した値。')
    問い = '資料「A」と資料「B」に資料「規則」を使って、費用を計算して、比較して、Pythonで検算し、詳しく説明して'
    初 = 応答(会話, 問い, 期待値={'A':'410','B':'370'})
    if len(初.追跡['能力試行']) != 7:
        raise RuntimeError('計算から回答まで7工程が発火していない')
    応答(会話, '資料「A」の数量を6個に変更して', ('原資料は変更していません',), 期待値={'A':'770','B':'370'})
    短 = 応答(会話, '短く説明して', ('6個',), 期待値={'A':'770','B':'370'})
    if [行['能力'] for 行 in 短.追跡['能力試行']] != ['数量回答再表現']:
        raise RuntimeError('再表現で別の計算計画を実行した')
    応答(会話, '表にして', ('| 資料 | 費用 |',), 期待値={'A':'770','B':'370'})
    応答(会話, 'コードを省いて', 期待値={'A':'770','B':'370'})
    応答(会話, '資料「B」を更新:単価は80円/個。数量は3個。固定費は100円。')
    if 会話.状態()['前回有効']:
        raise RuntimeError('資料更新後に旧回答が有効')
    応答(会話, '詳しく説明して', ('失効',), 成立=False)
    応答(会話, '再計算して', 期待値={'A':'770','B':'340'})
    応答(会話, '元の条件で再計算して', 期待値={'A':'410','B':'340'})
    会話 = HDS運用セッション.復元(会話.保存())
    応答(会話, '再計算して', 期待値={'A':'410','B':'340'})
    応答(会話, '資料「A」の原文を再参照して', ('数量は3個',))

    不足 = HDS運用セッション('不足確認実演', 手順形成=False)
    応答(不足, '資料「見積」を登録:単価は12円/個。費用は単価*数量。')
    応答(不足, '資料「見積」の費用を計算して', ('数量不足',), 成立=False)
    応答(不足, '数量は5個です', 期待値={'見積':'60'})

    手順 = HDS運用セッション('手順転用実演', 再利用=False)
    応答(手順, '資料「測定」を登録:個数は3個。結果は個数*2。')
    形成 = 応答(手順, '資料「測定」の結果を計算して', 期待値={'測定':'6'})
    if 形成.追跡['手順形成'].get('再現工程数') != 7:
        raise RuntimeError('7工程の形成再実行が確認できない')
    応答(手順, '資料「測定」を更新:個数は4個。結果は個数*2。')
    再利用 = 応答(手順, '再計算して', 期待値={'測定':'8'})
    if (not 再利用.追跡['手順形成'].get('手順再利用')
            or any(行['再利用'] for 行 in 再利用.追跡['能力試行'])):
        raise RuntimeError('手順再利用と値キャッシュが分離されていない')
    成果 = {'種別':'人工資料の数量運用v3実演', '検査数':len(記録),
             'COMMIT数':sum(行['状態']=='COMMIT' for 行 in 記録),
             '期待した保留数':sum(not 行['期待成立'] for 行 in 記録),
             '検査合格':all(行['検査合格'] for 行 in 記録), '記録':記録,
             '境界':'有限数量構文の全経路試験。任意自然文・GPT-4比較・現実の事実認定ではない。再表現時も内部整合検査は再計算を行う。'}
    if 引数.output:
        引数.output.parent.mkdir(parents=True,exist_ok=True)
        引数.output.write_text(json.dumps(成果,ensure_ascii=False,indent=2),encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
