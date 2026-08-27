from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Sequence

from .言語構造 import 言語関係構造
from .模型 import MINIDORA模型核, 関係寄与, 標準模型核


関係連鎖演算版 = "v1-associative-relation-chain"
関係連鎖作用名 = "参照関係寄与:関係連鎖"

# 固定番号は意味の大小ではなく、関係族を数値状態へ写す安定IDである。
_関係番号 = {
    "因果": 1,
    "増加": 2,
    "減少": 3,
    "阻害": 4,
    "活性化": 5,
    "生成": 6,
    "要求": 7,
    "包含": 8,
    "使用": 9,
    "防止": 10,
    "相関": 11,
    "結合": 12,
    "相互作用": 13,
    "構成": 14,
    "所属": 15,
    "位置": 16,
    "由来": 17,
}
_対称関係 = frozenset({"相関", "結合", "相互作用"})
_問い専用関係 = frozenset({"命題適合", "説明適合", "問い適合", "同定", "数量同定"})


def _端点キー(values: frozenset[str]) -> tuple[str, ...]:
    return tuple(sorted(values))


def _条件キー(conditions: tuple[frozenset[str], ...]) -> tuple[tuple[str, ...], ...]:
    return tuple(sorted(tuple(sorted(item)) for item in conditions))


def _条件合成(
    left: tuple[frozenset[str], ...],
    right: tuple[frozenset[str], ...],
) -> tuple[frozenset[str], ...] | None:
    if not left:
        return right
    if not right:
        return left
    if _条件キー(left) != _条件キー(right):
        return None
    return left


def _条件適合(
    target: tuple[frozenset[str], ...],
    path: tuple[frozenset[str], ...],
) -> bool:
    # 無条件の事実列は条件付き問いの下でも利用できるが、その逆は許さない。
    if not path:
        return True
    if not target:
        return False
    return _条件キー(target) == _条件キー(path)


def _端点一致(left: frozenset[str], right: frozenset[str]) -> bool:
    if not left or not right:
        return False
    overlap = len(left.intersection(right))
    return overlap / max(1, min(len(left), len(right))) >= 0.75


def _関係識別子(relation: 言語関係構造) -> str:
    if relation.種別 and relation.種別 != "開放述語":
        return relation.種別
    predicates = tuple(sorted(item for item in relation.述語 if item))
    return "開放述語:" + "|".join(predicates)


def 関係数値ID(relation: 言語関係構造) -> int:
    """関係を決定論的な数値IDへ写す。大小関係は意味しない。"""
    known = _関係番号.get(relation.種別)
    if known is not None:
        return known
    identity = _関係識別子(relation).encode("utf-8")
    # 既知17族と衝突しない安定ID。Python hashは使わない。
    return 1000 + int.from_bytes(hashlib.blake2b(identity, digest_size=4).digest(), "big")


@dataclass(frozen=True, slots=True)
class 関係数値:
    関係ID: int
    方向: int
    極性: int


@dataclass(frozen=True, slots=True)
class 関係辺:
    辺ID: str
    出典ID: str
    始点: frozenset[str]
    終点: frozenset[str]
    数値: 関係数値
    種別: str
    条件: tuple[frozenset[str], ...]


@dataclass(frozen=True, slots=True)
class 関係連鎖状態:
    始点: frozenset[str]
    終点: frozenset[str]
    数値列: tuple[関係数値, ...]
    種別列: tuple[str, ...]
    深さ: int
    出典ID列: tuple[str, ...]
    辺ID列: tuple[str, ...]
    条件: tuple[frozenset[str], ...]
    訪問節点: tuple[tuple[str, ...], ...]

    @property
    def 数値署名(self) -> tuple[tuple[int, int, int], ...]:
        return tuple((item.関係ID, item.方向, item.極性) for item in self.数値列)


@dataclass(frozen=True, slots=True)
class 関係連鎖結果:
    基礎辺数: int
    多段状態数: int
    最大到達深さ: int
    打切り: bool
    状態群: tuple[関係連鎖状態, ...]


