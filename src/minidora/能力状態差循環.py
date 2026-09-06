from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .semantic_tokens import 意味語
from .模型 import (
    _不成立入力の留保結果,
    MINIDORA模型核,
    内部言語状態,
    候補共同参照作用,
    成立候補,
    成立差,
    文脈付き言語状態,
    模型Checkpoint,
    模型結果,
    模型統計,
    関係寄与,
    _コア寄与同一性,
)


@dataclass(frozen=True, slots=True)
class 能力作用記録:
    作用ID: str
    種別: str
    入力状態: str | None
    出力状態: str | None
    条件: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class 能力状態差記録:
    差分ID: str
    原因作用ID: str
    前状態: str
    後状態: str
    変化有無: bool = True


@dataclass(frozen=True, slots=True)
class 能力後続利用記録:
    原因差分ID: str
    成立状態: str
    後続作用ID: str
    追加条件: tuple[str, ...] = ()
    状態条件充足: bool = True


@dataclass(frozen=True, slots=True)
class 能力作用構造:
    作用: tuple[能力作用記録, ...] = ()
    状態差: tuple[能力状態差記録, ...] = ()
    後続利用: tuple[能力後続利用記録, ...] = ()


@dataclass(frozen=True, slots=True)
class 能力候補状態差:
    差分ID: str
    前段: str
    後段: str
    変化候補ID: tuple[str, ...]
    得点変化: tuple[tuple[str, int, int], ...]

    @property
    def 変化有無(self) -> bool:
        return bool(self.変化候補ID)



def _寄与名正規化(name: str) -> str:
    value = str(name)
    if value.startswith("候補共同再照合:"):
        return "候補共同参照"
    return value


def _寄与同一性(item: 関係寄与) -> tuple[object, ...]:
    return _コア寄与同一性(item)


@dataclass
class _循環作業状態:
    寄与: dict[str, list[関係寄与]]
    checkpoint: list[模型Checkpoint]
    既訪問: set[tuple[object, ...]]
    生成数: int = 0
    再利用数: int = 0
    再活性数: int = 0
    大域再照合数: int = 0
    候補横断更新数: int = 0
    再作用回数: int = 0

    def 追加(self, 候補ID: str, item: 関係寄与) -> bool:
        identity = _寄与同一性(item)
        if any(_寄与同一性(old) == identity for old in self.寄与[候補ID]):
            return False
        self.寄与[候補ID].append(item)
        self.生成数 += 1
        return True

    def 得点(self) -> dict[str, int]:
        return {cid: sum(item.差 for item in rows) for cid, rows in self.寄与.items()}

    def 状態署名(self) -> dict[str, tuple[int, tuple[tuple[object, ...], ...]]]:
        scores = self.得点()
        return {
            cid: (
                scores[cid],
                tuple(sorted((_寄与同一性(item) for item in rows), key=repr)),
            )
            for cid, rows in self.寄与.items()
        }

    def 差分(
        self,
        before: dict[str, tuple[int, tuple[tuple[object, ...], ...]]],
        after: dict[str, tuple[int, tuple[tuple[object, ...], ...]]],
        *,
        前段: str,
        後段: str,
        番号: int,
    ) -> 能力候補状態差:
        changed: list[str] = []
        score_delta: list[tuple[str, int, int]] = []
        for cid in sorted(after):
            old = before.get(cid, (0, ()))
            new = after[cid]
            if old != new:
                changed.append(cid)
                score_delta.append((cid, int(old[0]), int(new[0])))
        return 能力候補状態差(
            f"能力状態差:{番号:03d}",
            前段,
            後段,
            tuple(changed),
            tuple(score_delta),
        )

    def 記録(self, 段階: str, active: Sequence[str] = (), reuse: Sequence[str] = ()) -> None:
        self.checkpoint.append(
            模型Checkpoint(
                段階,
                tuple(sorted(self.得点().items())),
                tuple(active),
                tuple(reuse),
            )
        )


