from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
import json
from typing import Iterable

from .hds_choice_runtime import HDS選択実行結果, HDS選択推論実行
from .hds_ir import HDSIR
from .hds_runtime_projection import HDSR質問射影
from .hds候補提案runtime import HDS候補提案実行
from .hds介入制御 import (
    HDS介入制御,
    HDS介入記録,
    HDS指令種別,
    HDS監督状態,
    介入観測,
    既存作用,
    既存作用機会,
    既存判定,
    残差種別,
    標準HDS介入制御,
)
from .hds参照拡張 import HDS候補被覆優先統合, HDS追加参照検索
from .hds既存能力resolver import (
    既存MINIDORA提案解決,
    既存提案源,
    既存提案状態,
    既存能力提案,
    既存解決結果,
)
from .k3_functional import K3相当能力核
from .模型 import MINIDORA模型核
from .能力状態差循環 import MINIDORA能力状態差模型核
from .参照 import 参照供給器, 参照記録


_介入不能理由 = frozenset({
    "HDS_CHOICE_SET_INCOMPLETE",
    "HDS_CHOICE_LABEL_DUPLICATE",
    "HDS_CHOICE_UNRESOLVED",
    "HDS_QUESTION_SEMANTIC_LOSS",
    "HDS_K_QUESTION_SEMANTIC_LOSS",
    "HDS_CHOICE_COMPILE_FAILED",
    "HDS_CHOICE_SEMANTIC_LOSS",
})


def _hash(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":"))
    return sha256(raw.encode("utf-8")).hexdigest()[:20]


def _choices(ir: HDSIR) -> dict[str, str]:
    return {
        coord.座標ID.split(":", 1)[1]: str(coord.内容)
        for coord in ir.座標
        if coord.座標ID.startswith("choice:")
    }


def _safe_model_core(core: MINIDORA模型核 | None) -> MINIDORA模型核 | None:
    """同一Dataの候補集合縮小だけで再投票しない能力模型view。"""
    if core is None or not isinstance(core, MINIDORA能力状態差模型核):
        return core
    return MINIDORA能力状態差模型核(
        core.関係群,
        言語対応_=core.言語対応,
        能力作用群=core.能力作用群,
        形成済み関係群=core.形成済み関係群,
        最大再作用回数=0,
    )


def _legacy_proposal(result: HDS選択実行結果) -> 既存能力提案:
    approved = result.状態 == "APPROVE" and result.回答ラベル is not None
    root = bool(result.K3結果 is not None and result.K3結果.根拠事実数 > 0)
    direct = "DIRECTED_RELATION_VERIFIED" in result.理由
    return 既存能力提案(
        既存提案源.直接関係 if direct else 既存提案源.K3,
        既存提案状態.承認候補 if approved else 既存提案状態.保留,
        result.回答ラベル if approved else None,
        根拠成立=root,
        一意=approved,
        直接検証済み=direct,
        理由=tuple(result.理由),
    )


def _model_proposal(result: HDS選択実行結果) -> 既存能力提案:
    model = result.MINIDORA模型結果
    approved = result.状態 in {"PROPOSE", "APPROVE"} and result.回答ラベル is not None
    score = 0
    unique = False
    if model is not None and result.回答ラベル is not None:
        score = int(model.参照候補辞書().get(result.回答ラベル, 0))
        unique = bool(model.参照最有力候補ID == result.回答ラベル and not model.参照同率候補ID)
    return 既存能力提案(
        既存提案源.能力模型,
        既存提案状態.承認候補 if approved else 既存提案状態.保留,
        result.回答ラベル if approved else None,
        根拠成立=score > 0,
        一意=unique,
        理由=tuple(result.理由),
    )


