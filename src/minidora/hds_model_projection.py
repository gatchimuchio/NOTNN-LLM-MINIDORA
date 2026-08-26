from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .hds_ir import HDSIR, HDS関係, 値状態
from .semantic_tokens import 意味語
from .言語構造 import 言語関係構造
from .模型 import MINIDORA模型核, 成立候補, 言語状態, 模型結果, 標準模型核


_BLOCKING_ENDPOINT = {値状態.未確定, 値状態.未観測, 値状態.矛盾, 値状態.留保}
_SCOPE_KEYS = frozenset({"様相", "量化", "条件scope", "scope", "条件作用"})


def _条件値(relation: HDS関係, key: str) -> str:
    prefix = key + "="
    for raw in relation.条件:
        value = str(raw)
        if value.startswith(prefix):
            return value[len(prefix):].strip()
    return ""


def _端点意味(ir: HDSIR, ids: tuple[str, ...]) -> frozenset[str]:
    coords = ir.座標辞書()
    out: set[str] = set()
    for cid in ids:
        coord = coords.get(cid)
        if coord is None or coord.値状態 in _BLOCKING_ENDPOINT:
            continue
        out.update(意味語(coord.内容))
    return frozenset(out)


def _述語意味(ir: HDSIR, relation: HDS関係) -> frozenset[str]:
    surface = _条件値(relation, "検索述語")
    if not surface:
        relation_coord_values = [
            str(coord.内容)
            for coord in ir.座標
            if str(coord.種別) == "関係.述語" and str(coord.内容).strip()
        ]
        surface = " ".join(relation_coord_values) or str(relation.種別)
    return 意味語(surface)


def _関係構造(ir: HDSIR, relation: HDS関係) -> 言語関係構造 | None:
    start = _端点意味(ir, relation.始点)
    end = _端点意味(ir, relation.終点)
    if not start and not end:
        return None

    polarity = _条件値(relation, "極性") != "否定"
    conditions: list[frozenset[str]] = []
    seen: set[tuple[str, ...]] = set()
    for raw in relation.条件:
        key, sep, payload = str(raw).partition("=")
        if not sep or key.strip() not in _SCOPE_KEYS or not payload.strip():
            continue
        semantic = 意味語(payload)
        signature = tuple(sorted(semantic))
        if semantic and signature not in seen:
            seen.add(signature)
            conditions.append(semantic)

    return 言語関係構造(
        str(relation.種別),
        start,
        end,
        polarity,
        tuple(conditions),
        _述語意味(ir, relation),
    )


def HDS内部言語状態(ir: HDSIR, *, 識別子: str = "") -> 言語状態:
    """HDS型を模型核へ漏らさず、意味保存済み構造だけを汎用言語状態へ変換する。"""
    relations = tuple(
        converted
        for relation in ir.関係
        if (converted := _関係構造(ir, relation)) is not None
    )
    language = str(getattr(ir, "入力言語", "en") or "en").casefold()
    language_system = "自然言語:ja" if language.startswith("ja") else "自然言語:en"
    return 言語状態(
        str(ir.正規化文 or ir.原文),
        language_system,
        識別子,
        relations,
    )


def _文脈条件(question_ir: HDSIR) -> tuple[str, ...]:
    out: list[str] = []
    for relation in question_ir.関係:
        intent = _条件値(relation, "選択意図")
        if intent:
            out.append("選択意図=" + intent)
    for coord in question_ir.座標:
        if str(coord.種別) == "制御.選択意図" and str(coord.内容).strip():
            out.append("選択意図=" + str(coord.内容).strip())
    return tuple(dict.fromkeys(out))


@dataclass(frozen=True, slots=True)
class HDSMINIDORA射影結果:
    模型結果: 模型結果
    状態: str
    回答ラベル: str | None
    理由: tuple[str, ...]


def HDSMINIDORA模型評価(
    question_ir: HDSIR,
    candidate_irs: Mapping[str, HDSIR],
    data_irs: Sequence[HDSIR],
    *,
    模型核: MINIDORA模型核 | None = None,
) -> HDSMINIDORA射影結果:
    """R→HDSで意味保存した状態を、正式MINIDORA模型核で評価する。

    K3相当能力核はここへ入らない。これをGPQA等の正式性能経路として使い、旧K3 helperは
    互換診断に限定する。
    """
    core = 模型核 or 標準模型核()
    question_state = HDS内部言語状態(question_ir, 識別子="question")
    candidates = tuple(
        成立候補(
            str(label),
            HDS内部言語状態(candidate_ir, 識別子="candidate:" + str(label)),
        )
        for label, candidate_ir in sorted(candidate_irs.items())
    )
    references = tuple(
        HDS内部言語状態(data_ir, 識別子=f"reference:{index}")
        for index, data_ir in enumerate(data_irs)
    )

    result = core.評価言語状態(
        question_state,
        candidates,
        条件=_文脈条件(question_ir),
        参照状態=references,
    )
    if result.最有力候補ID is None:
        return HDSMINIDORA射影結果(
            result,
            "SUSPEND",
            None,
            (
                "MINIDORA_MODEL_CORE_NO_UNIQUE_POSITIVE_DIFFERENCE",
                "CAPABILITY_PROJECTION_V1",
            ),
        )

    selected = next(item for item in result.候補差 if item.候補ID == result.最有力候補ID)
    reference_contributions = tuple(
        item for item in selected.寄与
        if item.関係名 in {"参照関係寄与", "候補共同参照"} and item.差 != 0
    )
    # knowledge choiceは、質問と候補の表層近接だけで確定しない。
    # 少なくとも一つの参照状態が候補差へ到達して初めて選択を外へ出す。
    if not reference_contributions:
        return HDSMINIDORA射影結果(
            result,
            "SUSPEND",
            None,
            (
                "MINIDORA_MODEL_CORE_NO_REFERENCE_CONTRIBUTION",
                "NO_GUESS",
                "CAPABILITY_PROJECTION_V1",
            ),
        )

    return HDSMINIDORA射影結果(
        result,
        "APPROVE",
        result.最有力候補ID,
        (
            "MINIDORA_MODEL_CORE_SELECTED",
            "REFERENCE_CONTRIBUTION_PRESENT",
            "CAPABILITY_PROJECTION_V1",
        ),
    )


__all__ = [
    "HDS内部言語状態",
    "HDSMINIDORA射影結果",
    "HDSMINIDORA模型評価",
]
