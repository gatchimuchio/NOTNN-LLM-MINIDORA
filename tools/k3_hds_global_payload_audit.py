#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
from pathlib import Path

EXPECTED_SHARDS = 96
EXPECTED_PAYLOAD = 1560860324864
EXPECTED_TENSORS = 497220
EXPECTED_WEIGHT_FILE_BYTES = 1560936091448
MOTHER = Path('解析/K3全公開データコンパイル/v6/mother-set/public-artifact-inventory.json')
NONWEIGHT = Path('解析/K3全公開データコンパイル/v6/nonweight-full/nonweight-full-audit.json')


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--audit-dir',type=Path,required=True)
    ap.add_argument('--header-probe',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()

    hp=json.loads(args.header_probe.read_text(encoding='utf-8'))
    mother=json.loads(MOTHER.read_text(encoding='utf-8'))
    nonweight=json.loads(NONWEIGHT.read_text(encoding='utf-8'))
    audit_files=sorted(args.audit_dir.rglob('*.audit.json'))
    rows=[json.loads(p.read_text(encoding='utf-8')) for p in audit_files]

    shard_names=[r.get('source',{}).get('shard') for r in rows]
    unique=sorted(x for x in set(shard_names) if x is not None)
    duplicate=sorted({x for x in shard_names if x is not None and shard_names.count(x)>1})

    official_weight_rows={
        r['path']:r for r in mother['files']
        if r['path'].startswith('model-') and r['path'].endswith('.safetensors')
    }
    observed_by_shard={r.get('source',{}).get('shard'):r for r in rows if r.get('source',{}).get('shard')}
    official_shards=sorted(official_weight_rows)
    missing_official_shards=sorted(set(official_shards)-set(observed_by_shard))
    unexpected_shards=sorted(set(observed_by_shard)-set(official_shards))
    identity_mismatch=[]
    per_file_size_mismatch=[]
    for shard in sorted(set(official_shards)&set(observed_by_shard)):
        meta=official_weight_rows[shard]
        aud=observed_by_shard[shard]
        expected_sha=None
        lfs=meta.get('lfs')
        if isinstance(lfs,dict):
            expected_sha=lfs.get('sha256') or lfs.get('oid')
            if isinstance(expected_sha,str) and expected_sha.startswith('sha256:'):
                expected_sha=expected_sha.split(':',1)[1]
        actual_sha=aud.get('file_sha256_if_complete')
        if expected_sha and actual_sha!=expected_sha:
            identity_mismatch.append({'shard':shard,'official_lfs_sha256':expected_sha,'observed_sha256':actual_sha})
        expected_size=int(meta.get('size') or 0)
        actual_size=int(aud.get('remote_total_bytes') or 0)
        if expected_size!=actual_size:
            per_file_size_mismatch.append({'shard':shard,'official_size':expected_size,'observed_remote_size':actual_size})

    total_expected=sum(int(r.get('payload_bytes_expected',0)) for r in rows)
    total_scanned=sum(int(r.get('payload_bytes_scanned',0)) for r in rows)
    total_tensor_scanned=sum(int(r.get('tensor_payload_bytes_scanned',0)) for r in rows)
    total_header_scanned=sum(int(r.get('header_bytes_scanned',0)) for r in rows)
    total_file_scanned=total_header_scanned+total_scanned
    total_remote_file=sum(int(r.get('remote_total_bytes',0)) for r in rows)
    tensors_expected=sum(int(r.get('tensor_count_expected',0)) for r in rows)
    tensors_completed=sum(int(r.get('tensor_count_completed',0)) for r in rows)
    unassigned=sum(int(r.get('unassigned_payload_bytes',0)) for r in rows)
    unknown=sum(int(r.get('HDS適合不能tensor数',0)) for r in rows)
    nonpass=[r.get('source',{}).get('shard') for r in rows if not r.get('PASS')]
    partial=[r.get('source',{}).get('shard') for r in rows if r.get('partial')]
    gap_shards=[r.get('source',{}).get('shard') for r in rows if r.get('gaps')]
    overlap_shards=[r.get('source',{}).get('shard') for r in rows if r.get('overlaps')]
    size_mismatch=[r.get('source',{}).get('shard') for r in rows if int(r.get('trailing_or_size_mismatch_bytes',0))!=0]
    missing_file_hash=[r.get('source',{}).get('shard') for r in rows if not r.get('file_sha256_if_complete')]

    expected_from_header=int(hp.get('total_tensor_payload_bytes_from_headers',-1))
    expected_file_from_header=int(hp.get('total_safetensors_file_bytes',-1))
    expected_header_from_probe=int(hp.get('total_header_bytes',-1))
    expected_tensors_from_header=int(hp.get('tensor_count_from_headers',-1))
    address_closed=bool(hp.get('PASS_住所全数固定'))

    weight_checks={
        'shard_audit_files_96':len(rows)==EXPECTED_SHARDS,
        'unique_shards_96':len(unique)==EXPECTED_SHARDS and not duplicate and None not in shard_names,
        'official_weight_mother_set_96':len(official_weight_rows)==EXPECTED_SHARDS,
        'no_missing_official_shards':not missing_official_shards,
        'no_unexpected_shards':not unexpected_shards,
        'official_LFS_SHA256_match_96':not identity_mismatch and len(observed_by_shard)==EXPECTED_SHARDS,
        'official_per_file_size_match_96':not per_file_size_mismatch and len(observed_by_shard)==EXPECTED_SHARDS,
        'all_shard_PASS':not nonpass,
        'no_partial':not partial,
        'no_gaps':not gap_shards,
        'no_overlaps':not overlap_shards,
        'no_size_mismatch':not size_mismatch,
        'full_file_sha256_present_96':not missing_file_hash and len(rows)==EXPECTED_SHARDS,
        'payload_expected_matches_official_index':total_expected==EXPECTED_PAYLOAD==expected_from_header,
        'payload_scanned_all_bytes':total_scanned==EXPECTED_PAYLOAD,
        'tensor_payload_scanned_all_bytes':total_tensor_scanned==EXPECTED_PAYLOAD,
        'header_bytes_scanned_all':total_header_scanned==expected_header_from_probe,
        'remote_file_bytes_match_mother_set':total_remote_file==EXPECTED_WEIGHT_FILE_BYTES==expected_file_from_header==int(mother['weight_file_size']),
        'all_weight_file_bytes_read':total_file_scanned==EXPECTED_WEIGHT_FILE_BYTES,
        'tensor_count_matches_index':tensors_expected==EXPECTED_TENSORS==expected_tensors_from_header,
        'tensor_count_completed_all':tensors_completed==EXPECTED_TENSORS,
        'unassigned_payload_zero':unassigned==0,
        'HDS適合不能_zero':unknown==0,
        'address_probe_closed':address_closed,
    }
    weight_pass=all(weight_checks.values())

    nonweight_bytes=int(nonweight.get('processed_nonweight_bytes',0))
    expected_public_bytes=int(mother['total_file_size'])
    processed_public_bytes=total_file_scanned+nonweight_bytes
    processed_public_files=len(unique)+int(nonweight.get('processed_nonweight_files',0))
    public_checks={
        'mother_set_files_114':int(mother['file_count'])==114,
        'mother_set_weight_96':int(mother['weight_shard_count'])==96,
        'mother_set_nonweight_18':int(mother['nonweight_file_count'])==18,
        'weight_full_PASS':weight_pass,
        'nonweight_full_PASS':bool(nonweight.get('PASS_NONWEIGHT_FULL_COMPILE')),
        'all_114_files_processed':processed_public_files==int(mother['file_count'])==114,
        'all_public_file_bytes_read':processed_public_bytes==expected_public_bytes,
        'nonweight_unprocessed_bytes_zero':int(nonweight.get('unprocessed_nonweight_bytes',-1))==0,
        'nonweight_HDS適合不能_zero':int(nonweight.get('HDS適合不能artifact数',-1))==0,
    }
    public_pass=all(public_checks.values())

    report={
        'kind':'K3公式公開母集合 全114ファイル・全byte・公式identity HDS日本語コンパイル全数監査',
        'mother_set':{
            'repo':mother['repo'],'revision':mother['revision'],'manifest_sha256':mother['manifest_sha256'],
            'files':mother['file_count'],'weight_shards':mother['weight_shard_count'],'nonweight_files':mother['nonweight_file_count'],
            'all_public_file_bytes':expected_public_bytes,
        },
        'weight':{
            'expected':{'shards':EXPECTED_SHARDS,'tensors':EXPECTED_TENSORS,'tensor_payload_bytes':EXPECTED_PAYLOAD,'weight_file_bytes_including_headers':EXPECTED_WEIGHT_FILE_BYTES},
            'observed':{'audit_files':len(rows),'unique_shards':len(unique),'remote_file_bytes_sum':total_remote_file,'header_bytes_scanned_sum':total_header_scanned,'payload_bytes_scanned_sum':total_scanned,'all_file_bytes_scanned_sum':total_file_scanned,'tensor_payload_bytes_scanned_sum':total_tensor_scanned,'tensor_count_completed_sum':tensors_completed,'unassigned_payload_bytes':unassigned,'HDS適合不能tensor数':unknown},
            'identity':{'missing_official_shards':missing_official_shards,'unexpected_shards':unexpected_shards,'official_LFS_SHA256_mismatch':identity_mismatch,'official_per_file_size_mismatch':per_file_size_mismatch},
            'failures':{'duplicate_shards':duplicate,'nonpass_shards':nonpass,'partial_shards':partial,'gap_shards':gap_shards,'overlap_shards':overlap_shards,'size_mismatch_shards':size_mismatch,'missing_complete_file_sha256_shards':missing_file_hash},
            'checks':weight_checks,
            'unprocessed_weight_file_bytes':EXPECTED_WEIGHT_FILE_BYTES-total_file_scanned,
            'unprocessed_weight_payload_bytes':EXPECTED_PAYLOAD-total_tensor_scanned,
            'unprocessed_weight_tensors':EXPECTED_TENSORS-tensors_completed,
            'PASS_WEIGHT_FULL_COMPILE':weight_pass,
        },
        'nonweight':{
            'processed_files':nonweight.get('processed_nonweight_files'),'processed_bytes':nonweight_bytes,
            'unprocessed_files':nonweight.get('unprocessed_nonweight_files'),'unprocessed_bytes':nonweight.get('unprocessed_nonweight_bytes'),
            'HDS適合不能artifact数':nonweight.get('HDS適合不能artifact数'),'structure_records':nonweight.get('structure_records'),
            'PASS_NONWEIGHT_FULL_COMPILE':nonweight.get('PASS_NONWEIGHT_FULL_COMPILE'),
        },
        'public_total':{
            'processed_files':processed_public_files,'expected_files':int(mother['file_count']),
            'processed_bytes':processed_public_bytes,'expected_bytes':expected_public_bytes,
            'unprocessed_items':int(mother['file_count'])-processed_public_files,
            'unprocessed_bytes':expected_public_bytes-processed_public_bytes,
            'checks':public_checks,
            'PASS_PUBLIC_FULL_COMPILE':public_pass,
        },
    }
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0 if public_pass else 2

if __name__=='__main__':
    raise SystemExit(main())
