"""統合前後の切断対照、再利用ON/OFFの出力・呼出回数・実時間を測る。汎用性能評価ではない。"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
import runpy
from statistics import median
import sys
from time import perf_counter_ns
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from minidora.統合実行 import 統合セッション
from minidora.能力合成 import 能力合成器, 合成計画, 合成工程, 素材参照, _結果辞書, _符号化
from minidora.能力合成_局所接続 import 局所能力群
from minidora.製品版.型 import 能力結果


def 実測(repeats=4):
    if type(repeats) is not int or not 2<=repeats<=8:
        raise ValueError('反復は2〜8')
    root=Path(__file__).resolve().parent
    workloads={
        '数学':runpy.run_path(str(root/'数学記号デモ.py'))['記号計画']('731'),
        '構造文書':runpy.run_path(str(root/'構造化文書デモ.py'))['用意'](731),
        '文章作成編集':runpy.run_path(str(root/'文章作成編集デモ.py'))['用意'](731)}
    rows=[]
    for name,(plan,data) in workloads.items():
        reference=None
        for enabled in (False,True):
            session=統合セッション('調整対照',再利用=enabled)
            durations=[];counts=[];hashes=[]
            for _ in range(repeats):
                start=perf_counter_ns();r=session.計画実行(plan,data);durations.append((perf_counter_ns()-start)/1000000)
                if not r.成立:
                    raise ValueError(f'{name}:{r.理由}')
                values=_符号化([(k,_結果辞書(v)) for k,v in r.出力])
                if reference is None:reference=values
                if reference!=values:raise ValueError('ON/OFF・反復の出力不一致')
                counts.append({field:sum(x[field] for x in r.計測['再利用差分'].values()) for field in ('原実行','再利用')})
                hashes.append(sha256(values).hexdigest())
            rows.append({'課題':name,'再利用有効':enabled,'反復数':repeats,'各回ミリ秒':durations,
                         '二回目以降中央値ミリ秒':median(durations[1:]),'処理回数':counts,'出力SHA256':hashes})
    source=能力結果(True,'。'.join(f'項目{i}' for i in range(20))+'。')
    p=合成計画((合成工程('変換',('文脈変換',),'指示',(素材参照('入力','本文'),),'設定'),),('変換',))
    d={'指示':能力結果(True,'箇条書き化'),'本文':source,'設定':能力結果(True,'',データ={'形式':'箇条書き'})}
    old=能力合成器(局所能力群()).実行(p,d)
    new=統合セッション('切断対照').計画実行(p,d)
    return {'範囲':'人工素材と既存計画。時間はこの環境の全処理実測で、一般速度・GPT-4比較ではない。',
            '出力一致':True,'測定':rows,'箇条書き項目数':{
                '旧経路':len(old.出力[0][1].本文.splitlines()),'統合経路':len(new.本文.splitlines()),'元項目数':20}}


def main():
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--反復',type=int,default=4)
    a=p.parse_args()
    print(json.dumps(実測(a.反復),ensure_ascii=False,indent=2))
    return 0


if __name__=='__main__':raise SystemExit(main())
