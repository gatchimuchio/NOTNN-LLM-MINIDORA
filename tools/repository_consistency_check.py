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
sys.path.insert(0, str(ROOT / "src"))

from minidora import Layer0, 計算実行器  # noqa: E402
from minidora.hds_compiler_v1 import 公開HDSコンパイラ  # noqa: E402
from minidora.模型 import (  # noqa: E402
    LLM成立規定リポジトリ,
    LLM成立規定参照コミット,
    LLM成立規定版,
    MINIDORA模型核,
)
from minidora.規模測定 import 規模測定  # noqa: E402


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
    "README.md", "REFERENCES.md", "AGENTS.md", "pyproject.toml", "LICENSE", "LICENSE-APACHE-2.0", "LICENSE-CC-BY-4.0", "NOTICE",
    ".github/workflows/ci.yml",
    "設計/02_大規模言語模型成立契約.md", "設計/09_公開HDS_Compiler仕様.md",
    "設計/25_計算中間表現_実行境界_v1.md", "設計/26_HDS_Compiler_Pipeline_v1_3.md",
    "構文化/MINIDORA_v0.4/README.md",
    "評価/README.md", "評価/MINIDORA_v0_4_REBUILD_ACCEPTANCE_2026-08-26.md",
    "評価/計算中間表現_実行境界_v1_受入_2026-08-26.md", "評価/HDS_Compiler_Pipeline_v1_3_受入_2026-08-26.md",
    "評価/MINIDORA_v0_4_規模測定_v2_2026-08-26.md",
    "src/minidora/模型.py", "src/minidora/言語構造.py", "src/minidora/規模測定.py",
    "src/minidora/計算中間表現.py", "src/minidora/計算実行境界.py", "src/minidora/計算実行器.py",
    "src/minidora/hds_compiler_v1.py", "src/minidora/hds_compiler_pipeline_v1_3.py",
    "src/minidora/runtime_v03.py", "src/minidora/旧_layer0_v03.py",
    "tests/test_模型.py", "tests/test_模型関係域.py", "tests/test_規模測定.py",
    "tests/test_計算IR_ABI.py", "tests/test_hds_compiler_pipeline_v1_3.py",
)

CORE_MARKDOWN = (
    "README.md", "REFERENCES.md", "AGENTS.md", "src/README.md", "tests/README.md",
    "設計/README.md", "設計/02_大規模言語模型成立契約.md", "設計/09_公開HDS_Compiler仕様.md",
    "設計/25_計算中間表現_実行境界_v1.md", "設計/26_HDS_Compiler_Pipeline_v1_3.md",
    "構文化/MINIDORA_v0.4/README.md", "評価/README.md", "評価/MINIDORA_v0_4_規模測定_v2_2026-08-26.md",
)

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def _text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _check_required(errors: list[str]) -> None:
    for path in REQUIRED_PATHS:
        if not (ROOT / path).exists():
            errors.append(f"必須path欠落: {path}")


def _check_links(errors: list[str]) -> None:
    for path in CORE_MARKDOWN:
        source = ROOT / path
        if not source.exists():
            continue
        for raw_target in LINK_RE.findall(source.read_text(encoding="utf-8")):
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


def _check_project(errors: list[str]) -> None:
    project = tomllib.loads(_text("pyproject.toml")).get("project", {})
    if project.get("version") != EXPECTED_MINIDORA_VERSION:
        errors.append(f"MINIDORA version不整合: {project.get('version')!r}")
    license_meta = project.get("license", {})
    if not isinstance(license_meta, dict) or license_meta.get("file") != "LICENSE-APACHE-2.0":
        errors.append("pyproject.toml: software package licenseがLICENSE-APACHE-2.0を参照していない")
    urls = project.get("urls", {})
    if urls.get("Repository") != EXPECTED_REPOSITORY:
        errors.append("pyproject.toml: Repository URL不整合")
    if urls.get("LLM Constitutive Specification") != EXPECTED_SPEC_REPO:
        errors.append("pyproject.toml: 上流LLM成立規定URL不整合")

    if LLM成立規定リポジトリ != EXPECTED_SPEC_REPO:
        errors.append("模型.py: 上流Repository定数不整合")
    if LLM成立規定参照コミット != EXPECTED_SPEC_COMMIT:
        errors.append("模型.py: 上流参照commit不整合")
    if LLM成立規定版 != EXPECTED_SPEC_VERSION:
        errors.append("模型.py: 上流版不整合")

    for path in ("REFERENCES.md", "AGENTS.md", "src/README.md", "設計/README.md", "設計/02_大規模言語模型成立契約.md", "構文化/MINIDORA_v0.4/README.md"):
        text = _text(path)
        if EXPECTED_SPEC_REPO not in text:
            errors.append(f"{path}: 上流URL欠落")
        if EXPECTED_SPEC_COMMIT not in text:
            errors.append(f"{path}: 上流commit欠落")
        if EXPECTED_SPEC_VERSION not in text:
            errors.append(f"{path}: 上流版欠落")


