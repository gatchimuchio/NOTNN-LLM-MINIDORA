"""要求計画の整合と明示した出力制約を検査してから、結果を上位へ返す。"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import re
from typing import Callable

from .要求解釈 import 要求解釈結果
from .能力合成 import 能力合成器, 合成結果
from .製品版.能力契約 import 能力文脈
from .製品版.型 import 能力結果


@dataclass(frozen=True, slots=True)
class 要求実行結果:
    状態: str
    出力: tuple[tuple[str, 能力結果], ...]
    理由: tuple[str, ...]
    解釈ハッシュ: str
    合成: 合成結果 | None = None

    @property
    def 成立(self) -> bool:
        return self.状態 == "合格"


def 要求計画を実行(解釈: 要求解釈結果, 合成器: 能力合成器, *,
                   文脈: 能力文脈 | None = None,
                   停止要求: Callable[[], bool] | None = None) -> 要求実行結果:
    if not isinstance(解釈, 要求解釈結果) or not 解釈.整合確認():
        return 要求実行結果("失敗", (), ("要求解釈の整合違反",), "")
    if not 解釈.成立:
        return 要求実行結果(解釈.状態, (), tuple(r.理由 for r in 解釈.残差), 解釈.ハッシュ)
    固定 = deepcopy(解釈)
    結果 = 合成器.実行(固定.計画, 固定.初期Data, 文脈=文脈, 停止要求=停止要求)
    if not 結果.成立:
        return 要求実行結果(結果.状態, (), (結果.理由,), 固定.ハッシュ, 結果)
    if not 結果.監査整合():
        return 要求実行結果("失敗", (), ("合成結果の整合違反",), 固定.ハッシュ, 結果)
    中間 = dict(結果.中間結果)
    不足 = []
    for t in 固定.要求:
        出力 = 中間[t.識別子].本文
        if t.行数条件 != "なし":
            実行数 = len(出力.splitlines())
            適合 = 実行数 == t.行数 if t.行数条件 == "一致" else 0 < 実行数 <= t.行数
            if not 適合:
                不足.append(f"{t.識別子}:要約行数条件未達:{t.行数条件}{t.行数}/実測{実行数}")
        if t.能力 == "文脈変換":
            素材 = (固定.初期Data if t.素材.領域 == "入力" else 中間)[t.素材.識別子].本文
            全項目 = [s.strip() for s in re.split(r"[。\n]+", 素材) if s.strip()]
            期待 = "\n".join(f"- {s}" for s in 全項目)
            if 出力 != 期待:
                不足.append(f"{t.識別子}:箇条書き変換に未保持項目")
    if 不足:
        return 要求実行結果("保留", (), tuple(不足), 固定.ハッシュ, 結果)
    return 要求実行結果("合格", deepcopy(結果.出力), (), 固定.ハッシュ, 結果)
