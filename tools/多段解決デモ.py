"""目的検証の失敗から子の別解へ戻る局所デモ。人工資料であり汎用性能評価ではない。"""
from __future__ import annotations
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from minidora.多段解決 import 多段解決器, 多段問題, 解決目的, 解法, 問題素材
from minidora.多段解決接続 import 解決補助能力群
from minidora.能力合成_局所接続 import 局所能力群
from minidora.製品版.型 import 能力結果, 参照資料


def 問題を用意(値: int = 120, 代替あり: bool = True):
    text = f"売上は{値}です。費用は75です。利益は45です。"
    data = {"原資料": 能力結果(True, text, 参照=(参照資料("元", "人工資料", "局所デモ", 本文=text),)),
            "指示": 能力結果(True, "宣言した文書操作を実行"),
            "非空設定": 能力結果(True, "", データ={"種別": "非空"}),
            "保持設定": 能力結果(True, "", データ={"種別": "数値列保持"}),
            "要約設定": 能力結果(True, "", データ={"行数": 1}),
            "抽出設定": 能力結果(True, "", データ={"種別": "数字"})}
    goals = (解決目的("素材準備", "成果検査", "指示", "非空設定"),
             解決目的("全数値抽出", "成果検査", "指示", "保持設定", ("原資料",)))
    methods = [解法("要約を使う", "素材準備", (), "抽出要約", "指示",
                      (問題素材("入力", "原資料"),), "要約設定", 0),
               解法("素材から抽出", "全数値抽出", ("素材準備",), "情報抽出", "指示",
                      (問題素材("目的", "素材準備"),), "抽出設定")]
    if 代替あり:
        methods.append(解法("原文を保持", "素材準備", (), "素材引継ぎ", "指示",
                             (問題素材("入力", "原資料"),), 優先度=1))
    return 多段問題(("全数値抽出",), goals, tuple(methods)), data


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--値", type=int, default=120)
    parser.add_argument("--代替なし", action="store_true")
    args = parser.parse_args()
    if not 0 <= args.値 <= 1000000:
        parser.error("--値は0〜1000000")
    p, data = 問題を用意(args.値, not args.代替なし)
    result = 多段解決器((*局所能力群(), *解決補助能力群()), 純粋作用確認=True).実行(p, data)
    print(json.dumps({"範囲": "宣言した有限解法からの目的分解・後戻りの局所試験。自由文理解ではない。",
        "状態": result.状態, "理由": result.理由, "出力": {k: v.本文 for k, v in result.出力},
        "採用解法": [r["解法"] for r in result.採用経路],
        "検証で退けた目的": [r["目的"] for r in result.履歴 if r["作用"] == "目的条件未達"],
        "展開数": result.展開数, "能力呼出数": result.呼出数, "監査整合": result.整合確認()},
        ensure_ascii=False, indent=2))
    expected = "保留" if args.代替なし else "合格"
    return 0 if result.状態 == expected and result.整合確認() else 1


if __name__ == "__main__":
    raise SystemExit(main())
