from __future__ import annotations

from dataclasses import replace
from typing import Sequence

from .選択意図 import HDS選択意図判定
from .HDS適合器 import HDS文脈
from .HDS構文化器 import 公開HDSコンパイラ as _基礎HDSコンパイラ
from .HDS構文化器 import 公開HDSコンパイラ方針
from .HDS構文化作用差分 import HDS作用差分構造生成
from .HDS構文化監査中間表現 import HDS監査参照IR射影
from .HDS構文化動態 import HDS状態遷移IR射影, HDS状態遷移抽出
from .HDS構文化失敗 import HDSチェックリスト生成, HDS失敗署名候補生成, HDS監査参照候補生成
from .HDS構文化失敗集 import HDS失敗署名Bank
from .HDS構文化前処理 import 公開HDSフロントエンド射影, 公開HDS詳細成果
from .HDS構文化履歴 import HDS認知世界差分IR射影, HDS認知世界差分生成
from .HDS構文化処理系列_v1_4 import (
    HDSコンパイル束,
    HDS意味IR化,
    HDS意味専用計画器,
    HDS計算コンパイル成果,
    HDS計算降下バックエンド,
)
from .HDS構文化記録 import HDS構文化器成果
from .HDS構文化記録_v1_2 import HDS失敗署名BankSnapshot, HDS抽出規則改善候補
from .HDS構文化記録_v1_3 import HDS作用差分構造
from .HDS構文化暗黙知 import HDS暗黙知IR射影, HDS暗黙知抽出
from .HDS中間表現 import HDSIR, HDS実行核, HDS座標, HDS関係, 値状態
from .HDSコア入力 import HDSコア入力束
from .HDSコア入力射影 import HDSコア入力へ
from .HDS言語協調 import HDS英語AND展開
from .HDS言語関係 import HDS英語基底関係射影
from .HDS言語範囲 import HDS英語関係範囲射影
from .HDS言語意味橋渡し import HDS英日意味射影
from .HDS意味主題射影 import HDS問い主題射影
from .意味字句 import 意味語
from .言語 import 言語計画
from .言語基底 import 言語基底P, 標準言語基底P


class _意味基礎HDSコンパイラ(_基礎HDSコンパイラ):
    '旧基礎構文化器の意味抽出だけを利用し、計算計画を無作用化する内部前段。'

    def __init__(self, 親: "公開HDSコンパイラ") -> None:
        super().__init__(親.方針)
        self._親 = 親
        self._legacy = HDS意味専用計画器()

    def _入力言語(self, text: str) -> str:
        return self._親._入力言語(text)


