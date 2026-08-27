from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .模型 import (
    MINIDORA模型核,
    内部言語状態,
    文脈付き言語状態,
    言語状態,
    関係寄与,
    標準模型核,
)
from .関係連鎖演算 import (
    関係連鎖作用名 as 旧関係連鎖作用名,
    関係連鎖状態,
    関係連鎖結果,
    _辺生成,
    _条件合成,
    _条件適合,
    _条件キー,
    _端点キー,
    _問い専用関係,
    _問い関係群,
    _候補関係が問いに対応,
)


関係連鎖演算版V2 = "v2-identity-separated-reasoning-state"
関係連鎖推論作用名 = "推論関係寄与:関係連鎖"


@dataclass(frozen=True, slots=True)
class 推論文脈付き言語状態(文脈付き言語状態):
    """通常文脈と分離して、再作用だけが読む推論用の中間状態を保持する。

    継承元の ``意味語集合`` はこの欄を参照しない。したがって、一般関係・履歴近接・
    参照寄与へ推論前提を無言混入させず、関係連鎖作用だけが明示的に読む。
    """

    推論状態: tuple[内部言語状態, ...] = ()


def 推論文脈形成(
    core: MINIDORA模型核,
    現在: 言語状態,
    *,
    推論状態: Sequence[言語状態] = (),
    履歴: Sequence[言語状態] = (),
    条件: Sequence[str] = (),
    参照状態: Sequence[言語状態] = (),
) -> 推論文脈付き言語状態:
    """既存模型文脈を変えず、推論専用状態だけを別欄へ付与する。"""

    base = core.文脈化(現在, 履歴=履歴, 条件=条件, 参照状態=参照状態)
    reasoning_internal = []
    for state in 推論状態:
        if state.言語体系 != 現在.言語体系:
            raise ValueError("推論状態と言語文脈の言語体系が一致しない")
        reasoning_internal.append(core.言語対応.内部化(state))
    return 推論文脈付き言語状態(
        base.現在,
        base.履歴,
        base.条件,
        base.参照状態,
        tuple(reasoning_internal),
    )


def _端点同一(left: frozenset[str], right: frozenset[str]) -> bool:
    """関係連鎖に必要な対称的意味同一性を判定する。

    v1の ``overlap / min(len(left), len(right))`` は、1語の端点が長い句へ含まれるだけで
    同一とみなせた。v2では双方の情報量を基準にし、片側包含だけでは接続しない。
    """

    if not left or not right:
        return False
    overlap = len(left.intersection(right))
    return overlap / max(len(left), len(right)) >= 0.75


def 関係連鎖演算V2(
    関係束,
    *,
    最大深さ: int = 4,
    最大状態数: int = 4096,
) -> 関係連鎖結果:
    """意味同一性を保持した端点だけを接続して、多段の関係列状態を形成する。"""

    depth_limit = max(1, int(最大深さ))
    state_limit = max(1, int(最大状態数))
    edges = _辺生成(関係束)

    frontier: list[関係連鎖状態] = []
    all_states: list[関係連鎖状態] = []
    seen_states: set[tuple[object, ...]] = set()

    for edge in edges:
        state = 関係連鎖状態(
            edge.始点,
            edge.終点,
            (edge.数値,),
            (edge.種別,),
            1,
            (edge.出典ID,),
            (edge.辺ID,),
            edge.条件,
            (_端点キー(edge.始点), _端点キー(edge.終点)),
        )
        frontier.append(state)
        all_states.append(state)

    truncated = False
    while frontier:
        current = frontier.pop(0)
        if current.深さ >= depth_limit:
            continue
        for edge in edges:
            if edge.辺ID in current.辺ID列:
                continue
            if not _端点同一(current.終点, edge.始点):
                continue
            endpoint_key = _端点キー(edge.終点)
            if endpoint_key in current.訪問節点:
                continue
            conditions = _条件合成(current.条件, edge.条件)
            if conditions is None:
                continue
            chained = 関係連鎖状態(
                current.始点,
                edge.終点,
                (*current.数値列, edge.数値),
                (*current.種別列, edge.種別),
                current.深さ + 1,
                (*current.出典ID列, edge.出典ID),
                (*current.辺ID列, edge.辺ID),
                conditions,
                (*current.訪問節点, endpoint_key),
            )
            signature = (
                _端点キー(chained.始点),
                _端点キー(chained.終点),
                chained.数値署名,
                _条件キー(chained.条件),
            )
            if signature in seen_states:
                continue
            seen_states.add(signature)
            all_states.append(chained)
            frontier.append(chained)
            if len(all_states) >= state_limit:
                truncated = True
                frontier.clear()
                break

    multi = tuple(state for state in all_states if state.深さ >= 2)
    return 関係連鎖結果(
        len(edges),
        len(multi),
        max((state.深さ for state in all_states), default=0),
        truncated,
        multi,
    )


