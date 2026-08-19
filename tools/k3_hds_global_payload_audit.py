#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
from pathlib import Path

EXPECTED_SHARDS = 96
EXPECTED_PAYLOAD = 1560860324864
EXPECTED_TENSORS = 497220


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--audit-dir', type=Path, required=True)
    ap.add_argument('--header-probe', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()

    hp = json.loads(args.header_probe.read_text(encoding='utf-8'))
    files = sorted(args.audit_dir.rglob('*.audit.json'))
    rows = [json.loads(p.read_text(encoding='utf-8')) for p in files]
    shard_names = [r.get('source', {}).get('shard') for r in rows]
    unique = sorted(set(shard_names))
    duplicate = sorted({x for x in shard_names if shard_names.count(x) > 1})

    total_expected = sum(int(r.get('payload_bytes_expected', 0)) for r in rows)
    total_scanned = sum(int(r.get('payload_bytes_scanned', 0)) for r in rows)
    total_tensor_scanned = sum(int(r.get('tensor_payload_bytes_scanned', 0)) for r in rows)
    tensors_expected = sum(int(r.get('tensor_count_expected', 0)) for r in rows)
    tensors_completed = sum(int(r.get('tensor_count_completed', 0)) for r in rows)
    unassigned = sum(int(r.get('unassigned_payload_bytes', 0)) for r in rows)
    unknown = sum(int(r.get('HDS適合不能tensor数', 0)) for r in rows)
    nonpass = [r.get('source', {}).get('shard') for r in rows if not r.get('PASS')]
    partial = [r.get('source', {}).get('shard') for r in rows if r.get('partial')]
    gap_shards = [r.get('source', {}).get('shard') for r in rows if r.get('gaps')]
    overlap_shards = [r.get('source', {}).get('shard') for r in rows if r.get('overlaps')]
    size_mismatch = [r.get('source', {}).get('shard') for r in rows if int(r.get('trailing_or_size_mismatch_bytes', 0)) != 0]

    expected_from_header = int(hp.get('total_tensor_payload_bytes_from_headers', -1))
    expected_tensors_from_header = int(hp.get('tensor_count_from_headers', -1))
    address_closed = bool(hp.get('PASS_住所全数固定'))

    checks = {
        'shard_audit_files_96': len(rows) == EXPECTED_SHARDS,
        'unique_shards_96': len(unique) == EXPECTED_SHARDS and not duplicate and None not in unique,
        'all_shard_PASS': not nonpass,
        'no_partial': not partial,
        'no_gaps': not gap_shards,
        'no_overlaps': not overlap_shards,
        'no_size_mismatch': not size_mismatch,
        'payload_expected_matches_official_index': total_expected == EXPECTED_PAYLOAD == expected_from_header,
        'payload_scanned_all_bytes': total_scanned == EXPECTED_PAYLOAD,
        'tensor_payload_scanned_all_bytes': total_tensor_scanned == EXPECTED_PAYLOAD,
        'tensor_count_matches_index': tensors_expected == EXPECTED_TENSORS == expected_tensors_from_header,
        'tensor_count_completed_all': tensors_completed == EXPECTED_TENSORS,
        'unassigned_payload_zero': unassigned == 0,
        'HDS適合不能_zero': unknown == 0,
        'address_probe_closed': address_closed,
    }
    passed = all(checks.values())
    report = {
        'kind': 'K3 weight全payload HDS日本語コンパイル全数監査',
        'expected': {'shards': EXPECTED_SHARDS, 'tensors': EXPECTED_TENSORS, 'payload_bytes': EXPECTED_PAYLOAD},
        'observed': {
            'audit_files': len(rows), 'unique_shards': len(unique),
            'payload_bytes_expected_sum': total_expected,
            'payload_bytes_scanned_sum': total_scanned,
            'tensor_payload_bytes_scanned_sum': total_tensor_scanned,
            'tensor_count_expected_sum': tensors_expected,
            'tensor_count_completed_sum': tensors_completed,
            'unassigned_payload_bytes': unassigned,
            'HDS適合不能tensor数': unknown,
        },
        'failures': {
            'duplicate_shards': duplicate, 'nonpass_shards': nonpass, 'partial_shards': partial,
            'gap_shards': gap_shards, 'overlap_shards': overlap_shards, 'size_mismatch_shards': size_mismatch,
        },
        'checks': checks,
        'unprocessed_weight_bytes': EXPECTED_PAYLOAD - total_tensor_scanned,
        'unprocessed_weight_tensors': EXPECTED_TENSORS - tensors_completed,
        'PASS_WEIGHT_FULL_COMPILE': passed,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if passed else 2


if __name__ == '__main__':
    raise SystemExit(main())
