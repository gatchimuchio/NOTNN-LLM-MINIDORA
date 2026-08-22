from __future__ import annotations

from dataclasses import replace
import re

from .hds_compiler_records_v1_1 import HDS状態ノード, HDS状態遷移図, HDS遷移辺
from .hds_ir import HDSIR, HDS座標, HDS関係, HDS残差, 値状態


_状態語 = r"[A-Za-z0-9_一-龥々ぁ-んァ-ヶー.+\-]{1,48}"
_JA_FROM_TO = re.compile(
    rf"(?P<src>{_状態語})から[、,\s]*(?:(?P<cond>[^。！？、,]{{1,80}}?)(?:ならば|なら|の場合)[、,\s]*)?(?P<dst>{_状態語})(?:へ|に)(?:遷移|移行|変化|変わる|移る)"
)
_JA_COND_TO = re.compile(
    rf"(?P<cond>[^。！？、]{{1,80}}?)(?:ならば|なら|の場合)[、,\s]*(?P<dst>{_状態語})(?:へ|に)(?:遷移|移行|変化|変わる|移る)"
)
_EN_FROM_TO = re.compile(
    r"(?:transition|move|change|switch|go|shift)(?:s|ed|ing)?\s+from\s+(?P<src>[A-Za-z0-9_.+\-]{1,48})\s+to\s+(?P<dst>[A-Za-z0-9_.+\-]{1,48})",
    re.I,
)
_EN_COND_TO = re.compile(
    r"(?:if|when|unless)\s+(?P<cond>[^,.;!?]{1,100})[, ]+(?:then\s+)?(?:transition|move|change|switch|go|shift)(?:s|ed|ing)?\s+to\s+(?P<dst>[A-Za-z0-9_.+\-]{1,48})",
    re.I,
)
_JA_ROLLBACK = re.compile(
    rf"(?:失敗時|エラー時|異常時)?[^。！？]{{0,30}}?(?:rollback|ロールバック|切り戻し?)(?:して|し|で)?\s*(?P<dst>{_状態語})(?:へ|に)(?:戻す|戻る|切り戻す|復帰する)"
)
_EN_ROLLBACK = re.compile(r"(?:rollback|roll back|revert|undo)(?:\s+to)\s+(?P<dst>[A-Za-z0-9_.+\-]{1,48})", re.I)
_状態役割prefix = ("初期状態", "開始状態", "次状態", "終了状態", "状態")


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split()).strip(" ,、:;。！？?!")
    return text or None


def _state_name(value: str | None) -> str | None:
    text = _clean(value)
    if text is None:
        return None
    for prefix in _状態役割prefix:
        if text.startswith(prefix) and len(text) > len(prefix):
            candidate = text[len(prefix):].strip(" :=：")
            if candidate:
                return candidate
    return text


def _append_edge(
    edges: list[HDS遷移辺],
    nodes: dict[str, HDS状態ノード],
    *,
    src: str | None,
    dst: str | None,
    cond: tuple[str, ...] = (),
    action: tuple[str, ...] = (),
    reversible: bool | None = None,
    rollback: str | None = None,
) -> None:
    src = _state_name(src)
    dst = _state_name(dst)
    rollback = _state_name(rollback)
    for value in (src, dst, rollback):
        if value and value not in nodes:
            nodes[value] = HDS状態ノード(f"state:{len(nodes):03d}", value)

    condition_values = tuple(dict.fromkeys(value for raw in cond if (value := _clean(raw))))
    action_values = tuple(dict.fromkeys(value for raw in action if (value := _clean(raw))))
    signature = (src, dst, condition_values, action_values, reversible, rollback)
    if any((edge.始点, edge.終点, edge.条件, edge.作用, edge.可逆, edge.rollback先) == signature for edge in edges):
        return
    edges.append(
        HDS遷移辺(
            f"transition:{len(edges):03d}",
            src,
            dst,
            condition_values,
            action_values,
            reversible,
            rollback,
        )
    )


