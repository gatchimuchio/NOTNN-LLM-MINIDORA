"""公開HDS Compiler→要求計画→既存Moduleの局所接続デモ。"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from minidora.hds_compiler import 公開HDSコンパイラ
from minidora.要求解釈 import 要求計画器
from minidora.要求解釈実行 import 要求計画を実行
from minidora.能力合成 import 能力合成器
from minidora.能力合成_局所接続 import 局所能力群
from minidora.製品版.型 import 能力結果, 参照資料


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--依頼", default="本文を1行で要約して、その結果から数字を抽出して、箇条書きにして")
    parser.add_argument("--本文", default="売上は120です。費用は75です。利益は45です。")
    args = parser.parse_args()
    原典 = 参照資料("利用者提供", "入力資料", "利用者", 本文=args.本文)
    ir = 公開HDSコンパイラ().コンパイル(args.依頼)
    解釈 = 要求計画器().コンパイル(ir, {"本文": 能力結果(True, args.本文, 参照=(原典,))})
    result = 要求計画を実行(解釈, 能力合成器(局所能力群()))
    print(json.dumps({
        "範囲": "文書操作の限定文法。汎用日本語理解やGPT-4同等性の認定ではない。",
        "依頼": args.依頼,
        "状態": result.状態, "理由": result.理由,
        "要求": [asdict(t) for t in 解釈.要求],
        "計画": asdict(解釈.計画) if 解釈.計画 else None,
        "残差": [asdict(r) for r in 解釈.残差],
        "上流残差": [asdict(r) for r in ir.残差],
        "局所解消": 解釈.局所解消,
        "最終出力": {k: v.本文 for k, v in result.出力},
        "実行数": result.合成.実行数 if result.合成 else 0,
        "解釈ハッシュ": result.解釈ハッシュ,
        "実行ハッシュ": result.合成.ルートハッシュ if result.合成 else None,
    }, ensure_ascii=False, indent=2))
    return 0 if result.成立 else 2


if __name__ == "__main__":
    raise SystemExit(main())
