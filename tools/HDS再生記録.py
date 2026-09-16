from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
import sys
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from minidora.HDS再生記録 import (  # noqa: E402
    HDS選択肢再生収録,
    再生JSONL保存,
    再生入力問題,
)


def _load_object(spec: str):
    '`モジュール:object` をimportし、factoryなら呼出してinstanceを返す。'
    if ":" not in spec:
        raise ValueError('plugin指定は モジュール:object 形式')
    モジュール_name, object_name = spec.split(":", 1)
    モジュール = importlib.import_module(モジュール_name)
    value = getattr(モジュール, object_name)
    return value() if callable(value) else value


def _choices(value: Any) -> dict[str, str]:
    if isinstance(value, Mapping):
        return {str(key): str(text) for key, text in value.items()}
    if isinstance(value, list):
        labels = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        if len(value) > len(labels):
            raise ValueError('選択肢数が多すぎる')
        return {labels[index]: str(text) for index, text in enumerate(value)}
    raise TypeError("choicesはobjectまたはlistが必要")


def _load_dataset(path: Path) -> tuple[再生入力問題, ...]:
    rows: list[再生入力問題] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, Mapping):
            raise ValueError(f"line {line_no}: JSON objectが必要")
        question = row.get("question", row.get("問題文"))
        choices = row.get("choices", row.get("選択肢"))
        if question is None or choices is None:
            raise ValueError(f"line {line_no}: question/choicesが必要")
        case_id = row.get("id", row.get("識別子", f"line:{line_no}"))
        gold = row.get("gold", row.get("answer", row.get("正解")))
        rows.append(
            再生入力問題(
                str(case_id),
                str(question),
                _choices(choices),
                None if gold is None else str(gold),
            )
        )
    return tuple(rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description='private HDS 構文化器/Rを公開せず、固定HDS 再生 bundleだけ生成する。'
    )
    parser.add_argument("input", type=Path, help="question/choices/goldを持つJSONL")
    parser.add_argument("output", type=Path, help='minidora.hds-選択肢-再生.v1 JSONL出力')
    parser.add_argument("--compiler", required=True, help="private Compiler factory: module:object")
    parser.add_argument("--provider", help="private/public R Provider factory: module:object")
    parser.add_argument(
        "--plugin-path",
        作用="append",
        default=[],
        help="private pluginをimportする追加sys.path。複数指定可。",
    )
    parser.add_argument("--stats", type=Path, help="収録統計JSON出力")
    args = parser.parse_args()

    # plugin pathは明示指定だけを利用し、private資産探索や自動uploadは行わない。
    for raw in reversed(args.plugin_path):
        sys.path.insert(0, str(Path(raw).expanduser().resolve()))

    構文化器 = _load_object(args.構文化器)
    provider = _load_object(args.provider) if args.provider else None
    problems = _load_dataset(args.input)
    rows, stats = HDS選択肢再生収録(
        problems,
        構文化器=構文化器,
        provider=provider,
    )
    再生JSONL保存(rows, args.output)

    要約 = {
        "契約形式": 'minidora.hds-選択肢-再生.記録-結果.v1',
        "input": str(args.input),
        "output": str(args.output),
        "problem_count": stats.問題数,
        '選択肢_compile_count': stats.選択肢コンパイル数,
        '資料_count': stats.資料件数,
        '資料_compile_count': stats.資料コンパイル数,
        '資料_compile_failure_count': stats.資料コンパイル失敗数,
        '構文化器_spec': args.構文化器,
        "provider_spec": args.provider,
    }
    text = json.dumps(要約, ensure_ascii=False, indent=2)
    if args.stats:
        args.stats.parent.mkdir(parents=True, exist_ok=True)
        args.stats.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
