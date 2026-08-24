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
from .hds_compiler_records import HDSCompiler成果
from .hds_compiler_records_v1_2 import HDS失敗署名BankSnapshot, HDS抽出規則改善候補
from .hds_compiler_tacit import HDS暗黙知IR射影, HDS暗黙知抽出
from .hds_ir import HDSIR
from .hds_language_coordination import HDS英語AND展開
from .hds_language_relations import HDS英語基底関係射影
from .hds_language_scope import HDS英語関係scope射影
from .hds_language_semantic_bridge import HDS英日意味射影
from .hds_semantic_topic_projection import HDS問い主題射影
from .言語基底 import 言語基底P, 標準言語基底P


class 公開HDSコンパイラ(_基礎HDSコンパイラ):
    """MINIDORA公開標準HDS Compiler Architecture v1.2。"""

    Architecture版 = "v1.2"
    基底言語 = "ja"

    def __init__(self, 方針: 公開HDSコンパイラ方針 | None = None, 言語基底P_: 言語基底P | None = None) -> None:
        super().__init__(方針)
        self.言語基底P = 言語基底P_ or 標準言語基底P

    def _入力言語(self, text: str) -> str:
        return self.言語基底P.入力言語判定(text)

    def _完成(self, base: HDSIR, *, HDS履歴: tuple[HDSIR, ...] = ()) -> HDSCompiler成果:
        # 質問の英語表層は日本語正本の意味構造へ射影する。
        base = HDS英日意味射影(base)

        # 宣言文の明示関係を共有言語基底Pから補完する。
        base = HDS英語基底関係射影(base, self.言語基底P)

        # `A and B inhibit C` 等の明示ANDで一体化した端点を、確定関係だけ個別辺へ展開する。
        # OR・未知端点・複雑な名詞句は展開しない。
        base = HDS英語AND展開(base)

        # `A may inhibit B` / `A does not inhibit B` の助動・極性を実体端点から分離し、
        # relation条件へ結合する。自然言語の解釈はRuntimeへ持ち込まない。
        base = HDS英語関係scope射影(base)

        # 目的.検索焦点はR/J向けの目的座標であり、意味主題の所有権を持たない。
        # 既存の意味役割で未表現な焦点語だけを対象.主題語へ独立射影する。
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

    def コンパイル(self, 入力: str, *, 前回結果: object = None, HDS履歴: tuple[HDSIR, ...] = (), 文脈: HDS文脈 | None = None) -> HDSIR:
        base = _基礎HDSコンパイラ.コンパイル(self, 入力, 前回結果=前回結果, HDS履歴=HDS履歴, 文脈=文脈)
        return self._完成(base, HDS履歴=HDS履歴).IR

    def 詳細コンパイル(self, 入力: str, *, 前回結果: object = None, HDS履歴: tuple[HDSIR, ...] = (), 文脈: HDS文脈 | None = None) -> HDSCompiler成果:
        base = _基礎HDSコンパイラ.コンパイル(self, 入力, 前回結果=前回結果, HDS履歴=HDS履歴, 文脈=文脈)
        return self._完成(base, HDS履歴=HDS履歴)

    def 詳細問題IR(self, question: str, choices: Sequence[str]) -> HDSCompiler成果:
        return self._完成(self.問題IR(question, choices))

    def 失敗帰還(self, 成果: HDSCompiler成果, Bank: HDS失敗署名Bank, *, Run参照: str) -> HDS失敗署名BankSnapshot:
        return Bank.観測(成果.失敗署名候補, Run参照=Run参照)

    def 改善候補(self, Bank: HDS失敗署名Bank) -> tuple[HDS抽出規則改善候補, ...]:
        return Bank.snapshot().改善候補


__all__ = ["公開HDSコンパイラ方針", "公開HDSコンパイラ", "HDSCompiler成果", "HDS失敗署名Bank"]
