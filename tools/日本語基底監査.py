from __future__ import annotations

import ast
import json
from pathlib import Path
import re
import runpy
import sys


def _標準出力UTF8化() -> None:
    for 出力先 in (sys.stdout, sys.stderr):
        再設定 = getattr(出力先, "reconfigure", None)
        if 再設定 is not None:
            再設定(encoding="utf-8", errors="strict")


根 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(根 / "src"))

from minidora import 標準言語基底P  # noqa: E402
from minidora.HDS構文化器_v1 import 公開HDSコンパイラ  # noqa: E402


_日本語文字 = re.compile(r"[ぁ-んァ-ヶ一-龠々]")
_旧意味語 = re.compile(
    r"(?:^|_)(?:core|module|capability|compiler|architecture|pipeline|runtime|gate|scope|"
    r"solver|helper|benchmark|fallback|registry|trace|checkpoint|manifest|inventory|"
    r"candidate|relation|state|action|result|source|summary|choice|context|reference|"
    r"projection|semantic|reasoning|effort|adapter|model|language)(?:_|$)",
    re.IGNORECASE,
)
_外部固定識別子 = {
    "main",
    "setUp",
    "tearDown",
    "setUpClass",
    "tearDownClass",
    "do_GET",
    "do_POST",
    "log_message",
}
_外部固定ファイル = {
    "__init__.py",
    "__main__.py",
    "api.py",
}
_現行説明資料 = (
    "現行正本.md",
    "参照正本.md",
    "設計/README.md",
    "src/README.md",
    "tests/README.md",
    "tools/README.md",
    "製品版/README.md",
)
_旧状態値 = {
    "PROVISIONAL_BY_DEFAULT",
    "CLOSED_FOR_OPERATION",
    "STRUCTURED_PUBLIC_PROJECTION",
    "FULL_FIELD_ACTIVE",
    "PARTIALLY_ARTICULATED",
    "MEANING_PRESERVED",
    "UNFORMED",
    "SHADOW",
    "PATTERN",
    "MECHANISM_CANDIDATE",
    "PRINCIPLE_CANDIDATE",
    "STANDARD_RELATIONS",
    "FORMED_RELATIONS",
    "PRIMARY_CAPABILITY_ACTIONS",
}


def _日本語を含む(名前: str) -> bool:
    return bool(_日本語文字.search(名前))


def _文字ファイル(対象: Path) -> str:
    try:
        return 対象.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return ""


def _互換入口(対象: Path) -> bool:
    内容 = _文字ファイル(対象)[:800]
    return "互換入口" in 内容 or "互換案内" in 内容


def _履歴または外部境界(対象: Path) -> bool:
    相対 = 対象.relative_to(根).as_posix()
    if 相対.startswith(("docs/", "artifacts/", "設計/旧/", "構文化/正本パッケージ/")):
        return True
    if "/web/" in 相対:
        return True
    if 対象.name.startswith("README.en."):
        return True
    if 対象.name.startswith("旧_"):
        return True
    return False


def _現役Python一覧() -> list[Path]:
    対象群: list[Path] = []
    for 基点 in (根 / "src/minidora", 根 / "tests", 根 / "tools"):
        for 対象 in 基点.rglob("*.py"):
            if _履歴または外部境界(対象) or _互換入口(対象):
                continue
            対象群.append(対象)
    return sorted(対象群)


def _現役パス監査(誤り: list[str]) -> None:
    for 対象 in _現役Python一覧():
        相対 = 対象.relative_to(根).as_posix()
        if 対象.name in _外部固定ファイル or 対象.name == "README.md":
            continue
        幹 = 対象.stem
        if 幹.startswith("test_"):
            幹 = 幹[5:]
        if _日本語を含む(幹):
            continue
        # HDS / K3 / GLM / GPQA / HTTP 等の外部・既定略号だけでは、内部作用名の日本語正本化にならない。
        誤り.append(f"現役Pythonファイル名が日本語正本ではない: {相対}")

    ワークフロー = 根 / ".github/workflows"
    if ワークフロー.exists():
        for 対象 in sorted(ワークフロー.glob("*.yml")):
            if not _日本語を含む(対象.stem):
                誤り.append(f"現役ワークフロー名が日本語正本ではない: {対象.relative_to(根).as_posix()}")

    設計 = 根 / "設計"
    if 設計.exists():
        for 対象 in sorted(設計.glob("*.md")):
            if _互換入口(対象) or 対象.name == "README.md":
                continue
            if not _日本語を含む(対象.stem):
                誤り.append(f"現役設計文書名が日本語正本ではない: {対象.relative_to(根).as_posix()}")