def _候補目標群V2(
    文脈,
    候補状態,
) -> tuple[tuple[frozenset[str], frozenset[str], tuple[frozenset[str], ...]], ...]:
    targets: list[tuple[frozenset[str], frozenset[str], tuple[frozenset[str], ...]]] = []
    seen: set[tuple[object, ...]] = set()
    questions = _問い関係群(文脈)

    for question in questions:
        for relation in 候補状態.関係構造:
            if not _候補関係が問いに対応(question, relation):
                continue
            if question.始点 and not question.終点:
                if _端点同一(question.始点, relation.始点) and relation.終点:
                    target = (question.始点, relation.終点, relation.条件)
                else:
                    continue
            elif question.終点 and not question.始点:
                if _端点同一(question.終点, relation.終点) and relation.始点:
                    target = (relation.始点, question.終点, relation.条件)
                else:
                    continue
            elif relation.始点 and relation.終点:
                target = (relation.始点, relation.終点, relation.条件)
            else:
                continue
            signature = (_端点キー(target[0]), _端点キー(target[1]), _条件キー(target[2]))
            if signature not in seen:
                seen.add(signature)
                targets.append(target)

    if targets:
        return tuple(targets)

    for relation in 候補状態.関係構造:
        if relation.種別 in _問い専用関係 or not relation.始点 or not relation.終点:
            continue
        target = (relation.始点, relation.終点, relation.条件)
        signature = (_端点キー(target[0]), _端点キー(target[1]), _条件キー(target[2]))
        if signature not in seen:
            seen.add(signature)
            targets.append(target)
    return tuple(targets)


def 候補連鎖支持V2(
    文脈,
    候補状態,
    演算結果: 関係連鎖結果,
) -> tuple[bool, tuple[str, ...]]:
    evidence: list[str] = []
    for start, end, conditions in _候補目標群V2(文脈, 候補状態):
        for state in 演算結果.状態群:
            if not _端点同一(start, state.始点) or not _端点同一(end, state.終点):
                continue
            if not _条件適合(conditions, state.条件):
                continue
            evidence.append(
                "関係連鎖V2:"
                f"深さ{state.深さ}:"
                f"数値={','.join(f'{item.関係ID}/{item.方向}/{item.極性}' for item in state.数値列)}:"
                f"種別={'>'.join(state.種別列)}:"
                f"出典={','.join(dict.fromkeys(state.出典ID列))}"
            )
    return bool(evidence), tuple(evidence)


@dataclass(frozen=True, slots=True)
class 関係連鎖作用V2:
    """推論専用状態と参照Dataから関係列を作り、一意な内部候補差だけを返す。

    この差は推論状態であり、参照証拠ではない。したがって ``参照最有力候補`` を単独で
    確定する権限を持たず、候補順序・再作用へだけ作用する。
    """

    名称: str = 関係連鎖推論作用名
    最大深さ: int = 4
    最大状態数: int = 4096

    def 演算(self, 文脈) -> 関係連鎖結果:
        reasoning_states = tuple(getattr(文脈, "推論状態", ()))
        reasoning_bundle = tuple(
            (
                state.識別子 or f"reasoning:{index}",
                state.関係構造,
            )
            for index, state in enumerate(reasoning_states)
        )
        reference_bundle = tuple(
            (
                state.識別子 or f"reference:{index}",
                state.関係構造,
            )
            for index, state in enumerate(文脈.参照状態)
        )
        return 関係連鎖演算V2(
            (*reasoning_bundle, *reference_bundle),
            最大深さ=self.最大深さ,
            最大状態数=self.最大状態数,
        )

    def 評価群(self, 文脈, 候補群):
        if any(str(item).casefold() == "選択意図=反転" for item in 文脈.条件):
            return {}

        result = self.演算(文脈)
        supported: dict[str, tuple[str, ...]] = {}
        for cid, state in 候補群:
            ok, evidence = 候補連鎖支持V2(文脈, state, result)
            if ok:
                supported[cid] = evidence

        # 「到達した」という共通状態は候補差ではない。差が一候補へ一意に形成された時だけ返す。
        if len(supported) != 1:
            return {}

        cid, evidence = next(iter(supported.items()))
        return {
            cid: 関係寄与(
                self.名称,
                1,
                (
                    f"連鎖V2基礎辺:{result.基礎辺数}",
                    f"連鎖V2多段状態:{result.多段状態数}",
                    f"連鎖V2最大深さ:{result.最大到達深さ}",
                    f"連鎖V2打切り:{int(result.打切り)}",
                    *evidence,
                ),
            )
        }


def 関係連鎖模型核V2(core: MINIDORA模型核 | None = None) -> MINIDORA模型核:
    """旧連鎖作用を除去し、推論権限だけを持つv2作用を一つだけ登録する。"""

    base = core or 標準模型核()
    chain_names = {旧関係連鎖作用名, 関係連鎖推論作用名}
    actions = tuple(
        action
        for action in base.能力作用群
        if getattr(action, "名称", "") not in chain_names
    )
    return MINIDORA模型核(
        base.関係群,
        言語対応_=base.言語対応,
        能力作用群=(*actions, 関係連鎖作用V2()),
        形成済み関係群=base.形成済み関係群,
        最大再作用回数=base.最大再作用回数,
    )


__all__ = [
    "関係連鎖演算版V2",
    "関係連鎖推論作用名",
    "推論文脈付き言語状態",
    "推論文脈形成",
    "関係連鎖演算V2",
    "候補連鎖支持V2",
    "関係連鎖作用V2",
    "関係連鎖模型核V2",
]
