# -*- coding: utf-8 -*-
"""日本語基底の詳細監査。

現役実装・試験・道具について、自己定義した識別子・内部辞書鍵・公開APIに
旧英語意味語が残っていないかを AST とパスから検査する。
外部仕様、Python/標準ライブラリ名、import された外部名、薄い互換入口は対象外。
"""
from __future__ import annotations

import ast
from pathlib import Path
import re

根 = Path(__file__).resolve().parents[1]
日本語文字 = re.compile(r"[ぁ-んァ-ヶ一-龠々]")

旧英語意味語 = {
    "core", "module", "capability", "compiler", "architecture", "pipeline",
    "runtime", "gate", "scope", "solver", "helper", "benchmark", "fallback",
    "registry", "trace", "checkpoint", "manifest", "inventory", "candidate",
    "relation", "state", "action", "result", "source", "summary", "choice",
    "context", "reference", "projection", "semantic", "reasoning", "effort",
    "adapter", "model", "language", "roundtrip", "dependency", "normalization",
    "budget", "priority", "roles", "role", "graph", "data", "verifier", "evidence",
    "quality", "replay", "capture", "compare", "eval", "residual", "retrieval",
    "route", "confidence", "integration", "unknown", "slots", "slot", "working",
    "subject", "boundary", "chain", "fidelity", "qualifiers", "qualifier", "polarity",
    "preservation", "standard", "tokens", "token", "contract",
}
外部固定識別子 = {
    "main", "setUp", "tearDown", "setUpClass", "tearDownClass",
    "do_GET", "do_POST", "log_message",
}
外部略号 = {"HDS", "K3", "GPQA", "HTTP", "JSON", "SHA", "URL", "CSV", "IR", "ABI", "CLI", "PMC"}
外部固定文字列 = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}


def 互換入口か(対象: Path) -> bool:
    try:
        先頭 = 対象.read_text(encoding="utf-8")[:1000]
    except (OSError, UnicodeDecodeError):
        return False
    return "互換入口" in 先頭 or "互換案内" in 先頭


def 現役Python一覧() -> list[Path]:
    結果: list[Path] = []
    for 基点 in (根 / "src/minidora", 根 / "tests", 根 / "tools"):
        if not 基点.exists():
            continue
        for 対象 in 基点.rglob("*.py"):
            相対 = 対象.relative_to(根).as_posix()
            if 相対.startswith(("docs/", "artifacts/")):
                continue
            if 対象.name == "日本語基底詳細監査.py" or 互換入口か(対象):
                continue
            結果.append(対象)
    return sorted(結果)


def 英字部分群(名前: str) -> list[str]:
    部分群: list[str] = []
    for 英字列 in re.findall(r"[A-Za-z][A-Za-z0-9]*", 名前):
        小片 = re.findall(r"[A-Z]+(?=[A-Z][a-z]|\d|$)|[A-Z]?[a-z]+|[A-Z]+|\d+", 英字列)
        部分群.extend(小片 or [英字列])
    return 部分群


def 旧意味語を含む(名前: str) -> list[str]:
    発見: list[str] = []
    for 部分 in 英字部分群(名前):
        if 部分 in 外部略号:
            continue
        小文字 = 部分.lower()
        if 小文字 in 旧英語意味語 and 小文字 not in 発見:
            発見.append(小文字)
    return 発見


def パス監査(誤り: list[str]) -> None:
    for 対象 in 現役Python一覧():
        相対 = 対象.relative_to(根).as_posix()
        幹 = 対象.stem[5:] if 対象.stem.startswith("test_") else 対象.stem
        残存 = 旧意味語を含む(幹)
        if 残存:
            誤り.append(f"現役パスに旧英語意味語: {相対}: {','.join(残存)}")
        if 対象.name not in {"__init__.py", "__main__.py", "api.py"} and not 日本語文字.search(幹):
            誤り.append(f"現役Pythonファイル名が日本語正本ではない: {相対}")


def _対象識別子群(対象: ast.AST) -> list[tuple[str, int, str]]:
    結果: list[tuple[str, int, str]] = []
    def 追加(節: ast.AST, 種別: str) -> None:
        行 = int(getattr(節, "lineno", 0) or 0)
        if isinstance(節, ast.Name):
            結果.append((節.id, 行, 種別))
        elif isinstance(節, (ast.Tuple, ast.List)):
            for 要素 in 節.elts:
                追加(要素, 種別)
        elif isinstance(節, ast.Attribute) and isinstance(節.value, ast.Name) and 節.value.id in {"self", "cls"}:
            結果.append((節.attr, 行, "自己属性識別子"))
    追加(対象, "代入識別子")
    return 結果