class 参照状態差連結作用:
    """参照Dataの明示状態差から、追加条件なしで接続できる終端状態だけを候補差へ使う。

    Compilerが「状態条件は満たすが追加条件は未確認」と残した接続は証拠化しない。
    単一遷移だけでも証拠化せず、状態差が別作用を成立可能にした連結がある場合だけ使う。
    """

    名称 = "候補共同参照:状態差連結"

    def 評価群(
        self,
        候補群: Sequence[tuple[str, 内部言語状態]],
        作用構造群: Sequence[能力作用構造],
    ) -> dict[str, 関係寄与]:
        scores = {cid: 0 for cid, _ in 候補群}
        evidence: dict[str, list[str]] = {cid: [] for cid, _ in 候補群}

        for structure_index, structure in enumerate(作用構造群):
            actions = {item.作用ID: item for item in structure.作用}
            deltas = {item.差分ID: item for item in structure.状態差 if item.変化有無}
            edges: list[tuple[str, str]] = []
            for link in structure.後続利用:
                if not link.状態条件充足 or link.追加条件:
                    continue
                delta = deltas.get(link.原因差分ID)
                next_action = actions.get(link.後続作用ID)
                if delta is None or next_action is None:
                    continue
                if delta.後状態 != link.成立状態:
                    continue
                edges.append((delta.原因作用ID, next_action.作用ID))

            if not edges:
                continue
            sources = {src for src, _ in edges}
            targets = {dst for _, dst in edges}
            terminal_ids = sorted(targets - sources)
            if not terminal_ids:
                continue

            terminal_states = tuple(
                dict.fromkeys(
                    actions[action_id].出力状態
                    for action_id in terminal_ids
                    if action_id in actions and actions[action_id].出力状態
                )
            )
            if not terminal_states:
                continue

            rank: dict[str, int] = {}
            for cid, candidate in 候補群:
                overlap = 0
                for state in terminal_states:
                    overlap = max(overlap, len(意味語(state).intersection(candidate.意味語集合)))
                rank[cid] = overlap
            maximum = max(rank.values(), default=0)
            top = sorted(cid for cid, value in rank.items() if value == maximum and value > 0)
            if maximum <= 0 or len(top) != 1:
                continue
            cid = top[0]
            scores[cid] += 1
            evidence[cid].append(
                f"状態差連結:{structure_index}:{'|'.join(terminal_states)}"
            )

        return {
            cid: 関係寄与(self.名称, score, tuple(evidence[cid]))
            for cid, score in scores.items()
            if score > 0
        }


