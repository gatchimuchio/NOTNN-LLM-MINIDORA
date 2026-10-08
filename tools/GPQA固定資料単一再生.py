from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import GPQA固定資料高速差分 as 共通


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--evidence",type=Path,required=True)
    p.add_argument("--evidence-name",required=True)
    p.add_argument("--code-name",required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    source=a.source.resolve(); evidence=a.evidence.resolve(); out=a.out.resolve()
    refs=共通._refs(evidence)
    missing=sorted(set(共通.対象問題)-set(refs))
    if missing: raise RuntimeError("checkpoint不足:"+repr(missing))
    cases=共通._cases(source)
    worker=Path(__file__).with_name("GPQA固定資料高速worker.py").resolve()
    with tempfile.TemporaryDirectory() as directory:
        d=Path(directory); input_path=d/"input.json"; output_path=d/"output.json"
        共通._write(input_path,cases,refs,a.evidence_name)
        rows=共通._run(source,worker,input_path,output_path)
    out.write_text(json.dumps({"code":a.code_name,"evidence":a.evidence_name,"rows":rows},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":main()
