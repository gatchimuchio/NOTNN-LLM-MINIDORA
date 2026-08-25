from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path
from urllib.parse import unquote


def _標準出力UTF8化() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="strict")


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
from minidora.規模測定 import 規模測定  # noqa: E402
from minidora import Layer0, 計算実行器  # noqa: E402


EXPECTED_REPOSITORY = "https://github.com/gatchimuchio/NOTNN-LLM-MINIDORA"
EXPECTED_SPEC_REPO = "https://github.com/gatchimuchio/LLM-Constitutive-Specification"
EXPECTED_SPEC_COMMIT = "e94a13ba32208aabd9dc88b6de320872963725be"
EXPECTED_SPEC_VERSION = "2026-08-26-成立規定-2"
EXPECTED_MINIDORA_VERSION = "0.4.0"
EXPECTED_BASE_LANGUAGE = "ja"
EXPECTED_HDS_ARCHITECTURE = "v1.2"
EXPECTED_HDS_PIPELINE = "v1.3"
EXPECTED_SCALE_STATUS = "局所成立候補"

REQUIRED_PATHS = (
    "README.md", "REFERENCES.md", "AGENTS.md", "pyproject.toml", "LICENSE", "NOTICE",
    ".github/README.md", ".github/workflows/ci.yml",
    "src/README.md", "tests/README.md", "tools/README.md", "docs/README.md", "artifacts/README.md",
    "設計/README.md", "設計/02_大規模言語模型成立契約.md", "設計/旧/02_Layer0責任契約_v4.md",
    "設計/03_日本語命令形P仕様.md", "設計/04_外部参照R仕様.md", "設計/05_完成判定関門.md",
    "設計/06_主体主幹仕様.md", "設計/07_HDS_IR入力契約.md", "設計/08_多言語_Trinity文脈契約.md",
    "設計/09_公開HDS_Compiler仕様.md", "設計/10_HDS_Compiler_Architecture_v1.md",
    "設計/11_HDS_Compiler_Architecture_v1_1.md", "設計/12_HDS_Compiler_Architecture_v1_2.md",
    "設計/25_計算中間表現_実行境界_v1.md", "設計/26_HDS_Compiler_Pipeline_v1_3.md",
    "構文化/README.md", "構文化/MINIDORA_v0.2/README.md", "構文化/MINIDORA_v0.3/README.md", "構文化/MINIDORA_v0.4/README.md",
    "評価/README.md", "評価/PROTOTYPE_COMPLETION_2026-08-22.md", "評価/GPQA_Diamond_PROTOTYPE_BASELINE_2026-08-22.json",
    "評価/計算中間表現_実行境界_v1_受入_2026-08-26.md", "評価/HDS_Compiler_Pipeline_v1_3_受入_2026-08-26.md",
    "評価/MINIDORA_v0_4_規模測定_v2_2026-08-26.md",
    "src/minidora/模型.py", "src/minidora/言語構造.py", "src/minidora/規模測定.py",
    "src/minidora/計算中間表現.py", "src/minidora/計算実行境界.py", "src/minidora/命令計算降下.py",
    "src/minidora/計算実行器.py", "src/minidora/layer0.py", "src/minidora/旧_layer0_v03.py", "src/minidora/runtime.py", "src/minidora/runtime_v03.py",
    "src/minidora/hds_compiler.py", "src/minidora/hds_compiler_v1.py", "src/minidora/hds_compiler_pipeline_v1_3.py",
    "tests/test_模型.py", "tests/test_模型関係域.py", "tests/test_規模測定.py", "tests/test_layer0.py", "tests/test_計算IR_ABI.py", "tests/test_hds_compiler_pipeline_v1_3.py",
)

