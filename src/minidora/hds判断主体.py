from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .hds_candidate_reconcile import HDS候補証拠, HDS候補横断調停
from .hds_ir import HDSIR, 値状態
from .模型 import 言語状態, 模型結果
from .能力作用則 import 証拠状態寄与群

_BLOCKING={値状態.未確定,値状態.未観測,値状態.矛盾,値状態.留保}

@dataclass(frozen=True, slots=True)
class HDS判断参照:
    出典ID:str
    状態:言語状態
    信頼:float=1.0

@dataclass(frozen=True, slots=True)
class HDS判定門結果:
    判定門:str
    状態:str
    理由:tuple[str,...]=()

@dataclass(frozen=True, slots=True)
class HDS候補判断状態:
    候補ID:str
    調停得点:float
    識別出典:tuple[str,...]
    確定支持出典:tuple[str,...]
    弱支持出典:tuple[str,...]
    反証出典:tuple[str,...]
    反対向出典:tuple[str,...]
    状態:str

@dataclass(frozen=True, slots=True)
class HDS判断結果:
    状態:str
    選択候補ID:str|None
    断定状態:str
    運用状態:str
    採用状態:str
    証拠状態:str
    閉包状態:str
    暫定性状態:str
    判定門:tuple[HDS判定門結果,...]
    候補状態:tuple[HDS候補判断状態,...]
    保持候補ID:tuple[str,...]
    不確実候補ID:tuple[str,...]
    理由:tuple[str,...]


def _反転質問(ir:HDSIR)->bool:
    for rel in ir.関係:
        if any(str(x).casefold()=="選択意図=反転" for x in rel.条件): return True
    for coord in ir.座標:
        if str(coord.種別)=="制御.選択意図" and str(coord.内容).strip()=="反転": return True
    return False


def _閉包阻害(ir:HDSIR)->tuple[str,...]:
    reasons=[]
    if any(str(r.種別)=="semantic_loss" for r in ir.残差):reasons.append("SEMANTIC_LOSS")
    if any(getattr(c,"値状態",値状態.確定) in _BLOCKING and str(c.種別).startswith(("対象","目的","制御")) for c in ir.座標):
        # 選択肢の未知slotは問いとして正常なので、choice:* 自体はここで阻害しない。
        blocking=[c for c in ir.座標 if getattr(c,"値状態",値状態.確定) in _BLOCKING and str(c.種別).startswith(("対象","目的","制御")) and not str(c.座標ID).startswith("choice:") and not str(c.種別).startswith("目的.未知")]
        if blocking: reasons.append("UNRESOLVED_FRAME")
    return tuple(reasons)


