#!/usr/bin/env python3
from __future__ import annotations

import json
import statistics
import time
from pathlib import Path

from minidora_k3 import ミニドラK3, 計算量, 実行状態

ROOT = Path(__file__).resolve().parents[1]

CASES = (
    ("K3総層数", "K3の層数は？", "合格", "93"),
    ("KDA層数", "K3のKDA層数は？", "合格", "69"),
    ("門制御MLA層数", "K3のGated MLA層数は？", "合格", "24"),
    ("経路選択専門器数", "K3の専門家数は？", "合格", "896"),
    ("各token選択数", "K3は各トークンで何人の専門家を選びますか？", "合格", "16"),
    ("共有専門器数", "K3の共有専門家数は？", "合格", "2"),
    ("総パラメータ", "K3の総パラメータは？", "合格", "2.8T"),
    ("活性パラメータ", "K3の活性パラメータは？", "合格", "104B"),
    ("論理式", "not ( True ) and ( True ) は", "合格", "False"),
    ("整数算術", "(2 + 3) * 4 =", "合格", "20"),
    ("未登録知識", "K3の社長の好物は？", "保留", ""),
)


def main() -> int:
    runtime = ミニドラK3.内蔵参照から構築()
    rows = []
    elapsed = []
    for name, query, expected_status, expected_answer in CASES:
        started = time.perf_counter_ns()
        result = runtime.実行(query, 計算量=計算量.最大)
        wall_ms = (time.perf_counter_ns() - started) / 1_000_000
        elapsed.append(wall_ms)
        correct = result.status.value == expected_status and (
            not expected_answer or result.answer == expected_answer
        )
        rows.append(
            {
                "名称": name,
                "入力": query,
                "期待状態": expected_status,
                "期待回答": expected_answer,
                "実測状態": result.status.value,
                "実測回答": result.answer,
                "正否": correct,
                "理由符号群": list(result.reason_codes),
                "実行系時間ミリ秒": result.elapsed_ms,
                "壁時計時間ミリ秒": wall_ms,
            }
        )
    passed = sum(row["正否"] for row in rows)
    payload = {
        "評価名": "K3公開構造・日本語命令化局所評価",
        "版": "0.3.1",
        "条件": {
            "ニューラルネットワーク": False,
            "Transformer": False,
            "外部参照層": True,
            "参照供給器": "同梱固定資料",
            "LLM_API": False,
            "Web検索": False,
            "計算量": "最大",
        },
        "概要": {
            "合格数": passed,
            "総数": len(rows),
            "一致率": passed / len(rows),
            "中央値ミリ秒": statistics.median(elapsed),
            "平均ミリ秒": statistics.fmean(elapsed),
            "逐次処理数毎秒": 1000 / statistics.fmean(elapsed),
        },
        "各問": rows,
        "主張境界": {
            "この評価が確認するもの": "公開構造知識、明示演算、参照橋、採否規約の局所閉路",
            "この評価が確認しないもの": [
                "全2.8T重み値の意味命令化",
                "open-domain知識同等",
                "視覚同等",
                "100万token文脈同等",
                "K3完全同等",
            ],
        },
    }
    output = ROOT / "結果/局所評価_0_3_1.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["概要"], ensure_ascii=False, indent=2))
    return 0 if passed == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
