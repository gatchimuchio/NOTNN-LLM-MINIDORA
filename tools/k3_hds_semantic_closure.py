#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
from collections import Counter
from pathlib import Path

import k3_hds_stream_compile as base
from k3_hds_semantics_v6 import install

install(base)

src = Path('解析/K3全公開データコンパイル/v6/header-probe/header-probe-summary.json')
out = Path('解析/K3全公開データコンパイル/v6/header-probe/HDS原理族閉包監査.json')
d = json.loads(src.read_text(encoding='utf-8'))
unknown_before = d.get('HDS適合不能tensor名', [])
resolved = []
still = []
counts = Counter()
for name in unknown_before:
    pid = base.principle_for_tensor(name)
    counts[pid] += 1
    if pid == 'P-OTHER':
        still.append(name)
    else:
        resolved.append({'tensor': name, 'HDS原理族': pid})
report = {
    'source_header_probe_sha256': d.get('index_sha256'),
    '住所全数固定済み': bool(d.get('PASS_住所全数固定')),
    'tensor総数': d.get('tensor_count_from_headers'),
    'payload総byte': d.get('total_tensor_payload_bytes_from_headers'),
    'HDS適合不能_補完前': len(unknown_before),
    '補完原理族別': dict(counts),
    'HDS適合不能_補完後': len(still),
    '残存tensor': still,
    'PASS_HDS原理族全数付与': bool(d.get('PASS_住所全数固定')) and len(still) == 0,
}
out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False, indent=2))
raise SystemExit(0 if report['PASS_HDS原理族全数付与'] else 2)
