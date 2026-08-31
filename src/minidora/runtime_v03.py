from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Iterable, Mapping, Sequence

from .hds_adapter import HDSコンパイラProtocol, HDS文脈
from .hds_choice_runtime import HDS選択実行結果, HDS選択問題, HDS選択推論実行
from .hds_ir import HDSIR
from .hds_reference import HDS参照予算選択, HDS参照検索
from .hds_runtime_projection import HDSR質問射影
from .layer0 import Layer0
from .multilingual_surface import 表面化 as 多言語表面化
from .trinity_context import Trinity文脈系
from .主体 import 主体主幹, 主体状態, 主体更新提案, 主体整合結果, 主体更新記録
from .参照 import 参照供給器, 参照記録, 参照矛盾数
from .命令 import 手順
from .採否 import 実行状態, 採否, 採否結果
from .言語 import 自然言語器

if TYPE_CHECKING:
    from .k3_functional import K3相当能力核, SystemResult as K3能力結果


@dataclass(frozen=True, slots=True)
class 要求:
    問合せ: str
    手順: 手順 | None = None
    初期状態: dict[str, Any] = field(default_factory=dict)
    参照必須: bool = False
    主体更新提案: 主体更新提案 | None = None
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
    主体状態: 主体状態 | None = None
    主体整合: 主体整合結果 | None = None
    主体監査履歴: tuple[主体更新記録, ...] = ()
    言語計画: str | None = None
    HDS_IR: HDSIR | None = None


