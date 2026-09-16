from __future__ import annotations

from typing import Callable, Sequence

from .HDS実行主体 import HDS作用機会, HDS作用結果, HDS作用状態, HDS実行状態
from .能力合成 import 能力合成器, 合成結果
from .製品版.能力契約 import 能力文脈


class HDS目的計画作用:
    """既存の目的計画器をHDSの計画作用として使うAdapter。

    計画成功は実行成功・最終採用ではない。計画と資料をHDS成果へ帰還し、次作用へ渡す。
    """

    def __init__(
        self,
        計画器,
        要求,
        *,
        入力状態: Sequence[str] = (),
        出力状態: str = "目的計画済み",
        解消対象: Sequence[str] = ("計画未形成",),
        禁止作用: Sequence[str] = (),
        資源負荷: int = 1,
    ) -> None:
        if not callable(getattr(計画器, "計画する", None)):
            raise TypeError("HDS目的計画作用には計画する()を持つ計画器が必要")
        self.計画器 = 計画器
        self.要求 = 要求
        self.入力状態 = frozenset(str(x) for x in 入力状態)
        self.出力状態 = str(出力状態)
        self.解消対象 = frozenset(str(x) for x in 解消対象)
        self.禁止作用 = tuple(str(x) for x in 禁止作用)
        self.資源負荷 = max(0, int(資源負荷))
        self.作用ID = "目的計画"

    def 機会(self, 状態: HDS実行状態) -> HDS作用機会 | None:
        if not self.入力状態.issubset(状態.成立状態):
            return None
        if self.出力状態 in 状態.成立状態:
            return None
        return HDS作用機会(
            self.作用ID,
            f"{状態.状態署名}:{repr(self.要求)}:{repr(self.禁止作用)}",
            self.入力状態,
            frozenset({self.出力状態}),
            self.解消対象,
            self.資源負荷,
            0.0,
            True,
            ("PURPOSE_PLANNER_AS_HDS_ACTION",),
        )

    def 実行(self, 状態: HDS実行状態) -> HDS作用結果:
        try:
            result = self.計画器.計画する(self.要求, 禁止作用=self.禁止作用)
        except TypeError:
            # 後期の役割計画器など、禁止作用の引数名が異なる計画器はこのAdapterの対象外。
            # 無言の引数変換はせず、明示的な別Adapterを要求する。
            return HDS作用結果(
                HDS作用状態.失敗,
                追加残差=frozenset({"計画器契約不一致"}),
                理由=("PURPOSE_PLANNER_CONTRACT_MISMATCH",),
            )
        except Exception as exc:
            return HDS作用結果(
                HDS作用状態.失敗,
                追加残差=frozenset({f"計画失敗:{type(exc).__name__}"}),
                理由=("PURPOSE_PLANNER_EXCEPTION", type(exc).__name__),
            )

        if bool(getattr(result, "成立", False)) and getattr(result, "計画", None) is not None:
            return HDS作用結果(
                HDS作用状態.成立,
                追加状態=frozenset({self.出力状態}),
                解消残差=self.解消対象,
                成果=(("目的計画結果", result),),
                理由=("PURPOSE_PLAN_FORMED",),
            )

        reason = str(getattr(result, "理由", "") or "計画未閉包")
        return HDS作用結果(
            HDS作用状態.保留,
            追加残差=frozenset({f"計画未閉包:{reason}"}),
            成果=(("目的計画結果", result),),
            理由=("PURPOSE_PLAN_SUSPENDED", reason),
        )


