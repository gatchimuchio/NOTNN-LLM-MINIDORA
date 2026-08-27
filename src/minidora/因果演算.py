from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .言語構造 import 言語関係構造
from .模型 import MINIDORA模型核, 関係寄与, 標準模型核


因果演算版 = "v1-signed-causal-composition"
因果演算作用名 = "参照関係寄与:因果演算"

# ここでの数値は候補採点用の序数ではない。
# 一つの関係が次状態へ与える作用方向を +1 / -1 として保持し、
# 同一路内の因果連鎖だけを乗算して次状態を形成する。
# 複数経路は票数にしない。同符号なら同じ ±1、正負が競合すれば未確定 0 とする。
_正作用 = frozenset({"因果", "増加", "活性化", "生成"})
_負作用 = frozenset({"減少", "阻害", "防止"})


def _述語関係種別(relation: 言語関係構造) -> frozenset[str]:
    return frozenset(
        token.split(":", 1)[1]
        for token in relation.述語
        if token.startswith("rel:") and ":" in token
    )


def 因果符号(relation: 言語関係構造) -> int | None:
    """関係を因果作用の符号へ写す。

    否定文は「逆作用」を意味しないため伝播させない。
    例: `A does not cause B` を `A inhibits B` へ読み替えない。
    """

    if not relation.肯定:
        return None
    kinds = {relation.種別, *_述語関係種別(relation)}
    signs = set()
    if kinds.intersection(_正作用):
        signs.add(1)
    if kinds.intersection(_負作用):
        signs.add(-1)
    if len(signs) != 1:
        return None
    return signs.pop()


def _端点接続(a: frozenset[str], b: frozenset[str]) -> bool:
    if not a or not b:
        return False
    overlap = len(a.intersection(b))
    return overlap / max(1, min(len(a), len(b))) >= 0.75


def _条件キー(conditions: tuple[frozenset[str], ...]) -> tuple[tuple[str, ...], ...]:
    return tuple(sorted(tuple(sorted(item)) for item in conditions))


def _条件合成(
    a: tuple[frozenset[str], ...],
    b: tuple[frozenset[str], ...],
) -> tuple[frozenset[str], ...] | None:
    if not a:
        return b
    if not b:
        return a
    if _条件キー(a) != _条件キー(b):
        return None
    return a


def _node_key(node: frozenset[str]) -> tuple[str, ...]:
    return tuple(sorted(node))


@dataclass(frozen=True, slots=True)
class 因果辺:
    辺ID: str
    出典ID: str
    始点: frozenset[str]
    終点: frozenset[str]
    作用値: int
    種別: str
    条件: tuple[frozenset[str], ...]


@dataclass(frozen=True, slots=True)
class 因果経路:
    始点: frozenset[str]
    終点: frozenset[str]
    作用値: int
    深さ: int
    辺ID列: tuple[str, ...]
    出典ID列: tuple[str, ...]
    種別列: tuple[str, ...]
    条件: tuple[frozenset[str], ...]
    訪問節点: tuple[tuple[str, ...], ...]


@dataclass(frozen=True, slots=True)
class 因果導出:
    始点: frozenset[str]
    終点: frozenset[str]
    値: int
    正経路数: int
    負経路数: int
    最小深さ: int
    最大深さ: int
    条件: tuple[frozenset[str], ...]
    根拠出典ID: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class 因果演算結果:
    基礎辺数: int
    経路数: int
    導出数: int
    最大到達深さ: int
    打切り: bool
    導出群: tuple[因果導出, ...]


def 因果関係演算(
    関係束: Sequence[tuple[str, Sequence[言語関係構造]]],
    *,
    最大深さ: int = 4,
    最大経路数: int = 4096,
) -> 因果演算結果:
    """参照関係を有界因果演算し、深さ2以上の新しい関係状態を形成する。"""

    depth_limit = max(1, int(最大深さ))
    path_limit = max(1, int(最大経路数))
    edges: list[因果辺] = []
    seen_edges: set[tuple[str, tuple[object, ...]]] = set()
    for source_index, (source_id, relations) in enumerate(関係束):
        sid = str(source_id).strip() or f"source:{source_index}"
        for relation_index, relation in enumerate(relations):
            sign = 因果符号(relation)
            if sign is None or not relation.始点 or not relation.終点:
                continue
            edge_signature = (sid, relation.署名)
            if edge_signature in seen_edges:
                continue
            seen_edges.add(edge_signature)
            edges.append(
                因果辺(
                    f"{sid}#{relation_index}",
                    sid,
                    relation.始点,
                    relation.終点,
                    sign,
                    relation.種別,
                    relation.条件,
                )
            )

    frontier: list[因果経路] = []
    all_paths: list[因果経路] = []
    for edge in edges:
        path = 因果経路(
            edge.始点,
            edge.終点,
            edge.作用値,
            1,
            (edge.辺ID,),
            (edge.出典ID,),
            (edge.種別,),
            edge.条件,
            (_node_key(edge.始点), _node_key(edge.終点)),
        )
        frontier.append(path)
        all_paths.append(path)

    truncated = False
    while frontier:
        current = frontier.pop(0)
        if current.深さ >= depth_limit:
            continue
        for edge in edges:
            if edge.辺ID in current.辺ID列:
                continue
            if not _端点接続(current.終点, edge.始点):
                continue
            end_key = _node_key(edge.終点)
            if end_key in current.訪問節点:
                continue
            conditions = _条件合成(current.条件, edge.条件)
            if conditions is None:
                continue
            composed = 因果経路(
                current.始点,
                edge.終点,
                current.作用値 * edge.作用値,
                current.深さ + 1,
                (*current.辺ID列, edge.辺ID),
                (*current.出典ID列, edge.出典ID),
                (*current.種別列, edge.種別),
                conditions,
                (*current.訪問節点, end_key),
            )
            all_paths.append(composed)
            frontier.append(composed)
            if len(all_paths) >= path_limit:
                truncated = True
                frontier.clear()
                break

    grouped: dict[
        tuple[tuple[str, ...], tuple[str, ...], tuple[tuple[str, ...], ...]],
        list[因果経路],
    ] = {}
    for path in all_paths:
        if path.深さ < 2:
            continue
        key = (_node_key(path.始点), _node_key(path.終点), _条件キー(path.条件))
        grouped.setdefault(key, []).append(path)

    derived: list[因果導出] = []
    for paths in grouped.values():
        first = paths[0]
        positive = sum(1 for item in paths if item.作用値 > 0)
        negative = sum(1 for item in paths if item.作用値 < 0)
        if positive and negative:
            value = 0
        elif positive:
            value = 1
        elif negative:
            value = -1
        else:
            value = 0
        sources = tuple(dict.fromkeys(source for item in paths for source in item.出典ID列))
        derived.append(
            因果導出(
                first.始点,
                first.終点,
                value,
                positive,
                negative,
                min(item.深さ for item in paths),
                max(item.深さ for item in paths),
                first.条件,
                sources,
            )
        )

    derived.sort(
        key=lambda item: (
            _node_key(item.始点),
            _node_key(item.終点),
            _条件キー(item.条件),
            item.値,
        )
    )
    return 因果演算結果(
        len(edges),
        len(all_paths),
        len(derived),
        max((path.深さ for path in all_paths), default=0),
        truncated,
        tuple(derived),
    )


