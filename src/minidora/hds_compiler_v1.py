from __future__ import annotations

from dataclasses import replace
from typing import Sequence

from .hds_adapter import HDS文脈
from .hds_compiler import 公開HDSコンパイラ as _基礎HDSコンパイラ
from .hds_compiler import 公開HDSコンパイラ方針
from .hds_compiler_audit_ir import HDS監査参照IR射影
from .hds_compiler_dynamics import HDS状態遷移IR射影, HDS状態遷移抽出
from .hds_compiler_failure import HDSチェックリスト生成, HDS失敗署名候補生成, HDS監査参照候補生成
from .hds_compiler_failure_bank import HDS失敗署名Bank
from .hds_compiler_frontend import 公開HDSフロントエンド射影, 公開HDS詳細成果
from .hds_compiler_history import HDS認知世界差分IR射影, HDS認知世界差分生成
from .hds_compiler_pipeline_v1_3 import (
    HDSコンパイル束,
    HDS意味IR化,
    HDS意味専用計画器,
    HDS計算コンパイル成果,
    HDS計算降下バックエンド,
)
from .hds_compiler_records import HDSCompiler成果
from .hds_compiler_records_v1_2 import HDS失敗署名BankSnapshot, HDS抽出規則改善候補
from .hds_compiler_tacit import HDS暗黙知IR射影, HDS暗黙知抽出
from .hds_ir import HDSIR, HDS実行核, HDS座標, 値状態
from .hds_language_coordination import HDS英語AND展開
from .hds_language_relations import HDS英語基底関係射影
from .hds_language_scope import HDS英語関係scope射影
from .hds_language_semantic_bridge import HDS英日意味射影
from .hds_semantic_topic_projection import HDS問い主題射影
from .言語 import 言語計画
from .言語基底 import 言語基底P, 標準言語基底P


class _意味基礎HDSコンパイラ(_基礎HDSコンパイラ):
    """旧基礎Compilerの意味抽出だけを利用し、計算計画を無作用化する内部front-end。"""

    def __init__(self, 親: "公開HDSコンパイラ") -> None:
        super().__init__(親.方針)
        self._親 = 親
        self._legacy = HDS意味専用計画器()

    def _入力言語(self, text: str) -> str:
        return self._親._入力言語(text)


class 公開HDSコンパイラ(_基礎HDSコンパイラ):
    """MINIDORA公開標準HDS Compiler。

    Meaning/Audit Architecture v1.2を保持し、Pipeline v1.3で意味フロントエンドと
    計算降下バックエンドを分離する。``意味コンパイル()`` が意味正本入口であり、
    返すHDS-IRは計算Pを内包しない。``コンパイル()`` は旧Runtime向け互換橋として
    最外周でのみPを再付与する。
    """

    Architecture版 = "v1.2"
    Pipeline版 = "v1.3"
    基底言語 = "ja"

    def __init__(self, 方針: 公開HDSコンパイラ方針 | None = None, 言語基底P_: 言語基底P | None = None) -> None:
        super().__init__(方針)
        self.言語基底P = 言語基底P_ or 標準言語基底P
        self._計算計画器 = self._legacy
        self._意味基礎 = _意味基礎HDSコンパイラ(self)
        self._計算降下 = HDS計算降下バックエンド()

    def _入力言語(self, text: str) -> str:
        return self.言語基底P.入力言語判定(text)

    def _完成(self, base: HDSIR, *, HDS履歴: tuple[HDSIR, ...] = ()) -> HDSCompiler成果:
        base = HDS英日意味射影(base)
        base = HDS英語基底関係射影(base, self.言語基底P)
        base = HDS英語AND展開(base)
        base = HDS英語関係scope射影(base)
        base = HDS問い主題射影(base, 上限=self.方針.最大主題語数)

        first = 公開HDSフロントエンド射影(base)
        graph = HDS状態遷移抽出(first.IR.正規化文 or first.IR.原文)
        ir = HDS状態遷移IR射影(first.IR, graph)
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
            状態遷移=graph,
            暗黙知構造=tacit,
            失敗署名候補=signatures,
            チェックリスト=checklist,
            認知世界差分=world_diff,
            監査参照候補=audit_queries,
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
        plan = self._計算計画器.計画(normalized)
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
    ) -> tuple[HDSコンパイル束, HDSCompiler成果]:
        semantic_base, plan = self._意味基礎IR(
            入力,
            前回結果=前回結果,
            HDS履歴=HDS履歴,
            文脈=文脈,
        )
        detailed = self._完成(semantic_base, HDS履歴=HDS履歴)
        semantic_ir = replace(detailed.IR, 手順=None, 初期状態={})
        detailed = replace(detailed, IR=semantic_ir)
        return HDSコンパイル束(semantic_ir, plan), detailed

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
        """Legacy互換入口。意味正本へ最外周でのみPを再付与する。"""

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
    ) -> HDSCompiler成果:
        _, detailed = self._意味束(
            入力,
            前回結果=前回結果,
            HDS履歴=HDS履歴,
            文脈=文脈,
        )
        return detailed

    def _問題基礎(self, question: str, choices: Sequence[str]) -> HDSIR:
        if len(choices) < 2:
            raise ValueError("選択問題には2件以上の候補が必要")
        if len(choices) > 26:
            raise ValueError("公開Compilerの選択ラベル上限は26件")
        base, _ = self._意味基礎IR(question)
        choice_coords = tuple(
            HDS座標(
                f"choice:{chr(ord('A') + index)}",
                "目的.候補",
                str(text),
                値状態.確定,
                由来="選択問題入力",
            )
            for index, text in enumerate(choices)
        )
        return replace(
            base,
            座標=base.座標 + choice_coords,
            参照必須=True,
            種別="knowledge_query",
            実行核=HDS実行核(
                "HDS_choice_selection",
                (),
                "結果",
                境界=("NO_GUESS", "gold非参照", "HDS-SEMANTIC"),
                検証=("全候補対称", "計算P非内包"),
            ),
            手順=None,
            初期状態={},
            閉包状態="CLOSED_FOR_SEMANTIC_TRANSFER",
        )

    def 問題IR(self, question: str, choices: Sequence[str]) -> HDSIR:
        return self._完成(self._問題基礎(question, choices)).IR

    def 詳細問題IR(self, question: str, choices: Sequence[str]) -> HDSCompiler成果:
        return self._完成(self._問題基礎(question, choices))

    def 失敗帰還(self, 成果: HDSCompiler成果, Bank: HDS失敗署名Bank, *, Run参照: str) -> HDS失敗署名BankSnapshot:
        return Bank.観測(成果.失敗署名候補, Run参照=Run参照)

    def 改善候補(self, Bank: HDS失敗署名Bank) -> tuple[HDS抽出規則改善候補, ...]:
        return Bank.snapshot().改善候補


__all__ = [
    "公開HDSコンパイラ方針",
    "公開HDSコンパイラ",
    "HDSCompiler成果",
    "HDS失敗署名Bank",
    "HDSコンパイル束",
    "HDS計算コンパイル成果",
]
