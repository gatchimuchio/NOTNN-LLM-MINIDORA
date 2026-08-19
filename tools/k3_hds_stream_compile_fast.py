#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K3 HDS v6 高速ストリーム全数コンパイラ。

shardを保存せず、複数HTTP Rangeを並列prefetchしつつ、処理順序はbyte順に固定する。
保持する生データは workers × block_size 程度のみ。
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import struct
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

import requests

import k3_hds_stream_compile as base
from k3_hds_semantics_v6 import install

install(base)


def payload_blocks(url: str, data_base: int, scan_limit: int, block_size: int, expected_total: int, workers: int):
    starts=list(range(0,scan_limit,block_size))
    tls=threading.local()
    def fetch(start: int):
        if not hasattr(tls,'session'):
            tls.session=requests.Session()
        end=min(start+block_size,scan_limit)
        rr=base.get_range(tls.session,url,data_base+start,data_base+end-1)
        if rr.total_size != expected_total:
            raise ValueError(f'remote size changed: {rr.total_size} != {expected_total}')
        return start,end,rr.data
    if workers<=1:
        for st in starts:
            yield fetch(st)
        return
    with ThreadPoolExecutor(max_workers=workers,thread_name_prefix='k3-range') as ex:
        # executor.map は入力順を保持するため、hash/provenanceも物理byte順のまま。
        for item in ex.map(fetch,starts):
            yield item


