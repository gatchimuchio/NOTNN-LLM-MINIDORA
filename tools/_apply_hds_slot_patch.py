from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: replace anchor count={count}, expected=1")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def regex_replace_once(path: Path, pattern: str, replacement: str) -> None:
    text = path.read_text(encoding="utf-8")
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError(f"{path}: regex anchor count={count}, expected=1")
    path.write_text(updated, encoding="utf-8")


compiler = ROOT / "src/minidora/hds_compiler.py"
reference = ROOT / "src/minidora/hds_reference.py"
readme = ROOT / "README.md"
design = ROOT / "設計/09_公開HDS_Compiler仕様.md"

helper_marker = "\n\n\n@dataclass(frozen=True, slots=True)\nclass 公開HDSコンパイラ方針:"
helper_block = r'''

_英語検索述語 = {
    "因果": "causes",
    "増加": "increases",
    "減少": "decreases",
    "阻害": "inhibits",
    "活性化": "activates",
    "生成": "produces",
    "要求": "requires",
    "包含": "contains",
    "使用": "uses",
    "防止": "prevents",
    "相関": "associated with",
}
_日本語検索述語 = {
    "因果": "引き起こす",
    "増加": "増加させる",
    "減少": "減少させる",
    "阻害": "阻害する",
    "活性化": "活性化する",
    "生成": "生成する",
    "要求": "必要とする",
    "包含": "含む",
    "使用": "使う",
    "防止": "防ぐ",
    "相関": "関連する",
}


def _未知端点(text: str) -> tuple[bool, str]:
    value = " ".join(str(text).split()).strip(" ,;:。！？?")
    if not value:
        return False, ""
    lowered = value.casefold()
    if lowered in {"who", "whom"}:
        return True, "person"
    if lowered in {"what", "which"}:
        return True, ""
    match = re.fullmatch(r"(?:which|what)\s+(?P<kind>.+)", value, flags=re.I)
    if match:
        kind = re.sub(r"^of\s+the\s+following\s+", "", match.group("kind"), flags=re.I).strip()
        return True, kind
    if value == "誰":
        return True, "人物"
    if value in {"何", "なに"}:
        return True, ""
    if value.startswith("どの") and len(value) > 2:
        return True, value[2:].strip()
    match = re.fullmatch(r"(?:何|なに)の(?P<kind>.+)", value)
    if match:
        return True, match.group("kind").strip()
    return False, ""


def _条件表層除去(text: str, conditions: tuple[str, ...]) -> str:
    value = " ".join(str(text).split()).strip()
    for condition in sorted((" ".join(c.split()).strip() for c in conditions if c), key=len, reverse=True):
        if value.casefold().endswith(condition.casefold()):
            value = value[: len(value) - len(condition)].strip(" ,;:。！？?")
    return value


def _関係検索述語(kind: str, surface: str, language: str, *, reverse: bool) -> str:
    if not reverse:
        return " ".join(str(surface).split()).strip()
    table = _日本語検索述語 if str(language).casefold().startswith("ja") else _英語検索述語
    return table.get(kind, " ".join(str(surface).split()).strip())
'''
replace_once(compiler, helper_marker, helper_block + helper_marker)

replace_once(
    compiler,
    '''        for pattern in _条件規則:\n            for match in pattern.finditer(normalized):\n                add_coord("条件.前提", match.group(0))\n\n        relation_count = 0\n''',
    '''        condition_surfaces: list[str] = []\n        for pattern in _条件規則:\n            for match in pattern.finditer(normalized):\n                condition = " ".join(match.group(0).split()).strip()\n                if not condition or condition in condition_surfaces:\n                    continue\n                condition_surfaces.append(condition)\n                add_coord("条件.前提", condition)\n\n        relation_count = 0\n''',
)

