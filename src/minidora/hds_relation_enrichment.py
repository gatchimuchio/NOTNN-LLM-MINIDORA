from __future__ import annotations

from dataclasses import replace
import re
from typing import Iterable

from .hds_ir import HDSIR, HDS座標, HDS関係, 値状態


# 基礎Compilerの高精度規則を置換せず、科学・技術文で頻出する明示関係だけを補完する。
# 文字列・gold・ベンチ固有分岐は持たない。
_英語補完規則: tuple[tuple[str, re.Pattern[str], bool], ...] = (
    # 既存関係の一般的な同義表現
    ("因果", re.compile(r"(?P<s>[^?!.;,]{1,140}?)\s+(?P<v>induces?|triggers?|elicits?)\s+(?P<o>[^?!.;,]{1,140})", re.I), False),
    ("増加", re.compile(r"(?P<s>[^?!.;,]{1,140}?)\s+(?P<v>promotes?|facilitates?|upregulates?)\s+(?P<o>[^?!.;,]{1,140})", re.I), False),
    ("減少", re.compile(r"(?P<s>[^?!.;,]{1,140}?)\s+(?P<v>attenuates?|diminishes?|downregulates?)\s+(?P<o>[^?!.;,]{1,140})", re.I), False),
    ("阻害", re.compile(r"(?P<s>[^?!.;,]{1,140}?)\s+(?P<v>represses?)\s+(?P<o>[^?!.;,]{1,140})", re.I), False),
    ("生成", re.compile(r"(?P<s>[^?!.;,]{1,140}?)\s+(?P<v>yields?|forms?)\s+(?P<o>[^?!.;,]{1,140})", re.I), False),
    ("相関", re.compile(r"(?P<s>[^?!.;,]{1,140}?)\s+(?P<v>is\s+linked\s+to)\s+(?P<o>[^?!.;,]{1,140})", re.I), False),

    # 科学・技術文で高頻度かつ関係方向が比較的明確なもの
    ("結合", re.compile(r"(?P<s>[^?!.;,]{1,140}?)\s+(?P<v>binds?(?:\s+to)?)\s+(?P<o>[^?!.;,]{1,140})", re.I), False),
    ("結合", re.compile(r"(?P<s>[^?!.;,]{1,140}?)\s+(?P<v>is\s+bound\s+to)\s+(?P<o>[^?!.;,]{1,140})", re.I), False),
    ("相互作用", re.compile(r"(?P<s>[^?!.;,]{1,140}?)\s+(?P<v>interacts?\s+with|couples?\s+to)\s+(?P<o>[^?!.;,]{1,140})", re.I), False),
    ("符号化", re.compile(r"(?P<s>[^?!.;,]{1,140}?)\s+(?P<v>encodes?)\s+(?P<o>[^?!.;,]{1,140})", re.I), False),
    ("局在", re.compile(r"(?P<s>[^?!.;,]{1,140}?)\s+(?P<v>localizes?\s+to|is\s+(?:located|localized)\s+(?:in|at|to))\s+(?P<o>[^?!.;,]{1,140})", re.I), False),
    ("包含", re.compile(r"(?P<s>[^?!.;,]{1,140}?)\s+(?P<v>consists?\s+of|is\s+composed\s+of)\s+(?P<o>[^?!.;,]{1,140})", re.I), False),
    ("媒介", re.compile(r"(?P<s>[^?!.;,]{1,140}?)\s+(?P<v>mediates?)\s+(?P<o>[^?!.;,]{1,140})", re.I), False),
    ("調節", re.compile(r"(?P<s>[^?!.;,]{1,140}?)\s+(?P<v>regulates?)\s+(?P<o>[^?!.;,]{1,140})", re.I), False),
    ("触媒", re.compile(r"(?P<s>[^?!.;,]{1,140}?)\s+(?P<v>catalyzes?|catalyses?)\s+(?P<o>[^?!.;,]{1,140})", re.I), False),
    ("放出", re.compile(r"(?P<s>[^?!.;,]{1,140}?)\s+(?P<v>emits?|releases?)\s+(?P<o>[^?!.;,]{1,140})", re.I), False),
    ("吸収", re.compile(r"(?P<s>[^?!.;,]{1,140}?)\s+(?P<v>absorbs?)\s+(?P<o>[^?!.;,]{1,140})", re.I), False),
    ("崩壊", re.compile(r"(?P<s>[^?!.;,]{1,140}?)\s+(?P<v>decays?\s+(?:into|to))\s+(?P<o>[^?!.;,]{1,140})", re.I), False),
    ("反応", re.compile(r"(?P<s>[^?!.;,]{1,140}?)\s+(?P<v>reacts?\s+with)\s+(?P<o>[^?!.;,]{1,140})", re.I), False),

    # 受動態を能動態と同じ方向へ正規化する。
    ("因果", re.compile(r"(?P<s>[^?!.;,]{1,140}?)\s+(?P<v>is\s+(?:induced|triggered|elicited)\s+by)\s+(?P<o>[^?!.;,]{1,140})", re.I), True),
    ("増加", re.compile(r"(?P<s>[^?!.;,]{1,140}?)\s+(?P<v>is\s+(?:promoted|facilitated|upregulated)\s+by)\s+(?P<o>[^?!.;,]{1,140})", re.I), True),
    ("減少", re.compile(r"(?P<s>[^?!.;,]{1,140}?)\s+(?P<v>is\s+(?:attenuated|diminished|downregulated|decreased|reduced)\s+by)\s+(?P<o>[^?!.;,]{1,140})", re.I), True),
    ("阻害", re.compile(r"(?P<s>[^?!.;,]{1,140}?)\s+(?P<v>is\s+(?:inhibited|suppressed|blocked|repressed)\s+by)\s+(?P<o>[^?!.;,]{1,140})", re.I), True),
    ("活性化", re.compile(r"(?P<s>[^?!.;,]{1,140}?)\s+(?P<v>is\s+(?:activated|stimulated)\s+by)\s+(?P<o>[^?!.;,]{1,140})", re.I), True),
    ("生成", re.compile(r"(?P<s>[^?!.;,]{1,140}?)\s+(?P<v>is\s+(?:produced|generated|formed)\s+by)\s+(?P<o>[^?!.;,]{1,140})", re.I), True),
    ("結合", re.compile(r"(?P<s>[^?!.;,]{1,140}?)\s+(?P<v>is\s+bound\s+by)\s+(?P<o>[^?!.;,]{1,140})", re.I), True),
    ("符号化", re.compile(r"(?P<s>[^?!.;,]{1,140}?)\s+(?P<v>is\s+encoded\s+by)\s+(?P<o>[^?!.;,]{1,140})", re.I), True),
    ("媒介", re.compile(r"(?P<s>[^?!.;,]{1,140}?)\s+(?P<v>is\s+mediated\s+by)\s+(?P<o>[^?!.;,]{1,140})", re.I), True),
    ("調節", re.compile(r"(?P<s>[^?!.;,]{1,140}?)\s+(?P<v>is\s+regulated\s+by)\s+(?P<o>[^?!.;,]{1,140})", re.I), True),
    ("触媒", re.compile(r"(?P<s>[^?!.;,]{1,140}?)\s+(?P<v>is\s+cataly[sz]ed\s+by)\s+(?P<o>[^?!.;,]{1,140})", re.I), True),
    ("使用", re.compile(r"(?P<s>[^?!.;,]{1,140}?)\s+(?P<v>is\s+used\s+by)\s+(?P<o>[^?!.;,]{1,140})", re.I), True),
    # "A is required for B" == "B requires A"
    ("要求", re.compile(r"(?P<s>[^?!.;,]{1,140}?)\s+(?P<v>is\s+required\s+for)\s+(?P<o>[^?!.;,]{1,140})", re.I), True),
)

