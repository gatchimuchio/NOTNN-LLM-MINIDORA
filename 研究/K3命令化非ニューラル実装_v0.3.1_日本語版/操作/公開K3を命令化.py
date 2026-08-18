#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from minidora_k3.日本語化 import 日本語辞書
from minidora_k3.構造 import architecture_manifest
from minidora_k3.重み変換 import expected_public_tensor_role_families

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    config = json.loads((ROOT / "一次資料/K3公式設定原文.json").read_text(encoding="utf-8"))
    architecture = 日本語辞書(architecture_manifest())
    expected = 日本語辞書(expected_public_tensor_role_families(config))
    architecture["時間軸"]["層数"] = architecture["時間軸"].pop("層群")
    architecture["幅軸"]["経路選択専門器数"] = architecture["幅軸"].pop("経路選択専門器群")
    architecture["幅軸"]["共有専門器数"] = architecture["幅軸"].pop("共有専門器群")
    expected["各層"] = expected.pop("層群")
    expected["期待数"]["層数"] = expected["期待数"].pop("層群")
    expected["期待数"]["経路選択専門器数"] = expected["期待数"].pop("経路選択専門器群")
    expected["期待数"]["共有専門器数"] = expected["期待数"].pop("共有専門器群")
    outputs = {
        ROOT / "台帳/公開構造命令台帳.json": architecture,
        ROOT / "台帳/予想テンソル役割台帳.json": expected,
    }
    for path, payload in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
