from __future__ import annotations

from fractions import Fraction
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

from minidora import Layer0, ミニドラ, 計算実行器  # noqa: E402
from minidora.hds_compiler_v1 import 公開HDSコンパイラ  # noqa: E402
from minidora.規定参照 import (  # noqa: E402
    LLM成立規定リポジトリ,
    LLM成立規定参照コミット,
    LLM成立規定版,
    厳密LM中核,
)
from minidora.言語確率法則 import (  # noqa: E402
    EOS記号,
    MINIDORA厳密言語模型,
    最小厳密言語模型,
)


EXPECTED_REPOSITORY = "https://github.com/gatchimuchio/NOTNN-LLM-MINIDORA"
EXPECTED_SPEC_REPO = "https://github.com/gatchimuchio/LLM-Constitutive-Specification"
EXPECTED_SPEC_COMMIT = "debb83e091a705a5eac09ef4fb97a5b36305db6d"
EXPECTED_SPEC_VERSION = "2026-08-28-成立規定-7"
EXPECTED_MINIDORA_VERSION = "0.5.0"
EXPECTED_BASE_LANGUAGE = "ja"
EXPECTED_HDS_ARCHITECTURE = "v1.2"
EXPECTED_HDS_PIPELINE = "v1.3"

REQUIRED_PATHS = (
    "README.md", "REFERENCES.md", "AGENTS.md", "pyproject.toml",
    "LICENSE", "LICENSE-APACHE-2.0", "LICENSE-CC-BY-4.0", "NOTICE",
    ".github/workflows/ci.yml",
    "設計/README.md", "設計/02_大規模言語模型成立契約.md",
    "構文化/MINIDORA_v0.4/README.md", "構文化/MINIDORA_v0.5/README.md",
    "評価/README.md", "評価/MINIDORA_v0_5_厳密LM受入_2026-08-28.md",
    "評価/MINIDORA_v0_4_規模測定_v2_2026-08-26.md",
    "src/minidora/規定参照.py", "src/minidora/言語確率法則.py",
    "src/minidora/模型_v05.py", "src/minidora/模型.py", "src/minidora/runtime.py",
    "src/minidora/計算実行器.py", "src/minidora/hds_compiler_v1.py",
    "tests/test_言語確率法則.py", "tests/test_v05_厳密LM統合.py", "tests/test_模型.py",
)

