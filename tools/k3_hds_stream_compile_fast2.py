#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K3 HDS v6 高速ストリームコンパイラ v2。
Range prefetchを固定窓にし、生payload保持量を workers × block_size 程度へ厳密に制限する。
"""
from __future__ import annotations

import threading
from collections import deque
from concurrent.futures import ThreadPoolExecutor

import requests

import k3_hds_stream_compile_fast as fast
import k3_hds_stream_compile as base


def bounded_payload_blocks(url: str, data_base: int, scan_limit: int, block_size: int, expected_total: int, workers: int):
    starts=iter(range(0,scan_limit,block_size))
    tls=threading.local()
    def fetch(start: int):
        if not hasattr(tls,'session'):
            tls.session=requests.Session()
        end=min(start+block_size,scan_limit)
        rr=base.get_range(tls.session,url,data_base+start,data_base+end-1)
        if rr.total_size!=expected_total:
            raise ValueError(f'remote size changed: {rr.total_size} != {expected_total}')
        return start,end,rr.data
    if workers<=1:
        for st in starts:
            yield fetch(st)
        return
    with ThreadPoolExecutor(max_workers=workers,thread_name_prefix='k3-range') as ex:
        q=deque()
        for _ in range(workers):
            try: st=next(starts)
            except StopIteration: break
            q.append(ex.submit(fetch,st))
        while q:
            fut=q.popleft()
            yield fut.result()
            try: st=next(starts)
            except StopIteration: continue
            q.append(ex.submit(fetch,st))

fast.payload_blocks=bounded_payload_blocks

if __name__=='__main__':
    raise SystemExit(fast.main())
