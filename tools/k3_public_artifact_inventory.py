#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kimi K3の固定revisionから公開artifact inventoryを生成する。

開発・監査用ツールであり、MINIDORA Runtimeの依存ではない。
出力先は呼び出し側が明示し、リポジトリへ自動commitしない。
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from huggingface_hub import HfApi


REPO = "moonshotai/Kimi-K3"
REV = "c5d1dd4c428bd1ce8b88c5044f3b6ccde9e3b721"


def obj_dict(value: Any) -> dict[str, Any]:
    """Hugging Face tree objectから再現に必要な属性だけを抽出する。"""
    result: dict[str, Any] = {
        "path": value.path,
        "type": value.__class__.__name__,
    }
    for key in ("size", "blob_id", "security"):
        item = getattr(value, key, None)
        if item is not None:
            result[key] = item

    lfs = getattr(value, "lfs", None)
    if lfs is not None:
        if hasattr(lfs, "__dict__"):
            result["lfs"] = {
                key: item
                for key, item in vars(lfs).items()
                if item is not None
            }
        else:
            result["lfs"] = str(lfs)
    return result


def _manifest_bytes(files: list[dict[str, Any]]) -> bytes:
    lines = (
        f"{row['path']}\t{row.get('size')}\t{row.get('blob_id')}\t"
        f"{json.dumps(row.get('lfs'), sort_keys=True, default=str)}"
        for row in files
    )
    return "\n".join(lines).encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Kimi K3固定revisionの公開artifact inventoryを生成する。"
    )
    parser.add_argument("--out", type=Path, required=True, help="JSON出力先")
    args = parser.parse_args()

    api = HfApi()
    rows = [
        obj_dict(item)
        for item in api.list_repo_tree(
            REPO,
            revision=REV,
            recursive=True,
            expand=True,
        )
    ]

    files = sorted(
        (row for row in rows if row["type"] == "RepoFile"),
        key=lambda row: row["path"],
    )
    directories = [row for row in rows if row["type"] != "RepoFile"]
    weight_files = [
        row
        for row in files
        if row["path"].startswith("model-")
        and row["path"].endswith(".safetensors")
    ]
    nonweight_files = [row for row in files if row not in weight_files]

    canonical = _manifest_bytes(files)
    output = {
        "repo": REPO,
        "revision": REV,
        "file_count": len(files),
        "dir_count": len(directories),
        "weight_shard_count": len(weight_files),
        "nonweight_file_count": len(nonweight_files),
        "total_file_size": sum(int(row.get("size") or 0) for row in files),
        "weight_file_size": sum(
            int(row.get("size") or 0) for row in weight_files
        ),
        "nonweight_file_size": sum(
            int(row.get("size") or 0) for row in nonweight_files
        ),
        "manifest_sha256": hashlib.sha256(canonical).hexdigest(),
        "files": files,
        "nonweight_files": nonweight_files,
        "directories": directories,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(output, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    summary_keys = (
        "file_count",
        "weight_shard_count",
        "nonweight_file_count",
        "total_file_size",
        "weight_file_size",
        "nonweight_file_size",
        "manifest_sha256",
    )
    print(
        json.dumps(
            {key: output[key] for key in summary_keys},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
