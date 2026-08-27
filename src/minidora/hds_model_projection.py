from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping, Sequence
from .hds_ir import HDSIR, HDS関係, 値状態
from .hds_runtime_projection import HDSK質問射影
from .semantic_tokens import 意味語
from .言語構造 import 言語関係構造
from .模型 import MINIDORA模型核, 成立候補, 言語状態, 模型結果, 標準模型核
from .関係連鎖演算 import 関係連鎖作用名
from .関係連鎖演算_v2 import 関係連鎖作用V2, 関係連鎖模型核V2, 推論文脈形成
from .hds判断主体 import HDS判断主体, HDS判断結果, MINIDORA出力, MINIDORA出力化

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

def _残差証拠境界(ir):
    source_blocked=any(str(item.種別)=="semantic_loss" for item in ir.残差)
    impacted=set()
    for residual in ir.残差:
        impacted.update(str(x) for x in residual.影響座標)
    return source_blocked,frozenset(impacted)

def HDS内部言語状態(ir,*,識別子="",言語体系=None,証拠境界=False):
    source_blocked,impacted=_残差証拠境界(ir) if 証拠境界 else (False,frozenset())
    relations=[]
    for relation in ir.関係:
        if source_blocked:
            continue
        if impacted and any(str(cid) in impacted for cid in (*relation.始点,*relation.終点)):
            continue
        structure=_関係構造(ir,relation)
        if structure is not None:
            relations.append(structure)
    ls=str(言語体系 or _対象言語体系(ir)).strip()
    return 言語状態(str(ir.正規化文 or ir.原文),ls,識別子,tuple(relations))

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
    模型結果: 模型結果
    状態: str
    回答ラベル: str|None
    理由: tuple[str,...]
    HDS判断: HDS判断結果|None=None
    MINIDORA出力: MINIDORA出力|None=None


def HDSMINIDORA模型評価(
    question_ir:HDSIR,
    candidate_irs:Mapping[str,HDSIR],
    data_irs:Sequence[HDSIR],
    *,
    模型核:MINIDORA模型核|None=None,
    判断主体:HDS判断主体|None=None,
    参照識別子:Sequence[str]|None=None,
    参照信頼:Sequence[float]|None=None,
):
    """HDS Compiler出力をMINIDORAへ渡し、MINIDORA出力だけを後段HDSへ渡す。

    正式模型の通常文脈には問い関係だけを置く。問題文中の確定事実は推論専用状態へ
    分離し、関係連鎖作用v2だけが参照する。これにより前提保持を維持しながら、一般関係・
    履歴・参照寄与へ前提を無言混入させない。後段HDSへ元Dataや推論状態は渡さない。
    """
    core=関係連鎖模型核V2(模型核 or 標準模型核());target=_対象言語体系(question_ir)

    full_question=HDS内部言語状態(question_ir,識別子="question:full",言語体系=target)
    question_core_ir=HDSK質問射影(question_ir)
    question=HDS内部言語状態(question_core_ir,識別子="question",言語体系=target)
    question_signatures={relation.署名 for relation in question.関係構造}
    premise_relations=tuple(
        relation
        for relation in full_question.関係構造
        if relation.署名 not in question_signatures
    )
    reasoning_states=(
        言語状態("",target,"question-premises",premise_relations),
    ) if premise_relations else ()

    candidate_internal={str(label):HDS内部言語状態(ir,識別子="candidate:"+str(label),言語体系=target) for label,ir in sorted(candidate_irs.items())}
    candidates=tuple(成立候補(label,state) for label,state in candidate_internal.items())
    ids=tuple(参照識別子 or tuple(f"reference:{i}" for i in range(len(data_irs))))
    if len(ids)!=len(data_irs):
        raise ValueError("参照識別子はData IRと同数である必要がある")
    if 参照信頼 is not None and len(tuple(参照信頼))!=len(data_irs):
        raise ValueError("参照信頼はData IRと同数である必要がある")
    ref_internal=tuple(HDS内部言語状態(ir,識別子=ids[i],言語体系=target,証拠境界=True) for i,ir in enumerate(data_irs))

    context=推論文脈形成(
        core,
        question,
        推論状態=reasoning_states,
        条件=_文脈条件(question_ir),
        参照状態=ref_internal,
    )
    result=core.評価(context,candidates)

    chain_action=next((item for item in core.能力作用群 if getattr(item,"名称","")==関係連鎖作用名),None)
    chain_result=chain_action.演算(result.文脈) if isinstance(chain_action,関係連鎖作用V2) else None
    chain_contributions=tuple(
        item
        for row in result.候補差
        for item in row.寄与
        if item.関係名==関係連鎖作用名
    )
    chain_candidates=sum(
        1
        for row in result.候補差
        if any(item.関係名==関係連鎖作用名 for item in row.寄与)
    )

    # ここが責任境界。後段HDSへ渡す入力はMINIDORA出力だけ。
    model_output=MINIDORA出力化(result)
    judge=判断主体 or HDS判断主体()
    decision=judge.判断(model_output)
    runtime_state="APPROVE" if decision.状態=="APPROVE" else "SUSPEND"
    answer=decision.選択候補ID if decision.状態=="APPROVE" else None

    chain_audit=[
        "RELATION_CHAIN_ARITHMETIC_V2",
        "RELATION_CHAIN_IDENTITY_SYMMETRIC",
        "RELATION_CHAIN_INFERENCE_STATE_SEPARATED",
        f"RELATION_CHAIN_PREMISE_RELATIONS:{len(premise_relations)}",
    ]
    if chain_result is not None and chain_result.多段状態数:
        chain_audit.extend((
            "RELATION_CHAIN_STATE_FORMED",
            f"RELATION_CHAIN_STATES:{chain_result.多段状態数}",
            f"RELATION_CHAIN_MAX_DEPTH:{chain_result.最大到達深さ}",
            f"RELATION_CHAIN_TRUNCATED:{int(chain_result.打切り)}",
        ))
    else:
        chain_audit.append("RELATION_CHAIN_STATE_NOT_FORMED")
    if chain_contributions:
        chain_audit.extend((
            "RELATION_CHAIN_APPLIED",
            f"RELATION_CHAIN_CONTRIBUTIONS:{len(chain_contributions)}",
            f"RELATION_CHAIN_CANDIDATES:{chain_candidates}",
        ))
    else:
        chain_audit.append("RELATION_CHAIN_NOT_APPLIED")

    reasons=tuple(dict.fromkeys((
        *decision.理由,
        "HDS_JUDGEMENT_SUBJECT_V2",
        "HDS_OUTPUT_ONLY_BOUNDARY",
        *chain_audit,
        "CAPABILITY_PROJECTION_V1",
    )))
    return HDSMINIDORA射影結果(result,runtime_state,answer,reasons,decision,model_output)
