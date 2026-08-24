from __future__ import annotations

from dataclasses import replace

from .hds_ir import HDSIR, HDS座標, HDS関係, HDS意味作用, 値状態
from .言語基底_英日意味 import 英日意味フレーム抽出


_VERSION = "v0.3"


def _norm(value: object) -> str:
    return " ".join(str(value).split()).strip()


def HDS英日意味射影(ir: HDSIR) -> HDSIR:
    """英語表層を日本語正本の意味フレームへ有限射影する。

    全文翻訳は行わない。否定・比較・条件・様相・量化・関係質問を日本語正本の意味として
    HDSへ保持し、外部Rへ戻す英語検索表層は別座標に分離する。世界知識は追加しない。
    """
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

    # 日本語正本の意味は検索queryへ混ぜず、意味作用履歴として保持する。
    if frame.正本意味:
        operations.append(
            HDS意味作用(
                "lang-sem:canonicalize",
                "英日意味正本化",
                ("normalized",),
                (),
                " / ".join(frame.正本意味),
                保持構造=("原文", "外部英語表層", "日本語意味正本"),
                損失=(),
                検証=("世界知識非追加", "外部検索表層分離"),
            )
        )

    if frame.外部検索語:
        # R境界へ戻す英語正規化表層は、単なる「その他」ではなく検索目的そのものとして保持する。
        # hds_reference側は目的座標を焦点群へ置くため、追加推論なしでR queryの上流へ直結できる。
        external = " ".join(token for token in frame.外部検索語 if not token.startswith("rel:"))
        if external:
            add_coord("lang-sem:search", "目的.検索焦点", external)

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
        # 検索ではこの意味正本関係を最初に使う。
        relations.insert(0, semantic_relation)

        if question.反転:
            if not any(str(coord.種別) == "制御.選択意図" and str(coord.内容) == "反転" for coord in coords):
                add_coord("lang-sem:selection", "制御.選択意図", "反転")

    return replace(ir, 座標=tuple(coords), 関係=tuple(relations), 意味作用履歴=tuple(operations))


__all__ = ["HDS英日意味射影"]