def HDS状態遷移抽出(text: str) -> HDS状態遷移図:
    source = " ".join(str(text).split()).strip()
    nodes: dict[str, HDS状態ノード] = {}
    edges: list[HDS遷移辺] = []
    unresolved: list[str] = []

    for match in _JA_FROM_TO.finditer(source):
        condition = (match.group("cond"),) if match.group("cond") else ()
        _append_edge(edges, nodes, src=match.group("src"), dst=match.group("dst"), cond=condition, action=("遷移",))

    for match in _EN_FROM_TO.finditer(source):
        _append_edge(edges, nodes, src=match.group("src"), dst=match.group("dst"), action=("transition",))

    for match in _JA_COND_TO.finditer(source):
        dst = _state_name(match.group("dst"))
        if not any(edge.終点 == dst and edge.条件 for edge in edges):
            _append_edge(edges, nodes, src=None, dst=dst, cond=(match.group("cond"),), action=("条件遷移",))

    for match in _EN_COND_TO.finditer(source):
        dst = _state_name(match.group("dst"))
        if not any(edge.終点 == dst and edge.条件 for edge in edges):
            _append_edge(edges, nodes, src=None, dst=dst, cond=(match.group("cond"),), action=("conditional transition",))

    for match in _JA_ROLLBACK.finditer(source):
        rollback = _state_name(match.group("dst"))
        _append_edge(edges, nodes, src=None, dst=rollback, cond=("失敗または撤回条件",), action=("rollback",), reversible=True, rollback=rollback)

    for match in _EN_ROLLBACK.finditer(source):
        rollback = _state_name(match.group("dst"))
        _append_edge(edges, nodes, src=None, dst=rollback, cond=("failure or withdrawal condition",), action=("rollback",), reversible=True, rollback=rollback)

    for edge in edges:
        if edge.始点 is None:
            unresolved.append(f"{edge.遷移ID}:始点未観測")
        if edge.終点 is None:
            unresolved.append(f"{edge.遷移ID}:終点未観測")

    return HDS状態遷移図(tuple(nodes.values()), tuple(edges), tuple(unresolved))


def HDS状態遷移IR射影(ir: HDSIR, graph: HDS状態遷移図) -> HDSIR:
    if not graph.ノード and not graph.遷移:
        return ir

    coords = list(ir.座標)
    relations = list(ir.関係)
    residuals = list(ir.残差)
    coord_map: dict[str, str] = {}
    existing = {(str(coord.種別), str(coord.内容)): coord.座標ID for coord in coords}

    for node in graph.ノード:
        key = ("動態.状態", node.名称)
        cid = existing.get(key)
        if cid is None:
            cid = f"archv11:state:{len(coord_map):03d}"
            coords.append(HDS座標(cid, "動態.状態", node.名称, 値状態.確定, 由来="公開HDS Compiler v1.1"))
            existing[key] = cid
        coord_map[node.名称] = cid

    for edge in graph.遷移:
        if edge.始点 and edge.終点:
            sid = coord_map.get(edge.始点)
            oid = coord_map.get(edge.終点)
            if sid and oid:
                conditions = [*edge.条件, *(f"作用={value}" for value in edge.作用)]
                if edge.rollback先:
                    conditions.append(f"rollback={edge.rollback先}")
                relations.append(
                    HDS関係(
                        f"archv11:{edge.遷移ID}",
                        (sid,),
                        (oid,),
                        "状態遷移",
                        条件=tuple(conditions),
                        値状態=値状態.確定,
                        由来="公開HDS Compiler v1.1",
                    )
                )
        else:
            residuals.append(
                HDS残差(
                    f"archv11:residual:{edge.遷移ID}",
                    "未閉包状態遷移",
                    f"{edge.始点 or '?'} -> {edge.終点 or '?'}",
                    "状態遷移の端点が入力から一意に固定できない",
                    解消条件=("Rまたは追加文脈で遷移端点を固定する",),
                )
            )

    return replace(ir, 座標=tuple(coords), 関係=tuple(dict.fromkeys(relations)), 残差=tuple(residuals))


__all__ = ["HDS状態遷移抽出", "HDS状態遷移IR射影"]