_日本語補完規則: tuple[tuple[str, re.Pattern[str], bool], ...] = (
    ("結合", re.compile(r"(?P<s>[^。！？、]{1,100}?)(?:が|は)(?P<o>[^。！？、]{1,100}?)(?:に|と)(?P<v>結合する)"), False),
    ("相互作用", re.compile(r"(?P<s>[^。！？、]{1,100}?)(?:が|は)(?P<o>[^。！？、]{1,100}?)(?:と)(?P<v>相互作用する)"), False),
    ("符号化", re.compile(r"(?P<s>[^。！？、]{1,100}?)(?:が|は)(?P<o>[^。！？、]{1,100}?)(?:を)(?P<v>符号化する|コードする)"), False),
    ("局在", re.compile(r"(?P<s>[^。！？、]{1,100}?)(?:が|は)(?P<o>[^。！？、]{1,100}?)(?:に)(?P<v>局在する)"), False),
    ("媒介", re.compile(r"(?P<s>[^。！？、]{1,100}?)(?:が|は)(?P<o>[^。！？、]{1,100}?)(?:を)(?P<v>媒介する)"), False),
    ("調節", re.compile(r"(?P<s>[^。！？、]{1,100}?)(?:が|は)(?P<o>[^。！？、]{1,100}?)(?:を)(?P<v>調節する|制御する)"), False),
    ("触媒", re.compile(r"(?P<s>[^。！？、]{1,100}?)(?:が|は)(?P<o>[^。！？、]{1,100}?)(?:を)(?P<v>触媒する)"), False),
)

