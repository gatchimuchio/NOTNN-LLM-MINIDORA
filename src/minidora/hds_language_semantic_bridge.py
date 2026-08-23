from __future__ import annotations

from dataclasses import replace

from .hds_ir import HDSIR, HDS座標, HDS関係, 値状態
from .言語基底 import 言語基底P, 標準言語基底P


_VERSION = "v0.3"


def _norm(value: object) -> str:
    return " ".join(str(value).split()).strip()


def HDS英日意味射影(ir: HDSIR, 言語基底P_: 言語基底P | None = None) -> HDSIR:
    """英語表層を日本語正本の意味フレームへ有限射影する。

    全文翻訳は行わない。否定・比較・条件・様相・量化・関係質問の構造を日本語正本へ
    射影し、外部Rへ戻すための英語表層は別座標で保持する。世界知識は追加しない。
    """
    language = str(getattr(ir, "入力言語", "") or "").casefold()
    if not language.startswith("en"):
        return ir

    language_base = 言語基底P_ or 標準言語基底P
    text = str(ir.正規化文 or ir.原文)
    frame = language_base.英日意味フレーム(text)
    if not frame.正本意味 and not frame.外部検索語 and frame.関係質問 is None:
        return ir

    coords = list(ir.座標)
    existing_ids = {coord.座標ID for coord in coords}
    relations = list(ir.関係)
    existing_relation_ids = {relation.関係ID for relation in relations}

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

    for index, meaning in enumerate(frame.正本意味):
        add_coord(f"lang-sem:meaning:{index}", "言語正本.意味", meaning)

    if frame.外部検索語:
        # 日本語正本の意味構造とは分離し、R境界へ戻す英語検索表層だけを保持する。
        external = " ".join(token for token in frame.外部検索語 if not token.startswith("rel:"))
        if external:
            add_coord("lang-sem:search", "検索.英語正規化", external)

    for index, control in enumerate(frame.制御):
        add_coord(f"lang-sem:control:{index}", f"言語正本.{control.種別}", control.正本)

    question = frame.関係質問
    if question is not None and question.既知端点:
        if question.未知位置 == "始点":
            start_id = add_coord(
                "lang-sem:unknown:start",
                "目的.未知始点",
                question.要求型 or "未特定",
                値状態.未観測,
            )
            end_id = add_coord("lang-sem:known:end", "対象.終点", question.既知端点)
        else:
            start_id = add_coord("lang-sem:known:start", "対象.始点", question.既知端点)
            end_id = add_coord(
                "lang-sem:unknown:end",
                "目的.未知終点",
                question.要求型 or "未特定",
                値状態.未観測,
            )

        add_coord("lang-sem:missing", "目的.不足位置", question.未知位置)
        if question.要求型:
            add_coord("lang-sem:type", "目的.要求型", question.要求型)
        add_coord("lang-sem:relation", "言語正本.関係", question.種別)

        rid = "lang-sem:relation-question"
        serial = 1
        while rid in existing_relation_ids:
            rid = f"lang-sem:relation-question:{serial}"
            serial += 1
        semantic_relation = HDS関係(
            rid,
            (start_id,),
            (end_id,),
            question.種別,
            条件=(
                f"検索述語={question.検索述語}",
                f"不足位置={question.未知位置}",
                f"英日意味射影={_VERSION}",
                f"受動態={str(question.受動).lower()}",
            ),
            値状態=値状態.未観測,
            由来="共有言語基底P",
            暫定性="EN_TO_JA_SEMANTIC_PROJECTION",
        )
        # 検索・候補代入でこの意味正本関係を先に使えるよう、既存表層関係より前へ置く。
        relations.insert(0, semantic_relation)

        if question.反転:
            # 基礎Compilerが拾えない `unlikely` 等も、日本語正本の選択反転へ落とす。
            if not any(str(coord.種別) == "制御.選択意図" and str(coord.内容) == "反転" for coord in coords):
                add_coord("lang-sem:selection", "制御.選択意図", "反転")

    return replace(ir, 座標=tuple(coords), 関係=tuple(relations))


__all__ = ["HDS英日意味射影"]
