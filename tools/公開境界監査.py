# -*- coding: utf-8 -*-
"""公開リポジトリへ非公開内部理論の直接導線・固定参照・禁止配布物が再混入しないか検査する。"""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys

根 = Path(__file__).resolve().parents[1]

def _標準出力UTF8化() -> None:
    for 出力先 in (sys.stdout, sys.stderr):
        再設定 = getattr(出力先, "reconfigure", None)
        if 再設定 is not None:
            再設定(encoding="utf-8", errors="strict")


禁止文字列 = (
    "cognitive-engineering-foundations",
    "60131da52ba7931ed7f82c7648a74ac790f50d08",
    "神域原理",
    "トリニティ原理",
)

例外経路 = {
    "評価/公開境界_漏洩危険性監査_2026-09-20.md",
    "tools/公開境界監査.py",
}

高危険公開境界文書 = (
    "現行正本.md",
    "正本系統.md",
    "CURRENT_CANONICAL.md",
    "HDS_MINIDORA_現行正本.md",
    "設計/07_HDS_IR入力契約.md",
    "設計/09_公開HDS_Compiler仕様.md",
    "設計/10_HDS_Compiler_Architecture_v1.md",
    "設計/11_HDS_Compiler_Architecture_v1_1.md",
    "設計/12_HDS_Compiler_Architecture_v1_2.md",
    "設計/20_HDS_Compiler_Runtime射影契約_v0_15.md",
    "設計/26_HDS_Compiler_Pipeline_v1_3.md",
    "設計/26_HDS_Compiler_Pipeline_v1_4.md",
    "設計/26_HDS構文化器_処理系列_v1_3.md",
    "設計/27_HDS判断主体_MINIDORA終端接続_v1.md",
    "設計/28_HDS判断主体_MINIDORA出力Gate_v2.md",
    "設計/29_HDS_Compiler_作用差分構文化_v1_3.md",
    "設計/29_HDS構文化器_作用差分構文化_v1_3.md",
    "設計/31_MINIDORA_HDS統合判断主体_v1.md",
    "設計/32_MINIDORA_HDS監督介入制御_v1.md",
    "設計/58_MINIDORA_HDS実行主体_v1.md",
    "設計/59_MINIDORA_HDS内包統合_v2.md",
    "設計/60_MINIDORA_HDS自律接続_v3.md",
    "設計/61_MINIDORA_HDS原子的更新非退行_v1.md",
    "設計/62_MINIDORA_HDS非退行包絡_v1.md",
)

禁止変換成果接頭辞 = (
    "構文化/Llama3_HDS日本語構文_v1.0/",
    "構文化/Llama3_自己一貫性_HDS再構文化_v2/",
    "構文化/OLMo3_HDS日本語構文_v1.0/",
    "構文化/LLM横断_HDS日本語構文化_相対化ベンチマーク_v0_1/",
)

禁止生成成果物 = {
    "core24_repaired_ab_full.json",
    "gpqa_current_measurement.json",
    "gpqa_formal_parallel_full.json",
}

禁止生成成果接頭辞 = (
    "artifacts/refs_",
    "artifacts/gpqa_formal_",
    "artifacts/core_ab_",
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
        if 相対 in 禁止生成成果物 or any(相対.startswith(prefix) for prefix in 禁止生成成果接頭辞):
            誤り.append("default treeへ固定しない生成成果物: " + 相対)
            continue
        if 相対.startswith("構文化/") and (lower.endswith(".zip") or lower.endswith(".zip.sha256")):
            誤り.append("公開禁止の構文化アーカイブ: " + 相対)
            continue
        if 相対.startswith("構文化/") and "/教師固定/" in 相対:
            誤り.append("公開禁止の教師固定データ: " + 相対)
            continue
        if any(相対.startswith(prefix) for prefix in 禁止変換成果接頭辞):
            誤り.append("公開禁止の変換対応成果: " + 相対)
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
        if 相対 in 高危険公開境界文書:
            if "公開境界" not in 内容 or len(内容.encode("utf-8")) > 6000:
                誤り.append("高危険文書が公開境界スタブではない:" + 相対)
    return 誤り


def main() -> int:
    _標準出力UTF8化()
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
