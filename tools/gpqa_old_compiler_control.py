from __future__ import annotations

from dataclasses import replace
import re
import runpy
import sys
import unicodedata

import gpqa_measure_current as gpqa
from minidora.hds_ir import HDSIR, HDS実行核, HDS座標, HDS関係, 値状態
from minidora.semantic_tokens import 意味語


class 旧汎用意味射影Compiler:
    """v0.6系31/198測定時の汎用意味射影Compilerをcurrent R/K/J上で再現する対照器。"""

    並列安全 = True

    def __init__(self, 最大意味語数: int = 256) -> None:
        self.最大意味語数 = int(最大意味語数)

    def _ordered_terms(self, text: str) -> tuple[str, ...]:
        normalized = unicodedata.normalize("NFKC", str(text)).strip()
        raw = re.findall(r"[0-9A-Za-z_+\-]+|[一-龥ぁ-んァ-ヶー]+", normalized)
        out: list[str] = []
        seen: set[str] = set()
        for token in raw:
            derived = 意味語(token)
            if not derived:
                continue
            for term in sorted(derived):
                key = term.casefold()
                if not term or key in seen:
                    continue
                seen.add(key)
                out.append(term)
                if len(out) >= self.最大意味語数:
                    return tuple(out)
        if not out:
            out.extend(sorted(意味語(normalized))[: self.最大意味語数])
        return tuple(out)

    def コンパイル(self, 入力: str, **_: object) -> HDSIR:
        raw = str(入力)
        normalized = unicodedata.normalize("NFKC", raw).strip()
        terms = self._ordered_terms(normalized)
        coords: list[HDS座標] = [
            HDS座標("src", "source_text", raw),
            HDS座標("normalized", "language.normalized", normalized),
        ]
        for i, term in enumerate(terms):
            coords.append(HDS座標(f"m:{i}", "対象.意味原子", term, 値状態.確定, 由来="旧汎用意味射影対照"))
        relations = tuple(
            HDS関係(
                f"seq:{i}",
                (f"m:{i}",),
                (f"m:{i + 1}",),
                "談話順序",
                値状態=値状態.確定,
                由来="旧汎用意味射影対照",
            )
            for i in range(max(0, len(terms) - 1))
        )
        return HDSIR(
            原文=raw,
            正規化文=normalized,
            認知世界ID="gpqa:old-generic-control",
            座標=tuple(coords),
            関係=relations,
            残差=(),
            意味作用履歴=(),
            実行核=HDS実行核("意味構造転送"),
            初期状態={},
            参照必須=False,
            種別="意味構造",
            閉包状態="CLOSED_FOR_SEMANTIC_TRANSFER",
            入力言語="en",
        )

    def 問題IR(self, question: str, choices) -> HDSIR:
        labels = gpqa.LABELS
        base = self.コンパイル(question)
        choice_coords = tuple(
            HDS座標(f"choice:{label}", "目的.候補", text, 値状態.確定, 由来="GPQA公式選択肢")
            for label, text in zip(labels, choices)
        )
        return replace(
            base,
            座標=base.座標 + choice_coords,
            参照必須=True,
            種別="knowledge_query",
            実行核=HDS実行核("HDS_choice_selection"),
            手順=None,
        )


gpqa.汎用意味射影Compiler = 旧汎用意味射影Compiler
sys.argv = ["tools/benchmark.py", "gpqa-diamond", "--out", "gpqa_current_measurement.json"]
runpy.run_path("tools/benchmark.py", run_name="__main__")
