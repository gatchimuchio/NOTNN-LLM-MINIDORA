from __future__ import annotations

from pathlib import Path


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: anchor count={count}")
    path.write_text(text.replace(old, new), encoding="utf-8")


supervisor = Path("src/minidora/hds監督選択runtime.py")
replace_once(
    supervisor,
    "    HDS介入予算: int = 6,\n    初期選択: HDS選択実行結果 | None = None,\n",
    "    HDS介入予算: int = 6,\n    初期選択: HDS選択実行結果 | None = None,\n    統一fallback: bool = True,\n",
)
replace_once(
    supervisor,
    """    selection = session.final_result(records=tuple(records), stop_reasons=stop_reasons)\n    return HDS監督選択結果(\n        selection,\n        session.references,\n        len(records),\n        tuple(row.作用.value for row in records),\n        stop_reasons,\n    )\n""",
    """    selection = session.final_result(records=tuple(records), stop_reasons=stop_reasons)\n\n    # 歴代最高性能の既存経路を先に完走させ、その経路が未閉包の時だけ\n    # K3/GLM/Llama3由来の統一状態循環を単調fallbackとして許可する。\n    # 既存APPROVEを再解釈・置換しない。\n    if 統一fallback and not _approved(selection) and 模型核 is not None:\n        from .hds統一実行 import HDS統一選択評価\n        from .hds統一状態循環 import HDS統一状態Session\n\n        unified_session = HDS統一状態Session(\n            str(question_ir.正規化文 or question_ir.原文),\n            tuple(session.references),\n            主体状態=None,\n            認知世界ID=str(question_ir.認知世界ID or \"\"),\n        )\n        unified = HDS統一選択評価(\n            question_ir,\n            tuple(session.references),\n            コンパイル=コンパイル,\n            模型核=模型核,\n            統一session=unified_session,\n            主体状態=None,\n        )\n        if _approved(unified):\n            inherited_reasons = []\n            if records:\n                inherited_reasons.extend((\n                    \"HDS_FEEDBACK_SAFETY_VALVE\",\n                    f\"HDS_SUPERVISORY_INTERVENTIONS:{len(records)}\",\n                ))\n                inherited_reasons.extend(\n                    \"HDS_INTERVENTION_ACTION:\" + row.作用.value for row in records\n                )\n            selection = replace(\n                unified,\n                理由=tuple(dict.fromkeys(\n                    tuple(unified.理由)\n                    + tuple(inherited_reasons)\n                    + (\"HIGHWATER_MONOTONIC_FALLBACK_COMMIT\",)\n                )),\n            )\n\n    return HDS監督選択結果(\n        selection,\n        session.references,\n        len(records),\n        tuple(row.作用.value for row in records),\n        stop_reasons,\n    )\n""",
)

runtime = Path("src/minidora/runtime.py")
text = runtime.read_text(encoding="utf-8")
start_marker = "                # 55/198を成立させた既存MINIDORA経路を先に最後まで実行する。"
end_marker = "                return self._HDS選択結果(要求_, hds_ir, supervised.参照, supervised.選択)\n"
start = text.find(start_marker)
if start < 0:
    raise SystemExit("runtime monotonic block start not found")
# The block contains multiple identical return lines. We need the last one before the method's next def.
method_end = text.find("    def 言語確率", start)
if method_end < 0:
    raise SystemExit("runtime method end not found")
end_start = text.rfind(end_marker, start, method_end)
if end_start < 0:
    raise SystemExit("runtime monotonic block end not found")
end = end_start + len(end_marker)
replacement = """                # HDS監督選択実行が、55/198正本経路の完走と統一状態fallbackを\n                # 一つの製品経路として管理する。runtime側では再実装しない。\n                supervised = HDS監督選択実行(\n                    hds_ir,\n                    tuple(references),\n                    コンパイル=self.コンパイル,\n                    基礎能力核=self.K3能力核,\n                    模型核=self.能力模型核,\n                    参照供給器=self.参照供給器,\n                    HDS制御=self.HDS監督制御,\n                    初期選択=initial,\n                    統一fallback=True,\n                )\n                return self._HDS選択結果(要求_, hds_ir, supervised.参照, supervised.選択)\n"""
runtime.write_text(text[:start] + replacement + text[end:], encoding="utf-8")

print("centralized unified fallback into product HDS supervisor route")
