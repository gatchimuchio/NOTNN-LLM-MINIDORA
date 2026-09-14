from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


候補生成版 = "MINIDORA-候補生成-v0.1"


def _text(value, name: str) -> str:
    if type(value) is not str or not value.strip() or len(value) > 4096:
        raise ValueError(name + "の型・長さ不正")
    return value.strip()


@dataclass(frozen=True, slots=True)
class 候補生成残差:
    種別: str
    対象: str
    詳細: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class 仮説候補生成結果:
    候補: tuple[str, ...]
    関連命題: tuple[str, ...]
    既知閉包: tuple[str, ...]
    残差: tuple[候補生成残差, ...]
    版: str = 候補生成版


def _forward_closure(facts: Iterable[str], rules: tuple[tuple[tuple[str, ...], str], ...]) -> set[str]:
    known = set(facts)
    changed = True
    while changed:
        changed = False
        for left, right in rules:
            if right not in known and all(item in known for item in left):
                known.add(right)
                changed = True
    return known


def 仮説候補を生成(要求: dict, *, 最大候補数: int = 16) -> 仮説候補生成結果:
    """規則・事実・観測だけから、未説明観測の前件frontierを仮説候補化する。

    世界知識・尤度・正解情報は使わない。観測そのものを自己説明用仮説にはしない。
    規則が循環してfrontierへ到達しない場合は残差として停止する。
    """
    if type(要求) is not dict:
        raise ValueError("仮説要求はdictである必要がある")
    if type(最大候補数) is not int or not 1 <= 最大候補数 <= 64:
        raise ValueError("最大候補数の範囲不正")
    facts_rows = 要求.get("事実", [])
    rule_rows = 要求.get("規則", [])
    observations_raw = 要求.get("観測", [])
    if type(facts_rows) is not list or type(rule_rows) is not list or type(observations_raw) is not list:
        raise ValueError("事実・規則・観測はlistである必要がある")

    facts = []
    for row in facts_rows:
        if type(row) is not dict or "命題" not in row:
            raise ValueError("事実の形式不正")
        facts.append(_text(row["命題"], "事実命題"))

    rules = []
    for row in rule_rows:
        if type(row) is not dict or "前件" not in row or "後件" not in row or type(row["前件"]) is not list:
            raise ValueError("規則の形式不正")
        left = tuple(_text(x, "規則前件") for x in row["前件"])
        if not left:
            raise ValueError("規則前件は空にできない")
        right = _text(row["後件"], "規則後件")
        rules.append((left, right))
    rules_t = tuple(rules)
    observations = tuple(_text(x, "観測") for x in observations_raw)
    if not observations:
        raise ValueError("観測は1件以上必要")

    known = _forward_closure(facts, rules_t)
    producers: dict[str, list[tuple[str, ...]]] = {}
    for left, right in rules_t:
        producers.setdefault(right, []).append(left)

    related: set[str] = set(observations)
    frontier: set[str] = set()
    residuals: list[候補生成残差] = []
    observation_set = set(observations)

    def visit(target: str, path: tuple[str, ...]) -> None:
        if target in known:
            return
        if target in path:
            residuals.append(候補生成残差("規則循環", target, path + (target,)))
            return
        alternatives = producers.get(target, [])
        if not alternatives:
            if target in observation_set:
                residuals.append(候補生成残差("自己説明禁止", target, ("観測そのもの以外の前提候補がない",)))
                return
            frontier.add(target)
            related.add(target)
            return
        related.add(target)
        for left in alternatives:
            for item in left:
                related.add(item)
                visit(item, path + (target,))

    for observation in observations:
        if observation not in known:
            visit(observation, ())

    candidates = tuple(sorted(frontier - set(facts) - observation_set))
    if len(candidates) > 最大候補数:
        raise ValueError("自動生成した仮説候補が上限を超えた。無断枝刈りしない")
    return 仮説候補生成結果(
        candidates,
        tuple(sorted(related)),
        tuple(sorted(known)),
        tuple(residuals),
    )


def 自動仮説要求(要求: dict, *, 最大候補数: int = 16) -> tuple[dict, 仮説候補生成結果]:
    """既存の有限仮説探索へ渡せる要求を作る。元要求は変更しない。"""
    if type(要求) is not dict:
        raise ValueError("仮説要求はdictである必要がある")
    if 要求.get("仮説候補"):
        raise ValueError("明示仮説候補がある要求を自動生成で上書きしない")
    result = 仮説候補を生成(要求, 最大候補数=最大候補数)
    out = dict(要求)
    out["仮説候補"] = list(result.候補)
    return out, result


__all__ = [
    "候補生成版",
    "候補生成残差",
    "仮説候補生成結果",
    "仮説候補を生成",
    "自動仮説要求",
]
