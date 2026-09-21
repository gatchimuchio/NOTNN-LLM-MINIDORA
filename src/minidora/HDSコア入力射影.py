"""HDS意味IRからMINIDORA Core消費情報だけを射影する。

監査座標、計算手順、能力名、作用実行結果、最終採否は正本入力へ混入させない。
"""
from __future__ import annotations

from .コア.値 import 署名
from .HDSコア要求抽出 import 明示作用要求を抽出
from .HDSコア入力 import (
    HDSコア意味項目, HDSコア条件, HDSコア関係, HDSコア目的,
    HDSコア作用要求, HDSコア残差, HDSコア検証要求, HDSコア表現制約,
    HDSコア入力束,
)

_監査接頭辞 = ("監査.", "保持.", "暫定性.", "帰還.")


def _状態名(値) -> str:
    return str(getattr(値, "value", 値))


def _監査項目か(座標) -> bool:
    種別 = str(getattr(座標, "種別", ""))
    return 種別.startswith(_監査接頭辞)


def HDSコア入力へ(IR) -> HDSコア入力束:
    """意味IRをCore入力正本へ射影する。

    実行計画や計算Pを再利用しない。IRに明示された意味だけを移す。
    """
    必須 = ("原文", "認知世界ID", "座標", "関係", "残差", "入力言語", "出力言語", "文脈引用", "参照必須")
    if any(not hasattr(IR, 名) for 名 in 必須):
        raise TypeError("HDS意味IR契約が不足")
    if not isinstance(IR.原文, str) or not IR.原文.strip():
        raise ValueError("Core入力には空でない原文が必要")

    意味項目 = []
    除外ID = set()
    for 座標 in tuple(IR.座標):
        ID = str(getattr(座標, "座標ID"))
        if _監査項目か(座標):
            除外ID.add(ID)
            continue
        意味項目.append(HDSコア意味項目(
            ID=ID,
            種別=str(getattr(座標, "種別")),
            内容=getattr(座標, "内容"),
            状態=_状態名(getattr(座標, "値状態")),
            由来=str(getattr(座標, "由来", "自然言語入力")),
            原文範囲=getattr(座標, "原文範囲", None),
        ))
    意味ID = {x.ID for x in 意味項目}

    条件 = []
    for 項目 in 意味項目:
        if not 項目.種別.startswith("条件."):
            continue
        条件.append(HDSコア条件(
            ID=項目.ID,
            種別=項目.種別.split(".", 1)[1] or "条件",
            内容=項目.内容,
            状態=項目.状態,
            由来=項目.由来,
            原文範囲=項目.原文範囲,
        ))

    関係 = []
    追加残差 = []
    for 関係元 in tuple(IR.関係):
        関係ID = str(getattr(関係元, "関係ID"))
        始点 = tuple(str(x) for x in getattr(関係元, "始点"))
        終点 = tuple(str(x) for x in getattr(関係元, "終点"))
        参照 = set((*始点, *終点))
        if 参照 and 参照 <= 除外ID:
            continue
        if 参照 & 除外ID:
            追加残差.append(HDSコア残差(
                ID="Core入力:監査依存:" + 関係ID,
                種別="監査副産物依存",
                理由="意味関係が監査副産物を参照しておりCore入力へ安全に分離できない",
                影響参照=tuple(sorted(参照 - 除外ID)),
                解消条件=("監査副産物参照を意味関係から分離する",),
            ))
            continue
        if not 参照 <= 意味ID:
            追加残差.append(HDSコア残差(
                ID="Core入力:参照欠落:" + 関係ID,
                種別="関係参照欠落",
                理由="意味関係の参照先がCore入力意味項目に存在しない",
                影響参照=tuple(sorted(参照)),
                解消条件=("関係参照先を構文化する",),
            ))
            continue
        # HDS関係.条件には検索述語・不足位置など構文化/照合用メタデータが含まれる。
        # これを意味条件へ昇格せず、関係制約として分離保持する。
        関係.append(HDSコア関係(
            ID=関係ID,
            始点=始点,
            終点=終点,
            種別=str(getattr(関係元, "種別")),
            条件ID=(),
            制約=tuple(str(x) for x in getattr(関係元, "条件", ())),
            状態=_状態名(getattr(関係元, "値状態")),
            由来=str(getattr(関係元, "由来", "自然言語入力")),
        ))

    目的 = []
    for 項目 in 意味項目:
        if not 項目.種別.startswith("目的."):
            continue
        種別 = 項目.種別.split(".", 1)[1] or "目的"
        関連参照 = []
        for 関係項 in 関係:
            端点 = (*関係項.始点, *関係項.終点)
            if 項目.ID in 端点:
                関連参照.extend(x for x in 端点 if x != 項目.ID)
        目的.append(HDSコア目的(
            項目.ID, 種別, 項目.内容, tuple(dict.fromkeys(関連参照)), 項目.原文範囲
        ))

    # 目的.*を能力名へ読み替えず、原文に明示された作用意味だけを別経路で抽出する。
    要求抽出 = 明示作用要求を抽出(IR.原文)
    作用要求 = list(要求抽出.作用要求)

    残差 = list(要求抽出.残差)
    for 項目 in tuple(IR.残差):
        解消条件 = tuple(str(x) for x in getattr(項目, "解消条件", ()))
        残差.append(HDSコア残差(
            ID=str(getattr(項目, "残差ID")),
            種別=str(getattr(項目, "種別")),
            理由=str(getattr(項目, "理由")),
            原文=str(getattr(項目, "原文", "")),
            影響参照=tuple(str(x) for x in getattr(項目, "影響座標", ())),
            解消条件=解消条件,
        ))
    残差.extend(追加残差)

    検証要求 = tuple(
        HDSコア検証要求(
            ID="検証:" + 項目.ID,
            種別="残差解消確認",
            対象参照=項目.影響参照,
            条件=項目.解消条件 or ("残差が解消されること",),
        )
        for 項目 in 残差
    )

    # 完了条件は明示作用要求の期待成果だけを供給し、目的座標からは捏造しない。
    要求成果 = tuple(dict.fromkeys(成果 for 要求 in 作用要求 for 成果 in 要求.要求成果))
    表現制約 = HDSコア表現制約(
        str(IR.入力言語),
        None if IR.出力言語 is None else str(IR.出力言語),
        bool(IR.参照必須),
    )
    由来署名 = 署名((
        IR.原文, IR.認知世界ID,
        tuple((x.ID, x.種別, x.内容, x.状態, x.由来, x.原文範囲) for x in 意味項目),
        tuple((x.ID, x.始点, x.終点, x.種別, x.条件ID, x.制約, x.状態, x.由来) for x in 関係),
        tuple((x.ID, x.種別, x.理由, x.影響参照, x.解消条件) for x in 残差),
    ))
    結果 = HDSコア入力束(
        原文=IR.原文,
        認知世界ID=str(IR.認知世界ID),
        意味項目=tuple(意味項目),
        関係=tuple(関係),
        条件=tuple(条件),
        目的=tuple(目的),
        作用要求=tuple(作用要求),
        要求成果=要求成果,
        残差=tuple(残差),
        検証要求=検証要求,
        表現制約=表現制約,
        文脈引用=tuple(str(x) for x in IR.文脈引用),
        射影由来署名=由来署名,
    )
    結果.コア需要を検査()
    return 結果


__all__ = ["HDSコア入力へ"]