def _reason_residuals(results: Iterable[HDS選択実行結果]) -> set[残差種別]:
    out: set[残差種別] = set()
    for result in results:
        joined = "\n".join(str(x) for x in result.理由)
        if "QUESTION_SEMANTIC_LOSS" in joined or "HDS_K_QUESTION_SEMANTIC_LOSS" in joined:
            out.add(残差種別.問題意味損失)
        if "CHOICE_SEMANTIC_LOSS" in joined:
            out.add(残差種別.候補意味損失)
        if "DATA_COMPILE_PARTIAL" in joined or result.Dataコンパイル失敗数 > 0:
            out.add(残差種別.Data意味損失)
        if "NO_KNOWLEDGE_EVIDENCE" in joined or "NO_CANDIDATE" in joined or "MINIDORA_OUTPUT_ABSENT" in joined:
            out.add(残差種別.観測不足)
        if "AMBIGUOUS_EVIDENCE" in joined or "EXCEPTION_NOT_RESOLVED" in joined:
            out.add(残差種別.候補競合)
        if "HDS_ACTION_DELTA_ATTACHED" in joined and "HDS_ACTION_DELTA_CONSUMED" not in joined:
            out.add(残差種別.状態差未消費)
    return out


def _resolved_residuals(
    resolved: 既存解決結果,
    results: Iterable[HDS選択実行結果],
    references: tuple[参照記録, ...],
) -> frozenset[残差種別]:
    out = _reason_residuals(results)
    for raw in resolved.残差:
        value = str(raw)
        if "CANDIDATE_CONFLICT" in value:
            out.add(残差種別.候補競合)
        elif "DISCRIMINATION" in value:
            out.add(残差種別.候補識別不足)
        elif "FAILURE" in value:
            out.add(残差種別.未解残差)
    if not references:
        out.add(残差種別.観測不足)
    if resolved.状態 == 既存提案状態.保留 and not out:
        out.add(残差種別.候補識別不足)
    return frozenset(out)


@dataclass(frozen=True, slots=True)
class HDS監督選択結果:
    選択: HDS選択実行結果
    参照: tuple[参照記録, ...]
    HDS介入数: int
    HDS作用: tuple[str, ...]
    停止理由: tuple[str, ...] = ()


