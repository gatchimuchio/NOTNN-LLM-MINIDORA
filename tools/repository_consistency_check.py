from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from minidora.hds_compiler_v1 import 公開HDSコンパイラ  # noqa: E402
from minidora.layer0 import (  # noqa: E402
    LAYER0参照コミット,
    LAYER0仕様版,
    LAYER0正本リポジトリ,
    LAYER0機能責任,
)


EXPECTED_REPOSITORY = "https://github.com/gatchimuchio/NOTNN-LLM-MINIDORA"
EXPECTED_LAYER0_REPO = "https://github.com/gatchimuchio/LLM-Layer-0-Functional-Compliance-Specification"
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
EXPECTED_BASE_LANGUAGE = "ja"

REQUIRED_PATHS = (
    "README.md",
    "REFERENCES.md",
    "AGENTS.md",
    "pyproject.toml",
    ".github/README.md",
    ".github/workflows/ci.yml",
    "src/README.md",
    "tests/README.md",
    "tools/README.md",
    "docs/README.md",
    "docs/HDS_IR_NATIVE_K3.md",
    "artifacts/README.md",
    "設計/README.md",
    "設計/02_Layer0責任契約.md",
    "設計/03_日本語命令形P仕様.md",
    "設計/04_外部参照R仕様.md",
    "設計/05_完成判定関門.md",
    "設計/06_主体主幹仕様.md",
    "設計/07_HDS_IR入力契約.md",
    "設計/08_多言語_Trinity文脈契約.md",
    "設計/09_公開HDS_Compiler仕様.md",
    "設計/10_HDS_Compiler_Architecture_v1.md",
    "設計/11_HDS_Compiler_Architecture_v1_1.md",
    "設計/12_HDS_Compiler_Architecture_v1_2.md",
    "構文化/README.md",
    "構文化/MINIDORA_v0.2/README.md",
    "構文化/MINIDORA_v0.3/README.md",
    "評価/README.md",
    "評価/PROTOTYPE_COMPLETION_2026-08-22.md",
    "評価/GPQA_Diamond_PROTOTYPE_BASELINE_2026-08-22.json",
    "src/minidora/layer0.py",
    "src/minidora/hds_compiler.py",
    "src/minidora/hds_compiler_v1.py",
    "src/minidora/hds_compiler_frontend.py",
    "src/minidora/hds_compiler_records.py",
    "src/minidora/hds_compiler_records_v1_1.py",
    "src/minidora/hds_compiler_records_v1_2.py",
    "src/minidora/hds_compiler_dynamics.py",
    "src/minidora/hds_compiler_tacit.py",
    "src/minidora/hds_compiler_failure.py",
    "src/minidora/hds_compiler_failure_bank.py",
    "src/minidora/hds_compiler_history.py",
    "src/minidora/hds_compiler_audit_ir.py",
    "tests/test_hds_compiler.py",
    "tests/test_hds_compiler_architecture_v1.py",
    "tests/test_hds_compiler_architecture_v1_1.py",
    "tests/test_hds_compiler_architecture_v1_2.py",
)