def _独自識別子監査(誤り: list[str]) -> None:
    for 対象 in _現役Python一覧():
        相対 = 対象.relative_to(根).as_posix()
        内容 = _文字ファイル(対象)
        try:
            木 = ast.parse(内容, filename=相対)
        except SyntaxError as 例外:
            誤り.append(f"Python構文解析失敗: {相対}: {例外}")
            continue

        for 節 in ast.walk(木):
            if isinstance(節, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                名前 = 節.name
                if 名前.startswith("__") and 名前.endswith("__"):
                    continue
                if 名前 in _外部固定識別子:
                    continue
                if 名前.startswith("test_"):
                    意味名 = 名前[5:]
                    if not _日本語を含む(意味名):
                        誤り.append(f"試験識別子が日本語正本ではない: {相対}:{節.lineno}:{名前}")
                    continue
                if _旧意味語.search(名前):
                    誤り.append(f"独自識別子に旧英語意味語が残存: {相対}:{節.lineno}:{名前}")

        if 対象.name != "日本語基底監査.py":
            for 節 in ast.walk(木):
                if isinstance(節, ast.Constant) and isinstance(節.value, str) and 節.value in _旧状態値:
                    誤り.append(f"内部状態値が旧英語正本のまま: {相対}:{getattr(節, 'lineno', '?')}:{節.value}")


def _現行説明資料監査(誤り: list[str]) -> None:
    禁止語 = re.compile(
        r"\b(?:Core|Module|Capability|Compiler|Architecture|Pipeline|Runtime|Gate|scope|solver|helper|fallback|registry|checkpoint|manifest|inventory)\b"
    )
    for 相対 in _現行説明資料:
        対象 = 根 / 相対
        if not 対象.exists():
            誤り.append(f"現行説明資料欠落: {相対}")
            continue
        for 行番号, 行 in enumerate(_文字ファイル(対象).splitlines(), 1):
            if not 禁止語.search(行):
                continue
            if any(印 in 行 for 印 in ("旧", "互換", "外部原語", "外部名", "正式名")):
                continue
            誤り.append(f"現行説明資料で旧英語意味語が主語化: {相対}:{行番号}:{行.strip()}")


def 監査() -> list[str]:
    誤り: list[str] = []

    if 標準言語基底P.規定言語 != "日本語":
        誤り.append("言語基底P: 規定言語が日本語ではない")
    if 標準言語基底P.基底言語 != "日本語":
        誤り.append("言語基底P: 基底言語が日本語ではない")
    if 標準言語基底P.基底言語コード != "ja":
        誤り.append("言語基底P: 日本語外部互換コードがjaではない")

    構文化器 = 公開HDSコンパイラ()
    if 構文化器.規定言語 != "日本語":
        誤り.append("HDS構文化器: 規定言語が日本語ではない")
    if 構文化器.基底言語 != "日本語":
        誤り.append("HDS構文化器: 基底言語が日本語ではない")
    if 構文化器.基底言語コード != "ja":
        誤り.append("HDS構文化器: 日本語外部互換コードがjaではない")

    必須 = (
        "設計/00_日本語基底規定_v1.md",
        "設計/01_日本語正本語彙_v1.md",
        "設計/13_共有言語基底P仕様_v0_4.md",
        "設計/14_外部言語_日本語意味射影仕様_v0_4.md",
        "設計/29_HDS構文化器_作用差分構文化_v1_3.md",
        "評価/評価契約_v2.md",
        "現行正本.md",
        "参照正本.md",
        "構文化/言語模型横断_日本語基底作用構文化_v3/README.md",
        "構文化/言語模型横断_日本語基底作用構文化_v3/構文化規約_v3.json",
    )
    for 相対 in 必須:
        if not (根 / 相対).exists():
            誤り.append(f"日本語基底必須資料欠落: {相対}")

    設計本文 = (根 / "設計/README.md").read_text(encoding="utf-8")
    if "PUBLICATION_BOUNDARY.md" not in (根 / "AGENTS.md").read_text(encoding="utf-8"):
        誤り.append("AGENTS: 公開境界方針への参照がない")
    if "00_日本語基底規定_v1.md" not in 設計本文:
        誤り.append("設計README: 日本語基底規定参照がない")
    if "01_日本語正本語彙_v1.md" not in 設計本文:
        誤り.append("設計README: 日本語正本語彙参照がない")

    構文化本文 = (根 / "構文化/README.md").read_text(encoding="utf-8")
    if "言語模型横断_日本語基底作用構文化_v3" not in 構文化本文:
        誤り.append("構文化README: 現行日本語基底構文化v3参照がない")

    規約 = json.loads((根 / "構文化/言語模型横断_日本語基底作用構文化_v3/構文化規約_v3.json").read_text(encoding="utf-8"))
    if 規約.get("規定言語") != "日本語":
        誤り.append("構文化v3: 規定言語が日本語ではない")

    _現役パス監査(誤り)
    _独自識別子監査(誤り)
    _現行説明資料監査(誤り)

    try:
        runpy.run_path(str(根 / "構文化/言語模型横断_日本語基底作用構文化_v3/構文化監査.py"), run_name="__main__")
    except Exception as 例外:
        誤り.append(f"構文化v3監査失敗: {例外}")

    return 誤り


def main() -> int:
    _標準出力UTF8化()
    誤り = 監査()
    if 誤り:
        print("日本語基底監査: 失敗")
        for 項目 in 誤り:
            print(f"- {項目}")
        print(f"違反件数: {len(誤り)}")
        return 1
    print("日本語基底監査: 合格")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
