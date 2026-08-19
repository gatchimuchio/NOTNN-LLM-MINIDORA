#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K3公式公開データ HDS日本語全数コンパイル v6 最終統合監査・正本生成。

完了条件は狭義HFだけではなく、以下の固定母集合について同時に閉じること:
1. moonshotai/Kimi-K3 pinned HF revision: 114 files
   - 96 safetensors: 全file byte実読、全497,220 tensor、公式LFS SHA256一致
   - 18 nonweight: 全file byte実読・HDS日本語意味構文
2. MoonshotAI/Kimi-K3 pinned GitHub commit: 4 files
3. README直結の公式K3 Tech Blog取得時点HTML + 直結Kimi/Moonshot媒体

未処理item/byte、HDS適合不能、identity mismatch、corpus欠落のいずれかが1つでもあればFAIL。
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, Dict, Iterable, List

HF_REPO = "moonshotai/Kimi-K3"
HF_REV = "c5d1dd4c428bd1ce8b88c5044f3b6ccde9e3b721"
EXPECTED_HF_FILES = 114
EXPECTED_WEIGHT_SHARDS = 96
EXPECTED_HF_NONWEIGHT = 18
EXPECTED_TENSORS = 497_220
EXPECTED_WEIGHT_PAYLOAD = 1_560_860_324_864
EXPECTED_WEIGHT_FILE_BYTES = 1_560_936_091_448
EXPECTED_HF_TOTAL_BYTES = 1_560_998_983_621


def load(p: Path) -> Any:
    return json.loads(p.read_text(encoding="utf-8"))


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def find_one(root: Path, pattern: str) -> Path:
    xs = list(root.rglob(pattern))
    if len(xs) != 1:
        raise RuntimeError(f"expected exactly one {pattern} under {root}, got {len(xs)}: {xs[:10]}")
    return xs[0]


def identity_map(identity: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    if identity.get("repo") != HF_REPO or identity.get("repo_sha") != HF_REV:
        raise RuntimeError("HF official identity inventory is not the pinned K3 revision")
    out = {}
    for r in identity.get("files", []):
        name = r.get("rfilename")
        if name:
            out[name] = r
    return out


def inspect_weight_semantic(path: Path, expected_shard: str, expected_tensors: int) -> Dict[str, Any]:
    tensor_count = 0
    hds_bad = 0
    source_bad = 0
    payload_sum = 0
    seen_names = set()
    record_count = 0
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            record_count += 1
            r = json.loads(line)
            if r.get("kind") != "tensor_HDS日本語意味構文":
                continue
            tensor_count += 1
            src = r.get("source", {})
            if src.get("repo") != HF_REPO or src.get("revision") != HF_REV or src.get("shard") != expected_shard:
                source_bad += 1
            name = src.get("tensor")
            if not name or name in seen_names:
                source_bad += 1
            if name:
                seen_names.add(name)
            hds = r.get("HDS", {})
            if hds.get("status") != "HDS適合" or not hds.get("原理族"):
                hds_bad += 1
            jp = r.get("日本語意味構文", {})
            if not all(k in jp for k in ("対象", "成立関係", "条件", "作用量", "崩壊条件", "未確定")):
                hds_bad += 1
            obs = r.get("observed", {})
            payload_sum += int(obs.get("payload_bytes", 0))
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "records": record_count,
        "tensor_records": tensor_count,
        "unique_tensor_names": len(seen_names),
        "tensor_payload_bytes_from_semantic": payload_sum,
        "HDS不適合record": hds_bad,
        "source不整合record": source_bad,
        "PASS": tensor_count == expected_tensors and len(seen_names) == expected_tensors and hds_bad == 0 and source_bad == 0,
    }


