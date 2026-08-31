from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from fractions import Fraction
import inspect
from typing import Any

from .hds_adapter import HDS文脈
from .hds_choice_runtime import HDS選択実行結果, HDS選択問題, HDS選択推論実行
from .hds_ir import HDSIR
from .hds_reference import HDS参照予算選択, HDS参照検索
from .hds_runtime_projection import HDSR質問射影
from .hds介入制御 import HDS介入制御, 標準HDS介入制御
from .hds監督選択runtime import HDS監督選択実行
from .multilingual_surface import 表面化 as 多言語表面化
from .参照 import 参照供給器, 参照記録, 参照矛盾数
from .命令 import 手順
from .採否 import 実行状態, 採否, 採否結果
from .模型 import MINIDORA模型核, 模型結果, 成立候補, 言語状態
from .能力状態差循環 import 標準能力模型核
from .言語 import 自然言語器
from .言語確率法則 import (
    MINIDORA厳密言語模型,
    条件付き記号分布,
    言語確率監査結果,
    最小厳密言語模型,
)
from .計算実行器 import 計算実行器


_標準HDS監督 = object()


@dataclass(frozen=True, slots=True)
class 要求:
    問合せ: str
    手順: 手順 | None = None
    初期状態: dict[str, Any] = field(default_factory=dict)
    参照必須: bool = False
    # v0.3互換。既定LLM核では解釈せず、主体主幹を明示接続した時だけ使用する。
    主体更新提案: Any = None
    主体整合必須: bool = True
    矛盾数: int = 0
    境界違反: bool = False


@dataclass(frozen=True, slots=True)
class 結果:
    値: Any
    状態: dict[str, Any]
    参照: tuple[参照記録, ...]
    履歴: tuple[dict[str, Any], ...]
    採否: 採否結果
    主体状態: Any = None
    主体整合: Any = None
    主体監査履歴: tuple[Any, ...] = ()
    言語計画: str | None = None
    HDS_IR: HDSIR | None = None


@dataclass(frozen=True, slots=True)
class _LLM互換主体状態:
    """旧結果ABI用の固定値。判断主体・記憶・更新機構ではない。"""
    主体ID: str = "MINIDORA"
    現在目的: tuple[str, ...] = ()
    判断基準: tuple[str, ...] = ()
    立場: tuple[tuple[str, str], ...] = ()
    選好: tuple[tuple[str, str], ...] = ()
    約束: tuple[str, ...] = ()
    仮説: tuple[str, ...] = ()
    未解残差: tuple[str, ...] = ()
    版: int = 0

    def 辞書化(self) -> dict[str, Any]:
        return {
            "主体ID": self.主体ID, "現在目的": self.現在目的, "判断基準": self.判断基準,
            "立場": self.立場, "選好": self.選好, "約束": self.約束,
            "仮説": self.仮説, "未解残差": self.未解残差, "版": self.版,
        }


@dataclass(frozen=True, slots=True)
class _LLM互換主体整合:
    状態: 実行状態
    理由: tuple[str, ...]
    適用差分: tuple[tuple[str, Any, Any], ...] = ()
    更新後: Any = None


