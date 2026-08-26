from __future__ import annotations

from dataclasses import dataclass

from .言語構造 import 言語関係構造


能力作用則版 = "v2-recompose"
_問い専用関係 = frozenset({"命題適合", "説明適合", "問い適合", "同定", "数量同定"})

# K3の連続weight値を模写しない。観測できた作用順序だけを符号付き序数へ射影する。
_完全整合 = 2
_極性矛盾 = -2
_逆向関係 = -1
_弱整合 = 1


def _端点意味同一(a: frozenset[str], b: frozenset[str]) -> bool:
    """表層完全一致ではなく、意味語集合の局所対応で端点同一性を判定する。"""
    if not a or not b:
        return False
    if a == b:
        return True

    # v1のnegative controlを維持する。記号・数式の明示anchorが異なる場合は同一視しない。
    def anchors(values: frozenset[str]) -> tuple[frozenset[str], frozenset[str]]:
        symbol = frozenset(
            item.split(":", 1)[1]
            for item in values
            if item.startswith(("sym:", "atom:"))
        )
        math = frozenset(item.split(":", 1)[1] for item in values if item.startswith("math:"))
        return symbol, math

    symbols_a, math_a = anchors(a)
    symbols_b, math_b = anchors(b)
    if symbols_a and symbols_b and symbols_a != symbols_b:
        return False
    if math_a and math_b and math_a != math_b:
        return False

    intersection = len(a.intersection(b))
    return intersection / max(1, min(len(a), len(b))) >= 0.75


def _述語対応(a: 言語関係構造, b: 言語関係構造) -> bool:
    """世界関係と問い関係を、保持済み述語identityを失わず接続する。"""
    if a.種別 in _問い専用関係:
        # 問い適合/同定等は世界Dataの関係種別と一致しないため、検索述語由来の意味を使う。
        return bool(a.述語 and b.述語 and a.述語.intersection(b.述語))
    if a.種別 == b.種別 and a.種別 != "開放述語":
        return True
    return bool(a.述語 and b.述語 and a.述語.intersection(b.述語))


def _scope一致(a: 言語関係構造, b: 言語関係構造) -> bool:
    if not a.条件 and not b.条件:
        return True
    return a.条件 == b.条件


def 関係寄与(target: 言語関係構造, evidence: 言語関係構造) -> int:
    """一つの参照関係が候補関係へ与える符号付き寄与を返す。"""
    if not _述語対応(target, evidence):
        return 0

    same_direction = (
        _端点意味同一(target.始点, evidence.始点)
        and _端点意味同一(target.終点, evidence.終点)
    )
    reverse_direction = (
        _端点意味同一(target.始点, evidence.終点)
        and _端点意味同一(target.終点, evidence.始点)
    )

    if same_direction:
        value = _完全整合 if target.肯定 == evidence.肯定 else _極性矛盾
    elif reverse_direction:
        value = _逆向関係
    else:
        return 0

    if not _scope一致(target, evidence):
        return _弱整合 if value > 0 else -_弱整合
    return value


def 証拠状態寄与群(
    targets: tuple[言語関係構造, ...],
    evidence: tuple[言語関係構造, ...],
) -> tuple[int, ...]:
    """一参照状態の複数独立関係差を保持し、target内の重複だけを圧縮する。"""
    values: list[int] = []
    seen: set[tuple[object, ...]] = set()
    for target in targets:
        signature = target.署名
        if signature in seen:
            continue
        seen.add(signature)
        local = [関係寄与(target, item) for item in evidence]
        local = [value for value in local if value]
        if local:
            values.append(max(local, key=lambda value: (abs(value), value)))
    return tuple(values)


def 証拠状態合計寄与(
    targets: tuple[言語関係構造, ...],
    evidence: tuple[言語関係構造, ...],
) -> int:
    """正式v3模型向け。一参照状態に保持された独立関係差を再結合する。"""
    return sum(証拠状態寄与群(targets, evidence))


def 証拠状態寄与(
    targets: tuple[言語関係構造, ...],
    evidence: tuple[言語関係構造, ...],
) -> int:
    """旧互換。一参照状態から最も強い一差だけを返す。"""
    values = list(証拠状態寄与群(targets, evidence))
    return max(values, key=lambda value: (abs(value), value)) if values else 0


@dataclass(frozen=True, slots=True)
class 能力保存則:
    """実LLM横断観測から射影した、部品非依存の構成再現作用。"""

    状態分離: bool = True
    意味同一性: bool = True
    寄与Gate: bool = True
    状態Checkpoint: bool = True
    再選択: bool = True
    再結合: bool = True
    有界反復: bool = True
    形成分離: bool = True
    終端遅延: bool = True
    未確定差共存: bool = True
    寄与確定分離: bool = True
    再作用閉包: bool = True


標準能力保存則 = 能力保存則()


__all__ = [
    "能力作用則版",
    "能力保存則",
    "標準能力保存則",
    "関係寄与",
    "証拠状態寄与群",
    "証拠状態合計寄与",
    "証拠状態寄与",
]
