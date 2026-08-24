from __future__ import annotations

from dataclasses import replace
from typing import Mapping

from .hds_ir import HDSIR, HDS座標, HDS関係, 値状態


_BLOCKING = {値状態.未確定, 値状態.未観測, 値状態.矛盾, 値状態.留保}


def _条件値(relation: HDS関係, key: str) -> str:
    prefix = key + "="
    for raw in relation.条件:
        value = str(raw)
        if value.startswith(prefix):
            return value[len(prefix):].strip()
    return ""


def _候補表層(ir: HDSIR) -> str:
    return " ".join(str(ir.正規化文 or ir.原文).split()).strip()


def _質問関係(question_ir: HDSIR) -> tuple[HDS関係, ...]:
    """英日意味正本関係があれば表層由来の重複関係より優先する。"""
    canonical = tuple(
        relation
        for relation in question_ir.関係
        if _条件値(relation, "英日意味射影")
        and _条件値(relation, "不足位置") in {"始点", "終点"}
    )
    if canonical:
        return canonical
    return tuple(question_ir.関係)


def _仮説条件(qrelation: HDS関係, missing: str) -> tuple[str, ...]:
    inherited = tuple(
        str(condition)
        for condition in qrelation.条件
        if str(condition)
        and not str(condition).startswith("不足位置=")
        and not str(condition).startswith("由来=")
    )
    return tuple(dict.fromkeys(("由来=候補代入", f"不足位置={missing}", *inherited)))


def HDS候補代入仮説(question_ir: HDSIR, label: str, candidate_ir: HDSIR) -> HDSIR:
    """問いの未知関係端点へ候補を代入した、比較専用の仮説関係を候補IRへ追加する。

    Compilerが `不足位置=始点|終点` として明示した未観測端点だけを対象とする。
    極性・様相・検索述語等の意味条件も問いから継承し、候補代入時に落とさない。
    仮説は `推定` として候補IRにだけ保持し、Kの事実へ投入しない。
    """
    candidate = _候補表層(candidate_ir)
    if not candidate:
        return candidate_ir

    qcoords = question_ir.座標辞書()
    coords = list(candidate_ir.座標)
    relations = list(candidate_ir.関係)
    existing_ids = {coord.座標ID for coord in coords}
    existing_relation_ids = {relation.関係ID for relation in relations}
    added = 0

    def add_coord(kind: str, content: str, suffix: str) -> str:
        base = f"hyp:{label}:{suffix}"
        cid = base
        index = 1
        while cid in existing_ids:
            cid = f"{base}:{index}"
            index += 1
        existing_ids.add(cid)
        coords.append(
            HDS座標(
                cid,
                kind,
                content,
                値状態.推定,
                由来="HDS候補代入仮説",
                暫定性="CANDIDATE_SUBSTITUTION_HYPOTHESIS",
            )
        )
        return cid

    for qrelation in _質問関係(question_ir):
        missing = _条件値(qrelation, "不足位置")
        if missing not in {"始点", "終点"}:
            continue

        known_starts = [
            qcoords[cid]
            for cid in qrelation.始点
            if cid in qcoords and qcoords[cid].値状態 not in _BLOCKING
        ]
        known_ends = [
            qcoords[cid]
            for cid in qrelation.終点
            if cid in qcoords and qcoords[cid].値状態 not in _BLOCKING
        ]

        if missing == "終点":
            if not known_starts:
                continue
            for index, known in enumerate(known_starts):
                sid = add_coord("対象.仮説既知端点", str(known.内容), f"known-start:{added}:{index}")
                oid = add_coord("目的.候補代入", candidate, f"candidate-end:{added}:{index}")
                rid_base = f"hyp-rel:{label}:{added}:{index}"
                rid = rid_base
                serial = 1
                while rid in existing_relation_ids:
                    rid = f"{rid_base}:{serial}"
                    serial += 1
                existing_relation_ids.add(rid)
                relations.append(
                    HDS関係(
                        rid,
                        (sid,),
                        (oid,),
                        str(qrelation.種別),
                        条件=_仮説条件(qrelation, "終点"),
                        値状態=値状態.推定,
                        由来="HDS候補代入仮説",
                        暫定性="CANDIDATE_SUBSTITUTION_HYPOTHESIS",
                    )
                )
                added += 1
        else:
            if not known_ends:
                continue
            for index, known in enumerate(known_ends):
                sid = add_coord("目的.候補代入", candidate, f"candidate-start:{added}:{index}")
                oid = add_coord("対象.仮説既知端点", str(known.内容), f"known-end:{added}:{index}")
                rid_base = f"hyp-rel:{label}:{added}:{index}"
                rid = rid_base
                serial = 1
                while rid in existing_relation_ids:
                    rid = f"{rid_base}:{serial}"
                    serial += 1
                existing_relation_ids.add(rid)
                relations.append(
                    HDS関係(
                        rid,
                        (sid,),
                        (oid,),
                        str(qrelation.種別),
                        条件=_仮説条件(qrelation, "始点"),
                        値状態=値状態.推定,
                        由来="HDS候補代入仮説",
                        暫定性="CANDIDATE_SUBSTITUTION_HYPOTHESIS",
                    )
                )
                added += 1

    if not added:
        return candidate_ir
    return replace(candidate_ir, 座標=tuple(coords), 関係=tuple(relations))


def HDS候補代入仮説群(question_ir: HDSIR, candidates: Mapping[str, HDSIR]) -> dict[str, HDSIR]:
    return {
        str(label): HDS候補代入仮説(question_ir, str(label), candidate_ir)
        for label, candidate_ir in candidates.items()
    }


__all__ = ["HDS候補代入仮説", "HDS候補代入仮説群"]