class ミニドラ:
    """最小汎用LLM核を正本とするMINIDORA v0.5 Runtime。

    既定経路は厳密言語模型・能力模型・汎用計算器・外部Data/R・HDS安全弁だけで成立する。
    旧主体主幹、Trinity記憶、K3 helperは明示接続または明示API呼出時だけ利用する。
    候補得点を確率へ読み替えて厳密言語模型を偽装しない。
    """

    def __init__(
        self,
        参照供給器_: 参照供給器 | None = None,
        layer0=None,
        主体主幹_=None,
        自然言語器_: 自然言語器 | None = None,
        HDSコンパイラ_=None,
        Trinity文脈_=None,
        K3能力核_=None,
        *,
        模型核_: MINIDORA模型核 | None = None,
        言語模型核_: MINIDORA厳密言語模型 | None = None,
        計算実行器_: 計算実行器 | None = None,
        HDS監督制御_: HDS介入制御 | None | object = _標準HDS監督,
    ) -> None:
        executor = 計算実行器_ or layer0 or 計算実行器()
        self.参照供給器 = 参照供給器_
        self.layer0 = executor
        self.計算実行器 = executor
        self.自然言語器 = 自然言語器_ or 自然言語器()
        self.HDSコンパイラ = HDSコンパイラ_
        self.主体主幹 = 主体主幹_
        self.Trinity文脈 = Trinity文脈_
        self._K3能力核 = K3能力核_
        self._互換主体状態 = _LLM互換主体状態()
        self._HDS版 = 0
        self._HDS現在焦点: Any = None
        self._HDS直前結果: Any = None
        self._HDS直前IR: HDSIR | None = None
        self._HDS未解残差: tuple[tuple[str, str], ...] = ()
        self._HDS履歴状態: list[HDSIR] = []
        self.言語模型核 = 言語模型核_ or 最小厳密言語模型()
        self.能力模型核 = 模型核_ or 標準能力模型核()
        self.模型核 = self.能力模型核
        self.HDS監督制御 = 標準HDS介入制御() if HDS監督制御_ is _標準HDS監督 else HDS監督制御_

    @property
    def 主体状態(self):
        return self.主体主幹.現在 if self.主体主幹 is not None else self._互換主体状態

    @property
    def HDS履歴(self) -> tuple[HDSIR, ...]:
        if self.Trinity文脈 is not None:
            return self.Trinity文脈.記憶主体.IR履歴
        return tuple(self._HDS履歴状態)

    @property
    def HDS文脈(self) -> HDS文脈:
        if self.Trinity文脈 is not None:
            return self.Trinity文脈.判断主体.文脈()
        refs: list[str] = []
        if self._HDS現在焦点 is not None:
            refs.append("working:current_focus")
        if self._HDS直前結果 is not None:
            refs.append("working:last_result")
        if self._HDS直前IR is not None:
            refs.append("working:last_ir")
        if self._HDS未解残差:
            refs.append("working:unresolved")
        return HDS文脈(
            記憶版=self._HDS版,
            現在焦点=self._HDS現在焦点,
            直前結果=self._HDS直前結果,
            直前IR=self._HDS直前IR,
            未解残差=self._HDS未解残差,
            記憶引用=tuple(refs),
        )

    @property
    def K3能力核(self):
        """旧helperは明示アクセスされた時だけ生成する。"""
        if self._K3能力核 is None:
            from .k3_functional import K3相当能力核
            self._K3能力核 = K3相当能力核()
        setattr(self._K3能力核, "_minidora_model_core", self.能力模型核)
        return self._K3能力核

    def K3知識投入(self, statements: Iterable[str]):
        return self.K3能力核.知識投入(statements)

    def K3グリッド投入(self, grid: Sequence[Sequence[int]]):
        return self.K3能力核.グリッド投入(grid)

    def K3実行(self, request: str, effort: str | None = None):
        return self.K3能力核.実行(request, effort)

    def コンパイル(self, 問合せ: str) -> HDSIR:
        if self.HDSコンパイラ is None:
            raise RuntimeError("HDS Compilerが接続されていない")
        if self.Trinity文脈 is not None:
            return self.Trinity文脈.コンパイル(self.HDSコンパイラ, 問合せ)
        context = self.HDS文脈
        compile_fn = self.HDSコンパイラ.コンパイル
        params = inspect.signature(compile_fn).parameters
        has_kwargs = any(p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values())
        kwargs: dict[str, Any] = {}
        if "前回結果" in params or has_kwargs:
            kwargs["前回結果"] = context.直前結果
        if "HDS履歴" in params or has_kwargs:
            kwargs["HDS履歴"] = self.HDS履歴
        if "文脈" in params or has_kwargs:
            kwargs["文脈"] = context
        return compile_fn(問合せ, **kwargs)

    def _帰還(self, result: 結果) -> 結果:
        if self.Trinity文脈 is not None:
            if result.HDS_IR is not None:
                self.Trinity文脈.帰還(result.採否, result.値, result.HDS_IR)
            return result
        if result.HDS_IR is not None:
            self._HDS直前IR = result.HDS_IR
            self._HDS履歴状態.append(result.HDS_IR)
            self._HDS版 += 1
        if result.採否.状態 == 実行状態.合格 and result.値 is not None:
            self._HDS直前結果 = result.値
            self._HDS現在焦点 = result.値
            self._HDS未解残差 = ()
            self._HDS版 += 2
        elif result.採否.状態 == 実行状態.保留 and result.HDS_IR is not None:
            residuals = tuple((item.種別, item.理由) for item in result.HDS_IR.残差)
            if residuals:
                self._HDS未解残差 = residuals
                self._HDS版 += 1
        return result

    def _主体状態辞書(self) -> dict[str, Any]:
        if self.主体主幹 is None:
            return self._互換主体状態.辞書化()
        return self.主体主幹.状態辞書()

    def _非主体結果(self, 理由: str) -> _LLM互換主体整合:
        return _LLM互換主体整合(実行状態.非適用, (理由,), (), self._互換主体状態)

    def _主体更新候補(self, 文脈状態: Mapping[str, Any], 要求_: 要求):
        if self.主体主幹 is None:
            return None
        candidate = 文脈状態.get("主体更新提案", 要求_.主体更新提案)
        if candidate is None or hasattr(candidate, "変更"):
            return candidate
        if isinstance(candidate, Mapping):
            from .主体 import 主体更新提案
            return 主体更新提案(
                変更=candidate.get("変更", {}),
                理由=tuple(candidate.get("理由", ())),
                根拠=tuple(candidate.get("根拠", ())),
            )
        raise TypeError("主体更新提案は 主体更新提案 または mapping である必要がある")

    def _主体合成(self, 基礎: 採否結果, 文脈状態: Mapping[str, Any], 要求_: 要求):
        if self.主体主幹 is None:
            return 基礎, self._非主体結果("LLM核では主体機構を使用しない")
        subject = self.主体主幹.評価更新(self._主体更新候補(文脈状態, 要求_))
        if not 要求_.主体整合必須 or subject.状態 in {実行状態.合格, 実行状態.非適用}:
            return 基礎, subject
        if subject.状態 == 実行状態.失敗:
            return 採否結果(実行状態.失敗, 基礎.理由 + subject.理由), subject
        return 採否結果(実行状態.保留, 基礎.理由 + subject.理由), subject

    def _HDS未閉包(self, 要求_: 要求, ir: HDSIR, 理由: tuple[str, ...]) -> 結果:
        subject = self._非主体結果("HDS-IRが実行閉包していないため主体更新未実行") if self.主体主幹 is None else self.主体主幹.非適用結果("HDS-IRが実行閉包していないため主体更新未実行")
        return self._帰還(結果(
            None, dict(要求_.初期状態), (), (), 採否結果(実行状態.保留, 理由),
            self.主体状態, subject, tuple(getattr(self.主体主幹, "履歴", ())), "HDS_IR", ir,
        ))

    def _HDS選択結果(
        self,
        要求_: 要求,
        ir: HDSIR,
        参照: tuple[参照記録, ...],
        選択: HDS選択実行結果,
    ) -> 結果:
        value = 選択.回答内容 if 選択.状態 == "APPROVE" else None
        reasons = list(選択.理由)
        conflict_count = 要求_.矛盾数 + 参照矛盾数(参照)
        if 要求_.境界違反:
            base = 採否結果(実行状態.失敗, tuple(reasons + ["境界違反"])); value = None
        elif conflict_count:
            base = 採否結果(実行状態.保留, tuple(reasons + ["未解消矛盾"])); value = None
        elif 選択.状態 == "APPROVE" and value is not None:
            base = 採否結果(実行状態.合格, tuple(reasons))
        else:
            base = 採否結果(実行状態.保留, tuple(reasons or ["HDS_CHOICE_SUSPEND"])); value = None

        state: dict[str, Any] = dict(要求_.初期状態)
        state.update({
            "結果": value, "参照": 参照, "主体状態": self._主体状態辞書(), "HDS文脈": self.HDS文脈,
            "HDS候補ラベル": 選択.回答ラベル,
            "HDS候補コンパイル数": 選択.候補コンパイル数,
            "HDS_Dataコンパイル数": 選択.Dataコンパイル数,
            "HDS_Dataコンパイル失敗数": 選択.Dataコンパイル失敗数,
            "K追加事実数": 選択.K追加事実数,
            "K証拠事実数": 選択.K証拠事実数,
            "K証拠阻害事実数": 選択.K証拠阻害事実数,
        })
        if 選択.K3結果 is not None:
            state["K3努力水準"] = 選択.K3結果.努力水準
            state["K3探索深さ上限"] = 選択.K3結果.探索深さ上限
            state["K3証拠上限"] = 選択.K3結果.証拠上限
            state["K3候補診断"] = tuple({
                "候補": item.候補, "合計得点": item.合計得点, "証拠得点": item.証拠得点,
                "graph得点": item.graph得点, "独立出典数": item.独立出典数, "graph深さ": item.graph深さ,
            } for item in 選択.K3結果.候補診断)

        decision, subject = self._主体合成(base, state, 要求_)
        if decision.状態 in {実行状態.保留, 実行状態.失敗}:
            value = None
            state["結果"] = None
        history = (
            {"op":"HDS_CHOICE_NATIVE","status":選択.状態,"answer_label":選択.回答ラベル,"candidate_compiled":選択.候補コンパイル数},
            {"op":"R_TO_HDS_TO_K","reference_count":len(参照),"data_compiled":選択.Dataコンパイル数,"data_compile_failed":選択.Dataコンパイル失敗数,"k_facts_added":選択.K追加事実数,"evidence_facts":選択.K証拠事実数,"blocked_evidence_facts":選択.K証拠阻害事実数},
        )
        return self._帰還(結果(
            value, state, 参照, history, decision, self.主体状態, subject,
            tuple(getattr(self.主体主幹, "履歴", ())), "HDS_CHOICE_NATIVE", ir,
        ))

    def 実行(self, 要求_: 要求) -> 結果:
        自動計画 = 要求_.手順 is None
        hds_ir: HDSIR | None = None
        plan_name: str | None = None
        initial_from_plan: dict[str, Any] = {}
        reference_from_plan = False
        手順_: 手順 | None = 要求_.手順

        if 自動計画 and self.HDSコンパイラ is not None:
            try:
                hds_ir = self.コンパイル(要求_.問合せ)
            except (ValueError, TypeError) as exc:
                return 結果(None, dict(要求_.初期状態), (), (), 採否結果(実行状態.失敗, ("HDS Compiler実行失敗", str(exc))), self.主体状態, self._非主体結果("HDS Compiler実行失敗"), (), "HDS_IR", None)

            if HDS選択問題(hds_ir):
                references: tuple[参照記録, ...] = ()
                if self.参照供給器 is not None:
                    budget = HDS参照予算選択(hds_ir)
                    references = HDS参照検索(
                        self.参照供給器, HDSR質問射影(hds_ir), 上限=budget.取得上限,
                        一問合せ上限=budget.一問合せ上限, 最大問合せ並列=budget.最大問合せ並列,
                    )
                initial = HDS選択推論実行(
                    hds_ir, references, コンパイル=self.コンパイル, 基礎能力核=None,
                    模型核=self.能力模型核, 正式模型評価=True,
                )
                if self.HDS監督制御 is None or (initial.状態 == "APPROVE" and initial.回答ラベル is not None):
                    return self._HDS選択結果(要求_, hds_ir, references, initial)
                supervised = HDS監督選択実行(
                    hds_ir, references, コンパイル=self.コンパイル, 基礎能力核=None,
                    模型核=self.能力模型核, 参照供給器=self.参照供給器,
                    計算実行器_=self.計算実行器, HDS制御=self.HDS監督制御, 初期選択=initial,
                )
                return self._HDS選択結果(要求_, hds_ir, supervised.参照, supervised.選択)

            if not hds_ir.実行可能:
                reasons = ["HDS_IR未閉包", *hds_ir.実行阻害理由]
                reasons.extend(f"残差:{item.理由}" for item in hds_ir.残差)
                return self._HDS未閉包(要求_, hds_ir, tuple(reasons))
            手順_ = hds_ir.手順
            initial_from_plan = dict(hds_ir.初期状態)
            reference_from_plan = hds_ir.参照必須
            plan_name = hds_ir.種別 or "HDS_IR"
        elif 自動計画:
            plan = self.自然言語器.計画(要求_.問合せ)
            手順_ = plan.手順
            initial_from_plan = dict(plan.初期状態)
            reference_from_plan = plan.参照必須
            plan_name = plan.種別

        if 手順_ is None:
            raise ValueError("実行手順が確定していない")
        reference_required = 要求_.参照必須 or reference_from_plan
        references: tuple[参照記録, ...] = ()
        if self.参照供給器 is not None:
            if hds_ir is not None:
                budget = HDS参照予算選択(hds_ir)
                references = HDS参照検索(self.参照供給器, HDSR質問射影(hds_ir), 上限=budget.取得上限, 一問合せ上限=budget.一問合せ上限, 最大問合せ並列=budget.最大問合せ並列)
            else:
                references = self.参照供給器.検索(要求_.問合せ)
        if reference_required and not references:
            decision = 採否(根拠数=0)
            subject = self._非主体結果("参照不足のため主体更新未実行") if self.主体主幹 is None else self.主体主幹.非適用結果("参照不足のため主体更新未実行")
            result = 結果(None, dict(要求_.初期状態), (), (), decision, self.主体状態, subject, tuple(getattr(self.主体主幹, "履歴", ())), plan_name, hds_ir)
            return self._帰還(result) if hds_ir is not None else result

        initial = dict(要求_.初期状態)
        initial.update(initial_from_plan)
        initial["参照"] = references
        initial["主体状態"] = self._主体状態辞書()
        if hds_ir is not None:
            initial["HDS文脈"] = self.HDS文脈
        try:
            context = self.layer0.実行(手順_, initial)
        except (ValueError, TypeError, ZeroDivisionError) as exc:
            if not 自動計画:
                raise
            subject = self._非主体結果("自動計画の実行失敗") if self.主体主幹 is None else self.主体主幹.非適用結果("自動計画の実行失敗")
            result = 結果(None, initial, (), (), 採否結果(実行状態.失敗, ("自動計画実行失敗", str(exc))), self.主体状態, subject, tuple(getattr(self.主体主幹, "履歴", ())), plan_name, hds_ir)
            return self._帰還(result) if hds_ir is not None else result

        value = context.状態.get("結果")
        evidence_count = (len(references) if value is not None else 0) if reference_required else (1 if value is not None else 0)
        base = 採否(根拠数=evidence_count, 矛盾数=要求_.矛盾数 + 参照矛盾数(references), 危険=要求_.境界違反)
        decision, subject = self._主体合成(base, context.状態, 要求_)
        state = dict(context.状態)
        if decision.状態 in {実行状態.保留, 実行状態.失敗}:
            value = None
            state["結果"] = None
        result = 結果(value, state, references, tuple(context.履歴), decision, self.主体状態, subject, tuple(getattr(self.主体主幹, "履歴", ())), plan_name, hds_ir)
        return self._帰還(result) if hds_ir is not None else result

    def 応答(self, 問合せ: str) -> str:
        result = self.実行(要求(問合せ))
        if result.HDS_IR is not None:
            language = result.HDS_IR.出力言語 or result.HDS_IR.入力言語
            return 多言語表面化(result.値, result.採否.状態.value, result.採否.理由, language)
        return self.自然言語器.表面化(result.値, result.採否.状態.value, result.採否.理由)

    def 言語確率(self, 文章: str) -> Fraction:
        return self.言語模型核.系列確率(文章)

    def 次記号分布(self, 接頭辞: str = "") -> 条件付き記号分布:
        return self.言語模型核.次記号分布(接頭辞)

    def 言語模型監査(self) -> 言語確率監査結果:
        return self.言語模型核.正規化監査()

    def 言語評価(self, 文脈: str | 言語状態, 候補群: Sequence[str | 言語状態 | 成立候補], *, 言語体系: str = "自然言語:ja", 履歴: Sequence[str | 言語状態] = (), 条件: Sequence[str] = (), 参照状態: Sequence[str | 言語状態] = ()) -> 模型結果:
        current = 文脈 if isinstance(文脈, 言語状態) else 言語状態(str(文脈), 言語体系)
        history_states = tuple(item if isinstance(item, 言語状態) else 言語状態(str(item), current.言語体系) for item in 履歴)
        reference_states = tuple(item if isinstance(item, 言語状態) else 言語状態(str(item), current.言語体系) for item in 参照状態)
        candidates: list[成立候補] = []
        for index, item in enumerate(候補群):
            if isinstance(item, 成立候補): candidates.append(item)
            elif isinstance(item, 言語状態): candidates.append(成立候補(item.識別子 or f"候補{index + 1}", item))
            else: candidates.append(成立候補(f"候補{index + 1}", 言語状態(str(item), current.言語体系)))
        return self.能力模型核.評価言語状態(current, tuple(candidates), 履歴=history_states, 条件=条件, 参照状態=reference_states)


__all__ = ["ミニドラ", "要求", "結果"]
