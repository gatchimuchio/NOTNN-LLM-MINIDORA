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
from minidora.模型 import (  # noqa: E402
    LLM成立規定リポジトリ,
    LLM成立規定参照コミット,
    LLM成立規定版,
    MINIDORA模型核,
)
from minidora import Layer0, 計算実行器  # noqa: E402


EXPECTED_REPOSITORY = "https://github.com/gatchimuchio/NOTNN-LLM-MINIDORA"
EXPECTED_SPEC_REPO = "https://github.com/gatchimuchio/LLM-Constitutive-Specification"
EXPECTED_SPEC_COMMIT = "e94a13ba32208aabd9dc88b6de320872963725be"
EXPECTED_SPEC_VERSION = "2026-08-26-成立規定-2"
EXPECTED_MINIDORA_VERSION = "0.4.0"
EXPECTED_BASE_LANGUAGE = "ja"

REQUIRED_PATHS = (
    "README.md",
    "REFERENCES.md",
    "AGENTS.md",
    "pyproject.toml",
    "LICENSE",
    "NOTICE",
    ".github/README.md",
    ".github/workflows/ci.yml",
    "src/README.md",
    "tests/README.md",
    "tools/README.md",
    "docs/README.md",
    "artifacts/README.md",
    "設計/README.md",
    "設計/02_大規模言語模型成立契約.md",
    "設計/旧/02_Layer0責任契約_v4.md",
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
    "構文化/MINIDORA_v0.4/README.md",
    "評価/README.md",
    "評価/PROTOTYPE_COMPLETION_2026-08-22.md",
    "評価/GPQA_Diamond_PROTOTYPE_BASELINE_2026-08-22.json",
    "src/minidora/模型.py",
    "src/minidora/計算実行器.py",
    "src/minidora/layer0.py",
    "src/minidora/旧_layer0_v03.py",
    "src/minidora/runtime.py",
    "src/minidora/runtime_v03.py",
    "src/minidora/hds_compiler.py",
    "src/minidora/hds_compiler_v1.py",
    "tests/test_模型.py",
    "tests/test_layer0.py",
)

CORE_MARKDOWN = (
    "README.md",
    "REFERENCES.md",
    "AGENTS.md",
    "src/README.md",
    "tests/README.md",
    "設計/README.md",
    "設計/02_大規模言語模型成立契約.md",
    "設計/05_完成判定関門.md",
    "設計/07_HDS_IR入力契約.md",
    "設計/09_公開HDS_Compiler仕様.md",
    "構文化/MINIDORA_v0.4/README.md",
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


def _check_model_core(errors: list[str]) -> None:
    model_file = _text("src/minidora/模型.py")
    for required in (
        "class 言語状態",
        "class 言語対応",
        "class 文脈付き言語状態",
        "class 成立差",
        "class MINIDORA模型核",
        "勝手に一候補へ確定しない",
    ):
        if required not in model_file:
            errors.append(f"模型.py: v0.4模型核必須境界欠落: {required}")
    for forbidden in ("from .hds_", "from .layer0", "import torch", "import transformers"):
        if forbidden in model_file:
            errors.append(f"模型.py: 模型核独立性に反する依存: {forbidden}")

    if Layer0 is not 計算実行器:
        errors.append("Layer0旧名が計算実行器互換aliasではない")
    if not isinstance(MINIDORA模型核(), MINIDORA模型核):
        errors.append("MINIDORA模型核を構築できない")
    if (ROOT / "設計" / "02_Layer0責任契約.md").exists():
        errors.append("旧Layer0責任契約が現行設計pathに残っている")


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
    if urls.get("LLM Constitutive Specification") != EXPECTED_SPEC_REPO:
        errors.append("pyproject.toml: LLM成立規定URLが期待値と不一致")

    if LLM成立規定リポジトリ != EXPECTED_SPEC_REPO:
        errors.append("模型.py: 上流正本Repository定数が期待値と不一致")
    if LLM成立規定参照コミット != EXPECTED_SPEC_COMMIT:
        errors.append("模型.py: 上流正本参照commitが期待値と不一致")
    if LLM成立規定版 != EXPECTED_SPEC_VERSION:
        errors.append("模型.py: 上流正本版が期待値と不一致")

    active_reference_documents = (
        "README.md",
        "REFERENCES.md",
        "AGENTS.md",
        "src/README.md",
        "設計/README.md",
        "設計/02_大規模言語模型成立契約.md",
        "構文化/MINIDORA_v0.4/README.md",
    )
    for path in active_reference_documents:
        text = _text(path)
        if EXPECTED_SPEC_REPO not in text:
            errors.append(f"{path}: 上流LLM成立規定URL欠落")

    pinned_documents = (
        "REFERENCES.md",
        "AGENTS.md",
        "src/README.md",
        "設計/README.md",
        "設計/02_大規模言語模型成立契約.md",
        "構文化/MINIDORA_v0.4/README.md",
    )
    for path in pinned_documents:
        text = _text(path)
        if EXPECTED_SPEC_COMMIT not in text:
            errors.append(f"{path}: 上流正本参照commit欠落")
        if EXPECTED_SPEC_VERSION not in text:
            errors.append(f"{path}: 上流正本版欠落")

    readme = _text("README.md")
    for required in ("MINIDORA v0.4", "PROTOTYPE COMPLETE", "v0.4大規模性", "再測定要", "計算実行器"):
        if required not in readme:
            errors.append(f"README.md: v0.4境界欠落: {required}")

    evaluation = _text("評価/README.md")
    if "PROTOTYPE COMPLETE" not in evaluation or "製品・最終完成" not in evaluation:
        errors.append("評価/README.md: プロトタイプ完成と最終完成の分離が欠落")

    legacy = _text("構文化/MINIDORA_v0.2/README.md")
    if "LEGACY" not in legacy:
        errors.append("構文化/MINIDORA_v0.2/README.md: Legacy境界が不明確")

    _check_model_core(errors)
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
    print(f"LLM_CONSTITUTIVE_SPEC_VERSION={LLM成立規定版}")
    print(f"LLM_CONSTITUTIVE_SPEC_COMMIT={LLM成立規定参照コミット}")
    print(f"BASE_LANGUAGE={EXPECTED_BASE_LANGUAGE}")
    print("MODEL_CORE=PASS")
    print("LEGACY_LAYER0_ROLE=COMPUTE_EXECUTOR")
    print("HDS_IR_ROLE=SEMANTIC_OPERATIONAL_OUTER")
    print("PUBLIC_HDS_COMPILER=PASS")
    print("V03_HISTORY_PRESERVED=PASS")
    print("WORKFLOW_BRANCH_POLICY=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