def scan_shard(shard_index: int, out_path: Path, audit_path: Path, block_size: int,
               max_payload_bytes: Optional[int], allow_partial: bool, revision: str, fetch_workers: int) -> int:
    base.HF_REVISION=revision
    shard=base.shard_name(shard_index)
    url=base.resolve_url(shard,revision)
    s=requests.Session()
    first=base.get_range(s,url,0,7)
    header_len=struct.unpack('<Q',first.data)[0]
    if header_len<=1 or header_len>512*1024*1024:
        raise ValueError(f'implausible safetensors header length: {header_len}')
    hrr=base.get_range(s,url,8,8+header_len-1)
    if hrr.total_size!=first.total_size:
        raise ValueError('remote size changed while reading header')
    header=json.loads(hrr.data)
    entries=[]
    metadata=header.get('__metadata__')
    for name,meta in header.items():
        if name=='__metadata__': continue
        a,b=map(int,meta['data_offsets'])
        entries.append((a,b,name,meta))
    entries.sort(key=lambda x:(x[0],x[1],x[2]))
    if not entries: raise ValueError('no tensors in shard')
    gaps=[]; overlaps=[]; cursor=0
    for a,b,name,_ in entries:
        if a>cursor: gaps.append([cursor,a])
        if a<cursor: overlaps.append({'tensor':name,'start':a,'previous_end':cursor})
        cursor=max(cursor,b)
    payload_len=cursor
    data_base=8+header_len
    expected_file_size=data_base+payload_len
    trailing_or_mismatch=first.total_size-expected_file_size
    scan_limit=payload_len if max_payload_bytes is None else min(payload_len,max_payload_bytes)
    partial=scan_limit<payload_len
    file_hash=hashlib.sha256(); file_hash.update(first.data); file_hash.update(hrr.data)

    out_path.parent.mkdir(parents=True,exist_ok=True); audit_path.parent.mkdir(parents=True,exist_ok=True)
    tensors_completed=payload_scanned=tensor_payload_scanned=unassigned_payload=unknown_hds=0
    idx=0; active=None
    with gzip.open(out_path,'wt',encoding='utf-8') as out:
        out.write(base.jdump({'kind':'HDS原理族定義','source':{'repo':base.HF_REPO,'revision':revision},'principles':base.PRINCIPLE_FAMILIES})+'\n')
        out.write(base.jdump({'kind':'safetensors_header_observation','source':{'repo':base.HF_REPO,'revision':revision,'shard':shard},'remote_total_bytes':first.total_size,'header_length':header_len,'header_sha256':hashlib.sha256(hrr.data).hexdigest(),'metadata':metadata,'tensor_count':len(entries),'payload_bytes_expected_from_header':payload_len,'gaps':gaps,'overlaps':overlaps,'file_size_minus_header_derived':trailing_or_mismatch,'HDS':'物理shard境界は意味境界と仮定せず、headerをtensor住所関係として観測する。'})+'\n')
        for block_start,block_end,block in payload_blocks(url,data_base,scan_limit,block_size,first.total_size,fetch_workers):
            file_hash.update(block); payload_scanned+=len(block); local=0
            while local<len(block):
                pos=block_start+local
                while idx<len(entries) and entries[idx][1]<=pos:
                    a,b,name,meta=entries[idx]
                    if active is not None and active.name==name:
                        stats=active.finish(); rec=base.tensor_semantic_record(shard,active,stats,data_base)
                        if rec['HDS']['status']!='HDS適合': unknown_hds+=1
                        out.write(base.jdump({'kind':'tensor_HDS日本語意味構文',**rec})+'\n'); tensors_completed+=1; active=None
                    idx+=1
                if idx>=len(entries):
                    rest=block[local:]; unassigned_payload+=len(rest); local=len(block); continue
                a,b,name,meta=entries[idx]
                if pos<a:
                    take=min(len(block)-local,a-pos); unassigned_payload+=take; local+=take; continue
                if active is None:
                    active=base.TensorStats(name=name,dtype=str(meta.get('dtype')),shape=list(meta.get('shape',[])),start=a,end=b)
                elif active.name!=name:
                    raise RuntimeError(f'active tensor mismatch {active.name} != {name}')
                take=min(len(block)-local,b-pos); seg=block[local:local+take]
                active.update(seg); tensor_payload_scanned+=take; local+=take; pos+=take
                if pos==b:
                    stats=active.finish(); rec=base.tensor_semantic_record(shard,active,stats,data_base)
                    if rec['HDS']['status']!='HDS適合': unknown_hds+=1
                    out.write(base.jdump({'kind':'tensor_HDS日本語意味構文',**rec})+'\n'); tensors_completed+=1; active=None; idx+=1
            print(base.jdump({'shard':shard,'payload_scanned':payload_scanned,'payload_target':scan_limit,'tensors_completed':tensors_completed,'fetch_workers':fetch_workers}),flush=True)
        partial_active=None
        if active is not None:
            partial_active={'tensor':active.name,'bytes_seen':active.bytes_seen,'tensor_bytes':active.end-active.start,'partial_sha256':active.sha256.hexdigest()}

    complete=(not partial and not gaps and not overlaps and trailing_or_mismatch==0 and unassigned_payload==0 and payload_scanned==payload_len and tensor_payload_scanned==payload_len and tensors_completed==len(entries) and active is None)
    smoke_ok=(partial and allow_partial and payload_scanned==scan_limit and unassigned_payload==0 and not overlaps and trailing_or_mismatch==0)
    audit={
        'source':{'repo':base.HF_REPO,'revision':revision,'shard':shard,'url':url,'repo_commit_header':first.repo_commit,'etag':first.etag},
        'remote_total_bytes':first.total_size,'header_bytes_scanned':8+header_len,'payload_bytes_expected':payload_len,'payload_bytes_scanned':payload_scanned,'tensor_payload_bytes_scanned':tensor_payload_scanned,
        'tensor_count_expected':len(entries),'tensor_count_completed':tensors_completed,'gaps':gaps,'overlaps':overlaps,'unassigned_payload_bytes':unassigned_payload,'trailing_or_size_mismatch_bytes':trailing_or_mismatch,'HDS適合不能tensor数':unknown_hds,
        'partial':partial,'partial_active_tensor':partial_active,'file_sha256_if_complete':file_hash.hexdigest() if complete else None,
        'coverage':{'payload_ratio':payload_scanned/payload_len if payload_len else 1.0,'全byte実読':complete},'fetch_workers':fetch_workers,'PASS':complete,'SMOKE_PASS':smoke_ok,
    }
    audit_path.write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(audit,ensure_ascii=False,indent=2),flush=True)
    return 0 if complete or smoke_ok else 2


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--shard',type=int,required=True); ap.add_argument('--out',type=Path,required=True); ap.add_argument('--audit',type=Path,required=True)
    ap.add_argument('--block-size',type=int,default=base.DEFAULT_BLOCK); ap.add_argument('--max-payload-bytes',type=int); ap.add_argument('--allow-partial',action='store_true'); ap.add_argument('--revision',default=base.HF_REVISION); ap.add_argument('--fetch-workers',type=int,default=6)
    a=ap.parse_args()
    if a.fetch_workers<1 or a.fetch_workers>16: raise SystemExit('--fetch-workers must be 1..16')
    return scan_shard(a.shard,a.out,a.audit,a.block_size,a.max_payload_bytes,a.allow_partial,a.revision,a.fetch_workers)

if __name__=='__main__': raise SystemExit(main())
