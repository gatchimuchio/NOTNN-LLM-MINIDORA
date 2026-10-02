from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from GPQA現行測定 import _download_dataset, _load_cases
from 中核正本評価 import GPQA正本資料集合CSV_SHA256, _一問を実行, _集計, _リポジトリ版
from minidora.HDS構文化器_v1 import 公開HDSコンパイラ
from minidora.HDS駆動コア import HDS駆動コア


def 引数解析器() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="GPQA並列性能継承評価のshard実行器")
    parser.add_argument("--start-index", type=int, required=True)
    parser.add_argument("--limit", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    return parser


def main() -> int:
    args = 引数解析器().parse_args()
    if args.start_index < 0 or args.start_index >= 198:
        raise SystemExit("--start-index は0..197で指定する")
    if args.limit <= 0:
        raise SystemExit("--limit は1以上で指定する")

    with tempfile.TemporaryDirectory(prefix="minidora-gpqa-parallel-") as td:
        csv_path, zip_hash, csv_hash = _download_dataset(Path(td))
        cases = _load_cases(csv_path)
    if len(cases) != 198 or csv_hash != GPQA正本資料集合CSV_SHA256:
        raise RuntimeError(f"GPQA正本資料不一致: n={len(cases)} sha={csv_hash}")

    stop = min(198, args.start_index + args.limit)
    rows: list[dict[str, object]] = []
    for index in range(args.start_index, stop):
        question, choices, gold = cases[index]
        構文化器 = 公開HDSコンパイラ()
        中核 = HDS駆動コア(HDSコンパイラ=構文化器, 最大作用回数=40)
        row = _一問を実行(
            index,
            question,
            tuple(choices),
            gold,
            構文化器=構文化器,
            中核=中核,
        )
        rows.append(row)
        print(
            f"CASE {index + 1:03d}/198 terminal={row['終端']} pred={row['予測ラベル']} "
            f"correct={row['正答']} refs={row['初期参照件数']}->{row['最終参照件数']}",
            flush=True,
        )

    metrics, transition = _集計(rows)
    payload = {
        "契約形式": "minidora.gpqa.parallel-inheritance-shard.v1",
        "評価条件": {
            "外部評価": "GPQA Diamond",
            "資料集合ZIP_SHA256": zip_hash,
            "資料集合CSV_SHA256": csv_hash,
            "全問題数": 198,
            "選択番号群": list(range(args.start_index, stop)),
            "選択肢シャッフル種": 0,
            "実行方式": "問題独立並列",
            "問題間継続状態": False,
            "性能継承下限正答": 40,
            "全数wall_clock上限分": 90,
            "採点結果の学習利用": False,
            "リポジトリ版": _リポジトリ版(),
        },
        "指標": metrics,
        "実行内状態遷移": transition,
        "個票": rows,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
