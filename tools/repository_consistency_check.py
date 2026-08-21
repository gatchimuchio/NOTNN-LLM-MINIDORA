from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from minidora.layer0 import (  # noqa: E402
    LAYER0参照コミット,
    LAYER0仕様版,
    LAYER0正本リポジトリ,
    LAYER0機能責任,
)


EXPECTED_REPOSITORY = "https://github.com/gatchimuchio/NOTNN-LLM-MINIDORA"
EXPECTED_LAYER0_REPO = (
    "https://github.com/gatchimuchio/LLM-Layer-0-Functional-Compliance-Specification"
)
EXPECTED_LAYER0_COMMIT = "4adf86d13d7beb99fe5eaa9e240b22996ba3d3bc"
EXPECTED_LAYER0_VERSION = "v4.0-provisional"
EXPECTED_LAYER0_RESPONSIBILITIES = (
    "LINGUISTIC_ADDRESSABILITY",
    "CONTEXT_BOUND_STATE",
    "TRANSFORMATION_OR_COMPOSITION_CORE",
    "CONTEXT_DEPENDENT_RESULT_FORMATION",
    "RESULT_SURFACE",
)
EXPECTED_MINIDORA_VERSION = "0.3.0"

REQUIRED_PATHS = (
    "README.md",
    "REFERENCES.md",
    "AGENTS.md",
    "pyproject.toml",
    ".github/workflows/ci.yml",
    "設計/README.md",
    "設計/02_Layer0責任契約.md",
    "設計/03_日本語命令形P仕様.md",
    "設計/04_外部参照R仕様.md",
    "設計/05_完成判定関門.md",
    "設計/06_主体主幹仕様.md",
    "設計/07_HDS_IR入力契約.md",
    "設計/08_多言語_Trinity文脈契約.md",
    "構文化/README.md",
    "構文化/MINIDORA_v0.2/README.md",
    "構文化/MINIDORA_v0.3/README.md",
    "評価/README.md",
    "評価/PROTOTYPE_COMPLETION_2026-08-22.md",
    "評価/GPQA_Diamond_PROTOTYPE_BASELINE_2026-08-22.json",
    "docs/README.md",
    "docs/HDS_IR_NATIVE_K3.md",
    "artifacts/README.md",
    "tools/README.md",
    "tests/README.md",
    "src/minidora/layer0.py",
)

CORE_MARKDOWN = (
    "README.md",
    "REFERENCES.md",
    "AGENTS.md",
    "設計/README.md",
    "設計/02_Layer0責任契約.md",
    "設計/05_完成判定関門.md",
    "構文化/README.md",
    "構文化/MINIDORA_v0.2/README.md",
    "構文化/MINIDORA_v0.3/README.md",
    "評価/README.md",
    "docs/README.md",
    "docs/HDS_IR_NATIVE_K3.md",
    "artifacts/README.md",
    "tools/README.md",
    "tests/README.md",
)

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def _text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _check_local_links(path: str, errors: list[str]) -> None:
    source = ROOT / path
    text = source.read_text(encoding="utf-8")
    for raw_target in LINK_RE.findall(text):
        target = raw_target.strip().split(maxsplit=1)[0].strip("<>")
        if not target or target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        target = unquote(target.split("#", 1)[0])
        if not target:
            continue
        resolved = (source.parent / target).resolve()
        try:
            resolved.relative_to(ROOT.resolve())
        except ValueError:
            errors.append(f"{path}: リポジトリ外への相対リンク: {raw_target}")
            continue
        if not resolved.exists():
            errors.append(f"{path}: 壊れた相対リンク: {raw_target}")


def _check_workflows(errors: list[str]) -> None:
    workflow_dir = ROOT / ".github" / "workflows"
    for path in sorted(workflow_dir.glob("*.y*ml")):
        text = path.read_text(encoding="utf-8")
        if "chappie/" in text:
            errors.append(
                f"{path.relative_to(ROOT)}: 正本main方針に反する旧作業ブランチ参照"
            )


