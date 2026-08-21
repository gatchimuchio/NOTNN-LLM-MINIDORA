#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kimi K3の固定Hugging Face revisionから公式ファイル同一性を列挙する。

開発・監査用ツールであり、MINIDORA Runtimeの依存ではない。
出力先は呼び出し側が明示し、リポジトリへ自動commitしない。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from huggingface_hub import HfApi


REPO = "moonshotai/Kimi-K3"
REV = "c5d1dd4c428bd1ce8b88c5044f3b6ccde9e3b721"


def plain(value: Any) -> Any:
    """huggingface_hubの戻り値をJSON化可能な値へ再帰変換する。"""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(item) for item in value]
    if hasattr(value, "__dict__"):
        return {
            key: plain(item)
            for key, item in vars(value).items()
            if not key.startswith("_")
        }
    return repr(value)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Kimi K3固定revisionのHugging Faceファイル同一性を列挙する。"
    )
    parser.add_argument("--out", type=Path, required=True, help="JSON出力先")
    args = parser.parse_args()

    info = HfApi().model_info(REPO, revision=REV, files_metadata=True)
    rows = [plain(sibling) for sibling in info.siblings]
    rows.sort(key=lambda row: row.get("rfilename") or row.get("path") or "")

    output = {
        "repo": REPO,
        "revision_requested": REV,
        "repo_sha": getattr(info, "sha", None),
        "files": rows,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    sample_weight = next(
        (
            row
            for row in rows
            if str(row.get("rfilename", "")).endswith(".safetensors")
        ),
        None,
    )
    print(
        json.dumps(
            {
                "repo_sha": output["repo_sha"],
                "file_count": len(rows),
                "sample_weight": sample_weight,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