def _check_licenses(errors: list[str]) -> None:
    scope = _text("LICENSE")
    apache = _text("LICENSE-APACHE-2.0")
    cc = _text("LICENSE-CC-BY-4.0")
    notice = _text("NOTICE")
    readme = _text("README.md")

    for required in ("成果物の種類ごと", "Apache-2.0", "CC-BY-4.0", "デュアルライセンスではありません"):
        if required not in scope:
            errors.append(f"LICENSE: 適用範囲の必須句欠落: {required}")
    if "Apache License" not in apache or "Version 2.0" not in apache:
        errors.append("LICENSE-APACHE-2.0: Apache License 2.0全文ではない")
    if "CC-BY-4.0" not in cc or "creativecommons.org/licenses/by/4.0/legalcode" not in cc:
        errors.append("LICENSE-CC-BY-4.0: CC BY 4.0正式条件への参照がない")
    for required in ("Apache License 2.0", "Creative Commons Attribution 4.0 International", "デュアルライセンスではありません"):
        if required not in notice:
            errors.append(f"NOTICE: ライセンス分離の必須句欠落: {required}")
    for required in ("Apache License 2.0", "CC-BY-4.0", "LICENSE-APACHE-2.0", "LICENSE-CC-BY-4.0"):
        if required not in readme:
            errors.append(f"README.md: ライセンス分離の必須句欠落: {required}")


def _check_model(errors: list[str]) -> None:
    text = _text("src/minidora/模型.py")
    for required in (
        "class MINIDORA模型核", "正の成立差が一意", "class 順序連続関係", "class 有向関係整合",
        "class 肯否整合関係", "class 履歴近接関係", "class 条件結合関係",
    ):
        if required not in text:
            errors.append(f"模型.py: 必須境界欠落: {required}")
    for forbidden in ("from .hds_", "from .layer0", "import torch", "import transformers"):
        if forbidden in text:
            errors.append(f"模型.py: 模型核独立性違反: {forbidden}")
    if "hds_" in _text("src/minidora/言語構造.py").casefold():
        errors.append("言語構造.py: HDS依存逆流")
    if Layer0 is not 計算実行器:
        errors.append("Layer0旧名が計算実行器aliasではない")
    if not isinstance(MINIDORA模型核(), MINIDORA模型核):
        errors.append("MINIDORA模型核を構築できない")
    if (ROOT / "設計/02_Layer0責任契約.md").exists():
        errors.append("旧Layer0責任契約が現行pathへ復帰")


def _check_hds(errors: list[str]) -> None:
    if 公開HDSコンパイラ.基底言語 != EXPECTED_BASE_LANGUAGE:
        errors.append("公開HDS Compiler: 基底言語不整合")
    if getattr(公開HDSコンパイラ, "Architecture版", None) != EXPECTED_HDS_ARCHITECTURE:
        errors.append("公開HDS Compiler: Architecture版不整合")
    if getattr(公開HDSコンパイラ, "Pipeline版", None) != EXPECTED_HDS_PIPELINE:
        errors.append("公開HDS Compiler: Pipeline版不整合")
    semantic = 公開HDSコンパイラ().意味コンパイル("2+3")
    if semantic.手順 is not None or semantic.初期状態:
        errors.append("公開HDS Compiler: 意味正本へ計算P/初期状態混入")


def _check_scale(errors: list[str]) -> None:
    result = 規模測定()
    if result.大規模性状態 != EXPECTED_SCALE_STATUS:
        errors.append(f"規模測定status不整合: {result.大規模性状態!r}")
    state = result.状態域規模
    relation = result.関係域規模
    shared = result.共有適用規模
    if state.get("識別内部状態数") != state.get("試験状態数"):
        errors.append("規模測定: 状態域全識別未達")
    if relation.get("意味対応済み関係族数") != 17:
        errors.append("規模測定: 17一般関係族未達")
    if relation.get("識別関係構造数") != relation.get("関係構造生成試験数"):
        errors.append("規模測定: 関係構造全識別未達")
    for key in ("方向差が成立差へ到達", "肯否差が成立差へ到達", "履歴順序差が成立差へ到達", "条件結合差が成立差へ到達"):
        if not relation.get(key):
            errors.append(f"規模測定: {key} 未達")
    if not shared.get("関係実体再利用") or shared.get("成功率") != 1.0:
        errors.append("規模測定: 共有適用未達")

    root = _text("README.md")
    evaluation = _text("評価/README.md")
    for text_name, text in (("README.md", root), ("評価/README.md", evaluation)):
        if "局所成立候補" not in text:
            errors.append(f"{text_name}: 規模測定結果未反映")
    if "現代ニューラルLLM" not in root:
        errors.append("README.md: 物理規模同等性の否定境界欠落")


def _check_workflows(errors: list[str]) -> None:
    workflow_dir = ROOT / ".github/workflows"
    for path in sorted(workflow_dir.glob("*.y*ml")):
        if "chappie/" in path.read_text(encoding="utf-8"):
            errors.append(f"{path.relative_to(ROOT)}: 旧作業ブランチ参照")
    # 三面規模測定は再構築CIの受入責任。GPQA等の専用workflowへ強制しない。
    if "tools/規模測定.py" not in _text(".github/workflows/ci.yml"):
        errors.append("ci.yml: v0.4規模測定未接続")


def main() -> int:
    _標準出力UTF8化()
    errors: list[str] = []
    _check_required(errors)
    _check_project(errors)
    _check_licenses(errors)
    _check_model(errors)
    _check_hds(errors)
    _check_scale(errors)
    _check_links(errors)
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
    print("LICENSE_SPLIT=APACHE-2.0+CC-BY-4.0")
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
