from __future__ import annotations

import json
from pathlib import Path
import runpy
import sys


def _標準出力UTF8化() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="strict")


根 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(根 / "src"))

from minidora import 標準言語基底P  # noqa: E402


def 監査() -> list[str]:
    誤り: list[str] = []

    if 標準言語基底P.規定言語 != "日本語":
        誤り.append("言語基底P: 規定言語が日本語ではない")
    if 標準言語基底P.基底言語 != "日本語":
        誤り.append("言語基底P: 基底言語が日本語ではない")
    if 標準言語基底P.基底言語コード != "ja":
        誤り.append("言語基底P: 日本語外部互換コードがjaではない")

    必須 = (
        "設計/00_日本語基底規定_v1.md",
        "設計/13_共有言語基底P仕様_v0_4.md",
        "設計/14_外部言語_日本語意味射影仕様_v0_4.md",
        "構文化/言語模型横断_日本語基底作用構文化_v3/README.md",
        "構文化/言語模型横断_日本語基底作用構文化_v3/構文化規約_v3.json",
    )
    for 相対 in 必須:
        if not (根 / 相対).exists():
            誤り.append(f"日本語基底必須資料欠落: {相対}")

    設計 = (根 / "設計/README.md").read_text(encoding="utf-8")
    if "cognitive-engineering-foundations" not in 設計:
        誤り.append("設計README: 最上位認知工学正本参照がない")
    if "00_日本語基底規定_v1.md" not in 設計:
        誤り.append("設計README: 日本語基底規定参照がない")

    構文化 = (根 / "構文化/README.md").read_text(encoding="utf-8")
    if "言語模型横断_日本語基底作用構文化_v3" not in 構文化:
        誤り.append("構文化README: 現行日本語基底構文化v3参照がない")

    規約 = json.loads((根 / "構文化/言語模型横断_日本語基底作用構文化_v3/構文化規約_v3.json").read_text(encoding="utf-8"))
    if 規約.get("規定言語") != "日本語":
        誤り.append("構文化v3: 規定言語が日本語ではない")

    try:
        runpy.run_path(str(根 / "構文化/言語模型横断_日本語基底作用構文化_v3/構文化監査.py"), run_name="__main__")
    except Exception as exc:
        誤り.append(f"構文化v3監査失敗: {exc}")

    return 誤り


def main() -> int:
    _標準出力UTF8化()
    誤り = 監査()
    if 誤り:
        print("日本語基底監査: 失敗")
        for 項目 in 誤り:
            print(f"- {項目}")
        return 1
    print("日本語基底監査: 合格")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