class _Session:
    def __init__(
        self,
        question_ir: HDSIR,
        references: tuple[参照記録, ...],
        *,
        コンパイル,
        基礎能力核: K3相当能力核,
        模型核: MINIDORA模型核 | None,
        参照供給器: 参照供給器 | None,
    ) -> None:
        self.question_ir = question_ir
        self.search_ir = HDSR質問射影(question_ir)
        self.references = tuple(references)
        self.コンパイル = コンパイル
        self.基礎能力核 = 基礎能力核
        self.模型核 = _safe_model_core(模型核)
        self.参照供給器 = 参照供給器
        self.choice_map = _choices(question_ir)
        self.generation = 0
        self.extra_r_level = 0
        self.legacy_results: list[HDS選択実行結果] = []
        self.model_result: HDS選択実行結果 | None = None
        self.resolved: 既存解決結果 | None = None
        self.last_template: HDS選択実行結果 | None = None
        self.ran_working: set[int] = set()
        self.ran_local: set[int] = set()

    def _ref_sig(self) -> str:
        return _hash(tuple((r.識別子, r.信頼, r.条件) for r in self.references))

    def _candidate_sig(self) -> str:
        rows: list[tuple[object, ...]] = []
        for result in (*self.legacy_results, *((self.model_result,) if self.model_result else ())):
            rows.append((result.状態, bool(result.回答ラベル), tuple(sorted(set(result.理由)))))
        if self.resolved is not None:
            rows.append((self.resolved.状態.value, tuple(self.resolved.残差), tuple(x.value for x in self.resolved.採用源)))
        return _hash(rows)

    def _all_results(self) -> tuple[HDS選択実行結果, ...]:
        return tuple(self.legacy_results) + ((self.model_result,) if self.model_result else ())

    def all_reasons(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(
            reason
            for result in self._all_results()
            for reason in result.理由
        ))

    def intervention_blockers(self) -> tuple[str, ...]:
        return tuple(reason for reason in self.all_reasons() if reason in _介入不能理由)

    def _legacy(self, *, working: bool, local: bool) -> HDS選択実行結果:
        result = HDS選択推論実行(
            self.question_ir,
            self.references,
            コンパイル=self.コンパイル,
            基礎能力核=self.基礎能力核.clone(),
            作業再作用=working,
            局所再照合=local,
            正式模型評価=False,
        )
        self.last_template = result
        self.legacy_results.append(result)
        return result

    def _model(self) -> HDS選択実行結果:
        result = HDS候補提案実行(
            self.question_ir,
            self.references,
            コンパイル=self.コンパイル,
            基礎能力核=self.基礎能力核,
            模型核=self.模型核,
        )
        self.last_template = result
        self.model_result = result
        return result

    def evaluate_base(self) -> 既存解決結果:
        self.legacy_results.clear()
        self.model_result = None
        self._legacy(working=False, local=False)
        self._model()
        return self.resolve()

    def resolve(self) -> 既存解決結果:
        proposals = [_legacy_proposal(row) for row in self.legacy_results]
        if self.model_result is not None:
            proposals.append(_model_proposal(self.model_result))
        self.resolved = 既存MINIDORA提案解決(proposals)
        return self.resolved

    def residuals(self) -> frozenset[残差種別]:
        if self.resolved is None:
            return frozenset()
        return _resolved_residuals(self.resolved, self._all_results(), self.references)

    def supervisory_state(self) -> HDS監督状態:
        resolved = self.resolved
        approved = bool(resolved and resolved.状態 == 既存提案状態.承認候補 and resolved.回答 is not None)
        failed = bool(resolved and resolved.状態 == 既存提案状態.失敗)
        return HDS監督状態(
            既存判定.承認 if approved else 既存判定.失敗 if failed else 既存判定.保留,
            approved,
            bool(resolved and 既存提案源.直接関係 in resolved.採用源),
            approved,
            self._ref_sig(),
            self._candidate_sig(),
            frozenset() if approved else self.residuals(),
        )

    def offers(self) -> tuple[既存作用機会, ...]:
        residuals = self.residuals()
        base_sig = f"g{self.generation}:{self._ref_sig()}"
        offers: list[既存作用機会] = []
        if self.generation not in self.ran_working and residuals.intersection({
            残差種別.候補競合, 残差種別.候補識別不足, 残差種別.状態差未消費,
        }):
            offers.append(既存作用機会(
                既存作用.作業再作用,
                frozenset({残差種別.候補競合, 残差種別.候補識別不足, 残差種別.状態差未消費}),
                f"working:{base_sig}", 1, True, ("EXISTING_WORKING_RELATION_AVAILABLE",),
            ))
        if self.generation not in self.ran_local and residuals.intersection({
            残差種別.Data意味損失, 残差種別.候補競合, 残差種別.候補識別不足,
        }):
            offers.append(既存作用機会(
                既存作用.局所再照合,
                frozenset({残差種別.Data意味損失, 残差種別.候補競合, 残差種別.候補識別不足}),
                f"local:{base_sig}", 2, True, ("EXISTING_LOCAL_REPARSE_AVAILABLE",),
            ))
        if self.参照供給器 is not None and residuals.intersection({
            残差種別.観測不足, 残差種別.Data意味損失, 残差種別.候補識別不足, 残差種別.候補競合,
        }):
            offers.append(既存作用機会(
                既存作用.参照取得,
                frozenset({残差種別.観測不足, 残差種別.Data意味損失, 残差種別.候補識別不足, 残差種別.候補競合}),
                f"reference:{base_sig}:level{self.extra_r_level + 1}", 4, True,
                ("EXISTING_REFERENCE_PROVIDER_AVAILABLE",),
            ))
        return tuple(offers)

    def run_action(self, action: 既存作用) -> bool:
        before = (self._ref_sig(), self._candidate_sig(), tuple(sorted(x.value for x in self.residuals())))
        if action == 既存作用.作業再作用:
            self.ran_working.add(self.generation)
            self._legacy(working=True, local=False)
        elif action == 既存作用.局所再照合:
            self.ran_local.add(self.generation)
            self._legacy(working=False, local=True)
        elif action == 既存作用.能力模型照合:
            self._model()
        elif action == 既存作用.参照取得:
            if self.参照供給器 is None:
                return False
            self.extra_r_level += 1
            observed = HDS追加参照検索(self.参照供給器, self.search_ir, 段階=self.extra_r_level)
            limit = max(len(self.references), len(observed))
            merged = HDS候補被覆優先統合(self.references, observed, tuple(self.choice_map), limit)
            if tuple((x.識別子, x.条件) for x in merged) != tuple((x.識別子, x.条件) for x in self.references):
                self.references = merged
                self.generation += 1
                self.evaluate_base()
                after = (self._ref_sig(), self._candidate_sig(), tuple(sorted(x.value for x in self.residuals())))
                return before != after
            return False
        else:
            return False
        self.resolve()
        after = (self._ref_sig(), self._candidate_sig(), tuple(sorted(x.value for x in self.residuals())))
        return before != after

    def final_result(
        self,
        *,
        records: tuple[HDS介入記録, ...],
        stop_reasons: tuple[str, ...],
    ) -> HDS選択実行結果:
        if self.last_template is None:
            raise RuntimeError("既存MINIDORA能力が一度も実行されていない")
        resolved = self.resolved or self.resolve()
        approved = resolved.状態 == 既存提案状態.承認候補 and resolved.回答 is not None
        answer = resolved.回答 if approved else None
        content = self.choice_map.get(answer) if answer is not None else None
        template = self.last_template
        if approved and resolved.採用源 == (既存提案源.能力模型,) and self.model_result is not None:
            template = self.model_result
        elif approved:
            for row in reversed(self.legacy_results):
                if row.回答ラベル == answer:
                    template = row
                    break

        reasons: list[str] = [
            *self.all_reasons(),
            *resolved.理由,
            "EXISTING_MINIDORA_CAPABILITY_RESOLVER",
            "HDS_SUPERVISORY_CONTROL_ONLY",
            "NO_FINAL_HDS_JUDGEMENT_WRAPPER",
            f"HDS_SUPERVISORY_INTERVENTIONS:{len(records)}",
        ]
        reasons.extend("HDS_INTERVENTION_ACTION:" + row.作用.value for row in records)
        reasons.extend(stop_reasons)
        return replace(
            template,
            状態="APPROVE" if approved else "SUSPEND",
            回答ラベル=answer,
            回答内容=content,
            理由=tuple(dict.fromkeys(reasons)),
        )


