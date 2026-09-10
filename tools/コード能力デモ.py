"""明示アルゴリズム候補の生成・試験・後戻り。自由文からの自動修復ではない。"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from minidora.コード能力 import コードを評価
from minidora.コード能力接続 import コード能力群
from minidora.多段解決 import 多段解決器, 多段問題, 解決目的, 解法, 問題素材
from minidora.製品版.型 import 能力結果


def 二乗和仕様(比較="超"):
    def ref(name):
        return {"種別": "参照", "名前": name}
    def const(key):
        return {"種別": "定数参照", "キー": key}
    return {"名前": "条件付き二乗和", "引数": ["数列"], "手順": [
        {"種別": "代入", "名前": "合計", "式": const("初期値")},
        {"種別": "反復", "変数": "数", "対象": ref("数列"), "手順": [
            {"種別": "分岐", "条件": {"種別": "比較", "演算": 比較, "左": ref("数"), "右": const("閾値")},
             "真": [{"種別": "代入", "名前": "合計", "式": {"種別": "算術", "演算": "加算", "左": ref("合計"),
                     "右": {"種別": "算術", "演算": "乗算", "左": ref("数"), "右": ref("数")}}}], "偽": []}]},
        {"種別": "返却", "式": ref("合計")}]}


def 問題を用意(代替あり=True):
    constants = {"初期値": 0, "閾値": 2}
    data = {"候補A": 能力結果(True, "", データ={"仕様": 二乗和仕様("以上"), "定数": constants}),
            "候補B": 能力結果(True, "", データ={"仕様": 二乗和仕様("超"), "定数": constants}),
            "指示": 能力結果(True, "構造化された関数を生成"),
            "試験指示": 能力結果(True, "指定の入出力を確認"),
            "試験設定": 能力結果(True, "", データ={"試験": [
                {"引数": {"数列": [], "定数": constants}, "期待値": 0},
                {"引数": {"数列": [2], "定数": constants}, "期待値": 0},
                {"引数": {"数列": [1, 2, 3, 4], "定数": constants}, "期待値": 25}]})}
    methods = [解法("境界を含む候補", "コード完成", (), "コード生成", "指示", (問題素材("入力", "候補A"),))]
    if 代替あり:
        methods.append(解法("境界を含まない候補", "コード完成", (), "コード生成", "指示", (問題素材("入力", "候補B"),), 優先度=1))
    problem = 多段問題(("コード完成",), (解決目的("コード完成", "コード検証", "試験指示", "試験設定"),), tuple(methods))
    return problem, data


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--代替なし", action="store_true")
    args = parser.parse_args()
    p, data = 問題を用意(not args.代替なし)
    result = 多段解決器(コード能力群(), 純粋作用確認=True).実行(p, data)
    code = result.出力[0][1] if result.成立 else None
    unseen = コードを評価(code.本文, {"数列": [-3, 2, 5, 8], "定数": code.データ["定数"]}) if code else None
    print(json.dumps({"状態": result.状態, "コード": code.本文 if code else "", "理由": result.理由,
        "採用解法": [s["解法"] for s in result.採用経路],
        "検証で退けた解法": [s["解法"] for s in result.履歴 if s["作用"] == "目的条件未達"],
        "選別に未使用の入力結果": unseen.データ.get("値") if unseen else None,
        "監査整合": result.整合確認(),
        "範囲": "明示候補からの生成と有限試験。未知解法の発見・一般的なコード修復ではない"}, ensure_ascii=False, indent=2))
    ok = not result.成立 if args.代替なし else result.成立 and unseen.成立 and unseen.データ["値"] == 89
    return 0 if ok and result.整合確認() else 1


if __name__ == "__main__":
    raise SystemExit(main())