CORE_MARKDOWN = (
    "README.md", "REFERENCES.md", "AGENTS.md", "src/README.md", "tests/README.md",
    "設計/README.md", "設計/02_大規模言語模型成立契約.md", "設計/05_完成判定関門.md",
    "設計/07_HDS_IR入力契約.md", "設計/09_公開HDS_Compiler仕様.md",
    "設計/25_計算中間表現_実行境界_v1.md", "設計/26_HDS_Compiler_Pipeline_v1_3.md",
    "構文化/MINIDORA_v0.4/README.md", "評価/README.md", "評価/MINIDORA_v0_4_規模測定_v2_2026-08-26.md",
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
    for path in sorted((ROOT / ".github" / "workflows").glob("*.y*ml")):
        text = path.read_text(encoding="utf-8")
        if "chappie/" in text:
            errors.append(f"{path.relative_to(ROOT)}: 正本main方針に反する旧作業ブランチ参照")
        if "tools/規模測定.py" not in text:
            errors.append(f"{path.relative_to(ROOT)}: v0.4規模測定がCIへ接続されていない")


def _check_model_core(errors: list[str]) -> None:
    model_file = _text("src/minidora/模型.py")
    for required in (
        "class 言語状態", "class 言語対応", "class 文脈付き言語状態", "class 成立差",
        "class MINIDORA模型核", "正の成立差が一意", "class 有向関係整合", "class 肯否整合関係",
        "class 履歴近接関係", "class 条件結合関係",
    ):
        if required not in model_file:
            errors.append(f"模型.py: v0.4模型核必須境界欠落: {required}")
    for forbidden in ("from .hds_", "from .layer0", "import torch", "import transformers"):
        if forbidden in model_file:
            errors.append(f"模型.py: 模型核独立性に反する依存: {forbidden}")

    language_structure = _text("src/minidora/言語構造.py")
    if "hds_" in language_structure.casefold():
        errors.append("言語構造.py: LLM模型核へHDS依存を逆流させている")

    if Layer0 is not 計算実行器:
        errors.append("Layer0旧名が計算実行器互換aliasではない")
    if not isinstance(MINIDORA模型核(), MINIDORA模型核):
        errors.append("MINIDORA模型核を構築できない")
    if (ROOT / "設計" / "02_Layer0責任契約.md").exists():
        errors.append("旧Layer0責任契約が現行設計pathに残っている")


def _check_hds_boundary(errors: list[str]) -> None:
    if 公開HDSコンパイラ.基底言語 != EXPECTED_BASE_LANGUAGE:
        errors.append("公開HDS Compiler: 基底言語が日本語(ja)ではない")
    if getattr(公開HDSコンパイラ, "Architecture版", None) != EXPECTED_HDS_ARCHITECTURE:
        errors.append("公開HDS Compiler: Architecture版がv1.2ではない")
    if getattr(公開HDSコンパイラ, "Pipeline版", None) != EXPECTED_HDS_PIPELINE:
        errors.append("公開HDS Compiler: Pipeline版がv1.3ではない")

    compiler = 公開HDSコンパイラ()
    semantic = compiler.意味コンパイル("2+3")
    if semantic.手順 is not None or semantic.初期状態:
        errors.append("公開HDS Compiler: 意味正本へ計算Pまたは初期状態が混入")


def _check_scale(errors: list[str]) -> None:
    result = 規模測定()
    if result.大規模性状態 != EXPECTED_SCALE_STATUS:
        errors.append(f"規模測定: status={result.大規模性状態!r}, expected={EXPECTED_SCALE_STATUS!r}")
    if result.状態域規模.get("識別内部状態数") != result.状態域規模.get("試験状態数"):
        errors.append("規模測定: 状態域の試験状態を全識別できていない")
    if result.関係域規模.get("意味対応済み関係族数") != 17:
        errors.append("規模測定: 17一般関係族を保持していない")
    if result.関係域規模.get("識別関係構造数") != result.関係域規模.get("関係構造生成試験数"):
        errors.append("規模測定: 関係構造の識別が全件通っていない")
    for key in ("方向差が成立差へ到達", "肯否差が成立差へ到達", "履歴順序差が成立差へ到達", "条件結合差が成立差へ到達"):
        if not result.関係域規模.get(key):
            errors.append(f"規模測定: 関係域必須差未到達: {key}")
    if not result.共有適用規模.get("関係実体再利用"):
        errors.append("規模測定: 共有適用で同一関係実体を再利用できていない")


def main() -> int:
    _標準出力UTF8化()
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

    for path in ("README.md", "REFERENCES.md", "AGENTS.md", "src/README.md", "設計/README.md", "設計/02_大規模言語模型成立契約.md", "構文化/MINIDORA_v0.4/README.md"):
        if EXPECTED_SPEC_REPO not in _text(path):
            errors.append(f"{path}: 上流LLM成立規定URL欠落")

    for path in ("REFERENCES.md", "AGENTS.md", "src/README.md", "設計/README.md", "設計/02_大規模言語模型成立契約.md", "構文化/MINIDORA_v0.4/README.md"):
        text = _text(path)
        if EXPECTED_SPEC_COMMIT not in text:
            errors.append(f"{path}: 上流正本参照commit欠落")
        if EXPECTED_SPEC_VERSION not in text:
            errors.append(f"{path}: 上流正本版欠落")

    readme = _text("README.md")
    for required in ("MINIDORA v0.4", "PROTOTYPE COMPLETE", "v0.4大規模性", "局所成立候補", "計算実行器", "Pipeline"):
        if required not in readme:
            errors.append(f"README.md: v0.4/Pipeline/規模境界欠落: {required}")

    evaluation = _text("評価/README.md")
    for required in ("PROTOTYPE COMPLETE", "製品・最終完成", "局所成立候補", "MINIDORA_v0_4_規模測定_v2_2026-08-26.md"):
        if required not in evaluation:
            errors.append(f"評価/README.md: 状態境界欠落: {required}")

    if "LEGACY" not in _text("構文化/MINIDORA_v0.2/README.md"):
        errors.append("構文化/MINIDORA_v0.2/README.md: Legacy境界が不明確")

    _check_model_core(errors)
    _check_hds_boundary(errors)
    _check_scale(errors)
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
    print("MODEL_RELATION_DOMAIN=STRUCTURED")
    print(f"LARGE_SCALE_STATUS={EXPECTED_SCALE_STATUS}")
    print("LEGACY_LAYER0_ROLE=COMPUTE_EXECUTOR")
    print("HDS_IR_ROLE=SEMANTIC_OPERATIONAL_OUTER")
    print(f"HDS_ARCHITECTURE={EXPECTED_HDS_ARCHITECTURE}")
    print(f"HDS_PIPELINE={EXPECTED_HDS_PIPELINE}")
    print("PUBLIC_HDS_COMPILER=PASS")
    print("V03_HISTORY_PRESERVED=PASS")
    print("WORKFLOW_BRANCH_POLICY=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