new_add_relation = r'''        def add_relation(kind: str, subject: str, predicate_surface: str, object_: str, *, reverse: bool = False) -> None:
            nonlocal relation_count
            if relation_count >= self.方針.最大関係数:
                return
            subject = _条件表層除去(subject, tuple(condition_surfaces)).strip(" ,;:。！？")
            object_ = _条件表層除去(object_, tuple(condition_surfaces)).strip(" ,;:。！？")
            predicate_surface = predicate_surface.strip()
            if not subject or not object_ or not predicate_surface:
                return
            if reverse:
                subject, object_ = object_, subject

            subject_unknown, subject_type = _未知端点(subject)
            object_unknown, object_type = _未知端点(object_)
            if subject_unknown and object_unknown:
                residuals.append(
                    HDS残差(
                        f"residual:relation:{relation_count}",
                        "未解関係両端",
                        f"{subject} {predicate_surface} {object_}",
                        "関係の始点と終点がともに未観測",
                        解消条件=("Rまたは文脈で少なくとも一方の端点を確定する",),
                    )
                )
                relation_count += 1
                return

            query_predicate = _関係検索述語(kind, predicate_surface, language, reverse=reverse)
            relation_conditions: list[str] = [f"検索述語={query_predicate}"]
            relation_state = 値状態.確定

            if subject_unknown:
                sid = add_coord("目的.未知始点", subject_type or "未特定", state=値状態.未観測)
                add_coord("目的.不足位置", "始点")
                if subject_type:
                    add_coord("目的.要求型", subject_type)
                oid = add_coord("対象.終点", object_)
                relation_conditions.append("不足位置=始点")
                relation_state = 値状態.未観測
            elif object_unknown:
                sid = add_coord("対象.始点", subject)
                oid = add_coord("目的.未知終点", object_type or "未特定", state=値状態.未観測)
                add_coord("目的.不足位置", "終点")
                if object_type:
                    add_coord("目的.要求型", object_type)
                relation_conditions.append("不足位置=終点")
                relation_state = 値状態.未観測
            else:
                sid = add_coord("対象.始点", subject)
                oid = add_coord("対象.終点", object_)

            add_coord("関係.述語", predicate_surface)
            relations.append(
                HDS関係(
                    f"rel:{relation_count}",
                    (sid,),
                    (oid,),
                    kind,
                    条件=tuple(relation_conditions),
                    値状態=relation_state,
                    由来="公開HDS Compiler",
                )
            )
            relation_count += 1
'''
regex_replace_once(
    compiler,
    r"        def add_relation\(kind: str, subject: str, predicate_surface: str, object_: str, \*, reverse: bool = False\) -> None:\n.*?            relation_count \+= 1\n",
    new_add_relation,
)

replace_once(
    compiler,
    '                保持構造=("関係方向", "否定", "数量", "単位", "検索焦点"),',
    '                保持構造=("関係方向", "否定", "数量", "単位", "検索焦点", "不足スロット"),',
)

replace_once(
    reference,
    '_QUERY_META_PREFIXES = ("制御.", "監査.")',
    '_QUERY_META_PREFIXES = ("制御.", "監査.", "目的.不足位置", "条件.検索極性")',
)

slot_marker = "\n\ndef _問合せ仕様(ir: HDSIR, *, 最大候補数: int = 6) -> tuple[_HDS問合せ仕様, ...]:"
slot_helpers = r'''


def _関係条件値(relation: object, key: str) -> str:
    prefix = key + "="
    for raw in getattr(relation, "条件", ()):
        value = str(raw)
        if value.startswith(prefix):
            return value[len(prefix):].strip()
    return ""


def _不足スロット候補query(ir: HDSIR, choice: str) -> str:
    """Compilerが確定した関係の未知端点だけを候補で埋め、R用表層へ戻す。"""
    coords = ir.座標辞書()
    groups, _ = _役割語群(ir)
    conditions = groups["条件"]
    for relation in ir.関係:
        position = _関係条件値(relation, "不足位置")
        predicate = _関係条件値(relation, "検索述語")
        if position not in {"始点", "終点"} or not predicate:
            continue
        starts = [coords[cid] for cid in relation.始点 if cid in coords]
        ends = [coords[cid] for cid in relation.終点 if cid in coords]
        if position == "始点":
            known = next((str(coord.内容) for coord in ends if coord.値状態 not in _BLOCKING_STATES), "")
            parts = (choice, predicate, known, *conditions)
        else:
            known = next((str(coord.内容) for coord in starts if coord.値状態 not in _BLOCKING_STATES), "")
            parts = (known, predicate, choice, *conditions)
        query = _切詰め(" ".join(_unique(parts)), 360)
        if query:
            return query
    return ""
'''
replace_once(reference, slot_marker, slot_helpers + slot_marker)

