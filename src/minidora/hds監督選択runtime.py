from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
import json

from .hds_choice_runtime import HDS選択実行結果, HDS選択推論実行
from .hds_ir import HDSIR
from .hds_runtime_projection import HDSR質問射影
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
from .k3_functional import K3相当能力核
from .模型 import MINIDORA模型核
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


def _approved(result: HDS選択実行結果) -> bool:
    return bool(result.状態 == "APPROVE" and result.回答ラベル is not None)


def _residuals(
    result: HDS選択実行結果,
    references: tuple[参照記録, ...],
) -> frozenset[残差種別]:
    """通常MINIDORAの観測結果から、HDSへ渡す異常種別だけを抽出する。

    APPROVE済みの通常推論は安全弁の対象外とし、診断文字列を理由に再解釈しない。
    """
    if _approved(result):
        return frozenset()

    joined = "\n".join(str(x) for x in result.理由)
    out: set[残差種別] = set()
    if "QUESTION_SEMANTIC_LOSS" in joined or "HDS_K_QUESTION_SEMANTIC_LOSS" in joined:
        out.add(残差種別.問題意味損失)
    if "CHOICE_SEMANTIC_LOSS" in joined:
        out.add(残差種別.候補意味損失)
    if "DATA_COMPILE_PARTIAL" in joined or result.Dataコンパイル失敗数 > 0:
        out.add(残差種別.Data意味損失)
    if any(token in joined for token in (
        "NO_KNOWLEDGE_EVIDENCE",
        "NO_CANDIDATE",
        "MINIDORA_OUTPUT_ABSENT",
        "NO_GUESS",
        "EVIDENCE_INSUFFICIENT",
    )):
        out.add(残差種別.観測不足)
    if "AMBIGUOUS_EVIDENCE" in joined or "EXCEPTION_NOT_RESOLVED" in joined:
        out.add(残差種別.候補競合)
    if "HDS_ACTION_DELTA_ATTACHED" in joined and "HDS_ACTION_DELTA_CONSUMED" not in joined:
        out.add(残差種別.状態差未消費)
    if not references:
        out.add(残差種別.観測不足)
    if result.状態 == "FAIL":
        out.add(残差種別.未解残差)
    if not out:
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
    """通常MINIDORAを単一主体として保持するHDS安全弁セッション。"""

    def __init__(
        self,
        question_ir: HDSIR,
        references: tuple[参照記録, ...],
        *,
        コンパイル,
        基礎能力核: K3相当能力核,
        模型核: MINIDORA模型核 | None,
        参照供給器: 参照供給器 | None,
        初期選択: HDS選択実行結果 | None,
    ) -> None:
        self.question_ir = question_ir
        self.search_ir = HDSR質問射影(question_ir)
        self.references = tuple(references)
        self.コンパイル = コンパイル
        self.基礎能力核 = 基礎能力核
        self.模型核 = 模型核
        self.参照供給器 = 参照供給器
        self.choice_map = _choices(question_ir)
        self.generation = 0
        self.extra_r_level = 0
        self.ran_working: set[int] = set()
        self.ran_local: set[int] = set()
        self.ran_model: set[int] = set()
        self.initial = 初期選択 if 初期選択 is not None else self._normal()
        self.current = self.initial

    def _normal(
        self,
        *,
        working: bool = True,
        local: bool = True,
        formal_model: bool = False,
    ) -> HDS選択実行結果:
        kwargs = {
            "コンパイル": self.コンパイル,
            "基礎能力核": self.基礎能力核,
            "作業再作用": working,
            "局所再照合": local,
        }
        if formal_model:
            kwargs["模型核"] = self.模型核
            kwargs["正式模型評価"] = True
        return HDS選択推論実行(
            self.question_ir,
            self.references,
            **kwargs,
        )

    def _ref_sig(self) -> str:
        return _hash(tuple((r.識別子, r.信頼, r.条件) for r in self.references))

    def _candidate_sig(self) -> str:
        result = self.current
        return _hash((
            result.状態,
            bool(result.回答ラベル),
            tuple(sorted(set(result.理由))),
            result.Dataコンパイル数,
            result.Dataコンパイル失敗数,
            result.K証拠事実数,
            result.checkpoint再活性数,
            result.候補横断更新数,
        ))

    def residuals(self) -> frozenset[残差種別]:
        return _residuals(self.current, self.references)

    def intervention_blockers(self) -> tuple[str, ...]:
        return tuple(reason for reason in self.current.理由 if reason in _介入不能理由)

    def supervisory_state(self) -> HDS監督状態:
        result = self.current
        approved = _approved(result)
        failed = result.状態 == "FAIL"
        direct = "DIRECTED_RELATION_VERIFIED" in result.理由
        evidence = bool(
            result.K証拠事実数 > 0
            or (result.K3結果 is not None and result.K3結果.根拠事実数 > 0)
            or "EVIDENCE_PRESENT" in result.理由
        )
        return HDS監督状態(
            既存判定.承認 if approved else 既存判定.失敗 if failed else 既存判定.保留,
            approved,
            direct,
            evidence,
            self._ref_sig(),
            self._candidate_sig(),
            frozenset() if approved else self.residuals(),
        )

    def offers(self) -> tuple[既存作用機会, ...]:
        residuals = self.residuals()
        base_sig = f"g{self.generation}:{self._ref_sig()}:{self._candidate_sig()}"
        offers: list[既存作用機会] = []

        if self.generation not in self.ran_working and residuals.intersection({
            残差種別.候補競合,
            残差種別.候補識別不足,
            残差種別.状態差未消費,
        }):
            offers.append(既存作用機会(
                既存作用.作業再作用,
                frozenset({残差種別.候補競合, 残差種別.候補識別不足, 残差種別.状態差未消費}),
                f"working:{base_sig}",
                1,
                True,
                ("NORMAL_MINIDORA_WORKING_REACTION_AVAILABLE",),
            ))

        if self.generation not in self.ran_local and residuals.intersection({
            残差種別.Data意味損失,
            残差種別.候補競合,
            残差種別.候補識別不足,
        }):
            offers.append(既存作用機会(
                既存作用.局所再照合,
                frozenset({残差種別.Data意味損失, 残差種別.候補競合, 残差種別.候補識別不足}),
                f"local:{base_sig}",
                2,
                True,
                ("NORMAL_MINIDORA_LOCAL_REPARSE_AVAILABLE",),
            ))

        if self.generation not in self.ran_model and self.模型核 is not None and residuals.intersection({
            残差種別.候補競合,
            残差種別.候補識別不足,
            残差種別.状態差未消費,
        }):
            offers.append(既存作用機会(
                既存作用.能力模型照合,
                frozenset({残差種別.候補競合, 残差種別.候補識別不足, 残差種別.状態差未消費}),
                f"model:{base_sig}",
                3,
                True,
                ("NORMAL_MINIDORA_CAPABILITY_MODEL_AVAILABLE",),
            ))

        if self.参照供給器 is not None and residuals.intersection({
            残差種別.観測不足,
            残差種別.Data意味損失,
            残差種別.候補識別不足,
            残差種別.候補競合,
        }):
            offers.append(既存作用機会(
                既存作用.参照取得,
                frozenset({
                    残差種別.観測不足,
                    残差種別.Data意味損失,
                    残差種別.候補識別不足,
                    残差種別.候補競合,
                }),
                f"reference:{base_sig}:level{self.extra_r_level + 1}",
                4,
                True,
                ("NORMAL_MINIDORA_REFERENCE_EXPANSION_AVAILABLE",),
            ))
        return tuple(offers)

    def run_action(self, action: 既存作用) -> bool:
        before = (
            self._ref_sig(),
            self._candidate_sig(),
            tuple(sorted(x.value for x in self.residuals())),
        )

        if action == 既存作用.作業再作用:
            self.ran_working.add(self.generation)
            self.current = self._normal(working=True, local=False)
        elif action == 既存作用.局所再照合:
            self.ran_local.add(self.generation)
            self.current = self._normal(working=False, local=True)
        elif action == 既存作用.能力模型照合:
            self.ran_model.add(self.generation)
            self.current = self._normal(working=False, local=False, formal_model=True)
        elif action == 既存作用.参照取得:
            if self.参照供給器 is None:
                return False
            self.extra_r_level += 1
            observed = HDS追加参照検索(
                self.参照供給器,
                self.search_ir,
                段階=self.extra_r_level,
            )
            limit = max(len(self.references), len(observed))
            merged = HDS候補被覆優先統合(
                self.references,
                observed,
                tuple(self.choice_map),
                limit,
            )
            if tuple((x.識別子, x.条件) for x in merged) == tuple(
                (x.識別子, x.条件) for x in self.references
            ):
                return False
            self.references = merged
            self.generation += 1
            self.ran_working.discard(self.generation)
            self.ran_local.discard(self.generation)
            self.ran_model.discard(self.generation)
            self.current = self._normal()
        else:
            return False

        after = (
            self._ref_sig(),
            self._candidate_sig(),
            tuple(sorted(x.value for x in self.residuals())),
        )
        return before != after

    def final_result(
        self,
        *,
        records: tuple[HDS介入記録, ...],
        stop_reasons: tuple[str, ...],
    ) -> HDS選択実行結果:
        # 安全弁が動かなかった場合、通常MINIDORA結果を1bitも再解釈しない。
        if not records:
            return self.initial

        reasons = [
            *self.current.理由,
            "HDS_FEEDBACK_SAFETY_VALVE",
            f"HDS_SUPERVISORY_INTERVENTIONS:{len(records)}",
        ]
        reasons.extend("HDS_INTERVENTION_ACTION:" + row.作用.value for row in records)
        reasons.extend(stop_reasons)
        return replace(
            self.current,
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
    初期選択: HDS選択実行結果 | None = None,
    統一fallback: bool = True,
) -> HDS監督選択結果:
    """HDSをMINIDORAフィードバックループの安全弁として実行する。

    通常MINIDORAが閉包した場合は完全透過する。HDSは未閉包・競合・観測不足などの
    異常時だけ既存作用を起動し、作用後は必ず通常MINIDORAへ制御を戻す。
    """
    session = _Session(
        question_ir,
        references,
        コンパイル=コンパイル,
        基礎能力核=基礎能力核,
        模型核=模型核,
        参照供給器=参照供給器,
        初期選択=初期選択,
    )

    if HDS制御 is None or _approved(session.initial):
        return HDS監督選択結果(session.initial, session.references, 0, (), ())

    records: list[HDS介入記録] = []
    stop_reasons: tuple[str, ...] = session.intervention_blockers()

    while not stop_reasons:
        state = session.supervisory_state()
        if state.既存判定 == 既存判定.承認 and state.出力存在:
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
                item
                for item in observation.作用機会
                if item.作用 == directive.作用
                and set(directive.対象残差).issubset(item.解消対象)
            ),
            None,
        )
        if offer is None:
            stop_reasons = ("HDS_DIRECTIVE_NOT_BACKED_BY_EXISTING_OFFER",)
            break

        progressed = session.run_action(directive.作用)
        records.append(
            HDS介入記録(
                directive.作用,
                offer.作用入力署名,
                directive.対象残差,
                progressed,
            )
        )

        if _approved(session.current):
            break
        blockers = session.intervention_blockers()
        if blockers:
            stop_reasons = blockers
            break

    selection = session.final_result(records=tuple(records), stop_reasons=stop_reasons)

    # 歴代最高性能の既存経路を先に完走させ、その経路が未閉包の時だけ
    # K3/GLM/Llama3由来の統一状態循環を単調fallbackとして許可する。
    # 既存APPROVEを再解釈・置換しない。
    if 統一fallback and not _approved(selection) and 模型核 is not None:
        from .hds統一実行 import HDS統一選択評価
        from .hds統一状態循環 import HDS統一状態Session

        unified_session = HDS統一状態Session(
            str(question_ir.正規化文 or question_ir.原文),
            tuple(session.references),
            主体状態=None,
            認知世界ID=str(question_ir.認知世界ID or ""),
        )
        unified = HDS統一選択評価(
            question_ir,
            tuple(session.references),
            コンパイル=コンパイル,
            模型核=模型核,
            統一session=unified_session,
            主体状態=None,
        )
        if _approved(unified):
            inherited_reasons = []
            if records:
                inherited_reasons.extend((
                    "HDS_FEEDBACK_SAFETY_VALVE",
                    f"HDS_SUPERVISORY_INTERVENTIONS:{len(records)}",
                ))
                inherited_reasons.extend(
                    "HDS_INTERVENTION_ACTION:" + row.作用.value for row in records
                )
            selection = replace(
                unified,
                理由=tuple(dict.fromkeys(
                    tuple(unified.理由)
                    + tuple(inherited_reasons)
                    + ("HIGHWATER_MONOTONIC_FALLBACK_COMMIT",)
                )),
            )

    return HDS監督選択結果(
        selection,
        session.references,
        len(records),
        tuple(row.作用.value for row in records),
        stop_reasons,
    )


__all__ = ["HDS監督選択結果", "HDS監督選択実行", "標準HDS介入制御"]
