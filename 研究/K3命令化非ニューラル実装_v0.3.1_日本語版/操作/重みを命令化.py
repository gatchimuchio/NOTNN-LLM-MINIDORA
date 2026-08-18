#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from minidora_k3.重み変換 import (
    compile_checkpoint,
    bind_checkpoint_payloads,
    dump_compile_result,
    dump_payload_binding_manifest,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="K3公開checkpointのtensor情報・byte位置を日本語役割命令へ変換する")
    parser.add_argument("--索引", "--index", dest="索引", type=Path, help="model.safetensors.index.json")
    parser.add_argument("--分割", "--shard", dest="分割", action="append", type=Path, default=[], help="safetensors分割file。複数指定可")
    parser.add_argument("--出力", "--output", dest="出力", type=Path, default=Path("台帳/重み役割命令台帳.json"))
    parser.add_argument("--実体結合出力", dest="実体結合出力", type=Path, default=Path("台帳/重み実体結合台帳.json"))
    parser.add_argument("--内容摘要", "--hash-payloads", dest="内容摘要", action="store_true", help="各tensor byte領域をstreaming SHA-256する")
    args = parser.parse_args()

    instructions, summary = compile_checkpoint(index_path=args.索引, shard_paths=tuple(args.分割))
    dump_compile_result(args.出力, instructions, summary)
    print(f"役割命令台帳: {args.出力}")
    print(f"tensor総数: {summary.tensors_total}")
    print(f"役割解決数: {summary.tensors_mapped}")
    print(f"未解決数: {summary.tensors_unresolved}")

    if args.分割:
        bindings = bind_checkpoint_payloads(tuple(args.分割), hash_payloads=args.内容摘要)
        dump_payload_binding_manifest(args.実体結合出力, bindings)
        print(f"実体結合台帳: {args.実体結合出力}")
        print(f"結合tensor数: {len(bindings)}")
    return 0 if summary.tensors_total and not summary.tensors_unresolved else 2


if __name__ == "__main__":
    raise SystemExit(main())
