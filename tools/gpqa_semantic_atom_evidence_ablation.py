from __future__ import annotations

from dataclasses import replace
import re
import runpy
import sys
import unicodedata

from minidora.hds_data_k import HDSIR知識Adapter, HDS知識投入結果
from minidora.hds_ir import HDSIR, HDS実行核, HDS座標, HDS関係, 値状態
from minidora.semantic_tokens import 意味語


_original_ingest = HDSIR知識Adapter.投入


def _ordered_terms(text: str, limit: int = 256) -> tuple[str, ...]:
    normalized = unicodedata.normalize("NFKC", str(text)).strip()
    raw = re.findall(r"[0-9A-Za-z_+\-]+|[一-龥ぁ-んァ-ヶー]+", normalized)
    out: list[str] = []
    seen: set[str] = set()
    for token in raw:
        for term in sorted(意味語(token)):
            key = term.casefold()
            if not term or key in seen:
                continue
            seen.add(key)
            out.append(term)
            if len(out) >= limit:
                return tuple(out)
    if not out:
        out.extend(sorted(意味語(normalized))[:limit])
    return tuple(out)


def _atom_ir(ir: HDSIR) -> HDSIR | None:
    if str(ir.種別) == "retrieval_route_evidence":
        return None
    terms = _ordered_terms(ir.正規化文 or ir.原文)
    if not terms:
        return None
    coords = tuple(
        HDS座標(
            f"atom:{i}",
            "対象.意味原子",
            term,
            値状態.確定,
            由来="HDS意味原子保持ablation",
        )
        for i, term in enumerate(terms)
    )
    relations = tuple(
        HDS関係(
            f"atom-seq:{i}",
            (f"atom:{i}",),
            (f"atom:{i + 1}",),
            "談話順序",
            値状態=値状態.確定,
            由来="HDS意味原子保持ablation",
        )
        for i in range(max(0, len(terms) - 1))
    )
    return HDSIR(
        原文=ir.原文,
        正規化文=ir.正規化文,
        認知世界ID=ir.認知世界ID + ":semantic-atoms",
        座標=coords,
        関係=relations,
        残差=(),
        意味作用履歴=(),
        実行核=HDS実行核("意味構造転送"),
        初期状態={},
        参照必須=False,
        種別="semantic_atom_evidence",
        閉包状態="CLOSED_FOR_SEMANTIC_TRANSFER",
        入力言語=ir.入力言語,
        出力言語=ir.出力言語,
    )


def _ingest_with_atoms(self, ir: HDSIR, *, provenance=(), 信頼係数: float = 1.0):
    structured = _original_ingest(self, ir, provenance=provenance, 信頼係数=信頼係数)
    atom_ir = _atom_ir(ir)
    if atom_ir is None:
        return structured
    atoms = _original_ingest(self, atom_ir, provenance=provenance, 信頼係数=信頼係数)
    return HDS知識投入結果(
        追加事実数=structured.追加事実数 + atoms.追加事実数,
        座標事実数=structured.座標事実数 + atoms.座標事実数,
        関係事実数=structured.関係事実数 + atoms.関係事実数,
        残差数=structured.残差数 + atoms.残差数,
        semantic_loss=structured.semantic_loss or atoms.semantic_loss,
        証拠事実数=structured.証拠事実数 + atoms.証拠事実数,
        証拠阻害事実数=structured.証拠阻害事実数 + atoms.証拠阻害事実数,
        source_confidence=structured.source_confidence,
    )


HDSIR知識Adapter.投入 = _ingest_with_atoms
sys.argv = ["tools/benchmark.py", "gpqa-diamond", "--out", "gpqa_current_measurement.json"]
runpy.run_path("tools/benchmark.py", run_name="__main__")