def main() -> int:
    errors: list[str] = []

    for path in REQUIRED_PATHS:
        if not (ROOT / path).exists():
            errors.append(f"必須path欠落: {path}")

    pyproject = tomllib.loads(_text("pyproject.toml"))
    project = pyproject.get("project", {})
    version = project.get("version")
    if version != EXPECTED_MINIDORA_VERSION:
        errors.append(
            f"MINIDORA version不整合: pyproject={version!r}, expected={EXPECTED_MINIDORA_VERSION!r}"
        )

    urls = project.get("urls", {})
    if urls.get("Repository") != EXPECTED_REPOSITORY:
        errors.append("pyproject.toml: Repository URLが期待値と不一致")
    if urls.get("Layer-0 Reference") != EXPECTED_LAYER0_REPO:
        errors.append("pyproject.toml: Layer-0 Reference URLが期待値と不一致")

    if LAYER0正本リポジトリ != EXPECTED_LAYER0_REPO:
        errors.append("Layer-0正本Repository定数が期待値と不一致")
    if LAYER0参照コミット != EXPECTED_LAYER0_COMMIT:
        errors.append("Layer-0参照commit定数が期待値と不一致")
    if LAYER0仕様版 != EXPECTED_LAYER0_VERSION:
        errors.append("Layer-0仕様版定数が期待値と不一致")
    if tuple(LAYER0機能責任) != EXPECTED_LAYER0_RESPONSIBILITIES:
        errors.append("Layer-0 5機能責任が正本期待値と不一致")

    reference_documents = (
        "README.md",
        "REFERENCES.md",
        "AGENTS.md",
        "設計/README.md",
        "設計/02_Layer0責任契約.md",
        "構文化/README.md",
        "構文化/MINIDORA_v0.2/README.md",
        "構文化/MINIDORA_v0.3/README.md",
    )
    for path in reference_documents:
        text = _text(path)
        if EXPECTED_LAYER0_REPO not in text:
            errors.append(f"{path}: Layer-0正本Repository URL欠落")

    pinned_documents = (
        "REFERENCES.md",
        "AGENTS.md",
        "設計/README.md",
        "設計/02_Layer0責任契約.md",
        "構文化/README.md",
        "構文化/MINIDORA_v0.3/README.md",
    )
    for path in pinned_documents:
        text = _text(path)
        if EXPECTED_LAYER0_COMMIT not in text:
            errors.append(f"{path}: Layer-0参照commit欠落")
        if EXPECTED_LAYER0_VERSION not in text:
            errors.append(f"{path}: Layer-0仕様版欠落")

    readme = _text("README.md")
    if "PROTOTYPE COMPLETE" not in readme:
        errors.append("README.md: PROTOTYPE COMPLETE状態が明示されていない")
    if "現行実装候補" in readme:
        errors.append("README.md: prototype完成後も『現行実装候補』表現が残っている")

    evaluation = _text("評価/README.md")
    if "PROTOTYPE COMPLETE" not in evaluation or "製品・最終完成" not in evaluation:
        errors.append("評価/README.md: プロトタイプ完成と最終完成の分離が欠落")

    legacy = _text("構文化/MINIDORA_v0.2/README.md")
    if "LEGACY" not in legacy or "現行MINIDORAはv0.3" not in legacy:
        errors.append("構文化/MINIDORA_v0.2/README.md: Legacy境界が不明確")

    for path in CORE_MARKDOWN:
        _check_local_links(path, errors)
    _check_workflows(errors)

    if errors:
        print("REPOSITORY_CONSISTENCY=FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("REPOSITORY_CONSISTENCY=PASS")
    print(f"MINIDORA_VERSION={EXPECTED_MINIDORA_VERSION}")
    print(f"LAYER0_VERSION={LAYER0仕様版}")
    print(f"LAYER0_REFERENCE_COMMIT={LAYER0参照コミット}")
    print(f"CHECKED_MARKDOWN={len(CORE_MARKDOWN)}")
    print("WORKFLOW_BRANCH_POLICY=PASS")
    print("LEGACY_BOUNDARY=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
