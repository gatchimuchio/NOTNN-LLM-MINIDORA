# -*- coding: utf-8 -*-
"""公開リポジトリへ非公開内部理論の直接導線・固定参照・禁止配布物が再混入しないか検査する。"""
from __future__ import annotations

from pathlib import Path
import subprocess

根 = Path(__file__).resolve().parents[1]

禁止文字列 = (
    "cognitive-engineering-foundations",
    "60131da52ba7931ed7f82c7648a74ac790f50d08",
    "神域原理",
    "トリニティ原理",
)

例外経路 = {
    "評価/公開境界_漏洩危険性監査_2026-09-20.md",
}

禁止アーカイブ接頭辞 = (
    "構文化/正本パッケージ/",
    "構文化/K3_HDS日本語構文_v2/",
)


def 追跡一覧() -> list[str]:
    out = subprocess.check_output(
        ["git", "ls-files", "-z"],
        cwd=根,
    )
    return [x.decode("utf-8") for x in out.split(b"\0") if x]


def 監査() -> list[str]:
    誤り: list[str] = []
    for 相対 in 追跡一覧():
        if 相対 in 例外経路:
            continue
        対象 = 根 / 相対
        lower = 相対.lower()
        if lower.endswith(".zip") and any(相対.startswith(prefix) for prefix in 禁止アーカイブ接頭辞):
            誤り.append("公開禁止の変換済みアーカイブ: " + 相対)
            continue
        if lower.endswith(".zip.sha256") and any(相対.startswith(prefix) for prefix in 禁止アーカイブ接頭辞):
            誤り.append("公開禁止アーカイブの照合値: " + 相対)
            continue
        if 対象.suffix.lower() not in {".md", ".txt", ".py", ".json", ".yml", ".yaml", ".toml"}:
            continue
        try:
            内容 = 対象.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for 禁止 in 禁止文字列:
            if 禁止 in 内容:
                誤り.append(f"公開境界禁止文字列:{相対}:{禁止}")
    return 誤り


def main() -> int:
    誤り = 監査()
    if 誤り:
        print("公開境界監査: 失敗")
        for 項目 in 誤り:
            print("- " + 項目)
        return 1
    print("公開境界監査: 合格")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