class 公開HDSコンパイラ(_基礎HDSコンパイラ):
    'MINIDORA公開標準HDS 構文化器。\n\n    構造 v1.3の意味・監査観測を維持しつつ、Core v3が消費する情報だけを\n    HDSコア入力束へ射影し、これを正本とする。意味IR・計算計画・作用差分構造は\n    Legacy互換・監査・局所降下のために並列保持する。\n    構文化器自身は作用選択・最終採否・後続作用実行を行わない。\n    '

    構造版 = "v1.3"
    処理系列版 = "v1.5"
    コア入力版 = "HDS-コア入力-v1"
    規定言語 = "日本語"
    基底言語 = "日本語"
    基底言語コード = "ja"

    def __init__(self, 方針: 公開HDSコンパイラ方針 | None = None, 言語基底P_: 言語基底P | None = None) -> None:
        super().__init__(方針)
        self.言語基底P = 言語基底P_ or 標準言語基底P
        self._計算計画器 = self._legacy
        self._意味基礎 = _意味基礎HDSコンパイラ(self)
        self._計算降下 = HDS計算降下バックエンド()

    def _入力言語(self, text: str) -> str:
        return self.言語基底P.入力言語判定(text)

    def _完成(self, base: HDSIR, *, HDS履歴: tuple[HDSIR, ...] = ()) -> HDS構文化器成果:
        base = HDS英日意味射影(base)
        base = HDS英語基底関係射影(base, self.言語基底P)
        base = HDS英語AND展開(base)
        base = HDS英語関係範囲射影(base)
        base = HDS問い主題射影(base, 上限=self.方針.最大主題語数)

        first = 公開HDSフロントエンド射影(base)
        関係図 = HDS状態遷移抽出(first.IR.正規化文 or first.IR.原文)
        作用_delta = HDS作用差分構造生成(関係図)
        ir = HDS状態遷移IR射影(first.IR, 関係図)
        tacit = HDS暗黙知抽出(ir.正規化文 or ir.原文)
        ir = HDS暗黙知IR射影(ir, tacit)

        refreshed = 公開HDS詳細成果(ir)
        signatures = HDS失敗署名候補生成(refreshed.IR, refreshed.認知世界)
        checklist = HDSチェックリスト生成(refreshed.監査要求, signatures)
        audit_queries = HDS監査参照候補生成(refreshed.IR, checklist)
        audit_ir = HDS監査参照IR射影(refreshed.IR, audit_queries)
        world_diff = HDS認知世界差分生成(audit_ir, HDS履歴)
        final_ir = HDS認知世界差分IR射影(audit_ir, world_diff)
        return replace(
            refreshed,
            IR=final_ir,
            状態遷移=関係図,
            暗黙知構造=tacit,
            失敗署名候補=signatures,
            チェックリスト=checklist,
            認知世界差分=world_diff,
            監査参照候補=audit_queries,
            作用差分構造=作用_delta,
        )

    def _意味基礎IR(
        self,
        入力: str,
        *,
        前回結果: object = None,
        HDS履歴: tuple[HDSIR, ...] = (),
        文脈: HDS文脈 | None = None,
    ) -> tuple[HDSIR, 言語計画]:
        normalized = self._正規化(str(入力))
        文脈_focus = (
            getattr(文脈, "現在焦点", None) if 文脈 is not None else 前回結果
        )
        plan = self._計算計画器.計画(normalized, 文脈参照=文脈_focus)
        base = self._意味基礎.コンパイル(
            入力,
            前回結果=前回結果,
            HDS履歴=HDS履歴,
            文脈=文脈,
        )
        return HDS意味IR化(base, plan), plan

    def _意味束(
        self,
        入力: str,
        *,
        前回結果: object = None,
        HDS履歴: tuple[HDSIR, ...] = (),
        文脈: HDS文脈 | None = None,
    ) -> tuple[HDSコンパイル束, HDS構文化器成果]:
        意味_base, plan = self._意味基礎IR(
            入力,
            前回結果=前回結果,
            HDS履歴=HDS履歴,
            文脈=文脈,
        )
        detailed = self._完成(意味_base, HDS履歴=HDS履歴)
        意味_ir = replace(detailed.IR, 手順=None, 初期状態={})
        detailed = replace(detailed, IR=意味_ir)
        コア入力 = HDSコア入力へ(意味_ir)
        return HDSコンパイル束(
            意味_ir, plan, detailed.作用差分構造, コア入力=コア入力
        ), detailed

    def 意味コンパイル(
        self,
        入力: str,
        *,
        前回結果: object = None,
        HDS履歴: tuple[HDSIR, ...] = (),
        文脈: HDS文脈 | None = None,
    ) -> HDSIR:
        bundle, _ = self._意味束(
            入力,
            前回結果=前回結果,
            HDS履歴=HDS履歴,
            文脈=文脈,
        )
        return bundle.意味IR

    def コア入力コンパイル(
        self,
        入力: str,
        *,
        前回結果: object = None,
        HDS履歴: tuple[HDSIR, ...] = (),
        文脈: HDS文脈 | None = None,
    ) -> HDSコア入力束:
        """MINIDORA Core v3へ渡す正本入力だけを返す。"""
        bundle, _ = self._意味束(
            入力,
            前回結果=前回結果,
            HDS履歴=HDS履歴,
            文脈=文脈,
        )
        return bundle.正本

    def 作用差分コンパイル(
        self,
        入力: str,
        *,
        前回結果: object = None,
        HDS履歴: tuple[HDSIR, ...] = (),
        文脈: HDS文脈 | None = None,
    ) -> HDS作用差分構造:
        bundle, _ = self._意味束(
            入力,
            前回結果=前回結果,
            HDS履歴=HDS履歴,
            文脈=文脈,
        )
        return bundle.作用差分構造

    def コンパイル束(
        self,
        入力: str,
        *,
        前回結果: object = None,
        HDS履歴: tuple[HDSIR, ...] = (),
        文脈: HDS文脈 | None = None,
    ) -> HDSコンパイル束:
        bundle, _ = self._意味束(
            入力,
            前回結果=前回結果,
            HDS履歴=HDS履歴,
            文脈=文脈,
        )
        return bundle

    def 計算降下(self, bundle: HDSコンパイル束) -> HDS計算コンパイル成果:
        """形成済み束を計算中間表現へ降下する。自然言語を再解析しない。"""
        return self._計算降下.降下(bundle)

    def 計算コンパイル(
        self,
        入力: str,
        *,
        前回結果: object = None,
        HDS履歴: tuple[HDSIR, ...] = (),
        文脈: HDS文脈 | None = None,
    ) -> HDS計算コンパイル成果:
        return self.計算降下(
            self.コンパイル束(
                入力,
                前回結果=前回結果,
                HDS履歴=HDS履歴,
                文脈=文脈,
            )
        )

    def コンパイル(
        self,
        入力: str,
        *,
        前回結果: object = None,
        HDS履歴: tuple[HDSIR, ...] = (),
        文脈: HDS文脈 | None = None,
    ) -> HDSIR:
        """旧互換入口。意味正本へ最外周でのみPを再付与する。"""
        return self.コンパイル束(
            入力,
            前回結果=前回結果,
            HDS履歴=HDS履歴,
            文脈=文脈,
        ).互換IR()

    def 詳細コンパイル(
        self,
        入力: str,
        *,
        前回結果: object = None,
        HDS履歴: tuple[HDSIR, ...] = (),
        文脈: HDS文脈 | None = None,
    ) -> HDS構文化器成果:
        _, detailed = self._意味束(
            入力,
            前回結果=前回結果,
            HDS履歴=HDS履歴,
            文脈=文脈,
        )
        return detailed

    @staticmethod
    def _問い関係を持つ(ir: HDSIR) -> bool:
        for 関係 in ir.関係:
            for raw in 関係.条件:
                key, sep, payload = str(raw).partition("=")
                if sep and key.strip() == "不足位置" and payload.strip() in {"始点", "終点"}:
                    return True
        return False

    def _選択問題問い閉包(self, ir: HDSIR, question: str) -> HDSIR:
        """明示された選択問題型で、表層だけでは閉じなかった問いを世界知識なしで保持する。"""
        if self._問い関係を持つ(ir):
            return ir
        choices = tuple(coord for coord in ir.座標 if coord.座標ID.startswith('選択肢:'))
        if len(choices) < 2:
            return ir
        text = self._正規化(str(question))
        if not text:
            return ir

        intent = HDS選択意図判定(question)
        focus = self._正規化(str(intent.焦点 or text))
        content = frozenset(意味語(focus)) - {
            "find", "calculate", "determine", "identify", "select", "choose", "all",
        }
        if not content and intent.種別 != "EXCEPTION":
            return ir

        existing_coord_ids = {coord.座標ID for coord in ir.座標}
        existing_関係_ids = {関係.関係ID for 関係 in ir.関係}

        def unique(base: str, existing: set[str]) -> str:
            候補 = base
            serial = 1
            while 候補 in existing:
                候補 = f"{base}:{serial}"
                serial += 1
            existing.add(候補)
            return 候補

        未知_id = unique('selection-query:未知', existing_coord_ids)
        known_id = unique("selection-query:surface", existing_coord_ids)
        関係_id = unique('selection-query:関係', existing_関係_ids)
        selection = "反転" if intent.種別 == "EXCEPTION" else "通常"

        coords = (
            *ir.座標,
            HDS座標(
                未知_id,
                "目的.未知始点",
                "選択肢",
                値状態.未観測,
                由来="選択問題構造",
                暫定性="SELECTION_QUERY_GENERIC_CLOSURE",
            ),
            HDS座標(
                known_id,
                "対象.問い本文",
                focus,
                値状態.確定,
                由来="選択問題構造",
                暫定性="SELECTION_QUERY_GENERIC_CLOSURE",
            ),
        )
        関係 = HDS関係(
            関係_id,
            (未知_id,),
            (known_id,),
            "問い適合",
            条件=(
                "検索述語=match",
                "不足位置=始点",
                "選択問題閉包=v0.1",
                f"選択意図={selection}",
            ),
            値状態=値状態.未観測,
            由来="選択問題構造",
            暫定性="SELECTION_QUERY_GENERIC_CLOSURE",
        )
        residuals = tuple(
            残差
            for 残差 in ir.残差
            if not (
                str(残差.残差ID) == "lang-sem:question-loss"
                and str(残差.種別) == '意味_loss'
            )
        )
        return replace(ir, 座標=coords, 関係=(*ir.関係, 関係), 残差=residuals)

    def _問題基礎(self, question: str, choices: Sequence[str]) -> HDSIR:
        if len(choices) < 2:
            raise ValueError("選択問題には2件以上の候補が必要")
        if len(choices) > 26:
            raise ValueError('公開構文化器の選択ラベル上限は26件')
        base, _ = self._意味基礎IR(question)
        選択肢_coords = tuple(
            HDS座標(
                f"選択肢:{chr(ord('A') + index)}",
                "目的.候補",
                str(text),
                値状態.確定,
                由来="選択問題入力",
            )
            for index, text in enumerate(choices)
        )
        return replace(
            base,
            座標=base.座標 + 選択肢_coords,
            参照必須=True,
            種別="knowledge_query",
            実行核=HDS実行核(
                'HDS_選択肢_selection',
                (),
                "結果",
                境界=("NO_GUESS", "gold非参照", 'HDS-意味'),
                検証=("全候補対称", "計算P非内包"),
            ),
            手順=None,
            初期状態={},
            閉包状態='CLOSED_FOR_意味_TRANSFER',
        )

    def 問題IR(self, question: str, choices: Sequence[str]) -> HDSIR:
        completed = self._完成(self._問題基礎(question, choices)).IR
        return self._選択問題問い閉包(completed, question)

    def 問題コア入力(self, question: str, choices: Sequence[str]) -> HDSコア入力束:
        """選択問題もCore入力正本へ射影し、候補や問いを能力名へ変換しない。"""
        return HDSコア入力へ(self.問題IR(question, choices))

    def 詳細問題IR(self, question: str, choices: Sequence[str]) -> HDS構文化器成果:
        return self._完成(self._問題基礎(question, choices))

    def 失敗帰還(self, 成果: HDS構文化器成果, Bank: HDS失敗署名Bank, *, Run参照: str) -> HDS失敗署名BankSnapshot:
        return Bank.観測(成果.失敗署名候補, Run参照=Run参照)

    def 改善候補(self, Bank: HDS失敗署名Bank) -> tuple[HDS抽出規則改善候補, ...]:
        return Bank.snapshot().改善候補


__all__ = [
    "公開HDSコンパイラ方針",
    "公開HDSコンパイラ",
    'HDS構文化器成果',
    "HDS失敗署名Bank",
    "HDSコンパイル束",
    "HDS計算コンパイル成果",
]
