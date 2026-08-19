#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import struct
from collections import Counter
from pathlib import Path

import requests

from k3_hds_stream_compile import (
    HF_REPO,
    HF_REVISION,
    SHARD_COUNT,
    get_range,
    jdump,
    principle_for_tensor,
    resolve_url,
    shard_name,
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--out-summary', type=Path, required=True)
    ap.add_argument('--out-manifest', type=Path, required=True)
    ap.add_argument('--revision', default=HF_REVISION)
    args = ap.parse_args()

    session = requests.Session()
    tensor_to_shard = {}
    principle_counts = Counter()
    dtype_counts = Counter()
    unknown_names = []
    shard_audits = []
    total_payload = 0
    total_files = 0
    total_header = 0

    args.out_manifest.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(args.out_manifest, 'wt', encoding='utf-8') as out:
        for i in range(1, SHARD_COUNT + 1):
            shard = shard_name(i)
            url = resolve_url(shard, args.revision)
            first = get_range(session, url, 0, 7)
            hlen = struct.unpack('<Q', first.data)[0]
            hrr = get_range(session, url, 8, 8 + hlen - 1)
            header = json.loads(hrr.data)
            entries = []
            for name, meta in header.items():
                if name == '__metadata__':
                    continue
                a, b = map(int, meta['data_offsets'])
                entries.append((a, b, name, meta))
            entries.sort(key=lambda x: (x[0], x[1], x[2]))
            cursor = 0
            gaps = []
            overlaps = []
            for a, b, name, meta in entries:
                if a > cursor:
                    gaps.append([cursor, a])
                if a < cursor:
                    overlaps.append({'tensor': name, 'start': a, 'previous_end': cursor})
                cursor = max(cursor, b)
                pid = principle_for_tensor(name)
                principle_counts[pid] += 1
                dtype_counts[str(meta.get('dtype'))] += 1
                if pid == 'P-OTHER':
                    unknown_names.append(name)
                if name in tensor_to_shard:
                    raise RuntimeError(f'duplicate tensor name: {name}')
                tensor_to_shard[name] = shard
                out.write(jdump({
                    'tensor': name,
                    'shard': shard,
                    'dtype': meta.get('dtype'),
                    'shape': meta.get('shape'),
                    'data_offsets': [a, b],
                    'payload_bytes': b-a,
                    'HDS原理族': pid,
                }) + '\n')
            file_expected = 8 + hlen + cursor
            shard_audits.append({
                'shard': shard,
                'remote_total_bytes': first.total_size,
                'header_bytes': 8 + hlen,
                'payload_bytes': cursor,
                'tensor_count': len(entries),
                'gaps': gaps,
                'overlaps': overlaps,
                'file_size_match': file_expected == first.total_size,
                'etag': first.etag,
            })
            total_payload += cursor
            total_files += first.total_size
            total_header += 8 + hlen
            print(jdump({'header_scanned': i, 'shard': shard, 'tensors_total': len(tensor_to_shard)}), flush=True)

    index_url = f'https://huggingface.co/{HF_REPO}/resolve/{args.revision}/model.safetensors.index.json?download=true'
    r = session.get(index_url, timeout=(30, 180), allow_redirects=True)
    r.raise_for_status()
    index_bytes = r.content
    index = json.loads(index_bytes)
    weight_map = index['weight_map']
    expected_names = set(weight_map)
    scanned_names = set(tensor_to_shard)
    missing = sorted(expected_names - scanned_names)
    extra = sorted(scanned_names - expected_names)
    wrong_shard = []
    for name in expected_names & scanned_names:
        if weight_map[name] != tensor_to_shard[name]:
            wrong_shard.append({'tensor': name, 'index': weight_map[name], 'header': tensor_to_shard[name]})

    summary = {
        'source': {'repo': HF_REPO, 'revision': args.revision},
        'shards': SHARD_COUNT,
        'tensor_count_from_headers': len(tensor_to_shard),
        'tensor_count_from_index': len(weight_map),
        'total_tensor_payload_bytes_from_headers': total_payload,
        'index_metadata_total_size': index.get('metadata', {}).get('total_size'),
        'total_safetensors_file_bytes': total_files,
        'total_header_bytes': total_header,
        'index_bytes': len(index_bytes),
        'index_sha256': hashlib.sha256(index_bytes).hexdigest(),
        'principle_counts': dict(principle_counts),
        'dtype_counts': dict(dtype_counts),
        'HDS適合不能tensor数': len(unknown_names),
        'HDS適合不能tensor名': unknown_names,
        'index_missing_from_headers': missing,
        'header_extra_vs_index': extra,
        'wrong_shard_mapping': wrong_shard,
        'shard_failures': [x for x in shard_audits if x['gaps'] or x['overlaps'] or not x['file_size_match']],
    }
    summary['PASS_住所全数固定'] = (
        not missing and not extra and not wrong_shard and not summary['shard_failures']
        and total_payload == index.get('metadata', {}).get('total_size')
    )
    summary['PASS_HDS原理族全数付与'] = len(unknown_names) == 0
    args.out_summary.parent.mkdir(parents=True, exist_ok=True)
    args.out_summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({
        'PASS_住所全数固定': summary['PASS_住所全数固定'],
        'PASS_HDS原理族全数付与': summary['PASS_HDS原理族全数付与'],
        'tensor_count': len(tensor_to_shard),
        'HDS適合不能tensor数': len(unknown_names),
        'total_payload_bytes': total_payload,
    }, ensure_ascii=False, indent=2))
    return 0 if summary['PASS_住所全数固定'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
