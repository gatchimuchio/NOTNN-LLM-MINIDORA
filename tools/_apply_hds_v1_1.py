from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def patch(path: str, old: str, new: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"patch anchor not found: {path}: {old[:120]!r}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


# 1) R: 監査probeはprimaryへ混ぜずfallbackでのみ明示利用する。
patch(
    "src/minidora/hds_reference.py",
    "def HDS参照問合せ候補(ir: HDSIR, *, 最大候補数: int = 6) -> tuple[str, ...]:\n    return tuple(spec.問合せ for spec in _問合せ仕様(ir, 最大候補数=最大候補数))\n\n\ndef _縮退仕様(ir: HDSIR) -> tuple[_HDS問合せ仕様, ...]:\n",
    "def HDS参照問合せ候補(ir: HDSIR, *, 最大候補数: int = 6) -> tuple[str, ...]:\n    return tuple(spec.問合せ for spec in _問合せ仕様(ir, 最大候補数=最大候補数))\n\n\ndef _監査probe仕様(ir: HDSIR) -> tuple[_HDS問合せ仕様, ...]:\n    specs: list[_HDS問合せ仕様] = []\n    seen: set[str] = set()\n    for coord in ir.座標:\n        if str(coord.種別) != \"監査.R_query\":\n            continue\n        query = \" \".join(str(coord.内容).split()).strip()\n        key = query.casefold()\n        if not query or key in seen:\n            continue\n        seen.add(key)\n        specs.append(_HDS問合せ仕様(query, \"audit_probe\"))\n    return tuple(specs)\n\n\ndef _縮退仕様(ir: HDSIR) -> tuple[_HDS問合せ仕様, ...]:\n",
)
patch(
    "src/minidora/hds_reference.py",
    "    specs: list[_HDS問合せ仕様] = []\n    seen: set[str] = set(primary)\n    for label, choice in choices:\n",
    "    specs: list[_HDS問合せ仕様] = []\n    seen: set[str] = set(primary)\n\n    # 監査probeは高純度primaryが不足した時だけ使う。Compiler metaを通常queryへ混入させない。\n    for spec in _監査probe仕様(ir):\n        key = spec.問合せ.casefold()\n        if key in seen:\n            continue\n        seen.add(key)\n        specs.append(spec)\n\n    for label, choice in choices:\n",
)

# 2) 既存v1受入試験は現行Architecture版をv1.1へ更新する。
patch(
    "tests/test_hds_compiler_architecture_v1.py",
    '        self.assertEqual(self.compiler.Architecture版, "v1")\n',
    '        self.assertEqual(self.compiler.Architecture版, "v1.1")\n',
)

# 3) CLIは既存compiler表示を互換維持し、Architecture版だけ更新する。
patch(
    "src/minidora/__main__.py",
    '            "compiler_architecture": "v1",\n',
    '            "compiler_architecture": "v1.1",\n',
)

# 4) 公開APIへv1.1成果型を追加する。
patch(
    "src/minidora/__init__.py",
    "from .hds_compiler_records import (\n    HDS監査状態,\n    HDS原理段階,\n    HDS認知世界断片,\n    HDS監査項目,\n    HDS監査要求,\n    HDS原理探索要求,\n    HDS保持契約,\n    HDSCompiler成果,\n)\n",
    "from .hds_compiler_records import (\n    HDS監査状態,\n    HDS原理段階,\n    HDS認知世界断片,\n    HDS監査項目,\n    HDS監査要求,\n    HDS原理探索要求,\n    HDS保持契約,\n    HDSCompiler成果,\n)\nfrom .hds_compiler_records_v1_1 import (\n    HDS失敗署名状態,\n    HDS状態ノード,\n    HDS遷移辺,\n    HDS状態遷移図,\n    HDS暗黙知記録,\n    HDS失敗署名候補,\n    HDSチェックリスト項目,\n    HDS認知世界差分,\n    HDS監査参照候補,\n)\n",
)
patch(
    "src/minidora/__init__.py",
    '    "HDS監査状態", "HDS原理段階", "HDS認知世界断片", "HDS監査項目", "HDS監査要求", "HDS原理探索要求", "HDS保持契約", "HDSCompiler成果",\n',
    '    "HDS監査状態", "HDS原理段階", "HDS認知世界断片", "HDS監査項目", "HDS監査要求", "HDS原理探索要求", "HDS保持契約", "HDSCompiler成果",\n    "HDS失敗署名状態", "HDS状態ノード", "HDS遷移辺", "HDS状態遷移図", "HDS暗黙知記録", "HDS失敗署名候補", "HDSチェックリスト項目", "HDS認知世界差分", "HDS監査参照候補",\n',
)

# 5) 設計ガイドをv1.1正本へ接続する。v1文書は履歴として残す。
patch(
    "設計/README.md",
    "6. [`10_HDS_Compiler_Architecture_v1.md`](10_HDS_Compiler_Architecture_v1.md) — 座標・動態・暗黙知・論証・原理探索入力・監査要求を統合する公開Front-End Architectureを定める。\n7. [`06_主体主幹仕様.md`]",
    "6. [`10_HDS_Compiler_Architecture_v1.md`](10_HDS_Compiler_Architecture_v1.md) — v1の公開Front-End Architecture履歴を保持する。\n7. [`11_HDS_Compiler_Architecture_v1_1.md`](11_HDS_Compiler_Architecture_v1_1.md) — Failure Signature、状態遷移graph、暗黙知構造、監査R probe、CognitiveWorld差分まで接続する現行Architectureを定める。\n8. [`06_主体主幹仕様.md`]",
)
patch(
    "設計/09_公開HDS_Compiler仕様.md",
    "詳細Architectureは [`10_HDS_Compiler_Architecture_v1.md`](10_HDS_Compiler_Architecture_v1.md) を正本とする。",
    "Architecture v1の履歴は [`10_HDS_Compiler_Architecture_v1.md`](10_HDS_Compiler_Architecture_v1.md) に保持し、現行Architecture v1.1は [`11_HDS_Compiler_Architecture_v1_1.md`](11_HDS_Compiler_Architecture_v1_1.md) を正本とする。",
)

# 6) 整合性監査へv1.1の必須pathと境界を追加する。
patch(
    "tools/repository_consistency_check.py",
    '    "設計/10_HDS_Compiler_Architecture_v1.md",\n    "構文化/README.md",',
    '    "設計/10_HDS_Compiler_Architecture_v1.md",\n    "設計/11_HDS_Compiler_Architecture_v1_1.md",\n    "構文化/README.md",',
)
patch(
    "tools/repository_consistency_check.py",
    '    "src/minidora/hds_compiler_records.py",\n    "tests/test_hds_compiler.py",\n    "tests/test_hds_compiler_architecture_v1.py",',
    '    "src/minidora/hds_compiler_records.py",\n    "src/minidora/hds_compiler_records_v1_1.py",\n    "src/minidora/hds_compiler_dynamics.py",\n    "src/minidora/hds_compiler_tacit.py",\n    "src/minidora/hds_compiler_failure.py",\n    "src/minidora/hds_compiler_history.py",\n    "src/minidora/hds_compiler_audit_ir.py",\n    "tests/test_hds_compiler.py",\n    "tests/test_hds_compiler_architecture_v1.py",\n    "tests/test_hds_compiler_architecture_v1_1.py",',
)
patch(
    "tools/repository_consistency_check.py",
    '    "設計/10_HDS_Compiler_Architecture_v1.md",\n    "構文化/README.md",',
    '    "設計/10_HDS_Compiler_Architecture_v1.md",\n    "設計/11_HDS_Compiler_Architecture_v1_1.md",\n    "構文化/README.md",',
)
patch(
    "tools/repository_consistency_check.py",
    '    if getattr(公開HDSコンパイラ, "Architecture版", None) != "v1":\n        errors.append("公開HDS Compiler: Architecture版がv1ではない")\n',
    '    if getattr(公開HDSコンパイラ, "Architecture版", None) != "v1.1":\n        errors.append("公開HDS Compiler: Architecture版がv1.1ではない")\n\n    architecture_v11 = _text("設計/11_HDS_Compiler_Architecture_v1_1.md")\n    for required in ("Failure Signature", "状態遷移graph", "監査R probe", "CognitiveWorld差分", "fallback", "HDS本体の内部Gate判定アルゴリズム", "日本語"):\n        if required not in architecture_v11:\n            errors.append(f"設計/11: Architecture v1.1必須境界欠落: {required}")\n',
)

print("HDS_COMPILER_V1_1_PATCH=APPLIED")
