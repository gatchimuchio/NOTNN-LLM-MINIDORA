from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from .hds_adapter import HDSコンパイラProtocol, HDS独立コンパイル
from .hds_reference import HDS参照検索
from .hds_replay import HDSIR辞書化
from .参照 import 参照供給器


@dataclass(frozen=True, slots=True)
class Replay入力問題:
    識別子: str
    問題文: str
    選択肢: Mapping[str, str]
    gold: str | None = None


@dataclass(frozen=True, slots=True)
class Replay収録統計:
    問題数: int
    選択肢コンパイル数: int
    Data件数: int
    Dataコンパイル数: int
    Dataコンパイル失敗数: int


def HDSChoiceReplay収録(
    問題群: Iterable[Replay入力問題],
    *,
    compiler: HDSコンパイラProtocol,
    provider: 参照供給器 | None,
) -> tuple[tuple[dict[str, Any], ...], Replay収録統計]:
    """private Compilerを一度だけ使い、Runtime比較用HDS-IR bundleを作る。

    goldはIR生成・検索・Dataコンパイルへ渡さず、最終行へ採点情報として付与するだけ。
    外部Dataは生文字列のまま保存せず、HDS-IRとsource provenanceを保存する。
    """
    rows: list[dict[str, Any]] = []
    choice_compiled = 0
    data_count = 0
    data_compiled = 0
    data_failed = 0

    for problem in 問題群:
        question_ir = compiler.コンパイル(problem.問題文)
        choice_irs: dict[str, Any] = {}
        for label, text in sorted(problem.選択肢.items(), key=lambda item: str(item[0])):
            choice_ir = HDS独立コンパイル(compiler, str(text))
            choice_irs[str(label)] = HDSIR辞書化(choice_ir)
            choice_compiled += 1

        references = HDS参照検索(provider, question_ir) if provider is not None else ()
        data_rows: list[dict[str, Any]] = []
        data_count += len(references)
        for record in references:
            try:
                data_ir = HDS独立コンパイル(compiler, record.内容)
            except Exception:
                data_failed += 1
                continue
            data_compiled += 1
            data_rows.append(
                {
                    "provenance": [record.供給器, record.由来, record.識別子],
                    "source_confidence": float(record.信頼),
                    "ir": HDSIR辞書化(data_ir),
                }
            )

        row: dict[str, Any] = {
            "schema": "minidora.hds-choice-replay.v1",
            "id": problem.識別子,
            "question_ir": HDSIR辞書化(question_ir),
            "choices_ir": choice_irs,
            "data": data_rows,
        }
        if problem.gold is not None:
            row["gold"] = str(problem.gold)
        rows.append(row)

    return (
        tuple(rows),
        Replay収録統計(
            問題数=len(rows),
            選択肢コンパイル数=choice_compiled,
            Data件数=data_count,
            Dataコンパイル数=data_compiled,
            Dataコンパイル失敗数=data_failed,
        ),
    )


def ReplayJSONL保存(rows: Iterable[Mapping[str, Any]], path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), ensure_ascii=False, separators=(",", ":")) + "\n")


__all__ = [
    "Replay入力問題",
    "Replay収録統計",
    "HDSChoiceReplay収録",
    "ReplayJSONL保存",
]