def _辺生成(
    関係束: Sequence[tuple[str, Sequence[言語関係構造]]],
) -> tuple[関係辺, ...]:
    edges: list[関係辺] = []
    seen: set[tuple[str, tuple[object, ...], int]] = set()
    for source_index, (source_id, relations) in enumerate(関係束):
        sid = str(source_id).strip() or f"source:{source_index}"
        for relation_index, relation in enumerate(relations):
            # 否定関係は「反対の正関係」ではない。既存の肯否照合へ残し、連鎖支持には使わない。
            if not relation.肯定 or not relation.始点 or not relation.終点:
                continue
            code = 関係数値ID(relation)
            signature = (sid, relation.署名, 1)
            if signature not in seen:
                seen.add(signature)
                edges.append(
                    関係辺(
                        f"{sid}#{relation_index}:f",
                        sid,
                        relation.始点,
                        relation.終点,
                        関係数値(code, 1, 1),
                        relation.種別,
                        relation.条件,
                    )
                )
            if relation.種別 in _対称関係:
                reverse_signature = (sid, relation.署名, -1)
                if reverse_signature not in seen:
                    seen.add(reverse_signature)
                    edges.append(
                        関係辺(
                            f"{sid}#{relation_index}:r",
                            sid,
                            relation.終点,
                            relation.始点,
                            関係数値(code, -1, 1),
                            relation.種別,
                            relation.条件,
                        )
                    )
    return tuple(edges)


def 関係連鎖演算(
    関係束: Sequence[tuple[str, Sequence[言語関係構造]]],
    *,
    最大深さ: int = 4,
    最大状態数: int = 4096,
) -> 関係連鎖結果:
    """構造化された関係を候補非依存で連鎖し、多段の推論状態を形成する。

    `A -R1-> B -R2-> C` を `A R? C` という新しい世界事実へ勝手に縮約しない。
    形成物は `(R1, R2)` の順序を持つ関係列そのものであり、後段の候補照合時に利用する。
    """
    depth_limit = max(1, int(最大深さ))
    state_limit = max(1, int(最大状態数))
    edges = _辺生成(関係束)

    frontier: list[関係連鎖状態] = []
    all_states: list[関係連鎖状態] = []
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
    seen_states: set[tuple[object, ...]] = set()
    while frontier:
        current = frontier.pop(0)
        if current.深さ >= depth_limit:
            continue
        for edge in edges:
            if edge.辺ID in current.辺ID列:
                continue
            if not _端点一致(current.終点, edge.始点):
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


def _問い関係群(文脈) -> tuple[言語関係構造, ...]:
    out = []
    for relation in 文脈.現在.関係構造:
        if relation.種別 in _問い専用関係 or not relation.始点 or not relation.終点:
            out.append(relation)
    return tuple(out)


def _候補関係が問いに対応(question: 言語関係構造, candidate: 言語関係構造) -> bool:
    if question.種別 == candidate.種別:
        return True
    if question.述語 and candidate.述語 and question.述語.intersection(candidate.述語):
        return True
    return False


def _候補目標群(
    文脈,
    候補状態,
) -> tuple[tuple[frozenset[str], frozenset[str], tuple[frozenset[str], ...]], ...]:
    """問いの既知端点と候補代入端点から、連鎖が到達すべき向きを抽出する。"""
    targets: list[tuple[frozenset[str], frozenset[str], tuple[frozenset[str], ...]]] = []
    seen: set[tuple[object, ...]] = set()
    questions = _問い関係群(文脈)

    for question in questions:
        for relation in 候補状態.関係構造:
            if not _候補関係が問いに対応(question, relation):
                continue
            if question.始点 and not question.終点:
                if _端点一致(question.始点, relation.始点) and relation.終点:
                    target = (question.始点, relation.終点, relation.条件)
                else:
                    continue
            elif question.終点 and not question.始点:
                if _端点一致(question.終点, relation.終点) and relation.始点:
                    target = (relation.始点, question.終点, relation.条件)
                else:
                    continue
            elif relation.始点 and relation.終点:
                # 命題選択等で問い自身が未知端点を明示しない場合は、候補命題の端点を使う。
                target = (relation.始点, relation.終点, relation.条件)
            else:
                continue
            signature = (_端点キー(target[0]), _端点キー(target[1]), _条件キー(target[2]))
            if signature not in seen:
                seen.add(signature)
                targets.append(target)

    if targets:
        return tuple(targets)

    # 問い関係との対応が作れない命題選択でも、候補が明示関係を持つ場合だけ比較対象にする。
    for relation in 候補状態.関係構造:
        if relation.種別 in _問い専用関係 or not relation.始点 or not relation.終点:
            continue
        target = (relation.始点, relation.終点, relation.条件)
        signature = (_端点キー(target[0]), _端点キー(target[1]), _条件キー(target[2]))
        if signature not in seen:
            seen.add(signature)
            targets.append(target)
    return tuple(targets)


