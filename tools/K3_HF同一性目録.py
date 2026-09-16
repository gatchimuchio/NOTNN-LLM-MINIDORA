"""固定Hugging Face版の公式ファイル同一性を列挙する開発・監査用の道具。

保存済み外部API応答は原語の鍵を保つ。出力先は明示指定し、自動commitしない。
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Any

リポジトリ = "moonshotai/Kimi-K3"
固定版 = "c5d1dd4c428bd1ce8b88c5044f3b6ccde9e3b721"


def JSON値に変換(値: Any) -> Any:
    if 値 is None or isinstance(値, (str, int, float, bool)):
        return 値
    if isinstance(値, dict):
        return {str(鍵): JSON値に変換(項目) for 鍵, 項目 in 値.items()}
    if isinstance(値, (list, tuple)):
        return [JSON値に変換(項目) for 項目 in 値]
    if hasattr(値, "__dict__"):
        return {鍵: JSON値に変換(項目) for 鍵, 項目 in vars(値).items() if not 鍵.startswith("_")}
    return repr(値)


def main() -> int:
    from 標準入出力 import 標準出力をUTF8化

    標準出力をUTF8化()
    解析器 = argparse.ArgumentParser(description="Kimi K3固定版のHugging Faceファイル同一性を列挙")
    解析器.add_argument("--out", dest="出力先", type=Path, required=True, help="JSON出力先")
    引数 = 解析器.parse_args()
    # 任意依存は実取得時だけ必要とし、--helpや実行系のimportを拘束しない。
    from huggingface_hub import HfApi
    情報 = HfApi().model_info(リポジトリ, revision=固定版, files_metadata=True)
    行群 = [JSON値に変換(項目) for 項目 in 情報.siblings]
    行群.sort(key=lambda 行: 行.get("rfilename") or 行.get("path") or "")
    出力 = {"repo": リポジトリ, "revision_requested": 固定版, "repo_sha": getattr(情報, "sha", None), "files": 行群}
    引数.出力先.parent.mkdir(parents=True, exist_ok=True)
    引数.出力先.write_text(json.dumps(出力, ensure_ascii=False, indent=2), encoding="utf-8")
    標本 = next((行 for 行 in 行群 if str(行.get("rfilename", "")).endswith(".safetensors")), None)
    print(json.dumps({"repo_sha": 出力["repo_sha"], "file_count": len(行群), "sample_weight": 標本}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
