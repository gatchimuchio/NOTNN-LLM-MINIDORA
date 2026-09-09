"""本物の公開HDS Compilerによる、状態あり／初期化後の複数turn対照。"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from minidora.文脈要求 import 文脈付き要求セッション
from minidora.製品版.型 import 能力結果, 参照資料


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--売上", type=int, default=120)
    args = parser.parse_args()
    if not 0 <= args.売上 <= 1_000_000:
        parser.error("--売上 は0〜1000000の整数")
    text = f"売上は{args.売上}です。費用は75です。利益は45です。"
    data = {"本文": 能力結果(True, text, 参照=(参照資料("原典", "人工入力", "局所デモ", 本文=text),))}
    session = 文脈付き要求セッション("文脈デモ")
    rows = []
    for request, source in (("本文を1行で要約して", data),
                             ("それから数字を抽出して", None),
                             ("さっきの結果を箇条書きにして", None)):
        result = session.応答(request, source)
        rows.append({"依頼": request, "状態": result.状態, "理由": result.理由,
                     "出力": [v.本文 for _, v in result.出力],
                     "文脈束縛": [asdict(v) for v in result.解釈.文脈束縛] if result.解釈 else []})
    session.初期化()
    reset = session.応答("それから数字を抽出して")
    print(json.dumps({"範囲": "採用済み会話成果への限定照応。汎用会話能力の完成ではない。",
                      "会話": rows, "初期化後の同じ依頼": {"状態": reset.状態, "理由": reset.理由}},
                     ensure_ascii=False, indent=2))
    return 0 if (all(r["状態"] == "合格" for r in rows)
                 and rows[-1]["出力"] == [f"- {args.売上}"] and reset.状態 == "保留") else 1


if __name__ == "__main__":
    raise SystemExit(main())
