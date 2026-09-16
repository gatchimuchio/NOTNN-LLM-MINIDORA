"""GPQA正本条件を固定する入口。旧 benchmark_strict.py の実装を日本語正本へ復元。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

from 評価契約 import 契約を付与, 直接比較判定, GPQA実参照E2E契約


def _実行(命令列: list[str]) -> None:
    完了 = subprocess.run(命令列, check=False)
    if 完了.returncode != 0:
        raise SystemExit(完了.returncode)


def _保存(経路: Path, 内容: dict) -> None:
    経路.parent.mkdir(parents=True, exist_ok=True)
    経路.write_text(json.dumps(内容, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _得点(内容: dict) -> tuple[int | None, int | None]:
    指標 = 内容.get("metrics")
    if isinstance(指標, dict):
        return 指標.get("correct"), 指標.get("selected_total") or 指標.get("completed")
    return 内容.get("correct"), 内容.get("with_gold") or 内容.get("total")


def GPQA正本を実行(引数: argparse.Namespace) -> int:
    # 評価構成だけを固定する。参照結果は毎回新規取得し、固定資料を再投入しない。
    命令列 = [sys.executable, str(Path(__file__).with_name("形式評価.py")),
              "gpqa-diamond", "--controlled-ab", "--no-openalex", "--out", str(引数.出力)]
    _実行(命令列)
    内容 = json.loads(引数.出力.read_text(encoding="utf-8"))
    try:
        契約 = GPQA実参照E2E契約(内容.get("protocol", {}))
    except ValueError as 例外:
        raise SystemExit(f"GPQA正本手順違反: {例外}") from 例外
    _保存(引数.出力, 契約を付与(内容, 契約))
    print("外部評価識別子=" + 契約["外部評価識別子"])
    print("評価種別=" + 契約["評価種別"])
    print("参照方式=LIVE_ONLY")
    print("固定参照資料許可=false")
    print("実行間コード差直接比較=false")
    return 0


def 比較を実行(引数: argparse.Namespace) -> int:
    左 = json.loads(引数.左.read_text(encoding="utf-8"))
    右 = json.loads(引数.右.read_text(encoding="utf-8"))
    許可, 理由 = 直接比較判定(左, 右)
    左正答, 左全数 = _得点(左)
    右正答, 右全数 = _得点(右)
    結果 = {
        "実行間コード差直接比較": 許可, "理由": 理由,
        "左": {"正答": 左正答, "全数": 左全数},
        "右": {"正答": 右正答, "全数": 右全数},
        "得点時系列保存許可": True,
        "正答差": (右正答 - 左正答) if isinstance(左正答, int) and isinstance(右正答, int) else None,
        "正答差がコードだけの因果差": False,
    }
    print(json.dumps(結果, ensure_ascii=False, indent=2))
    if 引数.出力:
        _保存(引数.出力, 結果)
    return 0 if 許可 else 2


def 引数解析器() -> argparse.ArgumentParser:
    根 = argparse.ArgumentParser(description="MINIDORA正本評価契約v2の実行入口")
    sub = 根.add_subparsers(dest="方式", required=True)
    実測 = sub.add_parser("gpqa-e2e", help="GPQA正本。198問全数をLIVE参照取得で実行する")
    実測.add_argument("--out", dest="出力", type=Path, required=True)
    実測.set_defaults(処理=GPQA正本を実行)
    # compare / --out は既存利用者とのコマンドライン互換境界。
    比較 = sub.add_parser("compare", help="正本E2E実測間の得点差と因果帰属可否を表示する")
    比較.add_argument("左", type=Path)
    比較.add_argument("右", type=Path)
    比較.add_argument("--out", dest="出力", type=Path)
    比較.set_defaults(処理=比較を実行)
    return 根


def main() -> int:
    from 標準入出力 import 標準出力をUTF8化

    標準出力をUTF8化()
    引数 = 引数解析器().parse_args()
    return 引数.処理(引数)


if __name__ == "__main__":
    raise SystemExit(main())
