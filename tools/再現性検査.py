"""外部作用なしの21開発ケースを異なるhash seedの別プロセスで実行する。"""
from __future__ import annotations
from dataclasses import asdict
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
from 独立入力評価 import ケースを読む
from minidora.能力合成 import _符号化
from minidora.監査改善接続 import 改善計画を実行

root=Path(__file__).resolve().parents[1]


from minidora.標準入出力 import 標準入出力をUTF8にする

def main():
    標準入出力をUTF8にする()
    if len(sys.argv)==2 and sys.argv[1]=='--子実行':
        rows,_=ケースを読む(root/'評価/第22バッチ_開発ケース.jsonl')
        result=[asdict(改善計画を実行(r['種類'],r['要求'],詳細=False)) for r in rows]
        print(sha256(_符号化(result)).hexdigest());return 0
    outputs={}
    for seed in ('0','1','913'):
        env=dict(os.environ);env['PYTHONHASHSEED']=seed;env['PYTHONDONTWRITEBYTECODE']='1'
        p=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--子実行'],
            env=env,check=True,capture_output=True,text=True,encoding='utf-8',timeout=20)
        outputs[seed]=p.stdout.strip()
    result={'対象':'外部作用なしの開発21ケース、合成結果全体','hash_seed別SHA256':outputs,
            '一致':len(set(outputs.values()))==1,'LIVE再現性':'未検証'}
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if result['一致'] else 1

if __name__=='__main__':raise SystemExit(main())
