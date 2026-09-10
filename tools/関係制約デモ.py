"""差分関係の追加・削除・矛盾が比較結果を変える局所デモ。"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from minidora.関係制約 import 関係式, 関係問題, 関係制約器, 関係記録整合


def main() -> int:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group()
    group.add_argument('--関係欠落',action='store_true')
    group.add_argument('--矛盾',action='store_true')
    args=parser.parse_args()
    facts=[関係式('関係1','A','以上','B','3')]
    if not args.関係欠落:
        facts.append(関係式('関係2','B','以上','C','2'))
    if args.矛盾:
        facts.append(関係式('反対関係','C','以上','A'))
    p=関係問題(('A','B','C'),tuple(facts),(関係式('比較','A','以上','C','5'),))
    r=関係制約器().実行(p)
    state=r.データ['回答'][0]['判定'] if r.成立 else None
    print(json.dumps({'範囲':'明示された実数差分関係。自由文理解や汎用性能の評価ではない。',
        '判定':state,'監査整合':関係記録整合(r),'報告':r.データ,'保留理由':r.保留理由},ensure_ascii=False,indent=2))
    expected='前提矛盾' if args.矛盾 else '未確定' if args.関係欠落 else '導出'
    return 0 if state==expected and 関係記録整合(r) else 1


if __name__=='__main__':
    raise SystemExit(main())