class HDS判断主体:
    """MINIDORA計算主体Cの候補を、HDSのCm/判定門で局所採否する判断主体J。

    候補生成・世界知識生成は行わない。Cが保持した候補関係と参照関係を、出典単位で
    証拠・矛盾・候補横断・閉包へ分別し、APPROVE/SUSPENDだけを裁定する。
    """
    版="v1-hds-rev4.1-projection"

    def 判断(self,question_ir:HDSIR,候補群:Mapping[str,言語状態],参照群:Sequence[HDS判断参照],模型結果:模型結果)->HDS判断結果:
        labels=tuple(sorted(str(x) for x in 候補群))
        gates=[]
        frame_block=_閉包阻害(question_ir)
        if frame_block:
            gates.append(HDS判定門結果("対象・関係・閉包","SUSPEND",frame_block))
            return HDS判断結果("SUSPEND",None,"保留","HOLD","保留","未閉包","OPEN",str(question_ir.暫定性状態),tuple(gates),(),labels,labels,("HDS_FRAME_UNCLOSED",*frame_block))
        gates.append(HDS判定門結果("対象・関係・閉包","PASS",("FRAME_LOCALLY_CLOSED",)))
        proposal=模型結果.参照最有力候補ID or 模型結果.最有力候補ID
        gates.append(HDS判定門結果("計算候補","PASS",((f"C_PROPOSAL={proposal}" if proposal else "C_PROPOSAL=UNRESOLVED"),"C_AUTHORITY=CANDIDATE_ONLY")))
        gates.append(HDS判定門結果("権限","PASS",("FINAL_AUTHORITY=J/HDS",)))
        gates.append(HDS判定門結果("リスク・可逆性","NOT_APPLICABLE",("KNOWLEDGE_CHOICE_NO_EXTERNAL_ACTION",)))

        raw=[]; negatives={label:set() for label in labels}; reverse_neg={label:set() for label in labels}
        exact_pos={label:set() for label in labels}; weak_pos={label:set() for label in labels}
        for ref in 参照群:
            trust=max(0.0,min(1.0,float(ref.信頼)))
            for label in labels:
                candidate=候補群[label]
                values=証拠状態寄与群(candidate.関係構造,ref.状態.関係構造)
                positives=[v for v in values if v>0]
                if positives:
                    score=float(sum(positives))*trust
                    if score>0:
                        raw.append(HDS候補証拠(label,ref.出典ID,score,(f"relation:{ref.出典ID}:{label}",),"fact"))
                        if any(v>=2 for v in positives): exact_pos[label].add(ref.出典ID)
                        else: weak_pos[label].add(ref.出典ID)
                if any(v<=-2 for v in values): negatives[label].add(ref.出典ID)
                if any(v==-1 for v in values): reverse_neg[label].add(ref.出典ID)

        # 全sourceを保持する。top-k剪定や重要度削除はしない。
        limit=max(1,len(参照群)); reconciled=HDS候補横断調停(labels,raw,証拠重み=(1.0,)*limit,証拠上限=limit)
        states=[]; eligible=[]
        for label in labels:
            rows=reconciled[label].採用証拠
            discriminative={r.出典ID for r in rows}
            exact=tuple(sorted(exact_pos[label]&discriminative))
            weak=tuple(sorted(weak_pos[label]&discriminative))
            neg=tuple(sorted(negatives[label]))
            rev=tuple(sorted(reverse_neg[label]))
            # Commit可能な支持は、関係・方向・極性・scopeが完全に閉じた出典を最低1つ要求する。
            # 弱支持は捨てずに保持するが、それだけで断定へ昇格しない。
            if exact and not neg:
                state="COMMIT_ELIGIBLE"; eligible.append(label)
            elif neg:
                state="CONTRADICTED"
            elif weak:
                state="WEAK_EVIDENCE"
            else:
                state="UNSUPPORTED"
            states.append(HDS候補判断状態(label,reconciled[label].合計得点,tuple(sorted(discriminative)),exact,weak,neg,rev,state))

        if not 参照群:
            gates.append(HDS判定門結果("証拠","SUSPEND",("NO_REFERENCE",)))
            return self._hold(question_ir,labels,states,gates,("HDS_EVIDENCE_ABSENT","NO_GUESS"))

        evidence_count=sum(bool(x.確定支持出典) for x in states)
        gates.append(HDS判定門結果("証拠","PASS" if evidence_count else "SUSPEND",("EXACT_RELATION_EVIDENCE_PRESENT",) if evidence_count else ("NO_EXACT_RELATION_EVIDENCE",)))
        contradicted=tuple(x.候補ID for x in states if x.反証出典)
        gates.append(HDS判定門結果("矛盾","SUSPEND" if contradicted else "PASS",tuple(f"CONTRADICTED:{x}" for x in contradicted)))

        if _反転質問(question_ir):
            unsupported=tuple(label for label in labels if label not in eligible)
            # 例外選択はN-1候補が独立にCommit可能なときだけ、残る一候補を局所採用する。
            if len(eligible)==len(labels)-1 and len(unsupported)==1:
                selected=unsupported[0]
                # 残余候補自身に確定支持があるなら例外として閉じない（通常eligibleに入るため通常到達しない）。
                gates.append(HDS判定門結果("反論・反実仮想","PASS",("N_MINUS_ONE_ELIMINATION",)))
                gates.append(HDS判定門結果("Commit","PASS",("SCOPED_EXCEPTION_COMMIT",)))
                return self._approve(question_ir,selected,labels,states,gates,("HDS_JUDGEMENT_SELECTED","HDS_EXCEPTION_N_MINUS_ONE","AUTHORITY_SEPARATED"))
            gates.append(HDS判定門結果("反論・反実仮想","SUSPEND",("EXCEPTION_NOT_CLOSED",)))
            return self._hold(question_ir,labels,states,gates,("HDS_EXCEPTION_NOT_RESOLVED","NO_GUESS"))

        if contradicted:
            return self._hold(question_ir,labels,states,gates,("HDS_UNRESOLVED_CONTRADICTION","NO_COMMIT"))
        if len(eligible)==0:
            gates.append(HDS判定門結果("Commit","SUSPEND",("NO_COMMIT_ELIGIBLE_CANDIDATE",)))
            return self._hold(question_ir,labels,states,gates,("HDS_EVIDENCE_INSUFFICIENT","NO_GUESS"))
        if len(eligible)>1:
            gates.append(HDS判定門結果("反論・候補横断","SUSPEND",tuple(f"COMPETING:{x}" for x in eligible)))
            gates.append(HDS判定門結果("Commit","SUSPEND",("MULTIPLE_COMMIT_ELIGIBLE",)))
            return self._hold(question_ir,labels,states,gates,("HDS_COMPETING_EVIDENCE","NO_GUESS"))
        selected=eligible[0]
        gates.append(HDS判定門結果("反論・候補横断","PASS",("UNIQUE_COMMIT_ELIGIBLE",)))
        gates.append(HDS判定門結果("Commit","PASS",("SCOPED_PROVISIONAL_COMMIT",)))
        return self._approve(question_ir,selected,labels,states,gates,("HDS_JUDGEMENT_SELECTED","EVIDENCE_GATE_PASS","AUTHORITY_SEPARATED"))

    def _hold(self,ir,labels,states,gates,reasons):
        uncertain=tuple(x.候補ID for x in states if x.状態!="UNSUPPORTED") or labels
        gates=tuple((*gates,HDS判定門結果("総暫定性","PASS",("REOPENABLE_DECISION_RETAINED",))))
        return HDS判断結果("SUSPEND",None,"保留","HOLD","保留","未確定","OPEN",str(ir.暫定性状態),gates,tuple(states),labels,uncertain,tuple(reasons))

    def _approve(self,ir,selected,labels,states,gates,reasons):
        retained=tuple(x for x in labels if x!=selected)
        gates=tuple((*gates,HDS判定門結果("総暫定性","PASS",("SCOPED_COMMIT_REOPENABLE",))))
        return HDS判断結果("APPROVE",selected,"局所暫定断定","COMMIT","暫定採用","確定支持","CLOSED_FOR_OPERATION",str(ir.暫定性状態),gates,tuple(states),retained,retained,tuple(reasons))

__all__=["HDS判断参照","HDS判定門結果","HDS候補判断状態","HDS判断結果","HDS判断主体"]