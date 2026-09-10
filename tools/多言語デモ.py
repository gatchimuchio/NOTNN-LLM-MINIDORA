"""明示対訳語と人工資料の日英変換。未知語・否定・入力値の対照を行う。"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from minidora.多言語変換 import 対訳語, 対訳を変換, 翻訳記録整合
from minidora.多言語接続 import 多言語変換Module
from minidora.能力合成 import 能力合成器, 合成計画, 合成工程, 素材参照
from minidora.能力合成_局所接続 import 局所能力群
from minidora.製品版.型 import 能力結果


def 例の対訳():
    # 世界知識ではなくデモ用語彙。実運用では呼出側からDataとして供給する。
    return (対訳語("装置A", "対象", "装置A", "device A"),
            対訳語("電圧", "属性", "電圧", "voltage"),
            対訳語("通常条件", "条件", "通常", "normal"),
            対訳語("ボルト", "単位", "V", "V"))


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--値", type=int, default=120)
    parser.add_argument("--否定", action="store_true")
    parser.add_argument("--未対応", action="store_true")
    args = parser.parse_args()
    if not -1_000_000 <= args.値 <= 1_000_000:
        parser.error("--値は-1000000〜1000000")
    original = ('under condition "normal", the voltage of device A is '
                + ("not " if args.否定 else "") + f"at least {args.値} V.")
    if args.未対応:
        original += " However, this is only a hypothesis."
    translated = 対訳を変換(original, "en", "ja", 種別="数値記載", 対訳=例の対訳())
    reverse = (対訳を変換(translated.本文, "ja", "en", 種別="数値記載", 対訳=例の対訳())
               if translated.成立 else None)
    plan = 合成計画((
        合成工程("翻訳", ("多言語変換",), "指示", (素材参照("入力", "原文"),), "設定"),
        合成工程("抽出", ("情報抽出",), "指示", (素材参照("工程", "翻訳"),), "抽出設定")), ("抽出",))
    data = {"原文": 能力結果(True, original), "指示": 能力結果(True, "明示された処理を実行"),
            "設定": 能力結果(True, "", データ={"入力言語": "en", "出力言語": "ja", "種別": "数値記載",
                                                "対訳": [asdict(w) for w in 例の対訳()]}),
            "抽出設定": 能力結果(True, "", データ={"種別": "数字"})}
    result = 能力合成器((多言語変換Module().登録(), *局所能力群())).実行(plan, data)
    ok = (not translated.成立 and not result.成立) if args.未対応 else (
        translated.成立 and reverse.成立 and result.成立 and 翻訳記録整合(translated)
        and translated.データ["意味列"] == reverse.データ["意味列"]
        and result.出力[0][1].本文 == str(args.値))
    print(json.dumps({"範囲": "明示対訳語と有限文法の局所対照。汎用翻訳精度の評価ではない。",
        "原文": original, "日本語": translated.本文, "逆方向": reverse.本文 if reverse else "",
        "翻訳成立": translated.成立, "保留理由": translated.保留理由,
        "後続抽出": result.出力[0][1].本文 if result.成立 else "",
        "実行能力": [r.能力 for r in result.履歴], "合成監査": result.監査整合(), "対照成立": ok},
        ensure_ascii=False, indent=2))
    return 0 if ok and result.監査整合() else 1


if __name__ == "__main__":
    raise SystemExit(main())
