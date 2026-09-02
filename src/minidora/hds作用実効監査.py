from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Callable, Mapping, Any


def _sig(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":"))
    return sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class HDS作用差分観測:
    変種: str
    状態変更: bool
    参照集合変更: bool
    経路変更: bool
    計算量変更: bool
    出力変更: bool
    全体署名変更: bool

    @property
    def 実効差あり(self) -> bool:
        return any((
            self.状態変更,
            self.参照集合変更,
            self.経路変更,
            self.計算量変更,
            self.出力変更,
            self.全体署名変更,
        ))


@dataclass(frozen=True, slots=True)
class HDS作用実効監査結果:
    作用名: str
    基準署名: str
    差分: tuple[HDS作用差分観測, ...]

    @property
    def 実効作用(self) -> bool:
        return any(row.実効差あり for row in self.差分)


def _view(payload: Mapping[str, Any] | object) -> dict[str, Any]:
    if isinstance(payload, Mapping):
        data = dict(payload)
    elif hasattr(payload, "辞書") and callable(getattr(payload, "辞書")):
        data = dict(getattr(payload, "辞書")())
    elif hasattr(payload, "辞書化") and callable(getattr(payload, "辞書化")):
        data = dict(getattr(payload, "辞書化")())
    elif hasattr(payload, "__dict__"):
        data = dict(getattr(payload, "__dict__"))
    else:
        data = {"output": repr(payload)}
    return {
        "state": data.get("state", data.get("状態")),
        "references": data.get("references", data.get("参照集合", data.get("参照"))),
        "path": data.get("path", data.get("経路", data.get("作用履歴"))),
        "compute": data.get("compute", data.get("計算量", data.get("計算回数"))),
        "output": data.get("output", data.get("出力", data.get("結果"))),
        "raw": data,
    }


def HDS作用実効監査(
    作用名: str,
    *,
    基準実行: Callable[[], object],
    変種実行: Mapping[str, Callable[[], object]],
) -> HDS作用実効監査結果:
    """状態の存在ではなく、除去/固定/置換で後続が実際に変化するかを監査する。

    変種名は自由だが、推奨は `removed`, `fixed`, `replaced`, `route_fixed`, `reference_fixed`。
    """
    baseline = _view(基準実行())
    base_sig = _sig(baseline["raw"])
    rows: list[HDS作用差分観測] = []
    for name, runner in 変種実行.items():
        variant = _view(runner())
        rows.append(HDS作用差分観測(
            str(name),
            baseline["state"] != variant["state"],
            baseline["references"] != variant["references"],
            baseline["path"] != variant["path"],
            baseline["compute"] != variant["compute"],
            baseline["output"] != variant["output"],
            base_sig != _sig(variant["raw"]),
        ))
    return HDS作用実効監査結果(str(作用名), base_sig, tuple(rows))


__all__ = ["HDS作用差分観測", "HDS作用実効監査結果", "HDS作用実効監査"]