CORE_MARKDOWN = (
    "README.md", "REFERENCES.md", "AGENTS.md", "src/README.md",
    "設計/README.md", "設計/02_大規模言語模型成立契約.md",
    "構文化/MINIDORA_v0.5/README.md", "評価/README.md",
    "評価/MINIDORA_v0_5_厳密LM受入_2026-08-28.md",
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
    urls = project.get("urls", {})
    if urls.get("Repository") != EXPECTED_REPOSITORY:
        errors.append("pyproject.toml: Repository URL不整合")
    if urls.get("LLM Constitutive Specification") != EXPECTED_SPEC_REPO:
        errors.append("pyproject.toml: 上流LLM成立規定URL不整合")

    if LLM成立規定リポジトリ != EXPECTED_SPEC_REPO:
        errors.append("規定参照.py: 上流Repository不整合")
    if LLM成立規定参照コミット != EXPECTED_SPEC_COMMIT:
        errors.append("規定参照.py: 上流commit不整合")
    if LLM成立規定版 != EXPECTED_SPEC_VERSION:
        errors.append("規定参照.py: 上流版不整合")
    if 厳密LM中核 != ("完全言語状態空間", "整合した言語確率法則", "持続模型状態", "local-to-global接続"):
        errors.append("規定参照.py: v7厳密LM中核不整合")

    for path in ("README.md", "REFERENCES.md", "AGENTS.md", "src/README.md", "設計/README.md", "設計/02_大規模言語模型成立契約.md", "構文化/MINIDORA_v0.5/README.md"):
        text = _text(path)
        for required in (EXPECTED_SPEC_REPO, EXPECTED_SPEC_COMMIT, EXPECTED_SPEC_VERSION):
            if required not in text:
                errors.append(f"{path}: 上流参照欠落: {required}")


def _check_strict_lm(errors: list[str]) -> None:
    minimum = 最小厳密言語模型()
    audit = minimum.正規化監査()
    if not audit.合格:
        errors.append(f"最小厳密LM監査失敗: {audit.理由}")
    dist = minimum.次記号分布("任意")
    if sum(dist.辞書().values(), Fraction(0, 1)) != Fraction(1, 1):
        errors.append("最小厳密LM: 条件分布非正規化")
    if dist.確率_of(EOS記号) <= 0:
        errors.append("最小厳密LM: EOS確率非正")

    formed = MINIDORA厳密言語模型.形成(("猫。",) * 8 + ("犬。",), 次数=2)
    if not formed.正規化監査().合格:
        errors.append("形成済み厳密LM監査失敗")
    if formed.系列確率("猫。") <= formed.系列確率("犬。"):
        errors.append("形成済み厳密LM: 形成差が系列確率へ到達しない")
    restored = MINIDORA厳密言語模型.復元(formed.辞書化())
    if restored.状態sha256 != formed.状態sha256:
        errors.append("厳密LM模型状態: 保存復元hash不一致")

    source = _text("src/minidora/言語確率法則.py")
    for forbidden in ("import torch", "import transformers", "import numpy", "import random"):
        if forbidden in source:
            errors.append(f"厳密LM核に禁止依存: {forbidden}")
    if "Fraction" not in source or "EOS記号" not in source:
        errors.append("厳密LM核: exact probability / EOS境界欠落")


def _check_runtime_separation(errors: list[str]) -> None:
    body = ミニドラ()
    if body.模型核 is not body.能力模型核:
        errors.append("Runtime: 模型核互換aliasが能力模型核ではない")
    if body.言語模型核 is body.能力模型核:
        errors.append("Runtime: 厳密LM核と能力模型核が混同")
    if not body.言語模型監査().合格:
        errors.append("Runtime: 厳密LM監査不合格")
    text = _text("src/minidora/runtime.py")
    for required in ("self.言語模型核", "self.能力模型核", "候補scoreを確率へ読み替えて"):
        if required not in text:
            errors.append(f"runtime.py: 二核分離境界欠落: {required}")


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
    if Layer0 is not 計算実行器:
        errors.append("Layer0旧名が計算実行器aliasではない")


def _check_scale_and_history(errors: list[str]) -> None:
    root = _text("README.md")
    evaluation = _text("評価/README.md")
    for text_name, text in (("README.md", root), ("評価/README.md", evaluation)):
        if "Large" not in text or "再監査" not in text:
            errors.append(f"{text_name}: v0.5 Large再開放境界欠落")
    if "v0.4" not in evaluation or "自動継承しない" not in evaluation:
        errors.append("評価/README.md: v0.4規模履歴境界欠落")
    if not (ROOT / "評価/MINIDORA_v0_4_規模測定_v2_2026-08-26.md").exists():
        errors.append("v0.4規模履歴が欠損")


def _check_licenses(errors: list[str]) -> None:
    scope = _text("LICENSE")
    apache = _text("LICENSE-APACHE-2.0")
    cc = _text("LICENSE-CC-BY-4.0")
    readme = _text("README.md")
    for required in ("成果物の種類ごと", "Apache-2.0", "CC-BY-4.0"):
        if required not in scope:
            errors.append(f"LICENSE: 必須句欠落: {required}")
    if "Apache License" not in apache or "Version 2.0" not in apache:
        errors.append("LICENSE-APACHE-2.0不正")
    if "CC-BY-4.0" not in cc:
        errors.append("LICENSE-CC-BY-4.0不正")
    for required in ("Apache License 2.0", "CC-BY-4.0", "LICENSE-APACHE-2.0", "LICENSE-CC-BY-4.0"):
        if required not in readme:
            errors.append(f"README.md: ライセンス句欠落: {required}")


def audit() -> list[str]:
    errors: list[str] = []
    _check_required(errors)
    if errors:
        return errors
    _check_links(errors)
    _check_project(errors)
    _check_strict_lm(errors)
    _check_runtime_separation(errors)
    _check_hds(errors)
    _check_scale_and_history(errors)
    _check_licenses(errors)
    return errors


def main() -> int:
    _標準出力UTF8化()
    errors = audit()
    if errors:
        print("repository consistency: FAIL")
        for item in errors:
            print(f"- {item}")
        return 1
    print("repository consistency: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
