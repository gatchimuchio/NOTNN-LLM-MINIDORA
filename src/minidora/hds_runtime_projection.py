from __future__ import annotations

from dataclasses import replace

from .hds_ir import HDSIR, HDS座標, HDS関係, 値状態


_K_SEMANTIC_PREFIXES = (
    "対象.",
    "実体.",
    "関係.述語",
    "属性.",
    "値.",
    "状態.",
)
_K_EXCLUDED_KINDS = frozenset({"状態.否定"})
_R_CONTEXT_PREFIXES = (
    "検索.",
    "条件.",
    "文脈.",
    "時刻.",
    "時間.",
    "範囲.",
)
_R_FALLBACK_SEMANTIC_PREFIXES = (
    "対象.",
    "実体.",
    "状態.",
    "属性.",
    "値.",
)
_R_CONTROL_CONDITION_KINDS = frozenset({"条件.検索極性"})
_BLOCKING = {値状態.未確定, 値状態.未観測, 値状態.矛盾, 値状態.留保}
_K_QUALIFIER_SCOPE_KEYS = frozenset({"様相", "量化", "条件scope", "scope", "条件作用"})
_CANDIDATE_ASSERTION_PREFIXES = (
    "状態.", "条件.", "動態.", "不確実性.", "前提.", "射程.", "論証.",
)


def _条件値(relation: HDS関係, key: str) -> str:
    prefix = key + "="
    for raw in relation.条件:
        value = str(raw)
        if value.startswith(prefix):
            return value[len(prefix):].strip()
    return ""


def _座標重複除去(*groups: tuple[HDS座標, ...]) -> tuple[HDS座標, ...]:
    out: list[HDS座標] = []
    seen: set[str] = set()
    for group in groups:
        for coord in group:
            cid = str(coord.座標ID)
            if cid in seen:
                continue
            seen.add(cid)
            out.append(coord)
    return tuple(out)


def _文字列重複除去(values: tuple[str, ...]) -> tuple[str, ...]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in values:
        value = " ".join(str(raw).split()).strip()
        if not value:
            continue
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(value)
    return tuple(out)


def _R利用座標(coord: HDS座標) -> bool:
    return str(coord.種別) not in _R_CONTROL_CONDITION_KINDS


def _R検索表層(coords: tuple[HDS座標, ...], relations: tuple[HDS関係, ...] = ()) -> str:
    search = tuple(str(coord.内容) for coord in coords if str(coord.種別).startswith("検索."))
    predicates = tuple(_条件値(relation, "検索述語") for relation in relations)
    known_endpoints = tuple(
        str(coord.内容)
        for coord in coords
        if str(coord.種別).startswith(("対象.", "実体.", "状態.", "属性.", "値."))
        and coord.値状態 not in _BLOCKING
    )
    context = tuple(
        str(coord.内容)
        for coord in coords
        if str(coord.種別).startswith(("条件.", "時刻.", "時間.", "範囲."))
        and _R利用座標(coord)
        and coord.値状態 not in {値状態.矛盾, 値状態.留保}
    )
    return " ".join(_文字列重複除去((*search, *predicates, *known_endpoints, *context)))


def _K意味座標(coord: HDS座標) -> bool:
    kind = str(coord.種別)
    if kind in _K_EXCLUDED_KINDS:
        return False
    return kind.startswith(_K_SEMANTIC_PREFIXES)


def _候補は命題(ir: HDSIR) -> bool:
    if ir.関係:
        return True
    for coord in ir.座標:
        kind = str(coord.種別)
        if kind == "関係.述語" or kind.startswith(_CANDIDATE_ASSERTION_PREFIXES):
            return True
    return False


def _質問関係(ir: HDSIR) -> tuple[HDS関係, ...]:
    canonical = tuple(
        relation
        for relation in ir.関係
        if _条件値(relation, "英日意味射影")
        and _条件値(relation, "不足位置") in {"始点", "終点"}
    )
    if canonical:
        return canonical
    return tuple(
        relation
        for relation in ir.関係
        if _条件値(relation, "不足位置") in {"始点", "終点"}
    )


def _関係座標ID(relations: tuple[HDS関係, ...]) -> set[str]:
    ids: set[str] = set()
    for relation in relations:
        ids.update(relation.始点)
        ids.update(relation.終点)
    return ids


def _関係を座標へ閉じる(relations: tuple[HDS関係, ...], coordinate_ids: set[str]) -> tuple[HDS関係, ...]:
    return tuple(
        relation
        for relation in relations
        if (*relation.始点, *relation.終点)
        and all(cid in coordinate_ids for cid in (*relation.始点, *relation.終点))
    )


def _K未対応scope(
    relation: HDS関係,
    *,
    否定可: bool = False,
    修飾可: bool = False,
) -> bool:
    """K経路が損失なく保持できないscopeだけを辺から除外する。

    - Data否定はFact.polarityへ保持できる。
    - Dataの様相/条件/量化等はv0.18のHDS修飾Factへ保持できる。
    - 質問/候補はJの選択意味との接続があるため、現段階では従来どおり強いK関係へ通さない。
    """
    for raw in relation.条件:
        value = str(raw)
        key, sep, payload = value.partition("=")
        if not sep:
            continue
        key = key.strip()
        payload = payload.strip()
        if key == "極性" and payload:
            if payload == "肯定":
                continue
            if payload == "否定" and 否定可:
                continue
            return True
        if key in _K_QUALIFIER_SCOPE_KEYS and payload:
            if 修飾可:
                continue
            return True
    return False