CORE_MARKDOWN = (
    "README.md",
    "REFERENCES.md",
    "AGENTS.md",
    ".github/README.md",
    "src/README.md",
    "tests/README.md",
    "tools/README.md",
    "docs/README.md",
    "docs/HDS_IR_NATIVE_K3.md",
    "artifacts/README.md",
    "設計/README.md",
    "設計/02_Layer0責任契約.md",
    "設計/05_完成判定関門.md",
    "設計/07_HDS_IR入力契約.md",
    "設計/08_多言語_Trinity文脈契約.md",
    "設計/09_公開HDS_Compiler仕様.md",
    "設計/10_HDS_Compiler_Architecture_v1.md",
    "設計/11_HDS_Compiler_Architecture_v1_1.md",
    "設計/12_HDS_Compiler_Architecture_v1_2.md",
    "構文化/README.md",
    "構文化/MINIDORA_v0.2/README.md",
    "構文化/MINIDORA_v0.3/README.md",
    "評価/README.md",
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
            errors.append(f"{path.relative_to(ROOT)}: 正本main方針に反する旧作業ブランチ参照")


def _check_language_and_hds_boundary(errors: list[str]) -> None:
    if 公開HDSコンパイラ.基底言語 != EXPECTED_BASE_LANGUAGE:
        errors.append("公開HDS Compiler: 基底言語が日本語(ja)ではない")

    agents = _text("AGENTS.md")
    for required in ("日本語をMINIDORAリポジトリの基底・規定言語", "実務上やむを得ない境界", "HDS公開境界"):
        if required not in agents:
            errors.append(f"AGENTS.md: 言語/HDS公開方針欠落: {required}")

    compiler_spec = _text("設計/09_公開HDS_Compiler仕様.md")
    if "フル公開" not in compiler_spec:
        errors.append("設計/09: HDS Compilerフル公開境界が明示されていない")
    if "HDS本体" not in compiler_spec or "非公開" not in compiler_spec:
        errors.append("設計/09: HDS本体非公開境界が明示されていない")
    if "基底・規定言語" not in compiler_spec or "日本語" not in compiler_spec:
        errors.append("設計/09: 日本語基底・規定言語が明示されていない")
    for required in ("Failure Signature Bank", "自動自己改変", "改善候補"):
        if required not in compiler_spec:
            errors.append(f"設計/09: v1.2公開境界欠落: {required}")

    architecture = _text("設計/10_HDS_Compiler_Architecture_v1.md")
    for required in ("公開Front-End Compiler", "固定次元禁止", "不可能性要求", "原理探索Front-End", "最終採否委譲", "HDS本体の上流導出規則"):
        if required not in architecture:
            errors.append(f"設計/10: Architecture v1必須境界欠落: {required}")

    architecture_v11 = _text("設計/11_HDS_Compiler_Architecture_v1_1.md")
    for required in ("Failure Signature", "状態遷移graph", "監査R probe", "CognitiveWorld差分", "fallback", "HDS本体の内部Gate判定アルゴリズム", "日本語"):
        if required not in architecture_v11:
            errors.append(f"設計/11: Architecture v1.1必須境界欠落: {required}")

    architecture_v12 = _text("設計/12_HDS_Compiler_Architecture_v1_2.md")
    for required in ("Failure Signature Bank", "独立Run", "改善候補", "自動自己改変", "HDS本体", "日本語", "旧記録保持"):
        if required not in architecture_v12:
            errors.append(f"設計/12: Architecture v1.2必須境界欠落: {required}")

    if getattr(公開HDSコンパイラ, "Architecture版", None) != "v1.2":
        errors.append("公開HDS Compiler: Architecture版がv1.2ではない")


def main() -> int:
    errors: list[str] = []

    for path in REQUIRED_PATHS:
        if not (ROOT / path).exists():
            errors.append(f"必須path欠落: {path}")

    pyproject = tomllib.loads(_text("pyproject.toml"))
    project = pyproject.get("project", {})
    version = project.get("version")
    if version != EXPECTED_MINIDORA_VERSION:
        errors.append(f"MINIDORA version不整合: pyproject={version!r}, expected={EXPECTED_MINIDORA_VERSION!r}")

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
        "README.md", "REFERENCES.md", "AGENTS.md", "src/README.md", "設計/README.md",
        "設計/02_Layer0責任契約.md", "構文化/README.md", "構文化/MINIDORA_v0.2/README.md",
        "構文化/MINIDORA_v0.3/README.md",
    )
    for path in reference_documents:
        if EXPECTED_LAYER0_REPO not in _text(path):
            errors.append(f"{path}: Layer-0正本Repository URL欠落")

    pinned_documents = (
        "REFERENCES.md", "AGENTS.md", "設計/README.md", "設計/02_Layer0責任契約.md",
        "構文化/README.md", "構文化/MINIDORA_v0.3/README.md",
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

    _check_language_and_hds_boundary(errors)
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
    print(f"BASE_LANGUAGE={EXPECTED_BASE_LANGUAGE}")
    print("PUBLIC_HDS_COMPILER=PASS")
    print("HDS_CORE_PRIVATE_BOUNDARY=PASS")
    print(f"CHECKED_MARKDOWN={len(CORE_MARKDOWN)}")
    print("WORKFLOW_BRANCH_POLICY=PASS")
    print("LEGACY_BOUNDARY=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
