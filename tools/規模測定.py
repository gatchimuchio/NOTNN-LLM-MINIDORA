from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from minidora.規模測定 import 規模測定  # noqa: E402


def _標準出力UTF8化() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="strict")


def main() -> int:
    _標準出力UTF8化()
    result = 規模測定()
    print("MINIDORA_SCALE_MEASUREMENT=" + json.dumps(result.辞書(), ensure_ascii=False, sort_keys=True))
    print(f"LARGE_SCALE_STATUS={result.大規模性状態}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
