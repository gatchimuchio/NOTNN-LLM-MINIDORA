# -*- coding: utf-8 -*-
"""現行正本・日本語基底・主要配置のリポジトリ整合性を検証する正本監査器。"""
from __future__ import annotations

from pathlib import Path
import runpy
import sys


根 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(根 / "src"))


必須経路 = (
    "AGENTS.md",
    "現行正本.md",
    "参照正本.md",
    "設計/README.md",
    "設計/00_日本語基底規定_v1.md",
    "設計/01_日本語正本語彙_v1.md",
    "評価/評価契約_v3.md",
    "構文化/言語模型横断_日本語基底作用構文化_v3/README.md",
    "構文化/言語模型横断_日本語基底作用構文化_v3/構文化規約_v3.json",
    "構文化/言語模型横断_日本語基底作用構文化_v3/構文化監査.py",
    "src/minidora/__init__.py",
    "src/minidora/HDS構文化器_v1.py",
    "tools/日本語基底監査.py",
    "tools/repository_consistency_check.py",
)

必須領域 = (
    "src/minidora",
    "tests",
    "tools",
    "設計",
    "評価",
    "構文化",
)


def _失敗(内容: str) -> None:
    raise AssertionError(内容)


def _必須配置を確認() -> None:
    欠落 = [相対 for 相対 in 必須経路 if not (根 / 相対).is_file()]
    欠落.extend(相対 for 相対 in 必須領域 if not (根 / 相対).is_dir())
    if 欠落:
        _失敗("必須配置欠落: " + ", ".join(欠落))


def _互換入口を確認() -> None:
    対象 = 根 / "tools/repository_consistency_check.py"
    内容 = 対象.read_text(encoding="utf-8")
    if "互換入口" not in 内容 or "リポジトリ整合性監査.py" not in 内容:
        _失敗("旧英字整合性監査入口が日本語正本への薄い互換入口になっていない")


def _日本語基底を確認() -> None:
    名前空間 = runpy.run_path(str(根 / "tools/日本語基底監査.py"), run_name="_日本語基底監査")
    監査関数 = 名前空間.get("監査")
    if not callable(監査関数):
        _失敗("日本語基底監査の監査関数を取得できない")
    誤り = list(監査関数())
    if 誤り:
        _失敗("日本語基底監査違反:\n- " + "\n- ".join(誤り))


def main() -> int:
    from 標準入出力 import 標準出力をUTF8化

    標準出力をUTF8化()
    _必須配置を確認()
    _互換入口を確認()
    _日本語基底を確認()
    print("リポジトリ整合性監査: 合格")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
