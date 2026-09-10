"""記号微分→代入→採用の実合成と、連立方程式の解区分を示す局所デモ。"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from minidora.記号演算 import 数学記録整合
from minidora.線形方程式 import 線形を解く
from minidora.数学能力接続 import 数学能力群
from minidora.能力合成 import 能力合成器, 合成計画, 合成工程, 素材参照
from minidora.能力合成_局所接続 import 局所能力群
from minidora.製品版.型 import 能力結果


def 記号計画(値='2'):
    data={'式':能力結果(True,'',データ={'式':'(x+1)**3','変数':['x']}),
          '指示':能力結果(True,'宣言した数学操作を実行'),
          '微分設定':能力結果(True,'',データ={'操作':'微分','対象変数':'x'}),
          '代入設定':能力結果(True,'',データ={'操作':'代入','代入値':{'x':値}}),
          '採用設定':能力結果(True,'',データ={'期待':'定数値'}),
          '整形設定':能力結果(True,'',データ={'形式':'箇条書き'})}
    plan=合成計画((
        合成工程('微分',('記号演算',),'指示',(素材参照('入力','式'),),'微分設定'),
        合成工程('代入',('記号演算',),'指示',(素材参照('工程','微分'),),'代入設定'),
        合成工程('採用',('数学結果採用',),'指示',(素材参照('工程','代入'),),'採用設定'),
        合成工程('整形',('文脈変換',),'指示',(素材参照('工程','採用'),),'整形設定'),
    ),('整形',))
    return plan,data


def main():
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--値',default='2')
    parser.add_argument('--モード',choices=('記号','一意解','自由解','解なし'),default='記号')
    args=parser.parse_args()
    if args.モード=='記号':
        plan,data=記号計画(args.値)
        result=能力合成器((*数学能力群(),*局所能力群())).実行(plan,data)
        mids=dict(result.中間結果)
        audits=[数学記録整合(mids[k]) for k in ('微分','代入') if k in mids]
        out={'範囲':'形式数式の局所接続。自由文や汎用性能の評価ではない。',
             '成立':result.成立,'理由':result.理由,
             '中間結果':{k:v.本文 for k,v in result.中間結果},
             '最終結果':{k:v.本文 for k,v in result.出力},
             '合成監査':result.監査整合(),'数学監査':len(audits)==2 and all(audits)}
        ok=result.成立 and out['合成監査'] and out['数学監査']
    else:
        equations=[{'左辺':'x+y','右辺':'5'}]
        if args.モード=='一意解':equations.append({'左辺':'x-y','右辺':'1'})
        if args.モード=='解なし':equations.append({'左辺':'2*x+2*y','右辺':'11'})
        result=線形を解く(('x','y'),tuple(equations))
        out={'成立':result.成立,'本文':result.本文,'結果':result.データ,'数学監査':数学記録整合(result)}
        ok=result.成立 and out['数学監査'] and result.データ['判定']==args.モード
    print(json.dumps(out,ensure_ascii=False,indent=2))
    return 0 if ok else 2


if __name__=='__main__':
    raise SystemExit(main())
