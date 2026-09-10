"""指定セルの選択が後続の抽出へ到達する人工CSVの対照。自由文理解の評価ではない。"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from minidora.構造化文書接続 import 構造化文書能力群
from minidora.構造化文書操作 import 文書記録整合
from minidora.能力合成 import 能力合成器, 合成計画, 合成工程, 素材参照
from minidora.能力合成_局所接続 import 局所能力群
from minidora.製品版.型 import 能力結果, 参照資料


def 用意(値: int = 120, 列名: str = '金額'):
    text=f'番号,品目,金額,備考\r\n001,甲,{値},採用候補\r\n002,乙,999,別件\r\n'
    data={'原資料':能力結果(True,text,参照=(参照資料('CSV原典','人工明細','局所試験',本文=text),)),
          '指示':能力結果(True,'宣言した文書操作を実行'),
          '読取設定':能力結果(True,'',データ={'形式':'CSV'}),
          '抽出設定':能力結果(True,'',データ={'種別':'数字'})}
    stages=[合成工程('読取',('文書読取',),'指示',(素材参照('入力','原資料'),),'読取設定')]
    operations=[('列選択','CSV選択',{'列':[列名],'行':[0]}),
                ('JSON化','形式変換',{'出力':'JSON','行表現':'対象'}),
                ('セル選択','JSON選択',{'位置':'/0/'+列名}),
                ('値本文','値取出',{'型':'文字列'})]
    previous='読取'
    for key,op,settings in operations:
        data[key+'設定']=能力結果(True,'',データ={'操作':op,'設定':settings})
        stages.append(合成工程(key,('文書操作',),'指示',(素材参照('工程',previous),),key+'設定'))
        previous=key
    stages.append(合成工程('抽出',('情報抽出',),'指示',(素材参照('工程',previous),),'抽出設定'))
    return 合成計画(tuple(stages),('抽出',)),data


def main():
    if hasattr(sys.stdout,'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--値',type=int,default=120)
    p.add_argument('--欠落列',action='store_true')
    args=p.parse_args()
    if not 0<=args.値<=1000000: p.error('--値は0〜1000000')
    plan,data=用意(args.値,'存在しない列' if args.欠落列 else '金額')
    result=能力合成器((*構造化文書能力群(),*局所能力群())).実行(plan,data)
    documents=[v for _,v in result.中間結果 if v.データ.get('版')=='MINIDORA-構造化文書-v0.1']
    final=result.出力[0][1].本文 if result.成立 else ''
    selected=dict(result.中間結果).get('値本文')
    ok=(not result.成立 and not result.出力) if args.欠落列 else result.成立 and final==str(args.値)
    print(json.dumps({'範囲':'明示行列からの文書処理。意味的に正しい選択かは上位の責任。',
        '成立':result.成立,'理由':result.理由,'最終結果':final,
        '中間本文':{k:v.本文 for k,v in result.中間結果},
        '元セル対応':selected.データ['文書']['対応'].get('') if selected else None,
        '未選択位置':selected.データ['未選択位置'] if selected else [],
        '実行数':result.実行数,'合成監査':result.監査整合(),
        '文書監査':bool(documents) and all(文書記録整合(v) for v in documents),
        '対照成立':bool(ok)},ensure_ascii=False,indent=2))
    return 0 if ok and result.監査整合() else 1


if __name__=='__main__':
    raise SystemExit(main())