def _K関係射影(
    ir: HDSIR,
    coords: tuple[HDS座標, ...],
    *,
    否定可: bool = False,
    修飾可: bool = False,
) -> tuple[HDS関係, ...]:
    closed = _関係を座標へ閉じる(ir.関係, {coord.座標ID for coord in coords})
    return tuple(
        relation
        for relation in closed
        if not _K未対応scope(relation, 否定可=否定可, 修飾可=修飾可)
    )


def HDSR質問射影(ir: HDSIR) -> HDSIR:
    """質問HDS-IRからRが検索query生成に必要な最小構造だけを返す。"""
    choices = tuple(coord for coord in ir.座標 if coord.座標ID.startswith("choice:"))
    question_relations = _質問関係(ir)
    coords_by_id = ir.座標辞書()
    context = tuple(
        coord
        for coord in ir.座標
        if str(coord.種別).startswith(_R_CONTEXT_PREFIXES)
        and _R利用座標(coord)
        and coord.値状態 not in {値状態.矛盾, 値状態.留保}
        and str(coord.内容).strip()
    )

    if question_relations:
        endpoint_ids = _関係座標ID(question_relations)
        endpoints = tuple(coords_by_id[cid] for cid in endpoint_ids if cid in coords_by_id)
        projected_coords = _座標重複除去(choices, endpoints, context)
        surface = _R検索表層(projected_coords, question_relations)
        return replace(ir, 原文=surface, 正規化文=surface, 座標=projected_coords, 関係=question_relations, 意味作用履歴=())

    search_focus = tuple(coord for coord in context if str(coord.種別).startswith("検索."))
    if search_focus:
        projected_coords = _座標重複除去(choices, search_focus)
        surface = _R検索表層(projected_coords)
        return replace(ir, 原文=surface, 正規化文=surface, 座標=projected_coords, 関係=(), 意味作用履歴=())

    fallback = tuple(
        coord
        for coord in ir.座標
        if str(coord.種別).startswith((*_R_FALLBACK_SEMANTIC_PREFIXES, *_R_CONTEXT_PREFIXES))
        and _R利用座標(coord)
        and coord.値状態 not in _BLOCKING
        and str(coord.内容).strip()
    )
    relations = _関係を座標へ閉じる(ir.関係, {coord.座標ID for coord in fallback})
    projected_coords = _座標重複除去(choices, fallback)
    surface = _R検索表層(projected_coords, relations)
    return replace(ir, 原文=surface, 正規化文=surface, 座標=projected_coords, 関係=relations, 意味作用履歴=())


def HDSK質問射影(ir: HDSIR) -> HDSIR:
    """質問HDS-IRからC/Kの候補比較に必要な最小意味核だけを返す。"""
    choices = tuple(coord for coord in ir.座標 if coord.座標ID.startswith("choice:"))
    question_relations = _質問関係(ir)
    coords_by_id = ir.座標辞書()

    if question_relations:
        endpoint_ids = _関係座標ID(question_relations)
        endpoints = tuple(coords_by_id[cid] for cid in endpoint_ids if cid in coords_by_id)
        projected_relations = tuple(
            replace(
                relation,
                値状態=値状態.確定,
                由来="HDS Runtime K質問射影",
                暫定性="RELATION_TYPE_KNOWN_ENDPOINT_OPEN",
            )
            for relation in question_relations
            if not _K未対応scope(relation)
        )
        return replace(ir, 座標=_座標重複除去(choices, endpoints), 関係=projected_relations, 意味作用履歴=())

    topic = tuple(
        coord
        for coord in ir.座標
        if str(coord.種別) == "対象.主題語"
        and coord.値状態 not in _BLOCKING
        and str(coord.内容).strip()
    )
    if topic:
        return replace(ir, 座標=_座標重複除去(choices, topic), 関係=(), 意味作用履歴=())

    semantic_coords = tuple(coord for coord in ir.座標 if _K意味座標(coord))
    semantic_relations = _K関係射影(ir, semantic_coords)
    return replace(ir, 座標=_座標重複除去(choices, semantic_coords), 関係=semantic_relations, 意味作用履歴=())


def HDSK候補射影(ir: HDSIR) -> HDSIR:
    """候補IRから候補識別とKが表現可能な明示命題だけを残す。"""
    semantic_coords = tuple(coord for coord in ir.座標 if _K意味座標(coord))
    semantic_relations = _K関係射影(ir, semantic_coords)
    return replace(ir, 座標=semantic_coords, 関係=semantic_relations, 意味作用履歴=())


def HDSK候補代入可能(ir: HDSIR) -> bool:
    """完全候補IRが未知端点へ代入する実体句として扱える時だけTrue。"""
    if _候補は命題(ir):
        return False
    return any(
        str(coord.種別).startswith(("対象.", "実体."))
        and coord.値状態 not in _BLOCKING
        and str(coord.内容).strip()
        for coord in ir.座標
    )


def HDSKData射影(ir: HDSIR) -> HDSIR:
    """R取得DataからKへ投入してよい世界事実意味だけを残す。

    - 明示否定はFact.polarityへ写せるため保持する。
    - 様相/条件/量化等はHDS修飾Factへ写せるため関係自体を保持する。
    - 修飾付き関係はcanonical無条件Kへは入らず、HDS証拠台帳へだけ保存される。
    """
    semantic_coords = tuple(coord for coord in ir.座標 if _K意味座標(coord))
    semantic_relations = _K関係射影(ir, semantic_coords, 否定可=True, 修飾可=True)
    return replace(ir, 座標=semantic_coords, 関係=semantic_relations, 意味作用履歴=())


__all__ = ["HDSR質問射影", "HDSK質問射影", "HDSK候補射影", "HDSK候補代入可能", "HDSKData射影"]
