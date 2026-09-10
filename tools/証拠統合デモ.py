"""人工資料の一致・競合を対照する。汎用性能評価でもLIVE取得でもない。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from minidora.能力合成 import 能力合成器, 合成計画, 合成工程, 素材参照
from minidora.能力合成_局所接続 import 局所能力群
from minidora.証拠統合接続 import 証拠統合Module, 記載値採用Module
from minidora.製品版.型 import 能力結果, 参照資料


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--値", type=int, default=120)
    parser.add_argument("--競合", action="store_true")
    args = parser.parse_args()
    if not 0 <= args.値 <= 1_000_000:
        parser.error("--値は0〜1000000")
    first = f"装置Aの電圧は{args.値} Vです。"
    second = (f"装置Aの電圧は{args.値+1} Vです。" if args.競合
              else f"装置Aの電圧は{args.値*1000} mVです。")
    refs = (参照資料("a", "人工資料A", "局所対照", 本文=first),
            参照資料("b", "人工資料B", "局所対照", 本文=second))
    data = {"資料": 能力結果(True, "", 参照=refs),
            "証拠指示": 能力結果(True, "数値主張を比較"),
            "証拠設定": 能力結果(True, "", データ={"対象":"装置A", "属性":"電圧", "単位":"V"}),
            "採用指示": 能力結果(True, "記載値採用"),
            "抽出指示": 能力結果(True, "数字抽出"),
            "抽出設定": 能力結果(True, "", データ={"種別":"数字"})}
    plan = 合成計画((
        合成工程("証拠", ("証拠統合",), "証拠指示", (素材参照("入力", "資料"),), "証拠設定"),
        合成工程("採用", ("記載値採用",), "採用指示", (素材参照("工程", "証拠"),)),
        合成工程("抽出", ("情報抽出",), "抽出指示", (素材参照("工程", "採用"),), "抽出設定"),
    ), ("抽出",))
    runner = 能力合成器((証拠統合Module().登録(), 記載値採用Module().登録(), *局所能力群()))
    result = runner.実行(plan, data)
    proof = dict(result.中間結果).get("証拠")
    print(json.dumps({"範囲":"人工資料の局所対照。事実性の認定ではない。",
                      "入力":[first,second], "状態":result.状態, "理由":result.理由,
                      "最終出力":[v.本文 for _,v in result.出力],
                      "実行能力":[t.能力 for t in result.履歴],
                      "証拠報告":proof.データ if proof else None,
                      "監査整合":result.監査整合()}, ensure_ascii=False, indent=2))
    correct = (not result.成立 and result.実行数 == 2 if args.競合 else
               result.成立 and result.出力[0][1].本文 == str(args.値))
    return 0 if correct and result.監査整合() else 1


if __name__ == "__main__":
    raise SystemExit(main())
