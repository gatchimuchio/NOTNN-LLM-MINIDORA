"""資料からの文章組立て、限定修正、保護された留保の削除拒否を示す。"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from minidora.文章作成 import 文章仕様, 文章単位, 文章断片
from minidora.文章編集 import 文章記録整合
from minidora.文章能力接続 import 文章能力群
from minidora.能力合成 import 能力合成器, 合成計画, 合成工程, 素材参照, _結果辞書
from minidora.能力合成_局所接続 import 局所能力群
from minidora.製品版.型 import 能力結果, 参照資料


def 用意(値=120, 保護違反=False):
    materials = {"題": 能力結果(True, '運用メモ（草案）'),
        "記載": 能力結果(True, f'装置Aの電圧は{値} Vです。', 参照=(参照資料('人工資料', '試験入力', '局所デモ', 本文=f'装置Aの電圧は{値} Vです。'),)),
        "条件": 能力結果(True, '測定条件は試験時のみです。'),
        "留保": 能力結果(True, '本番環境への適用は未確認です。')}
    def unit(key, role, companions=()):
        return 文章単位(key, role, (文章断片(key, 0, len(materials[key].本文)),), companions)
    spec = 文章仕様((unit('題','見出し'),unit('記載','段落',('条件','留保')),
                    unit('条件','条件'),unit('留保','留保')), ('題','記載'))
    data = {'入力':能力結果(True,'',データ={'素材':{k:_結果辞書(v) for k,v in materials.items()},'仕様':asdict(spec)}),
        '指示':能力結果(True,'指定した文章処理を実行'),
        '置換設定':能力結果(True,'',データ={
            '検索文':'本番環境への適用は未確認です。' if 保護違反 else '草案',
            '置換文':'' if 保護違反 else '確認版', '理由':'明示された編集案'}),
        '抽出設定':能力結果(True,'',データ={'種別':'数字'})}
    plan = 合成計画((
        合成工程('作成',('文章作成',),'指示',(素材参照('入力','入力'),)),
        合成工程('箇所',('文章置換箇所',),'指示',(素材参照('工程','作成'),),'置換設定'),
        合成工程('編集',('文章編集',),'指示',(素材参照('工程','箇所'),)),
        合成工程('抽出',('情報抽出',),'指示',(素材参照('工程','編集'),),'抽出設定'),
    ),('編集','抽出'))
    return plan, data


def main():
    if hasattr(sys.stdout,'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--値',type=int,default=120)
    parser.add_argument('--保護違反',action='store_true')
    args=parser.parse_args()
    if not 0<=args.値<=1000000: parser.error('--値は0〜1000000')
    plan,data=用意(args.値,args.保護違反)
    result=能力合成器((*文章能力群(),*局所能力群())).実行(plan,data)
    middle=dict(result.中間結果)
    draft=middle.get('編集')
    reports=[v for v in middle.values() if v.データ.get('版')=='MINIDORA-文章作成編集-v0.1']
    ok=(not result.成立 and result.出力==()) if args.保護違反 else (
        result.成立 and dict(result.出力)['抽出'].本文==str(args.値) and '確認版' in draft.本文)
    out={'範囲':'人工素材と明示構成・修正文の局所試験。未知文章の生成や意味同値性の評価ではない。',
        '成立':result.成立,'理由':result.理由,'初稿':middle['作成'].本文 if '作成' in middle else '',
        '改稿':draft.本文 if draft else '', '差分':draft.データ['直近差分'] if draft else [],
        '後続抽出':dict(result.出力)['抽出'].本文 if result.成立 else '',
        '実行能力':[h.能力 for h in result.履歴],
        '文章監査':bool(reports) and all(文章記録整合(r) for r in reports),
        '合成監査':result.監査整合(),'対照成立':bool(ok)}
    print(json.dumps(out,ensure_ascii=False,indent=2))
    return 0 if ok and out['文章監査'] and out['合成監査'] else 1


if __name__=='__main__':
    raise SystemExit(main())
