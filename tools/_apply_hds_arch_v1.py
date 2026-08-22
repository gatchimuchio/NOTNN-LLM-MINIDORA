from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def patch(path: str, old: str, new: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"patch anchor not found: {path}: {old[:100]!r}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


# R: Compiler監査メタを検索語へ漏らさない。
patch(
    "src/minidora/hds_reference.py",
    "from .hds_effort import HDS努力水準\n",
    "from .hds_compiler_records import HDS_COMPILER_META_PREFIXES\nfrom .hds_effort import HDS努力水準\n",
)
patch(
    "src/minidora/hds_reference.py",
    '_QUERY_META_PREFIXES = ("制御.", "監査.", "目的.不足位置", "条件.検索極性")',
    '_QUERY_META_PREFIXES = HDS_COMPILER_META_PREFIXES + ("制御.", "目的.不足位置", "条件.検索極性")',
)

# 明示実行時のベンチも標準Architecture v1を使う。
patch(
    "tools/gpqa_measure_current.py",
    "from minidora.hds_compiler import 公開HDSコンパイラ\n",
    "from minidora.hds_compiler_v1 import 公開HDSコンパイラ\n",
)

# Front-End: 基礎Compilerが未対応の一般作用も、発話主体とは別の作用主体・対象として有限射影する。
patch(
    "src/minidora/hds_compiler_frontend.py",
    '_機構規則 = (\n    re.compile(r"(?:によって|を通じて|を介して|機構|メカニズム|経路|作用機序)"),\n    re.compile(r"\\b(?:through|via|by means of|mechanism|pathway|process)\\b", re.I),\n)\n\n_動態規則 = {',
    '_機構規則 = (\n    re.compile(r"(?:によって|を通じて|を介して|機構|メカニズム|経路|作用機序)"),\n    re.compile(r"\\b(?:through|via|by means of|mechanism|pathway|process)\\b", re.I),\n)\n_一般作用規則 = (\n    re.compile(r"(?P<s>[^。！？、]{1,80}?)(?:が|は)(?P<o>[^。！？、]{1,80}?)(?:を)?(?P<v>変える|変化させる|変更する|更新する|改善する|悪化させる)"),\n    re.compile(r"(?P<s>[^?!.;,]{1,100}?)\\s+(?P<v>changes?|transforms?|alters?|updates?|improves?|worsens?)\\s+(?P<o>[^?!.;,]{1,100})", re.I),\n)\n\n_動態規則 = {',
)
patch(
    "src/minidora/hds_compiler_frontend.py",
    'def _関係端点(ir: HDSIR) -> tuple[tuple[str, ...], tuple[str, ...]]:\n',
    'def _一般作用端点(text: str) -> tuple[tuple[str, ...], tuple[str, ...]]:\n    for pattern in _一般作用規則:\n        match = pattern.search(text)\n        if match:\n            return _unique((match.group("s"),)), _unique((match.group("o"),))\n    return (), ()\n\n\ndef _関係端点(ir: HDSIR) -> tuple[tuple[str, ...], tuple[str, ...]]:\n',
)
patch(
    "src/minidora/hds_compiler_frontend.py",
    '    starts, ends = _関係端点(ir)\n    speakers = _該当表層(text, _発話主体規則)\n',
    '    starts, ends = _関係端点(ir)\n    if not starts and not ends:\n        starts, ends = _一般作用端点(text)\n    speakers = _該当表層(text, _発話主体規則)\n',
)
patch(
    "src/minidora/hds_compiler_frontend.py",
    '    add("監査.Architecture", "v1")\n    for kind, values in semantic.items():\n',
    '    add("監査.Architecture", "v1")\n    existing_kinds = {str(coord.種別) for coord in ir.座標}\n    if "対象.始点" not in existing_kinds:\n        for value in world.作用主体:\n            add("対象.作用主体", value)\n    if "対象.終点" not in existing_kinds:\n        for value in world.対象:\n            add("対象.作用対象", value)\n    for kind, values in semantic.items():\n',
)

# 設計09: Architecture v1 orchestratorを標準正本とする。
patch(
    "設計/09_公開HDS_Compiler仕様.md",
    "`src/minidora/hds_compiler.py` をMINIDORAの公開標準HDS Compiler正本とする。",
    "`src/minidora/hds_compiler_v1.py` をMINIDORAの公開標準HDS Compiler正本とする。`src/minidora/hds_compiler.py` は既存の基礎意味Projection互換層として保持する。",
)
patch(
    "設計/09_公開HDS_Compiler仕様.md",
    "## 4. R性能との関係",
    "詳細Architectureは [`10_HDS_Compiler_Architecture_v1.md`](10_HDS_Compiler_Architecture_v1.md) を正本とする。\n\n## 4. R性能との関係",
)

# 設計ガイドを同期する。
patch(
    "設計/README.md",
    "5. [`09_公開HDS_Compiler仕様.md`](09_公開HDS_Compiler仕様.md) — フル公開する標準Compilerの責任・非責任・性能改善境界を定める。\n6. [`06_主体主幹仕様.md`](06_主体主幹仕様.md) — turnを跨ぐ主体状態と主体整合Gateを定める。\n7. [`08_多言語_Trinity文脈契約.md`](08_多言語_Trinity文脈契約.md) — 日本語基底と、実務上必要な多言語表層・J/C/M文脈循環を定める。\n8. [`05_完成判定関門.md`](05_完成判定関門.md) — 上記を横断して、プロトタイプ以後の製品・最終完成条件を定める。",
    "5. [`09_公開HDS_Compiler仕様.md`](09_公開HDS_Compiler仕様.md) — フル公開する標準Compilerの責任・非責任・性能改善境界を定める。\n6. [`10_HDS_Compiler_Architecture_v1.md`](10_HDS_Compiler_Architecture_v1.md) — 座標・動態・暗黙知・論証・原理探索入力・監査要求を統合する公開Front-End Architectureを定める。\n7. [`06_主体主幹仕様.md`](06_主体主幹仕様.md) — turnを跨ぐ主体状態と主体整合Gateを定める。\n8. [`08_多言語_Trinity文脈契約.md`](08_多言語_Trinity文脈契約.md) — 日本語基底と、実務上必要な多言語表層・J/C/M文脈循環を定める。\n9. [`05_完成判定関門.md`](05_完成判定関門.md) — 上記を横断して、プロトタイプ以後の製品・最終完成条件を定める。",
)
patch(
    "設計/README.md",
    "- `src/minidora/hds_compiler.py` はフル公開対象であり、MINIDORAの通常の性能改善対象とする。",
    "- `src/minidora/hds_compiler_v1.py` と、その公開Front-End構成はフル公開対象であり、MINIDORAの通常の性能改善対象とする。`hds_compiler.py` は互換基礎Projectionとして保持する。",
)

# 整合性監査をArchitecture v1へ更新する。
patch(
    "tools/repository_consistency_check.py",
    "from minidora.hds_compiler import 公開HDSコンパイラ  # noqa: E402\n",
    "from minidora.hds_compiler_v1 import 公開HDSコンパイラ  # noqa: E402\n",
)
patch(
    "tools/repository_consistency_check.py",
    '    "設計/09_公開HDS_Compiler仕様.md",\n    "構文化/README.md",',
    '    "設計/09_公開HDS_Compiler仕様.md",\n    "設計/10_HDS_Compiler_Architecture_v1.md",\n    "構文化/README.md",',
)
patch(
    "tools/repository_consistency_check.py",
    '    "src/minidora/hds_compiler.py",\n    "tests/test_hds_compiler.py",',
    '    "src/minidora/hds_compiler.py",\n    "src/minidora/hds_compiler_v1.py",\n    "src/minidora/hds_compiler_frontend.py",\n    "src/minidora/hds_compiler_records.py",\n    "tests/test_hds_compiler.py",\n    "tests/test_hds_compiler_architecture_v1.py",',
)
patch(
    "tools/repository_consistency_check.py",
    '    "設計/09_公開HDS_Compiler仕様.md",\n    "構文化/README.md",',
    '    "設計/09_公開HDS_Compiler仕様.md",\n    "設計/10_HDS_Compiler_Architecture_v1.md",\n    "構文化/README.md",',
)
patch(
    "tools/repository_consistency_check.py",
    '    if "基底・規定言語" not in compiler_spec or "日本語" not in compiler_spec:\n        errors.append("設計/09: 日本語基底・規定言語が明示されていない")\n',
    '    if "基底・規定言語" not in compiler_spec or "日本語" not in compiler_spec:\n        errors.append("設計/09: 日本語基底・規定言語が明示されていない")\n\n    architecture = _text("設計/10_HDS_Compiler_Architecture_v1.md")\n    for required in ("公開Front-End Compiler", "固定次元禁止", "不可能性要求", "原理探索Front-End", "最終採否委譲", "HDS本体の上流導出規則"):\n        if required not in architecture:\n            errors.append(f"設計/10: Architecture v1必須境界欠落: {required}")\n    if getattr(公開HDSコンパイラ, "Architecture版", None) != "v1":\n        errors.append("公開HDS Compiler: Architecture版がv1ではない")\n',
)

print("HDS_COMPILER_ARCH_V1_PATCH=APPLIED")
