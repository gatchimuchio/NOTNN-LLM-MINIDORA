#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from huggingface_hub import HfApi

REPO='moonshotai/Kimi-K3'
REV='c5d1dd4c428bd1ce8b88c5044f3b6ccde9e3b721'


def obj_dict(x):
    d={'path': x.path, 'type': x.__class__.__name__}
    for k in ('size','blob_id','security'):
        v=getattr(x,k,None)
        if v is not None:
            d[k]=v
    lfs=getattr(x,'lfs',None)
    if lfs is not None:
        if hasattr(lfs,'__dict__'):
            d['lfs']={k:v for k,v in vars(lfs).items() if v is not None}
        else:
            d['lfs']=str(lfs)
    return d


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    api=HfApi()
    rows=[]
    for x in api.list_repo_tree(REPO, revision=REV, recursive=True, expand=True):
        rows.append(obj_dict(x))
    files=[r for r in rows if r['type']=='RepoFile']
    dirs=[r for r in rows if r['type']!='RepoFile']
    files.sort(key=lambda x:x['path'])
    weight=[r for r in files if r['path'].startswith('model-') and r['path'].endswith('.safetensors')]
    nonweight=[r for r in files if r not in weight]
    canonical='\n'.join(f"{r['path']}\t{r.get('size')}\t{r.get('blob_id')}\t{json.dumps(r.get('lfs'),sort_keys=True,default=str)}" for r in files).encode()
    out={
      'repo':REPO,'revision':REV,
      'file_count':len(files),'dir_count':len(dirs),
      'weight_shard_count':len(weight),'nonweight_file_count':len(nonweight),
      'total_file_size':sum(int(r.get('size') or 0) for r in files),
      'weight_file_size':sum(int(r.get('size') or 0) for r in weight),
      'nonweight_file_size':sum(int(r.get('size') or 0) for r in nonweight),
      'manifest_sha256':hashlib.sha256(canonical).hexdigest(),
      'files':files,
      'nonweight_files':nonweight,
      'directories':dirs,
    }
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(out,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    print(json.dumps({k:out[k] for k in ('file_count','weight_shard_count','nonweight_file_count','total_file_size','weight_file_size','nonweight_file_size','manifest_sha256')},ensure_ascii=False,indent=2))

if __name__=='__main__': main()
