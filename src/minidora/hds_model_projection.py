from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping, Sequence
from .hds_ir import HDSIR,HDS関係,値状態
from .semantic_tokens import 意味語
from .言語構造 import 言語関係構造
from .模型 import MINIDORA模型核,成立候補,言語状態,模型結果,標準模型核
_BLOCKING_ENDPOINT={値状態.未確定,値状態.未観測,値状態.矛盾,値状態.留保}
_SCOPE_KEYS=frozenset({"様相","量化","条件scope","scope","条件作用"})
def _条件値(relation,key):
    prefix=key+"="
    for raw in relation.条件:
        value=str(raw)
        if value.startswith(prefix):return value[len(prefix):].strip()
    return ""
def _端点意味(ir,ids):
    coords=ir.座標辞書();out=set()
    for cid in ids:
        coord=coords.get(cid)
        if coord is None or coord.値状態 in _BLOCKING_ENDPOINT:continue
        out.update(意味語(coord.内容))
    return frozenset(out)
def _述語意味(ir,relation):
    surface=_条件値(relation,"検索述語")
    if not surface:
        vals=[str(c.内容) for c in ir.座標 if str(c.種別)=="関係.述語" and str(c.内容).strip()]
        surface=" ".join(vals) or str(relation.種別)
    return 意味語(surface)
def _関係構造(ir,relation):
    start=_端点意味(ir,relation.始点);end=_端点意味(ir,relation.終点)
    if not start and not end:return None
    polarity=_条件値(relation,"極性")!="否定"
    conditions=[];seen=set()
    for raw in relation.条件:
        key,sep,payload=str(raw).partition("=")
        if not sep or key.strip() not in _SCOPE_KEYS or not payload.strip():continue
        sem=意味語(payload);sig=tuple(sorted(sem))
        if sem and sig not in seen:seen.add(sig);conditions.append(sem)
    return 言語関係構造(str(relation.種別),start,end,polarity,tuple(conditions),_述語意味(ir,relation))
def _対象言語体系(ir):
    lang=str(getattr(ir,"入力言語","en") or "en").casefold();return "自然言語:ja" if lang.startswith("ja") else "自然言語:en"
def HDS内部言語状態(ir,*,識別子="",言語体系=None):
    relations=tuple(x for r in ir.関係 if (x:=_関係構造(ir,r)) is not None)
    ls=str(言語体系 or _対象言語体系(ir)).strip()
    return 言語状態(str(ir.正規化文 or ir.原文),ls,識別子,relations)
def _文脈条件(question_ir):
    out=[]
    for relation in question_ir.関係:
        intent=_条件値(relation,"選択意図")
        if intent:out.append("選択意図="+intent)
    for coord in question_ir.座標:
        if str(coord.種別)=="制御.選択意図" and str(coord.内容).strip():out.append("選択意図="+str(coord.内容).strip())
    return tuple(dict.fromkeys(out))
@dataclass(frozen=True, slots=True)
class HDSMINIDORA射影結果:
    模型結果:模型結果;状態:str;回答ラベル:str|None;理由:tuple[str,...]
def HDSMINIDORA模型評価(question_ir:HDSIR,candidate_irs:Mapping[str,HDSIR],data_irs:Sequence[HDSIR],*,模型核:MINIDORA模型核|None=None):
    core=模型核 or 標準模型核();target=_対象言語体系(question_ir)
    question=HDS内部言語状態(question_ir,識別子="question",言語体系=target)
    candidates=tuple(成立候補(str(label),HDS内部言語状態(ir,識別子="candidate:"+str(label),言語体系=target)) for label,ir in sorted(candidate_irs.items()))
    refs=tuple(HDS内部言語状態(ir,識別子=f"reference:{i}",言語体系=target) for i,ir in enumerate(data_irs))
    result=core.評価言語状態(question,candidates,条件=_文脈条件(question_ir),参照状態=refs)
    # knowledge choiceの終端は参照由来差で閉じる。表層差と参照差が競合しても表層で上書きしない。
    if result.参照最有力候補ID is None:
        ref_scores = result.参照候補辞書()
        if not any(ref_scores.values()):
            return HDSMINIDORA射影結果(
                result, "SUSPEND", None,
                ("MINIDORA_MODEL_CORE_NO_REFERENCE_CONTRIBUTION", "NO_GUESS", "CAPABILITY_PROJECTION_V1"),
            )
        return HDSMINIDORA射影結果(
            result, "SUSPEND", None,
            ("MINIDORA_MODEL_CORE_NO_UNIQUE_POSITIVE_DIFFERENCE", "REFERENCE_DIFFERENCE_NOT_UNIQUE", "CAPABILITY_PROJECTION_V1"),
        )
    return HDSMINIDORA射影結果(
        result, "APPROVE", result.参照最有力候補ID,
        ("MINIDORA_MODEL_CORE_SELECTED", "REFERENCE_CONTRIBUTION_PRESENT", "REFERENCE_DIFFERENCE_SELECTED", "CAPABILITY_PROJECTION_V1"),
    )
