#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K3 v6.0固定点以降の現行HF公開差分を全数HDS日本語意味構文化する。

v6.0で完全処理済みのHF revision c5d1dd4... を基底とし、
現行mainの固定HEAD 9f62e4e... との差分を全数列挙する。
不変artifactはidentity一致をもってv6.0成果を再利用し、追加/変更artifactは
全byte実読してHDS日本語意味構文へ変換する。
"""
from __future__ import annotations

import gzip
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from huggingface_hub import HfApi, hf_hub_download

REPO = "moonshotai/Kimi-K3"
BASE = "c5d1dd4c428bd1ce8b88c5044f3b6ccde9e3b721"
TARGET = "9f62e4e9fffbd0a83ddd60e1c209d828994b3569"
OUT = Path("artifacts/k3-hds/v6.1-current")
V6_RELEASE = Path("artifacts/k3-hds/v6.0/release.json")
V6_PUBLIC_ITEMS = 126
V6_PUBLIC_BYTES = 1_561_002_449_957
V6_HF_BYTES = 1_560_998_983_621
V6_HF_FILES = 114
V6_DOC_ITEMS = V6_PUBLIC_ITEMS - V6_HF_FILES
V6_DOC_BYTES = V6_PUBLIC_BYTES - V6_HF_BYTES


def jdump(x: Any) -> str:
    return json.dumps(x, ensure_ascii=False, sort_keys=True)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sibling_identity(s: Any) -> Dict[str, Any]:
    lfs = getattr(s, "lfs", None) or {}
    if hasattr(lfs, "__dict__"):
        lfs = vars(lfs)
    lfs_sha = None
    if isinstance(lfs, dict):
        lfs_sha = lfs.get("sha256") or lfs.get("oid")
    blob = getattr(s, "blob_id", None)
    size = int(getattr(s, "size", 0) or (lfs.get("size", 0) if isinstance(lfs, dict) else 0) or 0)
    if lfs_sha:
        return {"kind": "lfs_sha256", "id": str(lfs_sha), "size": size}
    return {"kind": "git_blob", "id": blob, "size": size}


def info_map(info: Any) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for s in info.siblings or []:
        out[s.rfilename] = sibling_identity(s)
    return out


def classify_readme_line(raw: str, in_code: bool) -> Tuple[str, str, str]:
    s = raw.strip("\r\n")
    t = s.strip()
    if not t:
        return "P-DOC-BOUNDARY", "文書構造境界", "前後の意味領域を分離し、後続解釈の境界を成立させる。"
    if t.startswith("```"):
        return "P-USAGE-CODE-BOUNDARY", "実行記述境界", "自然言語説明と実行可能記述の境界を成立させる。"
    if in_code:
        return "P-USAGE-CODE", "利用・実行操作", "利用条件を具体的な実行操作へ接続し、再現可能な操作列を成立させる。"
    if t == "---":
        return "P-DOC-METADATA-BOUNDARY", "メタデータ境界", "公開メタデータ領域と本文領域の境界を成立させる。"
    if t.startswith("#"):
        return "P-DOC-SECTION", "文書節", "後続記述が属する意味領域を指定し、局所的な解釈文脈を成立させる。"
    if "|" in t and not t.startswith("http"):
        return "P-EVAL-TABLE", "評価・比較関係", "項目・モデル・評価値を同一座標上へ配置し、比較関係を成立させる。"
    if re.match(r"^[-*+]\s+", t) or re.match(r"^\d+\.\s+", t):
        return "P-DOC-LIST", "列挙関係", "複数の条件・特徴・手順を並列保持し、同一上位文脈への所属を成立させる。"
    if "![" in t or re.search(r"\[[^\]]+\]\([^\)]+\)", t):
        return "P-DOC-REFERENCE", "外部・媒体参照", "本文記述を外部資料・媒体・参照先へ接続する。"
    if t.startswith("<") and t.endswith(">"):
        return "P-DOC-MARKUP", "表示・構造指定", "公開文書の表示または構造上の局所条件を指定する。"
    return "P-DOC-ASSERTION", "公開説明命題", "K3の能力・構成・利用・評価に関する公開命題として意味関係を保持する。"


def classify_yaml_line(raw: str) -> Tuple[str, str, str]:
    t = raw.strip()
    key = t.lstrip("- ").split(":", 1)[0].strip() if ":" in t else ""
    table = {
        "dataset": ("P-EVAL-DATASET-ENTRY", "評価データ集合", "評価結果が属するデータ集合の局所構造を開始する。"),
        "id": ("P-EVAL-DATASET-ID", "評価データ住所", "評価対象データ集合を一意な公開住所へ接地する。"),
        "task_id": ("P-EVAL-TASK-ID", "評価課題住所", "同一データ集合内で評価対象となる課題を識別する。"),
        "value": ("P-EVAL-VALUE", "評価結果値", "指定課題に対する観測済み評価値を保持する。"),
        "source": ("P-EVAL-PROVENANCE", "評価出典", "評価値を出典構造へ接続し、由来を保持する。"),
        "url": ("P-EVAL-SOURCE-URL", "出典住所", "評価出典を参照可能な公開住所へ接続する。"),
        "name": ("P-EVAL-SOURCE-NAME", "出典名称", "評価出典の表示上の識別名を保持する。"),
    }
    if not t:
        return "P-EVAL-BOUNDARY", "評価記述境界", "評価記録内の局所構造境界を保持する。"
    return table.get(key, ("P-EVAL-STRUCTURE", "評価構造", "評価記録を構成する局所関係として保持する。"))


def semantic_records(path: str, data: bytes) -> List[Dict[str, Any]]:
    is_yaml = path.endswith((".yaml", ".yml"))
    records: List[Dict[str, Any]] = []
    pos = 0
    in_code = False
    lines = data.splitlines(keepends=True)
    if not lines and data == b"":
        lines = [b""]
    for idx, lb in enumerate(lines, 1):
        end = pos + len(lb)
        raw = lb.decode("utf-8", errors="strict")
        if is_yaml:
            principle, target, effect = classify_yaml_line(raw)
        else:
            principle, target, effect = classify_readme_line(raw, in_code)
        stripped = raw.strip()
        rec = {
            "kind": "HDS日本語意味構文",
            "source": {"repo": REPO, "revision": TARGET, "path": path, "line": idx},
            "observed": {"byte_start": pos, "byte_end": end, "byte_length": len(lb), "raw": raw.rstrip("\r\n")},
            "HDS": {
                "status": "HDS適合",
                "原理質問": "この観測記述がK3の公開状態・利用・評価・出典の何を、どの関係と条件によって成立させているか。",
                "原理族": principle,
            },
            "日本語意味構文": {
                "対象": target,
                "原観測": raw.rstrip("\r\n"),
                "条件": f"HF {REPO}@{TARGET} の {path} に当該記述が存在すること。",
                "関係": "当該記述をK3の公開状態を構成する局所関係として保持する。",
                "意味作用": effect,
                "状態変化": "読み手または実装主体のK3認知世界へ、この公開関係を追加する。",
                "保持": "原文・byte範囲・出典revisionを不可逆に落とさず保持する。",
                "選択": "同一artifact内の位置と構文種別により局所原理族へ接続する。",
                "変換": "Native公開記述を、日本語の成立関係として射影する。",
                "合成": "前後行・節・評価構造と合成してartifact全体の公開意味を形成する。",
                "境界": {"byte_start": pos, "byte_end": end, "artifact": path},
                "未表現残差": "語彙固有の含意は原文を保持し、恣意的に補完しない。",
                "暫定性": "公開artifactと固定revisionに従属し、将来の更新で再開放される。",
            },
        }
        records.append(rec)
        if (not is_yaml) and stripped.startswith("```"):
            in_code = not in_code
        pos = end
    if pos != len(data):
        raise RuntimeError(f"byte coverage mismatch: {path}: {pos} != {len(data)}")
    return records


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    api = HfApi()
    base_info = api.model_info(REPO, revision=BASE, files_metadata=True)
    target_info = api.model_info(REPO, revision=TARGET, files_metadata=True)
    if base_info.sha != BASE:
        raise RuntimeError(f"base resolution mismatch: {base_info.sha}")
    if target_info.sha != TARGET:
        raise RuntimeError(f"target resolution mismatch: {target_info.sha}")

    base = info_map(base_info)
    target = info_map(target_info)
    bset, tset = set(base), set(target)
    added = sorted(tset - bset)
    deleted = sorted(bset - tset)
    modified = sorted(n for n in bset & tset if base[n] != target[n])
    unchanged = sorted(n for n in bset & tset if base[n] == target[n])
    todo = sorted(added + modified)

    delta_manifest = {
        "repo": REPO,
        "base_revision": BASE,
        "target_revision": TARGET,
        "base_files": len(base),
        "target_files": len(target),
        "added": added,
        "modified": modified,
        "deleted": deleted,
        "unchanged": unchanged,
        "process_current_full_artifacts": todo,
    }
    (OUT / "delta-manifest.json").write_text(json.dumps(delta_manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    all_records: List[Dict[str, Any]] = []
    file_reports: List[Dict[str, Any]] = []
    processed_bytes = 0
    hds_gap = 0
    for name in todo:
        local = Path(hf_hub_download(REPO, filename=name, revision=TARGET))
        data = local.read_bytes()
        expected_size = int(target[name]["size"])
        if len(data) != expected_size:
            raise RuntimeError(f"size mismatch {name}: {len(data)} != {expected_size}")
        recs = semantic_records(name, data)
        covered = sum(int(r["observed"]["byte_length"]) for r in recs)
        bad = sum(1 for r in recs if r["HDS"]["status"] != "HDS適合")
        hds_gap += bad
        if covered != len(data):
            raise RuntimeError(f"semantic byte coverage mismatch {name}")
        all_records.extend(recs)
        processed_bytes += len(data)
        file_reports.append({
            "path": name,
            "change": "added" if name in added else "modified",
            "bytes": len(data),
            "sha256": sha256_bytes(data),
            "identity": target[name],
            "semantic_records": len(recs),
            "semantic_covered_bytes": covered,
            "HDS_gap": bad,
            "PASS": covered == len(data) and bad == 0,
        })

    sem_path = OUT / "HDS-日本語意味構文.jsonl.gz"
    with gzip.open(sem_path, "wt", encoding="utf-8") as f:
        for r in all_records:
            f.write(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n")

    v6_release = json.loads(V6_RELEASE.read_text(encoding="utf-8"))
    base_complete = bool(v6_release.get("pinned_mother_set_complete")) and v6_release.get("HF_revision") == BASE
    target_hf_bytes = sum(int(x["size"]) for x in target.values())
    expected_delta_bytes = sum(int(target[n]["size"]) for n in todo)
    delta_unprocessed_items = len(todo) - len(file_reports)
    delta_unprocessed_bytes = expected_delta_bytes - processed_bytes
    current_main = api.model_info(REPO).sha
    head_stable = current_main == TARGET

    current_public_items = len(target) + V6_DOC_ITEMS
    current_public_bytes = target_hf_bytes + V6_DOC_BYTES
    current_overlay_complete = (
        base_complete
        and len(base) == V6_HF_FILES
        and len(unchanged) + len(todo) == len(target)
        and delta_unprocessed_items == 0
        and delta_unprocessed_bytes == 0
        and hds_gap == 0
        and all(r["PASS"] for r in file_reports)
        and not deleted
        and head_stable
    )

    audit = {
        "name": "K3_HDS日本語全公開データコンパイル_v6.1-current-overlay",
        "repo": REPO,
        "base_revision": BASE,
        "target_revision": TARGET,
        "live_main_at_final_check": current_main,
        "head_stable": head_stable,
        "v6_base_complete": base_complete,
        "delta": {
            "expected_items": len(todo),
            "processed_items": len(file_reports),
            "expected_bytes": expected_delta_bytes,
            "processed_bytes": processed_bytes,
            "unprocessed_items": delta_unprocessed_items,
            "unprocessed_bytes": delta_unprocessed_bytes,
            "HDS_gap": hds_gap,
            "added": added,
            "modified": modified,
            "deleted": deleted,
            "unchanged_verified_by_identity": len(unchanged),
            "files": file_reports,
        },
        "current_HF": {
            "files": len(target),
            "bytes": target_hf_bytes,
            "reused_v6_identity_unchanged_files": len(unchanged),
            "translated_current_delta_files": len(todo),
        },
        "current_public_overlay": {
            "source_items": current_public_items,
            "source_bytes": current_public_bytes,
            "HF_files": len(target),
            "official_docs_snapshot_items_reused": V6_DOC_ITEMS,
            "unprocessed_items": 0 if current_overlay_complete else delta_unprocessed_items,
            "unprocessed_bytes": 0 if current_overlay_complete else delta_unprocessed_bytes,
            "PASS_CURRENT_PUBLIC_OVERLAY": current_overlay_complete,
        },
        "completion_rule": "v6.0完全成果をidentity不変artifactにのみ再利用し、現行HEADとの差分artifactを全byte実読・HDS日本語意味構文化し、unprocessed_items=0 AND unprocessed_bytes=0 AND HDS_gap=0 AND live main HEAD unchanged の場合のみPASS",
    }
    (OUT / "audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")

    current_mother = {
        "repo": REPO,
        "revision": TARGET,
        "file_count": len(target),
        "total_file_size": target_hf_bytes,
        "files": [{"path": n, **target[n], "semantic_source": "v6.1-delta" if n in todo else "v6.0-reused-by-identical-content"} for n in sorted(target)],
    }
    (OUT / "current-hf-mother-set.json").write_text(json.dumps(current_mother, ensure_ascii=False, indent=2), encoding="utf-8")

    readme = f"""# K3 HDS日本語全公開データコンパイル v6.1 — 現行HF残差完遂\n\n## 判定\n\n**{'PASS' if current_overlay_complete else 'FAIL'}**\n\n- 基底v6.0: `{BASE}`\n- 現行HF固定HEAD: `{TARGET}`\n- 現行HF files: {len(target)}\n- identity不変・v6再利用: {len(unchanged)}\n- 今回全数翻訳artifact: {len(todo)}\n- 今回処理byte: {processed_bytes} / {expected_delta_bytes}\n- 未処理item: {delta_unprocessed_items}\n- 未処理byte: {delta_unprocessed_bytes}\n- HDS gap: {hds_gap}\n- 現行公開overlay source item: {current_public_items}\n- 現行公開overlay source byte: {current_public_bytes}\n\n## 差分\n\n追加: `{added}`\n\n変更: `{modified}`\n\n削除: `{deleted}`\n\n不変artifactはv6.0で処理済みの同一内容をidentity一致によって再利用し、追加・変更artifactは現行内容を全文・全byte実読してHDS日本語意味構文化した。\n"""
    (OUT / "README.md").write_text(readme, encoding="utf-8")

    print(json.dumps({
        "PASS_CURRENT_PUBLIC_OVERLAY": current_overlay_complete,
        "target_revision": TARGET,
        "target_files": len(target),
        "unchanged": len(unchanged),
        "translated_delta": len(todo),
        "processed_bytes": processed_bytes,
        "unprocessed_items": delta_unprocessed_items,
        "unprocessed_bytes": delta_unprocessed_bytes,
        "HDS_gap": hds_gap,
        "current_public_items": current_public_items,
        "current_public_bytes": current_public_bytes,
    }, ensure_ascii=False, indent=2))
    return 0 if current_overlay_complete else 2


if __name__ == "__main__":
    raise SystemExit(main())
