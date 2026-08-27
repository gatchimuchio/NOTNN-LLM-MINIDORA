from __future__ import annotations

from collections.abc import Sequence

from .runtime_v03 import ミニドラ as _ミニドラV03, 結果, 要求
from .模型 import MINIDORA模型核, 模型結果, 成立候補, 言語状態, 標準模型核
from .関係連鎖演算_v2 import 関係連鎖模型核V2, 推論文脈形成
from .計算実行器 import 計算実行器


class ミニドラ(_ミニドラV03):
    """MINIDORA v0.4 Runtime。

    大規模言語模型成立規定v3に対応する ``模型核`` を計算主体Cとして持ち、旧Layer0
    命令器は ``計算実行器`` へ降格する。正式knowledge choiceは
    ``HDS Compiler → MINIDORA入力 → C → MINIDORA出力 → 後段HDS`` の一方向で閉じる。

    MINIDORA内部では、構造化済み関係を候補へ直接採点するだけでなく、関係族・向き・極性を
    数値状態へ写し、前段の関係結果を次段の入力として有界連鎖する。v2では通常文脈と
    ``推論状態`` を分離し、推論前提を一般関係・履歴・参照寄与へ無言混入させない。
    端点接続は片側包含ではなく対称的意味同一性を要求し、複数候補へ共通に到達した状態は
    候補差として採用しない。

    後段HDSはMINIDORA出力だけを判断し、HOLD/REJECTはSILENTで終端する。
    再検索・再計算・差し戻しはMINIDORA単体へ持たせない。
    """

    def __init__(
        self,
        参照供給器_=None,
        layer0=None,
        主体主幹_=None,
        自然言語器_=None,
        HDSコンパイラ_=None,
        Trinity文脈_=None,
        K3能力核_=None,
        *,
        模型核_: MINIDORA模型核 | None = None,
        計算実行器_: 計算実行器 | None = None,
    ) -> None:
        executor = 計算実行器_ or layer0 or 計算実行器()
        super().__init__(
            参照供給器_=参照供給器_,
            layer0=executor,
            主体主幹_=主体主幹_,
            自然言語器_=自然言語器_,
            HDSコンパイラ_=HDSコンパイラ_,
            Trinity文脈_=Trinity文脈_,
            K3能力核_=K3能力核_,
        )
        self.模型核 = 関係連鎖模型核V2(模型核_ or 標準模型核())
        self.計算実行器 = executor
        # 旧API互換。新規設計ではLLM中核を意味しない。
        self.layer0 = executor

    @property
    def K3能力核(self):
        """旧helperを互換利用しつつ、v0.4正式模型核Cを実行境界へ渡す。

        runtime_v03側へv0.4型を逆流させないため、helperに非正本の接続参照だけを付与する。
        HDS選択Runtimeはこの参照がある時だけ正式模型核CでMINIDORA出力を形成し、
        その出力だけを後段HDSへ渡す。旧helperを正式回答権限へ復帰させない。
        """
        core = super().K3能力核
        setattr(core, "_minidora_model_core", self.模型核)
        return core

    def 言語評価(
        self,
        文脈: str | 言語状態,
        候補群: Sequence[str | 言語状態 | 成立候補],
        *,
        言語体系: str = "自然言語:ja",
        履歴: Sequence[str | 言語状態] = (),
        条件: Sequence[str] = (),
        参照状態: Sequence[str | 言語状態] = (),
        推論状態: Sequence[str | 言語状態] = (),
    ) -> 模型結果:
        """文脈に対する候補言語状態の成立差を決定論的に返す。

        このAPIがv0.4の模型中核C入口である。候補生成、sampling、外部検索、後段HDS判断は行わない。
        `参照状態` は外部Data、`推論状態` は通常文脈から分離して再作用だけが読む中間状態である。
        このAPIの ``模型結果`` を正式knowledge choiceでは ``MINIDORA出力`` へ変換し、
        `hds_choice_runtime.py` 経由で後段HDSへ一方向に渡す。
        """

        current = 文脈 if isinstance(文脈, 言語状態) else 言語状態(str(文脈), 言語体系)
        history_states = tuple(
            item if isinstance(item, 言語状態) else 言語状態(str(item), current.言語体系)
            for item in 履歴
        )
        reference_states = tuple(
            item if isinstance(item, 言語状態) else 言語状態(str(item), current.言語体系)
            for item in 参照状態
        )
        reasoning_states = tuple(
            item if isinstance(item, 言語状態) else 言語状態(str(item), current.言語体系)
            for item in 推論状態
        )
        candidates: list[成立候補] = []
        for index, item in enumerate(候補群):
            if isinstance(item, 成立候補):
                candidates.append(item)
            elif isinstance(item, 言語状態):
                candidates.append(成立候補(item.識別子 or f"候補{index + 1}", item))
            else:
                candidates.append(
                    成立候補(
                        f"候補{index + 1}",
                        言語状態(str(item), current.言語体系),
                    )
                )
        context = 推論文脈形成(
            self.模型核,
            current,
            推論状態=reasoning_states,
            履歴=history_states,
            条件=条件,
            参照状態=reference_states,
        )
        return self.模型核.評価(context, tuple(candidates))


__all__ = ["ミニドラ", "要求", "結果"]