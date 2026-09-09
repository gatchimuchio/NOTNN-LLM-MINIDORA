"""既存Moduleの合成接続を確認する局所デモ。汎用性能ベンチではない。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from minidora.能力合成 import 能力合成器, 合成計画, 合成工程, 素材参照
from minidora.能力合成_局所接続 import 局所能力群
from minidora.製品版.型 import 能力結果, 参照資料
from minidora.製品版.抽出 import 情報抽出Module


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--売上", type=int, default=120)
    args = parser.parse_args()
    if not 0 <= args.売上 <= 1_000_000:
        parser.error("--売上 は0〜1000000の整数")
    本文 = f"売上は{args.売上}です。費用は75です。利益は45です。"
    原典 = 参照資料("接続試験の入力", "人工入力資料", "局所デモ", 本文=本文)
    Data = {
        "本文": 能力結果(True, 本文, 参照=(原典,)),
        "要約指示": 能力結果(True, "抽出要約"),
        "抽出指示": 能力結果(True, "数字抽出"),
        "変換指示": 能力結果(True, "箇条書き変換"),
        "要約設定": 能力結果(True, "", データ={"行数": 1}),
        "抽出設定": 能力結果(True, "", データ={"種別": "数字"}),
        "変換設定": 能力結果(True, "", データ={"形式": "箇条書き"}),
    }
    計画 = 合成計画((
        合成工程("要約", ("抽出要約",), "要約指示", (素材参照("入力", "本文"),), "要約設定"),
        合成工程("抽出", ("情報抽出",), "抽出指示", (素材参照("工程", "要約"),), "抽出設定"),
        合成工程("変換", ("文脈変換",), "変換指示", (素材参照("工程", "抽出"),), "変換設定"),
    ), ("変換",))
    結果 = 能力合成器(局所能力群()).実行(計画, Data)
    対照 = 情報抽出Module().実行("数字", 本文)
    print(json.dumps({
        "範囲": "既存Module接続の局所契約試験。自由文解釈・GPT-4比較ではない。",
        "状態": 結果.状態, "理由": 結果.理由,
        "原文から直接抽出": 対照.本文,
        "工程結果": {k: v.本文 for k, v in 結果.中間結果},
        "最終出力": {k: v.本文 for k, v in 結果.出力},
        "実行数": 結果.実行数, "監査整合": 結果.監査整合(),
        "ルートハッシュ": 結果.ルートハッシュ,
    }, ensure_ascii=False, indent=2))
    return 0 if (結果.成立 and 結果.監査整合()
                 and 結果.出力[0][1].本文 == f"- {args.売上}") else 1


if __name__ == "__main__":
    raise SystemExit(main())