old_candidate = '''    distinctive = _候補差分語(choices)\n    for label, choice in choices:\n        suffix = _候補query片(choice, distinctive.get(label, ()))\n        query = _切詰め(" ".join(_unique((anchor, suffix))), 360)\n        if not query:\n            continue\n        key = query.casefold()\n        if key not in seen:\n            seen.add(key)\n            specs.append(_HDS問合せ仕様(query, "choice", label))\n'''
new_candidate = '''    distinctive = _候補差分語(choices)\n    for label, choice in choices:\n        query = _不足スロット候補query(ir, choice)\n        if not query:\n            suffix = _候補query片(choice, distinctive.get(label, ()))\n            query = _切詰め(" ".join(_unique((anchor, suffix))), 360)\n        if not query:\n            continue\n        key = query.casefold()\n        if key not in seen:\n            seen.add(key)\n            specs.append(_HDS問合せ仕様(query, "choice", label))\n'''
replace_once(reference, old_candidate, new_candidate)

# READMEの旧公開境界を現方針へ同期する。
replace_once(
    readme,
    "公開Runtimeは、HDS Compilerを用意しなくてもLegacy互換経路を使って即時実行できる。",
    "公開CLIは、リポジトリ内の公開標準HDS Compilerを接続して即時実行できる。Runtime APIではLegacy互換経路も維持する。",
)
replace_once(
    readme,
    "- HDS Compiler内部実装は公開Runtimeから分離され、公開側はHDS-IR受入契約だけを持つ",
    "- 公開標準HDS Compilerはリポジトリ内でフル公開し、HDS本体の上流理論・導出規則は公開物へ含めない",
)
replace_once(
    readme,
    "HDS Compilerが接続されている場合、自然言語入力はHDSで意味付けされた `HDS-IR` としてRuntimeへ渡す。公開MINIDORAはCompiler内部方式ではなく、HDS-IRの受入・実行境界を規定する。",
    "通常CLIでは公開標準HDS Compilerを接続し、自然言語入力をHDSで意味付けされた `HDS-IR` としてRuntimeへ渡す。Compilerはフル公開するが、HDS本体の上流理論・導出規則とは明確に分離する。",
)
replace_once(
    readme,
    "HDS Compilerは `HDSコンパイラProtocol` を満たす外部実装として差替え可能であり、Runtimeは直前結果と過去のHDS-IR履歴をCompilerへ帰還できる。HDS Compilerが接続されていない場合は、決定論的 `自然言語器` をLegacy互換経路として利用する。",
    "公開標準HDS Compilerは `HDSコンパイラProtocol` を満たし、同Protocol互換実装へ差替え可能である。Runtimeは直前結果と過去のHDS-IR履歴をCompilerへ帰還できる。Compilerが明示注入されない内部APIでは、決定論的 `自然言語器` をLegacy互換経路として利用できる。",
)

if "## 11. 不足スロット" not in design.read_text(encoding="utf-8"):
    with design.open("a", encoding="utf-8") as f:
        f.write(
            "\n## 11. 不足スロット\n\n"
            "関係構造が高信頼に確定でき、始点または終点だけが疑問語で未観測の場合、疑問語を実体として確定しない。"
            "未知端点を `未観測` として保持し、既知端点・関係種別・検索述語・条件と結び付ける。\n\n"
            "選択問題のR queryでは各候補を未観測端点へ差し込み、関係方向と条件を保持した候補別queryを生成する。"
            "関係構造を一意に決められない疑問文では不足スロットを推測生成せず、従来の焦点・構造queryへ縮退する。\n"
        )

