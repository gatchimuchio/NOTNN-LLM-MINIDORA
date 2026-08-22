from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def patch(path: str, old: str, new: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"patch anchor not found: {path}: {old[:80]!r}")
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

# ベンチの標準CompilerもArchitecture v1へ揃える。
patch(
    "tools/gpqa_measure_current.py",
    "from minidora.hds_compiler import 公開HDSコンパイラ\n",
    "from minidora.hds_compiler_v1 import 公開HDSコンパイラ\n",
)

# Front-End: 一般的な明示作用も発話主体とは別に座標化する。
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

# 設計09: v1 orchestratorを正本、旧hds_compiler.pyを互換基礎層へ再配置。
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

# 設計ガイドへArchitecture v1を追加し、公開境界の正本pathを更新。
patch(
    "設計/README.md",
    "5. [`09_公開HDS_Compiler仕様.md`](09_公開HDS_Compiler仕様.md) — フル公開する標準Compilerの責任・非責任・性能改善境界を定める。\n6. [`06_主体主幹仕様.md`]",
    "5. [`09_公開HDS_Compiler仕様.md`](09_公開HDS_Compiler仕様.md) — フル公開する標準Compilerの責任・非責任・性能改善境界を定める。\n6. [`10_HDS_Compiler_Architecture_v1.md`](10_HDS_Compiler_Architecture_v1.md) — 座標・動態・暗黙知・論証・原理探索入力・監査要求を統合する公開Front-End Architectureを定める。\n7. [`06_主体主幹仕様.md`]",
)
patch(
    "設計/README.md",
    "- `src/minidora/hds_compiler.py` はフル公開対象であり、MINIDORAの通常の性能改善対象とする。",
    "- `src/minidora/hds_compiler_v1.py` と、その公開Front-End構成はフル公開対象であり、MINIDORAの通常の性能改善対象とする。`hds_compiler.py` は互換基礎Projectionとして保持する。",
)

# 整合性監査をArchitecture v1へ更新。
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

# Architecture v1受入試験。
test = ROOT / "tests/test_hds_compiler_architecture_v1.py"
test.write_text('''from __future__ import annotations\n\nimport unittest\n\nfrom minidora.hds_compiler_records import HDS原理段階\nfrom minidora.hds_compiler_v1 import 公開HDSコンパイラ\nfrom minidora.hds_data_k import HDSIR知識Adapter, HDS証拠事実\nfrom minidora.hds_effort import HDS努力水準\nfrom minidora.hds_reference import HDS参照問合せ候補\nfrom minidora.k3_functional import K3相当能力核\n\n\nclass HDSCompilerArchitectureV1試験(unittest.TestCase):\n    def setUp(self) -> None:\n        self.compiler = 公開HDSコンパイラ()\n\n    def test_AI世界文で発話主体と作用主体を分離する(self) -> None:\n        result = self.compiler.詳細コンパイル("AIが世界を変える。")\n        self.assertIn("AI", result.認知世界.作用主体)\n        self.assertIn("世界", result.認知世界.対象)\n        for missing in ("発話主体", "時間", "空間", "目的", "機構"):\n            self.assertIn(missing, result.未固定座標)\n\n    def test_動態を静止命題へ潰さない(self) -> None:\n        result = self.compiler.詳細コンパイル("初期状態S0から、条件CならS1へ遷移し、失敗時はrollbackして次状態へ戻す。")\n        kinds = {item.種別 for item in result.監査項目}\n        for expected in ("初期状態", "遷移", "分岐", "帰還"):\n            self.assertIn(expected, kinds)\n        self.assertIn("可逆性要求", result.要求種別)\n        self.assertIn("時間帰属要求", result.要求種別)\n\n    def test_定義前提射程不確実性を分ける(self) -> None:\n        text = "AIとは人工知能を指す。データは固定と仮定する。この条件下のみ有効であり、結果には不確実性がある。"\n        result = self.compiler.詳細コンパイル(text)\n        kinds = {item.種別 for item in result.監査項目}\n        for expected in ("定義", "前提", "射程", "不確実性"):\n            self.assertIn(expected, kinds)\n\n    def test_可能性は不可能性監査要求へ落とす(self) -> None:\n        result = self.compiler.詳細コンパイル("この構成は実現可能である。")\n        self.assertIn("不可能性要求", result.要求種別)\n        request = next(item for item in result.監査要求 if item.種別 == "不可能性要求")\n        self.assertIn("不可能性証拠", request.必要情報)\n        self.assertIn("対称な否定候補", request.必要情報)\n\n    def test_原理語を採用済み原理へ昇格しない(self) -> None:\n        result = self.compiler.詳細コンパイル("観測されたパターンから原理候補Pを考える。")\n        self.assertEqual(result.原理探索.段階, HDS原理段階.原理候補)\n        self.assertIn("原理探索要求", result.要求種別)\n        self.assertIn("反証条件", result.原理探索.必要監査)\n        self.assertNotIn("SCOPED_PRINCIPLE", {str(c.内容) for c in result.IR.座標})\n\n    def test_単一因果は原理候補へ自動昇格しない(self) -> None:\n        result = self.compiler.詳細コンパイル("Protein A causes apoptosis.")\n        self.assertEqual(result.原理探索.段階, HDS原理段階.影)\n\n    def test_監査メタをR_queryへ漏らさない(self) -> None:\n        ir = self.compiler.問題IR("Which molecule causes apoptosis?", ("Protein A", "Protein B", "Protein C", "Protein D"))\n        queries = HDS参照問合せ候補(ir)\n        joined = " ".join(queries)\n        for forbidden in ("監査", "保持", "PROVISIONAL_BY_DEFAULT", "最終採否委譲"):\n            self.assertNotIn(forbidden, joined)\n\n    def test_監査メタをK_factへ昇格しない(self) -> None:\n        core = K3相当能力核()\n        ir = self.compiler.コンパイル("Protein A causes apoptosis.")\n        HDSIR知識Adapter(core).投入(ir, provenance=("fixture",))\n        payload = " ".join(str(fact.args) for fact in HDS証拠事実(core))\n        for forbidden in ("監査.", "保持.", "暫定性."):\n            self.assertNotIn(forbidden, payload)\n\n    def test_監査メタだけで努力水準を膨らませない(self) -> None:\n        self.assertEqual(HDS努力水準(self.compiler.コンパイル("2+3")), "low")\n\n    def test_日本語を基底規定言語として維持する(self) -> None:\n        result = self.compiler.詳細コンパイル("Protein A causes apoptosis.")\n        self.assertEqual(self.compiler.基底言語, "ja")\n        self.assertEqual(result.IR.入力言語, "en")\n        self.assertEqual(self.compiler.Architecture版, "v1")\n\n\nif __name__ == "__main__":\n    unittest.main()\n''', encoding="utf-8")\n\nprint("HDS_COMPILER_ARCH_V1_PATCH=APPLIED")\n