def HDS監督選択実行(
    question_ir: HDSIR,
    references: tuple[参照記録, ...],
    *,
    コンパイル,
    基礎能力核: K3相当能力核,
    模型核: MINIDORA模型核 | None,
    参照供給器: 参照供給器 | None = None,
    HDS制御: HDS介入制御 | None = None,
    HDS介入予算: int = 6,
) -> HDS監督選択結果:
    """既存MINIDORA能力を使い、未閉包時だけHDSが既存作用へ介入する。"""
    session = _Session(
        question_ir,
        references,
        コンパイル=コンパイル,
        基礎能力核=基礎能力核,
        模型核=模型核,
        参照供給器=参照供給器,
    )
    session.evaluate_base()
    records: list[HDS介入記録] = []
    stop_reasons: tuple[str, ...] = session.intervention_blockers()

    while HDS制御 is not None and not stop_reasons:
        state = session.supervisory_state()
        if state.既存判定 == 既存判定.承認 and state.出力存在 and not state.残差:
            break
        observation = 介入観測(
            state,
            session.offers(),
            tuple(records),
            max(0, int(HDS介入予算) - len(records)),
        )
        directive = HDS制御.判定(observation)
        if directive.種別 == HDS指令種別.不介入:
            break
        if directive.種別 == HDS指令種別.停止要求 or directive.作用 is None:
            stop_reasons = directive.理由 or ("HDS_SUPERVISORY_STOP_REQUEST",)
            break
        offer = next(
            (
                item for item in observation.作用機会
                if item.作用 == directive.作用 and set(directive.対象残差).issubset(item.解消対象)
            ),
            None,
        )
        if offer is None:
            stop_reasons = ("HDS_DIRECTIVE_NOT_BACKED_BY_EXISTING_OFFER",)
            break
        progressed = session.run_action(directive.作用)
        records.append(HDS介入記録(directive.作用, offer.作用入力署名, directive.対象残差, progressed))
        blockers = session.intervention_blockers()
        if blockers:
            stop_reasons = blockers
            break

    selection = session.final_result(records=tuple(records), stop_reasons=stop_reasons)
    return HDS監督選択結果(
        selection,
        session.references,
        len(records),
        tuple(row.作用.value for row in records),
        stop_reasons,
    )


__all__ = ["HDS監督選択結果", "HDS監督選択実行", "標準HDS介入制御"]