_未知端点 = re.compile(r"\b(?:which|what|who|whom)\b|(?:どの|何|なに|誰)", re.I)
_否定末尾 = re.compile(r"(?:\b(?:not|never|cannot|can't|does\s+not|do\s+not|did\s+not)\b|(?:ない|ず|しない))\s*$", re.I)


def _clean(value: object) -> str:
    return " ".join(str(value).split()).strip(" ,;:。！？?")


def _endpoint_ok(value: str) -> bool:
    if not value or _未知端点.search(value):
        return False
    # "A does not bind B" のように、非貪欲subject側へ否定助動詞が残った場合は関係化しない。
    if _否定末尾.search(value):
        return False
    return True


def _relation_key(kind: str, start: str, end: str) -> tuple[str, str, str]:
    return kind, start.casefold(), end.casefold()


def HDS関係補完射影(ir: HDSIR) -> HDSIR:
    """既存HDS-IRへ高確度の明示関係だけを追加する。

    既存関係は変更しない。疑問の未知端点・否定文は補完関係へ昇格させず、同一の
    種別×始点×終点は重複追加しない。これは公開Projectionであり真偽判定を行わない。
    """
    text = _clean(ir.正規化文 or ir.原文)
    if not text:
        return ir

    coords = list(ir.座標)
    relations = list(ir.関係)
    coord_by_key: dict[tuple[str, str], str] = {
        (str(coord.種別), _clean(coord.内容).casefold()): coord.座標ID
        for coord in coords
        if _clean(coord.内容)
    }
    coord_dict = ir.座標辞書()
    existing_edges: set[tuple[str, str, str]] = set()
    for relation in relations:
        if len(relation.始点) != 1 or len(relation.終点) != 1:
            continue
        start_coord = coord_dict.get(relation.始点[0])
        end_coord = coord_dict.get(relation.終点[0])
        if start_coord is None or end_coord is None:
            continue
        existing_edges.add(_relation_key(str(relation.種別), _clean(start_coord.内容), _clean(end_coord.内容)))

    counter = 0

    def coord(kind: str, content: str) -> str:
        nonlocal counter
        value = _clean(content)
        key = (kind, value.casefold())
        existing = coord_by_key.get(key)
        if existing is not None:
            return existing
        while True:
            cid = f"relx:{counter:03d}"
            counter += 1
            if all(existing_coord.座標ID != cid for existing_coord in coords):
                break
        coords.append(HDS座標(cid, kind, value, 値状態.確定, 由来="公開HDS Compiler 関係補完"))
        coord_by_key[key] = cid
        return cid

    added = 0
    for kind, pattern, reverse in (*_英語補完規則, *_日本語補完規則):
        for match in pattern.finditer(text):
            start = _clean(match.group("s"))
            end = _clean(match.group("o"))
            verb = _clean(match.group("v"))
            if not _endpoint_ok(start) or not _endpoint_ok(end) or not verb:
                continue
            if reverse:
                start, end = end, start
            if start.casefold() == end.casefold():
                continue
            key = _relation_key(kind, start, end)
            if key in existing_edges:
                continue
            sid = coord("対象.始点", start)
            oid = coord("対象.終点", end)
            coord("関係.述語", verb)
            relations.append(
                HDS関係(
                    f"relx:{added:03d}",
                    (sid,),
                    (oid,),
                    kind,
                    条件=(f"検索述語={verb}", "関係補完=高確度明示表現"),
                    値状態=値状態.確定,
                    由来="公開HDS Compiler 関係補完",
                )
            )
            existing_edges.add(key)
            added += 1

    if not added:
        return ir
    return replace(ir, 座標=tuple(coords), 関係=tuple(relations))


__all__ = ["HDS関係補完射影"]