# 回帰試験を追加する。
test_path = ROOT / "tests/test_hds_unknown_slots.py"
test_path.write_text(r'''from __future__ import annotations

import unittest

from minidora.hds_compiler import 公開HDSコンパイラ
from minidora.hds_ir import 値状態
from minidora.hds_reference import HDS参照問合せ候補


class HDS不足スロット試験(unittest.TestCase):
    def setUp(self) -> None:
        self.compiler = 公開HDSコンパイラ()

    def test_英語未知始点を候補へ置換したR_queryにする(self) -> None:
        ir = self.compiler.問題IR(
            "Which molecule causes apoptosis under hypoxia?",
            ("Protein A", "Protein B", "Protein C", "Protein D"),
        )
        unknown = [c for c in ir.座標 if c.種別 == "目的.未知始点"]
        self.assertEqual(len(unknown), 1)
        self.assertEqual(unknown[0].値状態, 値状態.未観測)
        self.assertEqual(str(unknown[0].内容).casefold(), "molecule")
        relation = next(r for r in ir.関係 if r.種別 == "因果" and r.値状態 == 値状態.未観測)
        self.assertIn("不足位置=始点", relation.条件)
        queries = tuple(q.casefold() for q in HDS参照問合せ候補(ir))
        for choice in ("protein a", "protein b", "protein c", "protein d"):
            self.assertIn(f"{choice} causes apoptosis under hypoxia", queries)

    def test_英語未知終点を候補へ置換する(self) -> None:
        ir = self.compiler.問題IR(
            "Protein A inhibits which pathway under hypoxia?",
            ("glycolysis", "apoptosis", "translation", "transport"),
        )
        unknown = [c for c in ir.座標 if c.種別 == "目的.未知終点"]
        self.assertEqual(len(unknown), 1)
        self.assertEqual(str(unknown[0].内容).casefold(), "pathway")
        queries = tuple(q.casefold() for q in HDS参照問合せ候補(ir))
        self.assertIn("protein a inhibits glycolysis under hypoxia", queries)

    def test_受動態でも意味方向に沿って未知終点を作る(self) -> None:
        ir = self.compiler.問題IR(
            "Which disease is caused by Protein A?",
            ("Disease A", "Disease B", "Disease C", "Disease D"),
        )
        relation = next(r for r in ir.関係 if r.種別 == "因果")
        coords = ir.座標辞書()
        self.assertEqual(str(coords[relation.始点[0]].内容), "Protein A")
        self.assertEqual(coords[relation.終点[0]].種別, "目的.未知終点")
        queries = tuple(q.casefold() for q in HDS参照問合せ候補(ir))
        self.assertIn("protein a causes disease a", queries)

    def test_日本語未知始点も同じ意味構造へ落とす(self) -> None:
        ir = self.compiler.問題IR(
            "どのタンパク質がアポトーシスを引き起こす？",
            ("タンパク質A", "タンパク質B", "タンパク質C", "タンパク質D"),
        )
        unknown = [c for c in ir.座標 if c.種別 == "目的.未知始点"]
        self.assertEqual(len(unknown), 1)
        self.assertEqual(str(unknown[0].内容), "タンパク質")
        queries = HDS参照問合せ候補(ir)
        self.assertIn("タンパク質A 引き起こす アポトーシス", queries)

    def test_関係が確定しない疑問文へ不足スロットを捏造しない(self) -> None:
        ir = self.compiler.問題IR(
            "Which of the following statements is correct under hypoxia?",
            ("A statement", "B statement", "C statement", "D statement"),
        )
        self.assertFalse(any(c.種別.startswith("目的.未知") for c in ir.座標))
        self.assertFalse(any("不足位置=" in cond for r in ir.関係 for cond in r.条件))

    def test_選択極性は外部検索語へ漏らさない(self) -> None:
        ir = self.compiler.問題IR(
            "Which molecule is least likely to cause apoptosis under hypoxia?",
            ("Protein A", "Protein B", "Protein C", "Protein D"),
        )
        queries = tuple(q.casefold() for q in HDS参照問合せ候補(ir))
        self.assertFalse(any("least likely" in q for q in queries if "protein " in q))
        self.assertFalse(any("始点" in q or "終点" in q for q in queries))


if __name__ == "__main__":
    unittest.main()
''', encoding="utf-8")

# 一時patch infrastructureは成果物へ残さない。
for relative in ("tools/_apply_hds_slot_patch.py", ".github/workflows/_hds_slot_builder.yml"):
    target = ROOT / relative
    if target.exists():
        target.unlink()

print("HDS_SLOT_PATCH=APPLIED")
