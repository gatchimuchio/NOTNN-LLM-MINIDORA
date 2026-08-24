from __future__ import annotations

from dataclasses import replace

from .hds_ir import HDSIR, HDS座標, HDS関係, HDS意味作用, 値状態
from .言語基底_英日意味 import 英日意味フレーム, 英日意味フレーム抽出


_VERSION = "v0.4"
_GENERIC_RELATIONS = {
    "意味原子→節",
    "談話順序",
    "節→述語",
    "候補→集合",
    "問い×候補→選択目的",
    "共参照",
    "数量単位",
}


def _norm(value: object) -> str:
    return " ".join(str(value).split()).strip()


def _意味条件(frame: 英日意味フレーム, *, question: bool) -> tuple[str, ...]:
    out: list[str] = []
    for control in frame.制御:
        kind = str(control.種別)
        canonical = str(control.正本)
        surface = _norm(control.表層)
        if kind == "選択":
            continue
        if question and kind == "蓋然性":
            continue
        if kind == "否定":
            out.append("極性=否定")
            if surface:
                out.append(f"極性表層={surface}")
        elif kind == "量化":
            out.append(f"量化={canonical}")
            if surface:
                out.append(f"量化表層={surface}")
        elif kind == "比較":
            out.append(f"比較={canonical}")
            if surface:
                out.append(f"比較表層={surface}")
        elif kind == "条件":
            out.append(f"条件種別={canonical}")
            if surface:
                out.append(f"条件接続表層={surface}")
        elif kind == "様相":
            out.append(f"様相={canonical}")
            if surface:
                out.append(f"様相表層={surface}")
        elif kind == "蓋然性":
            out.append(f"蓋然性={canonical}")
            if surface:
                out.append(f"蓋然性表層={surface}")
    return tuple(dict.fromkeys(out))


def _scope_existing_relation(relations: list[HDS関係], coords: list[HDS座標], frame: 英日意味フレーム) -> list[HDS関係]:
    """短い単一命題だけ、制御意味をその関係へscopeする。複数関係では誤scopeを避ける。"""
    candidates = [
        relation
        for relation in relations
        if relation.値状態 == 値状態.確定
        and str(relation.由来) in {"公開HDS Compiler", "共有言語基底P"}
        and str(relation.種別) not in _GENERIC_RELATIONS
    ]
    if len(candidates) != 1:
        return relations

    target = candidates[0]
    inherited = list(target.条件)
    semantic_conditions = list(_意味条件(frame, question=False))
    # 比較の方向・閾値意味を relation.種別 自体が既に持つ場合、同じ意味をscopeへ二重格納しない。
    if str(target.種別).startswith("比較."):
        semantic_conditions = [
            value for value in semantic_conditions
            if not str(value).startswith(("比較=", "比較表層="))
        ]
    inherited.extend(semantic_conditions)
    for coord in coords:
        if str(coord.種別) == "条件.前提" and str(coord.内容).strip():
            inherited.append("条件表層=" + _norm(coord.内容))
    merged = tuple(dict.fromkeys(str(value) for value in inherited if str(value)))
    return [replace(relation, 条件=merged) if relation is target else relation for relation in relations]


def HDS英日意味射影(ir: HDSIR) -> HDSIR:
    """英語表層を日本語正本の意味フレームへ有限射影する。"""
    language = str(getattr(ir, "入力言語", "") or "").casefold()
    if not language.startswith("en"):
        return ir

    text = str(ir.正規化文 or ir.原文)
    frame = 英日意味フレーム抽出(text)
    if not frame.正本意味 and not frame.外部検索語 and frame.関係質問 is None:
        return ir

    coords = list(ir.座標)
    existing_ids = {coord.座標ID for coord in coords}
    relations = list(ir.関係)
    existing_relation_ids = {relation.関係ID for relation in relations}
    operations = list(ir.意味作用履歴)

    def add_coord(base: str, kind: str, content: str, state: 値状態 = 値状態.確定) -> str:
        value = _norm(content)
        candidate = base
        serial = 1
        while candidate in existing_ids:
            candidate = f"{base}:{serial}"
            serial += 1
        existing_ids.add(candidate)
        coords.append(
            HDS座標(
                candidate,
                kind,
                value,
                state,
                由来="共有言語基底P",
                暫定性="EN_TO_JA_SEMANTIC_PROJECTION",
            )
        )
        return candidate

    if frame.正本意味:
        operations.append(
            HDS意味作用(
                "lang-sem:canonicalize",
                "英日意味正本化",
                ("normalized",),
                (),
                " / ".join(frame.正本意味),
                保持構造=("原文", "外部英語表層", "日本語意味正本", "関係scope", "scope復号表層"),
                損失=(),
                検証=("世界知識非追加", "外部検索表層分離", "制御scope保持", "復号表層非正本化"),
            )
        )

    if frame.外部検索語:
        external = " ".join(token for token in frame.外部検索語 if not token.startswith("rel:"))
        if external:
            add_coord("lang-sem:search", "検索.英語正規化", external)

    question = frame.関係質問
    if question is not None and question.既知端点:
        if question.未知位置 == "始点":
            start_id = add_coord("lang-sem:unknown:start", "目的.未知始点", question.要求型 or "未特定", 値状態.未観測)
            end_id = add_coord("lang-sem:known:end", "対象.終点", question.既知端点)
        else:
            start_id = add_coord("lang-sem:known:start", "対象.始点", question.既知端点)
            end_id = add_coord("lang-sem:unknown:end", "目的.未知終点", question.要求型 or "未特定", 値状態.未観測)

        add_coord("lang-sem:missing", "目的.不足位置", question.未知位置)
        if question.要求型:
            add_coord("lang-sem:type", "目的.要求型", question.要求型)

        rid = "lang-sem:relation-question"
        serial = 1
        while rid in existing_relation_ids:
            rid = f"lang-sem:relation-question:{serial}"
            serial += 1
        conditions = tuple(dict.fromkeys((
            f"検索述語={question.検索述語}",
            f"極性={question.極性}",
            f"不足位置={question.未知位置}",
            f"英日意味射影={_VERSION}",
            f"受動態={str(question.受動).lower()}",
            *_意味条件(frame, question=True),
        )))
        semantic_relation = HDS関係(
            rid,
            (start_id,),
            (end_id,),
            question.種別,
            条件=conditions,
            値状態=値状態.未観測,
            由来="共有言語基底P",
            暫定性="EN_TO_JA_SEMANTIC_PROJECTION",
        )
        relations.insert(0, semantic_relation)

        if question.反転:
            if not any(str(coord.種別) == "制御.選択意図" and str(coord.内容) == "反転" for coord in coords):
                add_coord("lang-sem:selection", "制御.選択意図", "反転")
    else:
        relations = _scope_existing_relation(relations, coords, frame)

    return replace(ir, 座標=tuple(coords), 関係=tuple(relations), 意味作用履歴=tuple(operations))


__all__ = ["HDS英日意味射影"]
