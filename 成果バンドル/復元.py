#!/usr/bin/env python3
"""分割格納された完全成果バンドルを復元し、SHA-256を検証する。"""
from __future__ import annotations

import base64
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT.parent / "NOTNN-LLM-MINIDORA_成果バンドル_20260818.zip"
EXPECTED_SHA256 = "777073b9f6b1d4ff299b971c11ee695f89f9b4db6476f26d02a5be4aab536d4f"


def main() -> int:
    parts = sorted(ROOT.glob("part-*.b64"))
    if not parts:
        raise SystemExit("ERROR: 分割ファイルがありません")

    encoded = "".join(part.read_text(encoding="ascii").strip() for part in parts)
    try:
        data = base64.b64decode(encoded, validate=True)
    except Exception as exc:
        raise SystemExit(f"ERROR: Base64復号に失敗しました: {exc}") from exc

    actual = hashlib.sha256(data).hexdigest()
    if actual != EXPECTED_SHA256:
        raise SystemExit(
            "ERROR: SHA-256不一致\n"
            f"expected: {EXPECTED_SHA256}\n"
            f"actual:   {actual}"
        )

    OUTPUT.write_bytes(data)
    print(f"WROTE: {OUTPUT}")
    print(f"SHA-256: {actual}")
    print(f"PARTS: {len(parts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