class HDS能力合成作用:
    """計画済みの既存能力合成をHDSの実行作用として使う。

    統合セッションの会話採用状態は更新しない。能力合成結果をHDS成果へ帰還し、
    HDSが別の検証作用を経てCOMMITする余地を維持する。
    """

    def __init__(
        self,
        合成器: 能力合成器,
        *,
        計画成果名: str = "目的計画結果",
        入力状態: Sequence[str] = ("目的計画済み",),
        出力状態: str = "能力合成済み",
        解消対象: Sequence[str] = ("実行未完了",),
        文脈: 能力文脈 | None = None,
        文脈生成: Callable[[HDS実行状態], 能力文脈] | None = None,
        外部読取許可: bool = False,
        停止要求=None,
        資源負荷: int = 2,
    ) -> None:
        if not isinstance(合成器, 能力合成器):
            raise TypeError("HDS能力合成作用には能力合成器が必要")
        if 文脈 is not None and 文脈生成 is not None:
            raise ValueError("固定文脈と文脈生成は同時指定できない")
        if 文脈 is not None and not isinstance(文脈, 能力文脈):
            raise TypeError("固定文脈は能力文脈である必要がある")
        self.合成器 = 合成器
        self.計画成果名 = str(計画成果名)
        self.入力状態 = frozenset(str(x) for x in 入力状態)
        self.出力状態 = str(出力状態)
        self.解消対象 = frozenset(str(x) for x in 解消対象)
        self.文脈 = 文脈
        self.文脈生成 = 文脈生成
        self.外部読取許可 = bool(外部読取許可)
        self.停止要求 = 停止要求
        self.資源負荷 = max(0, int(資源負荷))
        self.作用ID = "能力合成"

    def _文脈(self, 状態: HDS実行状態) -> 能力文脈:
        if self.文脈生成 is not None:
            value = self.文脈生成(状態)
            if not isinstance(value, 能力文脈):
                raise TypeError("HDS能力合成作用の文脈生成は能力文脈を返す必要がある")
            return value
        if self.文脈 is not None:
            return self.文脈
        purpose = " / ".join(状態.目的)
        return 能力文脈(purpose, "HDS実行主体", 補助={"HDS状態署名": 状態.状態署名})

    def 機会(self, 状態: HDS実行状態) -> HDS作用機会 | None:
        if not self.入力状態.issubset(状態.成立状態):
            return None
        plan = 状態.成果辞書().get(self.計画成果名)
        if plan is None or not bool(getattr(plan, "成立", False)):
            return None
        if self.出力状態 in 状態.成立状態:
            return None
        return HDS作用機会(
            self.作用ID,
            f"{状態.状態署名}:{self.計画成果名}",
            self.入力状態,
            frozenset({self.出力状態}),
            self.解消対象,
            self.資源負荷,
            0.0,
            True,
            ("CAPABILITY_COMPOSER_AS_HDS_ACTION",),
        )

    def 実行(self, 状態: HDS実行状態) -> HDS作用結果:
        plan_result = 状態.成果辞書().get(self.計画成果名)
        plan = getattr(plan_result, "計画", None)
        materials = getattr(plan_result, "資料", None)
        if plan is None or not isinstance(materials, dict):
            return HDS作用結果(
                HDS作用状態.失敗,
                追加残差=frozenset({"能力合成入力欠落"}),
                理由=("CAPABILITY_COMPOSITION_INPUT_MISSING",),
            )
        try:
            result = self.合成器.実行(
                plan,
                materials,
                文脈=self._文脈(状態),
                外部読取許可=self.外部読取許可,
                停止要求=self.停止要求,
            )
        except Exception as exc:
            return HDS作用結果(
                HDS作用状態.失敗,
                追加残差=frozenset({f"能力合成例外:{type(exc).__name__}"}),
                理由=("CAPABILITY_COMPOSITION_EXCEPTION", type(exc).__name__),
            )

        if not isinstance(result, 合成結果):
            return HDS作用結果(
                HDS作用状態.失敗,
                追加残差=frozenset({"能力合成結果型不正"}),
                理由=("CAPABILITY_COMPOSITION_RETURN_TYPE_INVALID",),
            )

        artifacts = [("能力合成結果", result)]
        artifacts.extend((f"合成出力:{name}", value) for name, value in result.出力)
        if result.成立:
            return HDS作用結果(
                HDS作用状態.成立,
                追加状態=frozenset({self.出力状態}),
                解消残差=self.解消対象,
                成果=tuple(artifacts),
                理由=("CAPABILITY_COMPOSITION_SUCCEEDED",),
            )

        residual = f"能力合成未閉包:{result.状態}:{result.理由}"
        state = HDS作用状態.失敗 if result.状態 == "失敗" else HDS作用状態.保留
        return HDS作用結果(
            state,
            追加残差=frozenset({residual}),
            成果=tuple(artifacts),
            理由=("CAPABILITY_COMPOSITION_NOT_CLOSED", result.状態, result.理由),
        )


__all__ = ["HDS目的計画作用", "HDS能力合成作用"]