def inspect_jsonl_gz(path: Path) -> Dict[str, Any]:
    records = 0
    parse_errors = 0
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            records += 1
            try:
                json.loads(line)
            except Exception:
                parse_errors += 1
    return {"path": str(path), "sha256": sha256_file(path), "records": records, "parse_errors": parse_errors, "PASS": records > 0 and parse_errors == 0}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--weight-audits", type=Path, required=True)
    ap.add_argument("--weight-semantics", type=Path, required=True)
    ap.add_argument("--hf-identity", type=Path, required=True)
    ap.add_argument("--hf-mother", type=Path, required=True)
    ap.add_argument("--nonweight-audit", type=Path, required=True)
    ap.add_argument("--nonweight-semantic", type=Path, required=True)
    ap.add_argument("--docs-audit", type=Path, required=True)
    ap.add_argument("--docs-mother", type=Path, required=True)
    ap.add_argument("--docs-semantic", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    a = ap.parse_args()

    out = a.output_dir
    out.mkdir(parents=True, exist_ok=True)

    identity = load(a.hf_identity)
    ids = identity_map(identity)
    hf_mother = load(a.hf_mother)
    nonweight = load(a.nonweight_audit)
    docs = load(a.docs_audit)
    docs_mother = load(a.docs_mother)

    if hf_mother.get("repo") != HF_REPO or hf_mother.get("revision") != HF_REV:
        raise RuntimeError("HF mother set revision mismatch")

    audit_paths = sorted(a.weight_audits.rglob("*.audit.json"))
    semantic_paths = sorted(a.weight_semantics.rglob("*.jsonl.gz"))
    audits_by_shard: Dict[str, Dict[str, Any]] = {}
    audit_file_by_shard: Dict[str, Path] = {}
    for p in audit_paths:
        r = load(p)
        shard = r.get("source", {}).get("shard")
        if not shard or shard in audits_by_shard:
            raise RuntimeError(f"invalid/duplicate shard audit: {p} -> {shard}")
        audits_by_shard[shard] = r
        audit_file_by_shard[shard] = p

    semantic_by_shard: Dict[str, Path] = {}
    for p in semantic_paths:
        # filenames are shard-001.jsonl.gz etc.; source is confirmed during scan.
        stem = p.name
        import re
        m = re.search(r"shard-(\d{3})\.jsonl\.gz$", stem)
        if not m:
            continue
        idx = int(m.group(1))
        shard = f"model-{idx:05d}-of-000096.safetensors"
        if shard in semantic_by_shard:
            raise RuntimeError(f"duplicate semantic shard {shard}")
        semantic_by_shard[shard] = p

    official_weight_names = sorted(
        n for n, r in ids.items()
        if n.startswith("model-") and n.endswith(".safetensors")
    )

    shard_reports = []
    total_file_bytes = 0
    total_payload = 0
    total_tensors = 0
    semantic_tensor_total = 0
    semantic_payload_total = 0
    identity_mismatches = []
    audit_failures = []
    semantic_failures = []

    for shard in official_weight_names:
        meta = ids[shard]
        lfs = meta.get("lfs") or {}
        official_sha = lfs.get("sha256")
        official_size = int(meta.get("size") or 0)
        aud = audits_by_shard.get(shard)
        sem_path = semantic_by_shard.get(shard)
        if aud is None or sem_path is None:
            shard_reports.append({"shard": shard, "missing_audit": aud is None, "missing_semantic": sem_path is None, "PASS": False})
            continue

        observed_sha = aud.get("file_sha256_if_complete")
        observed_size = int(aud.get("remote_total_bytes") or 0)
        payload = int(aud.get("payload_bytes_scanned") or 0)
        tensors = int(aud.get("tensor_count_completed") or 0)
        identity_ok = bool(official_sha) and official_sha == observed_sha and official_size == observed_size
        if not identity_ok:
            identity_mismatches.append({
                "shard": shard,
                "official_sha256": official_sha,
                "observed_sha256": observed_sha,
                "official_size": official_size,
                "observed_size": observed_size,
            })

        audit_ok = (
            aud.get("PASS") is True
            and aud.get("coverage", {}).get("全byte実読") is True
            and aud.get("source", {}).get("repo") == HF_REPO
            and aud.get("source", {}).get("revision") == HF_REV
            and int(aud.get("unassigned_payload_bytes") or 0) == 0
            and int(aud.get("HDS適合不能tensor数") or 0) == 0
            and not aud.get("gaps") and not aud.get("overlaps")
            and int(aud.get("trailing_or_size_mismatch_bytes") or 0) == 0
        )
        if not audit_ok:
            audit_failures.append(shard)

        sem = inspect_weight_semantic(sem_path, shard, tensors)
        if sem["tensor_payload_bytes_from_semantic"] != int(aud.get("tensor_payload_bytes_scanned") or 0):
            sem["PASS"] = False
            sem["payload_vs_audit_mismatch"] = True
        if not sem["PASS"]:
            semantic_failures.append(shard)

        total_file_bytes += observed_size
        total_payload += payload
        total_tensors += tensors
        semantic_tensor_total += sem["tensor_records"]
        semantic_payload_total += sem["tensor_payload_bytes_from_semantic"]
        shard_reports.append({
            "shard": shard,
            "official_size": official_size,
            "official_LFS_SHA256": official_sha,
            "observed_full_file_SHA256": observed_sha,
            "identity_match": identity_ok,
            "audit_PASS": audit_ok,
            "semantic": sem,
            "PASS": identity_ok and audit_ok and sem["PASS"],
        })

    nw_sem = inspect_jsonl_gz(a.nonweight_semantic)
    docs_sem = inspect_jsonl_gz(a.docs_semantic)

    hf_checks = {
        "pinned_revision": identity.get("repo_sha") == HF_REV == hf_mother.get("revision"),
        "hf_mother_files_114": int(hf_mother.get("file_count", -1)) == EXPECTED_HF_FILES,
        "weight_shards_96": len(official_weight_names) == EXPECTED_WEIGHT_SHARDS == len(audits_by_shard) == len(semantic_by_shard),
        "official_identity_present_96": all((ids[n].get("lfs") or {}).get("sha256") for n in official_weight_names),
        "official_LFS_SHA256_match_all": len(identity_mismatches) == 0,
        "all_weight_audits_PASS": len(audit_failures) == 0 and len(shard_reports) == EXPECTED_WEIGHT_SHARDS and all(x.get("audit_PASS") for x in shard_reports),
        "all_weight_semantics_PASS": len(semantic_failures) == 0 and len(shard_reports) == EXPECTED_WEIGHT_SHARDS and all((x.get("semantic") or {}).get("PASS") for x in shard_reports),
        "weight_file_bytes_exact": total_file_bytes == EXPECTED_WEIGHT_FILE_BYTES == int(hf_mother.get("weight_file_size", -1)),
        "weight_payload_bytes_exact": total_payload == EXPECTED_WEIGHT_PAYLOAD == semantic_payload_total,
        "tensor_count_exact": total_tensors == EXPECTED_TENSORS == semantic_tensor_total,
        "nonweight_18_PASS": bool(nonweight.get("PASS_NONWEIGHT_FULL_COMPILE")) and int(nonweight.get("processed_nonweight_files", -1)) == EXPECTED_HF_NONWEIGHT,
        "nonweight_bytes_exact": int(nonweight.get("processed_nonweight_bytes", -1)) == int(hf_mother.get("nonweight_file_size", -2)) == 62_892_173,
        "nonweight_unprocessed_zero": int(nonweight.get("unprocessed_nonweight_bytes", -1)) == 0 and not nonweight.get("unprocessed_nonweight_files"),
        "nonweight_HDS_gap_zero": int(nonweight.get("HDS適合不能artifact数", -1)) == 0,
        "nonweight_semantic_corpus_valid": nw_sem["PASS"],
        "hf_total_bytes_exact": total_file_bytes + int(nonweight.get("processed_nonweight_bytes", 0)) == EXPECTED_HF_TOTAL_BYTES == int(hf_mother.get("total_file_size", -1)),
    }
    hf_pass = all(hf_checks.values())

    docs_expected_items = int(docs.get("expected_items", -1))
    docs_processed_items = int(docs.get("processed_items", -2))
    docs_expected_bytes = int(docs.get("expected_bytes_from_observed_manifest", -1))
    docs_processed_bytes = int(docs.get("processed_bytes", -2))
    docs_checks = {
        "official_docs_PASS": bool(docs.get("PASS_OFFICIAL_DOCS_FULL_COMPILE")),
        "github_4_of_4": int(docs.get("github", {}).get("expected_files", -1)) == 4 == int(docs.get("github", {}).get("processed_files", -2)),
        "docs_items_all": docs_expected_items == docs_processed_items and docs_expected_items > 0,
        "docs_bytes_all": docs_expected_bytes == docs_processed_bytes and docs_expected_bytes > 0,
        "docs_unprocessed_zero": int(docs.get("unprocessed_items", -1)) == 0 and int(docs.get("unprocessed_bytes", -1)) == 0,
        "docs_HDS_gap_zero": int(docs.get("HDS適合不能", -1)) == 0,
        "docs_semantic_corpus_valid": docs_sem["PASS"],
    }
    docs_pass = all(docs_checks.values())

    public_expected_items = EXPECTED_HF_FILES + docs_expected_items
    public_processed_items = (EXPECTED_WEIGHT_SHARDS + int(nonweight.get("processed_nonweight_files", 0))) + docs_processed_items
    public_expected_bytes = EXPECTED_HF_TOTAL_BYTES + docs_expected_bytes
    public_processed_bytes = total_file_bytes + int(nonweight.get("processed_nonweight_bytes", 0)) + docs_processed_bytes

    final_checks = {
        "HF_FULL_PASS": hf_pass,
        "OFFICIAL_DOCS_FULL_PASS": docs_pass,
        "public_items_all": public_processed_items == public_expected_items,
        "public_bytes_all": public_processed_bytes == public_expected_bytes,
        "unprocessed_items_zero": public_expected_items - public_processed_items == 0,
        "unprocessed_bytes_zero": public_expected_bytes - public_processed_bytes == 0,
        "HDS_gap_zero": len(audit_failures) == 0 and len(semantic_failures) == 0 and int(nonweight.get("HDS適合不能artifact数", -1)) == 0 and int(docs.get("HDS適合不能", -1)) == 0,
    }
    final_pass = all(final_checks.values())

    report = {
        "正本名": "K3_HDS日本語全公開データコンパイル_v6.0",
        "対象": {
            "HF": {"repo": HF_REPO, "revision": HF_REV, "files": EXPECTED_HF_FILES},
            "公式資料": docs_mother.get("sources"),
            "重複方針": "異なる公式公開面に同一/類似artifactが存在しても、出典provenanceを失わないため物理source itemとして別個に保持する。",
        },
        "HF": {
            "checks": hf_checks,
            "PASS": hf_pass,
            "weight": {
                "shards": len(shard_reports),
                "file_bytes": total_file_bytes,
                "payload_bytes": total_payload,
                "tensors": total_tensors,
                "semantic_tensor_records": semantic_tensor_total,
                "semantic_payload_bytes": semantic_payload_total,
                "identity_mismatches": identity_mismatches,
                "audit_failures": audit_failures,
                "semantic_failures": semantic_failures,
            },
            "nonweight": nonweight,
            "nonweight_semantic_integrity": nw_sem,
        },
        "公式GitHub_TechBlog": {
            "checks": docs_checks,
            "PASS": docs_pass,
            "audit": docs,
            "semantic_integrity": docs_sem,
        },
        "全公開母集合": {
            "expected_items": public_expected_items,
            "processed_items": public_processed_items,
            "expected_bytes": public_expected_bytes,
            "processed_bytes": public_processed_bytes,
            "unprocessed_items": public_expected_items - public_processed_items,
            "unprocessed_bytes": public_expected_bytes - public_processed_bytes,
            "checks": final_checks,
            "PASS_PUBLIC_FULL_COMPILE": final_pass,
        },
        "weight_shards": shard_reports,
    }

    report_path = out / "00_最終全数監査.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    canonical = {
        "name": report["正本名"],
        "HF_repo": HF_REPO,
        "HF_revision": HF_REV,
        "HF_manifest_sha256": hf_mother.get("manifest_sha256"),
        "HF_identity_inventory_sha256": sha256_file(a.hf_identity),
        "official_docs_mother_sha256": sha256_file(a.docs_mother),
        "weight_run_id": 32261212025,
        "weight_run_head_sha": "fca926d53152eb93aa17b667c8f9834fee886e32",
        "public_expected_items": public_expected_items,
        "public_expected_bytes": public_expected_bytes,
        "tensor_count": EXPECTED_TENSORS,
        "completion_rule": "PASS only when unprocessed_items=0 AND unprocessed_bytes=0 AND HDS_gap=0 AND all 96 official LFS SHA256 identities match",
        "PASS": final_pass,
    }
    (out / "01_母集合正本.json").write_text(json.dumps(canonical, ensure_ascii=False, indent=2), encoding="utf-8")

    index = {
        "weight_semantic_files": [
            {"shard": x["shard"], "semantic_sha256": (x.get("semantic") or {}).get("sha256"), "tensor_records": (x.get("semantic") or {}).get("tensor_records")}
            for x in shard_reports
        ],
        "nonweight_semantic": nw_sem,
        "official_docs_semantic": docs_sem,
    }
    (out / "02_日本語意味構文索引.json").write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")

    readme = f"""# K3 HDS日本語全公開データコンパイル v6.0

## 判定

**{'PASS' if final_pass else 'FAIL'}**

- 公開source item: {public_processed_items:,} / {public_expected_items:,}
- 公開source byte: {public_processed_bytes:,} / {public_expected_bytes:,}
- weight shard: {len(shard_reports)} / 96
- tensor: {total_tensors:,} / {EXPECTED_TENSORS:,}
- tensor日本語意味構文: {semantic_tensor_total:,} / {EXPECTED_TENSORS:,}
- 未処理item: {public_expected_items - public_processed_items}
- 未処理byte: {public_expected_bytes - public_processed_bytes}
- weight identity mismatch: {len(identity_mismatches)}
- weight audit failure: {len(audit_failures)}
- weight semantic failure: {len(semantic_failures)}

## 正本境界

HF `{HF_REPO}` revision `{HF_REV}` の114 fileに加え、公式GitHub pinned commitとREADME直結のK3 Tech Blog/直結公式媒体を出典別に保持した。

weightは1.56TBを保存したのではなく、各shardをRange streamingで全byte実読し、tensor単位の実payload SHA・数値状態・HDS成立関係・日本語意味構文・provenanceだけを成果物として残した。

完了条件は `unprocessed_items=0 && unprocessed_bytes=0 && HDS_gap=0 && 96 shard official LFS SHA256 match`。
"""
    (out / "README.md").write_text(readme, encoding="utf-8")

    # Canonical input ledgers and semantic corpora are copied into final package.
    shutil.copy2(a.hf_identity, out / "03_HF公式identity台帳.json")
    shutil.copy2(a.hf_mother, out / "04_HF母集合.json")
    shutil.copy2(a.nonweight_audit, out / "05_HF非weight全数監査.json")
    shutil.copy2(a.nonweight_semantic, out / "06_HF非weight_HDS日本語意味構文.jsonl.gz")
    shutil.copy2(a.docs_audit, out / "07_公式GitHub_TechBlog全数監査.json")
    shutil.copy2(a.docs_mother, out / "08_公式GitHub_TechBlog母集合.json")
    shutil.copy2(a.docs_semantic, out / "09_公式GitHub_TechBlog_HDS日本語意味構文.jsonl.gz")

    weight_dir = out / "10_weight_HDS日本語意味構文"
    weight_dir.mkdir(exist_ok=True)
    for shard, p in sorted(semantic_by_shard.items()):
        idx = int(shard.split('-')[1])
        shutil.copy2(p, weight_dir / f"shard-{idx:03d}.jsonl.gz")

    aud_dir = out / "11_weight_shard監査"
    aud_dir.mkdir(exist_ok=True)
    for shard, p in sorted(audit_file_by_shard.items()):
        idx = int(shard.split('-')[1])
        shutil.copy2(p, aud_dir / f"shard-{idx:03d}.audit.json")

    manifest = []
    for p in sorted(x for x in out.rglob("*") if x.is_file() and x.name != "12_成果物SHA256.json"):
        manifest.append({"path": str(p.relative_to(out)), "bytes": p.stat().st_size, "sha256": sha256_file(p)})
    (out / "12_成果物SHA256.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "PASS_PUBLIC_FULL_COMPILE": final_pass,
        "expected_items": public_expected_items,
        "processed_items": public_processed_items,
        "expected_bytes": public_expected_bytes,
        "processed_bytes": public_processed_bytes,
        "unprocessed_items": public_expected_items - public_processed_items,
        "unprocessed_bytes": public_expected_bytes - public_processed_bytes,
        "weight_tensors": total_tensors,
        "semantic_tensor_records": semantic_tensor_total,
        "identity_mismatches": len(identity_mismatches),
        "audit_failures": len(audit_failures),
        "semantic_failures": len(semantic_failures),
    }, ensure_ascii=False, indent=2))
    return 0 if final_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