def 候補連鎖支持(
    文脈,
    候補状態,
    演算結果: 関係連鎖結果,
) -> tuple[bool, tuple[str, ...]]:
    targets = _候補目標群(文脈, 候補状態)
    evidence: list[str] = []
    for start, end, conditions in targets:
        for state in 演算結果.状態群:
            if not _端点一致(start, state.始点) or not _端点一致(end, state.終点):
                continue
            if not _条件適合(conditions, state.条件):
                continue
            evidence.append(
                "関係連鎖:"
                f"深さ{state.深さ}:"
                f"数値={','.join(f'{item.関係ID}/{item.方向}/{item.極性}' for item in state.数値列)}:"
                f"種別={'>'.join(state.種別列)}:"
                f"出典={','.join(dict.fromkeys(state.出典ID列))}"
            )
    return bool(evidence), tuple(evidence)


@dataclass(frozen=True, slots=True)
class 関係連鎖作用:
    """関係列を先に形成し、その後で候補へ一回だけ支持差を戻す模型作用。"""
    名称: str = 関係連鎖作用名
    最大深さ: int = 4
    最大状態数: int = 4096

    def 演算(self, 文脈) -> 関係連鎖結果:
        question_facts = tuple(
            relation
            for relation in 文脈.現在.関係構造
            if relation.種別 not in _問い専用関係
            and relation.始点
            and relation.終点
            and relation.肯定
        )
        bundle = ((("question-context", question_facts),) if question_facts else ()) + tuple(
            (
                state.識別子 or f"reference:{index}",
                state.関係構造,
            )
            for index, state in enumerate(文脈.参照状態)
        )
        return 関係連鎖演算(bundle, 最大深さ=self.最大深さ, 最大状態数=self.最大状態数)

    def 評価群(self, 文脈, 候補群):
        # 例外/反転問題では「経路が無い」を負の証拠としないため、本作用を使わない。
        if any(str(item).casefold() == "選択意図=反転" for item in 文脈.条件):
            return {}
        result = self.演算(文脈)
        out = {}
        for cid, state in 候補群:
            supported, evidence = 候補連鎖支持(文脈, state, result)
            if supported:
                # 経路数・深さを候補点へ水増ししない。多段到達の成立差は一候補あたり+1だけ。
                out[cid] = 関係寄与(
                    self.名称,
                    1,
                    (
                        f"連鎖基礎辺:{result.基礎辺数}",
                        f"連鎖多段状態:{result.多段状態数}",
                        f"連鎖最大深さ:{result.最大到達深さ}",
                        f"連鎖打切り:{int(result.打切り)}",
                        *evidence,
                    ),
                )
        return out


def 関係連鎖模型核(core: MINIDORA模型核 | None = None) -> MINIDORA模型核:
    base = core or 標準模型核()
    if any(getattr(action, "名称", "") == 関係連鎖作用名 for action in base.能力作用群):
        return base
    return MINIDORA模型核(
        base.関係群,
        言語対応_=base.言語対応,
        能力作用群=(*base.能力作用群, 関係連鎖作用()),
        形成済み関係群=base.形成済み関係群,
        最大再作用回数=base.最大再作用回数,
    )


__all__ = [
    "関係連鎖演算版",
    "関係連鎖作用名",
    "関係数値ID",
    "関係数値",
    "関係辺",
    "関係連鎖状態",
    "関係連鎖結果",
    "関係連鎖演算",
    "候補連鎖支持",
    "関係連鎖作用",
    "関係連鎖模型核",
]
