from __future__ import annotations

from dataclasses import replace
import re

from .hds_ir import HDSIR, HDS座標, HDS関係, HDS残差, HDS意味作用, 値状態
from .言語基底_英日意味強化 import 英日意味フレーム抽出


_VERSION = "v0.5"
_WH = re.compile(r"\b(?:which|what|who|where|when|why|how)\b", re.I)


def _norm(value: object) -> str:
    return " ".join(str(value).split()).strip()


def HDS英日意味射影(ir: HDSIR) -> HDSIR:
    """英語表層を日本語正本の意味フレームへ有限射影する。

    v0.5では有限関係語彙外の**明示述語**を開放述語として保持し、命題選択・説明選択も
    「世界事実」へ誤変換せず問い関係として保持する。未知の意味を世界知識で補わない。
    """
    language = str(getattr(ir, "入力言語", "") or "").casefold()
    if not language.startswith("en"):
        return ir

    text = str(ir.正規化文 or ir.原文)
    frame = 英日意味フレーム抽出(text)
    if not frame.正本意味 and not frame.外部検索語 and frame.関係質問 is None:
        if _WH.search(text) and not any(residual.種別 == "semantic_loss" for residual in ir.残差):
            residual = HDS残差(
                "lang-sem:question-loss",
                "semantic_loss",
                text,
                "質問の未知関係を意味IRへ保持できない",
                解消条件=("開放述語または問い適合関係へ射影する",),
            )
            return replace(ir, 残差=(*ir.残差, residual))
        return ir

    coords = list(ir.座標)
    existing_ids = {coord.座標ID for coord in coords}
    relations = list(ir.関係)
    existing_relation_ids = {relation.関係ID for relation in relations}
    operations = list(ir.意味作用履歴)
    residuals = list(ir.残差)

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
                保持構造=("原文", "外部英語表層", "日本語意味正本", "質問関係修飾", "開放述語"),
                損失=(),
                検証=("世界知識非追加", "外部検索表層分離", "背景制御非伝染", "有限語彙外明示述語保持"),
            )
        )

    if frame.外部検索語:
        external = " ".join(token for token in frame.外部検索語 if not token.startswith("rel:"))
        if external:
            add_coord("lang-sem:search", "検索.英語正規化", external)

    question = frame.関係質問
    if question is not None:
        known = question.既知端点 or "問い対象"
        if question.未知位置 == "始点":
            start_id = add_coord("lang-sem:unknown:start", "目的.未知始点", question.要求型 or "未特定", 値状態.未観測)
            end_id = add_coord("lang-sem:known:end", "対象.終点", known)
        else:
            start_id = add_coord("lang-sem:known:start", "対象.始点", known)
            end_id = add_coord("lang-sem:unknown:end", "目的.未知終点", question.要求型 or "未特定", 値状態.未観測)

        add_coord("lang-sem:missing", "目的.不足位置", question.未知位置)
        if question.要求型:
            add_coord("lang-sem:type", "目的.要求型", question.要求型)

        rid = "lang-sem:relation-question"
        serial = 1
        while rid in existing_relation_ids:
            rid = f"lang-sem:relation-question:{serial}"
            serial += 1

        relation_conditions = [
            f"検索述語={question.検索述語}",
            f"不足位置={question.未知位置}",
            f"英日意味射影={_VERSION}",
            f"受動態={str(question.受動).lower()}",
            f"選択意図={'反転' if question.反転 else '通常'}",
        ]
        relation_conditions.extend(f"{key}={value}" for key, value in question.修飾)

        relations.insert(
            0,
            HDS関係(
                rid,
                (start_id,),
                (end_id,),
                question.種別,
                条件=tuple(dict.fromkeys(relation_conditions)),
                値状態=値状態.未観測,
                由来="共有言語基底P",
                暫定性="EN_TO_JA_SEMANTIC_PROJECTION",
            ),
        )

        if question.反転 and not any(
            str(coord.種別) == "制御.選択意図" and str(coord.内容) == "反転" for coord in coords
        ):
            add_coord("lang-sem:selection", "制御.選択意図", "反転")
    elif _WH.search(text) and not any(residual.種別 == "semantic_loss" for residual in residuals):
        residuals.append(
            HDS残差(
                "lang-sem:question-loss",
                "semantic_loss",
                text,
                "質問の未知関係を意味IRへ保持できない",
                解消条件=("開放述語または問い適合関係へ射影する",),
            )
        )

    return replace(ir, 座標=tuple(coords), 関係=tuple(relations), 残差=tuple(residuals), 意味作用履歴=tuple(operations))


__all__ = ["HDS英日意味射影"]
