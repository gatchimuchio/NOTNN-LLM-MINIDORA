#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json
from pathlib import Path
from huggingface_hub import HfApi

REPO='moonshotai/Kimi-K3'
REV='c5d1dd4c428bd1ce8b88c5044f3b6ccde9e3b721'

def plain(x):
    if x is None or isinstance(x,(str,int,float,bool)): return x
    if isinstance(x,dict): return {str(k):plain(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)): return [plain(v) for v in x]
    if hasattr(x,'__dict__'): return {k:plain(v) for k,v in vars(x).items() if not k.startswith('_')}
    return repr(x)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--out',type=Path,required=True); a=ap.parse_args()
    info=HfApi().model_info(REPO,revision=REV,files_metadata=True)
    rows=[]
    for s in info.siblings:
        d=plain(s)
        rows.append(d)
    rows.sort(key=lambda x:x.get('rfilename') or x.get('path') or '')
    out={'repo':REPO,'revision_requested':REV,'repo_sha':getattr(info,'sha',None),'files':rows}
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'repo_sha':out['repo_sha'],'file_count':len(rows),'sample_weight':next((r for r in rows if str(r.get('rfilename','')).endswith('.safetensors')),None)},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