class ミニドラ:
    """HDS-IR、Trinity J/C/M、Layer-0とK3機能相当能力核を接続する非ニューラルLLM Runtime。"""

    def __init__(
        self,
        参照供給器_: 参照供給器 | None = None,
        layer0: Layer0 | None = None,
        主体主幹_: 主体主幹 | None = None,
        自然言語器_: 自然言語器 | None = None,
        HDSコンパイラ_: HDSコンパイラProtocol | None = None,
        Trinity文脈_: Trinity文脈系 | None = None,
        K3能力核_: K3相当能力核 | None = None,
    ) -> None:
        self.参照供給器 = 参照供給器_
        self.layer0 = layer0 or Layer0()
        self.主体主幹 = 主体主幹_ or 主体主幹()
        self.自然言語器 = 自然言語器_ or 自然言語器()
        self.HDSコンパイラ = HDSコンパイラ_
        self.Trinity文脈 = Trinity文脈_ or Trinity文脈系()
        self._K3能力核 = K3能力核_

    @property
    def 主体状態(self) -> 主体状態:
        return self.主体主幹.現在

    @property
    def HDS履歴(self) -> tuple[HDSIR, ...]:
        return self.Trinity文脈.記憶主体.IR履歴

    @property
    def HDS文脈(self) -> HDS文脈:
        return self.Trinity文脈.判断主体.文脈()

    @property
    def K3能力核(self) -> K3相当能力核:
        if self._K3能力核 is None:
            from .k3_functional import K3相当能力核
            self._K3能力核 = K3相当能力核()
        return self._K3能力核

    def K3知識投入(self, statements: Iterable[str]) -> list[dict[str, Any]]:
        return self.K3能力核.知識投入(statements)

    def K3グリッド投入(self, grid: Sequence[Sequence[int]]) -> list[dict[str, Any]]:
        return self.K3能力核.グリッド投入(grid)

    def K3実行(self, request: str, effort: str | None = None) -> K3能力結果:
        return self.K3能力核.実行(request, effort)

    def _主体更新提案(self, 文脈状態: Mapping[str, Any], 要求_: 要求) -> 主体更新提案 | None:
        候補 = 文脈状態.get("主体更新提案", 要求_.主体更新提案)
        if 候補 is None:
            return None
        if isinstance(候補, 主体更新提案):
            return 候補
        if isinstance(候補, Mapping):
            return 主体更新提案(
                変更=候補.get("変更", {}),
                理由=tuple(候補.get("理由", ())),
                根拠=tuple(候補.get("根拠", ())),
            )
        raise TypeError("主体更新提案は 主体更新提案 または mapping である必要がある")

    def _採否合成(self, 基礎: 採否結果, 主体: 主体整合結果, 必須: bool) -> 採否結果:
        if not 必須 or 主体.状態 in {実行状態.合格, 実行状態.非適用}:
            return 基礎
        if 主体.状態 == 実行状態.失敗:
            return 採否結果(実行状態.失敗, 基礎.理由 + 主体.理由)
        return 採否結果(実行状態.保留, 基礎.理由 + 主体.理由)

    def _帰還(self, result: 結果) -> 結果:
        if result.HDS_IR is not None:
            self.Trinity文脈.帰還(result.採否, result.値, result.HDS_IR)
        return result

    def _HDS未閉包(self, 要求_: 要求, ir: HDSIR, 理由: tuple[str, ...]) -> 結果:
        主体整合 = self.主体主幹.非適用結果("HDS-IRが実行閉包していないため主体更新未実行")
        return self._帰還(
            結果(
                None,
                dict(要求_.初期状態),
                (),
                (),
                採否結果(実行状態.保留, 理由),
                self.主体主幹.現在,
                主体整合,
                self.主体主幹.履歴,
                "HDS_IR",
                ir,
            )
        )

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
            base = 採否結果(実行状態.失敗, tuple(reasons + ["境界違反"]))
            value = None
        elif conflict_count:
            base = 採否結果(実行状態.保留, tuple(reasons + ["未解消矛盾"]))
            value = None
        elif 選択.状態 == "APPROVE" and value is not None:
            base = 採否結果(実行状態.合格, tuple(reasons))
        else:
            base = 採否結果(実行状態.保留, tuple(reasons or ["HDS_CHOICE_SUSPEND"]))
            value = None

        state: dict[str, Any] = dict(要求_.初期状態)
        state.update(
            {
                "結果": value,
                "参照": 参照,
                "主体状態": self.主体主幹.状態辞書(),
                "HDS文脈": self.HDS文脈,
                "HDS候補ラベル": 選択.回答ラベル,
                "HDS候補コンパイル数": 選択.候補コンパイル数,
                "HDS_Dataコンパイル数": 選択.Dataコンパイル数,
                "HDS_Dataコンパイル失敗数": 選択.Dataコンパイル失敗数,
                "K追加事実数": 選択.K追加事実数,
                "K証拠事実数": 選択.K証拠事実数,
                "K証拠阻害事実数": 選択.K証拠阻害事実数,
            }
        )
        if 選択.K3結果 is not None:
            state["K3努力水準"] = 選択.K3結果.努力水準
            state["K3探索深さ上限"] = 選択.K3結果.探索深さ上限
            state["K3証拠上限"] = 選択.K3結果.証拠上限
            state["K3候補診断"] = tuple(
                {
                    "候補": item.候補,
                    "合計得点": item.合計得点,
                    "証拠得点": item.証拠得点,
                    "graph得点": item.graph得点,
                    "独立出典数": item.独立出典数,
                    "graph深さ": item.graph深さ,
                }
                for item in 選択.K3結果.候補診断
            )

        proposal = self._主体更新提案(state, 要求_)
        subject = self.主体主幹.評価更新(proposal)
        decision = self._採否合成(base, subject, 要求_.主体整合必須)
        if 要求_.主体整合必須 and decision.状態 in {実行状態.保留, 実行状態.失敗}:
            value = None
            state["結果"] = None

        history = (
            {
                "op": "HDS_CHOICE_NATIVE",
                "status": 選択.状態,
                "answer_label": 選択.回答ラベル,
                "candidate_compiled": 選択.候補コンパイル数,
            },
            {
                "op": "R_TO_HDS_TO_K",
                "reference_count": len(参照),
                "data_compiled": 選択.Dataコンパイル数,
                "data_compile_failed": 選択.Dataコンパイル失敗数,
                "k_facts_added": 選択.K追加事実数,
                "evidence_facts": 選択.K証拠事実数,
                "blocked_evidence_facts": 選択.K証拠阻害事実数,
            },
        )
        return self._帰還(
            結果(
                value,
                state,
                参照,
                history,
                decision,
                self.主体主幹.現在,
                subject,
                self.主体主幹.履歴,
                "HDS_CHOICE_NATIVE",
                ir,
            )
        )

    def コンパイル(self, 問合せ: str) -> HDSIR:
        if self.HDSコンパイラ is None:
            raise RuntimeError("HDS Compilerが接続されていない")
        return self.Trinity文脈.コンパイル(self.HDSコンパイラ, 問合せ)

    def 実行(self, 要求_: 要求) -> 結果:
        自動計画 = 要求_.手順 is None
        hds_ir: HDSIR | None = None
        hds_choice = False
        plan_name: str | None = None
        initial_from_plan: dict[str, Any] = {}
        reference_from_plan = False
        手順_: 手順 | None = 要求_.手順

        if 自動計画 and self.HDSコンパイラ is not None:
            try:
                hds_ir = self.コンパイル(要求_.問合せ)
            except (ValueError, TypeError) as exc:
                主体整合 = self.主体主幹.非適用結果("HDS Compiler実行失敗")
                return 結果(
                    None,
                    dict(要求_.初期状態),
                    (),
                    (),
                    採否結果(実行状態.失敗, ("HDS Compiler実行失敗", str(exc))),
                    self.主体主幹.現在,
                    主体整合,
                    self.主体主幹.履歴,
                    "HDS_IR",
                    None,
                )
            hds_choice = HDS選択問題(hds_ir)
            if hds_choice:
                手順_ = None
                initial_from_plan = dict(hds_ir.初期状態)
                reference_from_plan = hds_ir.参照必須
                plan_name = "HDS_CHOICE_NATIVE"
            else:
                if not hds_ir.実行可能:
                    理由 = ["HDS_IR未閉包", *hds_ir.実行阻害理由]
                    if hds_ir.残差:
                        理由.extend(f"残差:{item.理由}" for item in hds_ir.残差)
                    return self._HDS未閉包(要求_, hds_ir, tuple(理由))
                手順_ = hds_ir.手順
                initial_from_plan = dict(hds_ir.初期状態)
                reference_from_plan = hds_ir.参照必須
                plan_name = hds_ir.種別 or "HDS_IR"
        elif 自動計画:
            計画 = self.自然言語器.計画(要求_.問合せ)
            手順_ = 計画.手順
            initial_from_plan = dict(計画.初期状態)
            reference_from_plan = 計画.参照必須
            plan_name = 計画.種別

        if 手順_ is None and not hds_choice:
            raise ValueError("実行手順が確定していない")
        参照必須 = 要求_.参照必須 or reference_from_plan

        参照: tuple[参照記録, ...] = ()
        if self.参照供給器 is not None:
            if hds_ir is not None:
                budget = HDS参照予算選択(hds_ir)
                参照 = HDS参照検索(
                    self.参照供給器,
                    HDSR質問射影(hds_ir),
                    上限=budget.取得上限,
                    一問合せ上限=budget.一問合せ上限,
                    最大問合せ並列=budget.最大問合せ並列,
                )
            else:
                参照 = self.参照供給器.検索(要求_.問合せ)
        if 参照必須 and not 参照:
            判定 = 採否(根拠数=0)
            主体整合 = self.主体主幹.非適用結果("参照不足のため主体更新未実行")
            result = 結果(
                None,
                dict(要求_.初期状態),
                (),
                (),
                判定,
                self.主体主幹.現在,
                主体整合,
                self.主体主幹.履歴,
                plan_name,
                hds_ir,
            )
            return self._帰還(result) if hds_ir is not None else result

        if hds_choice and hds_ir is not None:
            selected = HDS選択推論実行(
                hds_ir,
                参照,
                コンパイル=self.コンパイル,
                基礎能力核=self.K3能力核,
            )
            return self._HDS選択結果(要求_, hds_ir, 参照, selected)

        初期 = dict(要求_.初期状態)
        初期.update(initial_from_plan)
        初期["参照"] = 参照
        初期["主体状態"] = self.主体主幹.状態辞書()
        if hds_ir is not None:
            初期["HDS文脈"] = self.HDS文脈

        assert 手順_ is not None
        try:
            文脈 = self.layer0.実行(手順_, 初期)
        except (ValueError, TypeError, ZeroDivisionError) as exc:
            if not 自動計画:
                raise
            主体整合 = self.主体主幹.非適用結果("自動計画の実行失敗")
            result = 結果(
                None,
                初期,
                (),
                (),
                採否結果(実行状態.失敗, ("自動計画実行失敗", str(exc))),
                self.主体主幹.現在,
                主体整合,
                self.主体主幹.履歴,
                plan_name,
                hds_ir,
            )
            return self._帰還(result) if hds_ir is not None else result

        値 = 文脈.状態.get("結果")
        提案 = self._主体更新提案(文脈.状態, 要求_)
        主体整合 = self.主体主幹.評価更新(提案)
        結果根拠数 = (len(参照) if 値 is not None else 0) if 参照必須 else (1 if 値 is not None else 0)
        基礎判定 = 採否(
            根拠数=結果根拠数,
            矛盾数=要求_.矛盾数 + 参照矛盾数(参照),
            危険=要求_.境界違反,
        )
        判定 = self._採否合成(基礎判定, 主体整合, 要求_.主体整合必須)
        if 要求_.主体整合必須 and 判定.状態 in {実行状態.保留, 実行状態.失敗}:
            値 = None

        result = 結果(
            値,
            dict(文脈.状態),
            参照,
            tuple(文脈.履歴),
            判定,
            self.主体主幹.現在,
            主体整合,
            self.主体主幹.履歴,
            plan_name,
            hds_ir,
        )
        return self._帰還(result) if hds_ir is not None else result

    def 応答(self, 問合せ: str) -> str:
        result = self.実行(要求(問合せ))
        if result.HDS_IR is not None:
            language = result.HDS_IR.出力言語 or result.HDS_IR.入力言語
            return 多言語表面化(result.値, result.採否.状態.value, result.採否.理由, language)
        return self.自然言語器.表面化(
            result.値,
            result.採否.状態.value,
            result.採否.理由,
        )