def 識別子監査(誤り: list[str]) -> None:
    for 対象 in 現役Python一覧():
        相対 = 対象.relative_to(根).as_posix()
        try:
            木 = ast.parse(対象.read_text(encoding="utf-8"), filename=相対)
        except (SyntaxError, UnicodeDecodeError) as 例外:
            誤り.append(f"Python構文解析失敗: {相対}:{例外}")
            continue

        # 規定3.4: 実際に標準HTMLParserを継承するクラスの固定フックだけを除外する。
        # 同名の自作関数や、引数・自己属性までは除外しない。
        HTML解析器名 = {
            項目.asname or 項目.name
            for 節 in ast.walk(木)
            if isinstance(節, ast.ImportFrom) and 節.module == "html.parser"
            for 項目 in 節.names if 項目.name == "HTMLParser"
        }
        外部定義 = {
            (関数.lineno, 関数.name)
            for 型 in ast.walk(木) if isinstance(型, ast.ClassDef)
            and any(isinstance(基底, ast.Name) and 基底.id in HTML解析器名 for 基底 in 型.bases)
            for 関数 in 型.body if isinstance(関数, (ast.FunctionDef, ast.AsyncFunctionDef))
            and 関数.name == "handle_data"
        }
        # 規定3.7/3.8: 依頼対訳の原語表層。内部の意味鍵を英語にする例外ではない。
        外部対訳鍵 = set()
        if 相対 == "src/minidora/多言語変換.py":
            for 関数 in 木.body:
                if not isinstance(関数, ast.FunctionDef) or 関数.name != "_依頼を読む":
                    continue
                for 代入 in ast.walk(関数):
                    if not isinstance(代入, ast.Assign) or not isinstance(代入.value, ast.Dict):
                        continue
                    if not any(isinstance(先, ast.Name) and 先.id == "英語対象語対応" for 先 in 代入.targets):
                        continue
                    for 鍵, 値 in zip(代入.value.keys, 代入.value.values):
                        if isinstance(鍵, ast.Constant) and 鍵.value == "the result" and isinstance(値, ast.Constant) and 値.value == "その結果":
                            外部対訳鍵.add(id(鍵))

        # 公開済みv1監査記録との交換鍵。内部の任意辞書には適用しない。
        if 相対 == "tools/GLM重み流監査.py":
            for 関数 in 木.body:
                if not isinstance(関数, ast.FunctionDef) or 関数.name != "断片を監査":
                    continue
                for 返却 in ast.walk(関数):
                    if not isinstance(返却, ast.Return) or not isinstance(返却.value, ast.Dict):
                        continue
                    対応 = list(zip(返却.value.keys, 返却.value.values))
                    if not any(isinstance(鍵, ast.Constant) and 鍵.value == "schema"
                               and isinstance(値, ast.Constant) and 値.value == "minidora.glm.weight_payload_audit.v1"
                               for 鍵, 値 in 対応):
                        continue
                    for 鍵, _ in 対応:
                        if isinstance(鍵, ast.Constant) and 鍵.value == "source_url":
                            外部対訳鍵.add(id(鍵))

        検査済み: set[tuple[int, str, str]] = set()
        def 検査(名前: str, 行: int, 種別: str) -> None:
            if not 名前 or 名前 in 外部固定識別子:
                return
            if 種別 == "定義識別子" and (行, 名前) in 外部定義:
                return
            if 名前.startswith("__") and 名前.endswith("__"):
                return
            意味名 = 名前[5:] if 名前.startswith("test_") else 名前
            残存 = 旧意味語を含む(意味名)
            if not 残存:
                return
            鍵 = (行, 種別, 名前)
            if 鍵 in 検査済み:
                return
            検査済み.add(鍵)
            誤り.append(f"{種別}に旧英語意味語: {相対}:{行}:{名前}:{','.join(残存)}")

        for 節 in ast.walk(木):
            行 = int(getattr(節, "lineno", 0) or 0)
            if isinstance(節, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                検査(節.name, 行, "定義識別子")
            if isinstance(節, ast.arg):
                検査(節.arg, 行, "引数識別子")
            if isinstance(節, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
                対象群 = 節.targets if isinstance(節, ast.Assign) else [節.target]
                for 代入先 in 対象群:
                    for 名前, 行2, 種別 in _対象識別子群(代入先):
                        検査(名前, 行2, 種別)
            elif isinstance(節, (ast.For, ast.AsyncFor, ast.comprehension)):
                for 名前, 行2, 種別 in _対象識別子群(節.target):
                    検査(名前, 行2, 種別)
            elif isinstance(節, (ast.With, ast.AsyncWith)):
                for 項目 in 節.items:
                    if 項目.optional_vars:
                        for 名前, 行2, 種別 in _対象識別子群(項目.optional_vars):
                            検査(名前, 行2, 種別)
            elif isinstance(節, ast.ExceptHandler) and 節.name:
                検査(節.name, 行, "例外識別子")

            if isinstance(節, ast.Dict):
                for 鍵節 in 節.keys:
                    if not isinstance(鍵節, ast.Constant) or not isinstance(鍵節.value, str):
                        continue
                    if id(鍵節) in 外部対訳鍵:
                        continue
                    値 = 鍵節.value
                    if 値 in 外部固定文字列:
                        continue
                    残存 = 旧意味語を含む(値)
                    if 残存:
                        誤り.append(f"内部辞書鍵に旧英語意味語: {相対}:{getattr(鍵節, 'lineno', '?')}:{値}:{','.join(残存)}")

        for 節 in 木.body:
            if isinstance(節, (ast.Assign, ast.AnnAssign)):
                targets = 節.targets if isinstance(節, ast.Assign) else [節.target]
                if not any(isinstance(t, ast.Name) and t.id == "__all__" for t in targets):
                    continue
                値節 = 節.value
                if isinstance(値節, (ast.List, ast.Tuple, ast.Set)):
                    for 要素 in 値節.elts:
                        if isinstance(要素, ast.Constant) and isinstance(要素.value, str):
                            残存 = 旧意味語を含む(要素.value)
                            if 残存:
                                誤り.append(f"公開API名に旧英語意味語: {相対}:{要素.lineno}:{要素.value}:{','.join(残存)}")


def main() -> int:
    from 標準入出力 import 標準出力をUTF8化

    標準出力をUTF8化()
    誤り: list[str] = []
    パス監査(誤り)
    識別子監査(誤り)
    if 誤り:
        print("日本語基底詳細監査: 失敗")
        for 項目 in 誤り:
            print(f"- {項目}")
        print(f"日本語基底詳細監査: {len(誤り)}件")
        return 1
    print("日本語基底詳細監査: 合格")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