def 候補因果差(
    候補関係群: Sequence[言語関係構造],
    演算結果: 因果演算結果,
) -> tuple[int, tuple[str, ...]]:
    """導出済み因果状態と候補仮説を照合する。

    ここで初めて候補差へ戻す。因果演算それ自体は候補採点とは独立して完了している。
    """

    total = 0
    evidence: list[str] = []
    seen: set[tuple[object, ...]] = set()
    for relation in 候補関係群:
        if relation.署名 in seen:
            continue
        seen.add(relation.署名)
        sign = 因果符号(relation)
        if sign is None:
            continue
        for derived in 演算結果.導出群:
            if derived.値 == 0:
                continue
            if not _端点接続(relation.始点, derived.始点):
                continue
            if not _端点接続(relation.終点, derived.終点):
                continue
            if _条件キー(relation.条件) != _条件キー(derived.条件):
                continue
            derived_sign = 1 if derived.値 > 0 else -1
            delta = 1 if sign == derived_sign else -1
            total += delta
            evidence.append(
                "因果導出:"
                f"{derived.最小深さ}-{derived.最大深さ}:"
                f"{derived.値}:"
                f"正{derived.正経路数}:負{derived.負経路数}:"
                f"{','.join(derived.根拠出典ID)}"
            )
    return total, tuple(evidence)


@dataclass(frozen=True, slots=True)
class 因果演算作用:
    """MINIDORA模型核へ因果演算結果を候補差として再投入する作用。"""

    名称: str = 因果演算作用名
    最大深さ: int = 4
    最大経路数: int = 4096

    def 演算(self, 文脈) -> 因果演算結果:
        bundle = tuple(
            (
                state.識別子 or f"reference:{index}",
                state.関係構造,
            )
            for index, state in enumerate(文脈.参照状態)
        )
        return 因果関係演算(bundle, 最大深さ=self.最大深さ, 最大経路数=self.最大経路数)

    def 評価群(self, 文脈, 候補群):
        result = self.演算(文脈)
        reverse = any(str(item).casefold() == "選択意図=反転" for item in 文脈.条件)
        out = {}
        for cid, state in 候補群:
            delta, evidence = 候補因果差(state.関係構造, result)
            if reverse:
                delta = -delta
            if not delta:
                continue
            out[cid] = 関係寄与(
                self.名称,
                delta,
                (
                    f"因果基礎辺:{result.基礎辺数}",
                    f"因果経路:{result.経路数}",
                    f"因果導出:{result.導出数}",
                    f"因果最大深さ:{result.最大到達深さ}",
                    f"因果打切り:{int(result.打切り)}",
                    *evidence,
                ),
            )
        return out


def 因果演算模型核(core: MINIDORA模型核 | None = None) -> MINIDORA模型核:
    """既存模型核を壊さず、因果演算作用を一度だけ追加した模型核を返す。"""

    base = core or 標準模型核()
    if any(getattr(action, "名称", "") == 因果演算作用名 for action in base.能力作用群):
        return base
    return MINIDORA模型核(
        base.関係群,
        言語対応_=base.言語対応,
        能力作用群=(*base.能力作用群, 因果演算作用()),
        形成済み関係群=base.形成済み関係群,
        最大再作用回数=base.最大再作用回数,
    )


__all__ = [
    "因果演算版",
    "因果演算作用名",
    "因果符号",
    "因果辺",
    "因果経路",
    "因果導出",
    "因果演算結果",
    "因果関係演算",
    "候補因果差",
    "因果演算作用",
    "因果演算模型核",
]