class MINIDORA能力状態差模型核(MINIDORA模型核):
    """状態差が存在した時だけ次作用集合を開く現行能力模型核。

    旧模型核の一般関係・形成済み関係・能力作用を保持しつつ、再作用の起動条件を
    「上位候補集合が未訪問」から「直前作用によって候補状態が実際に変化した」へ置き換える。
    """

    def _評価作用付き(
        self,
        文脈: 文脈付き言語状態,
        候補群: Sequence[成立候補],
        *,
        作用構造群: Sequence[能力作用構造] = (),
    ) -> 模型結果:
        if not 候補群:
            raise ValueError("成立差の評価には1候補以上が必要")
        ids = [item.候補ID for item in 候補群]
        if len(ids) != len(set(ids)):
            raise ValueError("候補IDは評価内で一意である必要がある")

        internal: list[tuple[str, 内部言語状態]] = []
        for candidate in 候補群:
            if candidate.状態.言語体系 != 文脈.現在.言語体系:
                raise ValueError("候補と言語文脈の言語体系が一致しない")
            internal.append((candidate.候補ID, self.言語対応.内部化(candidate.状態)))

        incomplete = _不成立入力の留保結果(文脈, tuple(internal))
        if incomplete is not None:
            return incomplete
        work = _循環作業状態({cid: [] for cid in ids}, [], set())
        state_diffs: list[能力候補状態差] = []

        for cid, state in internal:
            for relation in self._関係群:
                item = relation.評価(文脈, state)
                if item:
                    work.追加(cid, item)
        work.記録("STANDARD_RELATIONS", ids)

        for cid, state in internal:
            for relation in self._形成済み関係群:
                item = relation.評価(文脈, state)
                if item:
                    work.追加(cid, item)
        work.記録("FORMED_RELATIONS", ids)

        before_primary = work.状態署名()

        if 作用構造群:
            result = 参照状態差連結作用().評価群(tuple(internal), tuple(作用構造群))
            for cid, item in result.items():
                work.追加(cid, item)

        for action in self._能力作用群:
            if hasattr(action, "評価群"):
                result = action.評価群(文脈, tuple(internal))
                for cid, item in result.items():
                    work.追加(cid, item)
            else:
                for cid, state in internal:
                    item = action.評価(文脈, state)
                    if item:
                        work.追加(cid, item)

        after_primary = work.状態署名()
        primary_delta = work.差分(
            before_primary,
            after_primary,
            前段="FORMED_RELATIONS",
            後段="PRIMARY_CAPABILITY_ACTIONS",
            番号=len(state_diffs),
        )
        if primary_delta.変化有無:
            state_diffs.append(primary_delta)
        work.記録(
            "PRIMARY_CAPABILITY_ACTIONS",
            primary_delta.変化候補ID,
            (primary_delta.差分ID,) if primary_delta.変化有無 else (),
        )

        pending = primary_delta if primary_delta.変化有無 else None
        for round_index in range(1, self.最大再作用回数 + 1):
            if pending is None or not pending.変化候補ID:
                break

            scores = work.得点()
            ordered = sorted(ids, key=lambda cid: (-scores[cid], cid))
            changed = sorted(pending.変化候補ID, key=lambda cid: (-scores[cid], cid))
            # 再作用は「変化した候補どうし」だけで閉じず、現在の成立境界を必ず含める。
            # 現在首位 + 最も強い変化候補を比較し、首位自身が変化候補なら次の変化候補を使う。
            active: list[str] = []
            if ordered:
                active.append(ordered[0])
            for cid in changed:
                if cid not in active:
                    active.append(cid)
                if len(active) >= 2:
                    break
            if len(active) < 2:
                for cid in ordered:
                    if cid not in active:
                        active.append(cid)
                        break
            active_tuple = tuple(active)
            if len(active_tuple) < 2:
                break

            enabled = tuple(
                action
                for action in self._能力作用群
                if hasattr(action, "再評価群")
                and not (
                    isinstance(action, 候補共同参照作用)
                    and not 文脈.参照状態
                )
            )
            if not enabled:
                break

            trigger = (
                pending.得点変化,
                active_tuple,
                tuple(getattr(action, "名称", type(action).__name__) for action in enabled),
            )
            if trigger in work.既訪問:
                break
            work.既訪問.add(trigger)
            work.再活性数 += 1
            work.大域再照合数 += 1
            work.再作用回数 += 1

            before = work.状態署名()
            active_rows = tuple(row for row in internal if row[0] in active_tuple)
            reused_labels: list[str] = [pending.差分ID]
            for action in enabled:
                action_name = str(getattr(action, "名称", type(action).__name__))
                reused_labels.append(action_name)
                # 参照比較だけは元の全候補を維持し、候補除外による人工的な固有語を作らない。
                scope = tuple(internal) if isinstance(action, 候補共同参照作用) else active_rows
                result = action.再評価群(文脈, scope, round_index)
                for cid, item in result.items():
                    if work.追加(cid, item):
                        work.再利用数 += 1

            after = work.状態署名()
            next_delta = work.差分(
                before,
                after,
                前段=f"RECONCILE_{round_index - 1}" if round_index > 1 else "PRIMARY_CAPABILITY_ACTIONS",
                後段=f"RECONCILE_{round_index}",
                番号=len(state_diffs),
            )
            if next_delta.変化有無:
                state_diffs.append(next_delta)
                work.候補横断更新数 += len(next_delta.変化候補ID)
            work.記録(
                f"RECONCILE_{round_index}",
                active_tuple,
                tuple(reused_labels),
            )
            pending = next_delta if next_delta.変化有無 else None

        differences = tuple(
            成立差(cid, sum(item.差 for item in work.寄与[cid]), tuple(work.寄与[cid]))
            for cid in ids
        )
        maximum = max(item.差 for item in differences)
        top = tuple(item.候補ID for item in differences if item.差 == maximum)
        winner = top[0] if maximum > 0 and len(top) == 1 else None

        reference_prefixes = (
            "参照関係寄与",
            "候補共同参照",
            "候補共同再照合",
        )
        ref_scores = {
            row.候補ID: sum(
                contribution.差
                for contribution in row.寄与
                if contribution.関係名.startswith(reference_prefixes)
            )
            for row in differences
        }
        ref_max = max(ref_scores.values(), default=0)
        ref_top = tuple(cid for cid, value in ref_scores.items() if value == ref_max)
        ref_winner = ref_top[0] if ref_max > 0 and len(ref_top) == 1 else None

        stats = 模型統計(
            work.生成数,
            work.再利用数,
            work.再活性数,
            work.大域再照合数,
            work.候補横断更新数,
            work.再作用回数,
            len(work.checkpoint),
        )
        return 模型結果(
            文脈,
            differences,
            winner,
            top if len(top) > 1 else (),
            tuple(work.checkpoint),
            stats,
            ref_winner,
            ref_top if len(ref_top) > 1 else (),
        )

    def 評価(self, 文脈: 文脈付き言語状態, 候補群: Sequence[成立候補]) -> 模型結果:
        return self._評価作用付き(文脈, 候補群)

    def 評価言語状態(
        self,
        現在,
        候補群,
        *,
        履歴=(),
        条件=(),
        参照状態=(),
        作用構造群: Sequence[能力作用構造] = (),
    ) -> 模型結果:
        context = self.文脈化(現在, 履歴, 条件, 参照状態)
        return self._評価作用付き(context, 候補群, 作用構造群=作用構造群)


def 標準能力模型核() -> MINIDORA能力状態差模型核:
    from .模型 import (
        参照関係寄与作用,
        意味連続関係,
        有向関係整合,
        条件結合関係,
        肯否整合関係,
        履歴近接関係,
        順序連続関係,
    )

    return MINIDORA能力状態差模型核(
        (
            意味連続関係(),
            順序連続関係(),
            有向関係整合(),
            肯否整合関係(),
            履歴近接関係(),
            条件結合関係(),
        ),
        能力作用群=(参照関係寄与作用(), 候補共同参照作用()),
    )


__all__ = [
    "能力作用記録",
    "能力状態差記録",
    "能力後続利用記録",
    "能力作用構造",
    "能力候補状態差",
    "参照状態差連結作用",
    "MINIDORA能力状態差模型核",
    "標準能力模型核",
]
