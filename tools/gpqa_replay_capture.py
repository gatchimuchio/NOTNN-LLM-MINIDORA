from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

import gpqa_measure_current as gpqa  # noqa: E402
from minidora.hds_compiler_v1 import 公開HDSコンパイラ  # noqa: E402
from minidora.hds_replay_capture import HDSChoiceReplay収録, ReplayJSONL保存, Replay入力問題  # noqa: E402
from minidora.standard_reference import 一般知識参照供給器  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="GPQA DiamondのR→HDSまでを固定し、K/J改修比較用Replay bundleを生成する。"
    )
    parser.add_argument("--out", type=Path, default=Path("gpqa_hds_replay.jsonl"))
    parser.add_argument("--stats", type=Path, default=Path("gpqa_hds_replay_stats.json"))
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="minidora-gpqa-replay-") as td:
        work = Path(td)
        csv_path, zip_hash, csv_hash = gpqa._download_dataset(work)
        cases = gpqa._load_cases(csv_path)
        if len(cases) != 198:
            raise RuntimeError(f"GPQA Diamond expected 198 rows, got {len(cases)}")

        problems = tuple(
            Replay入力問題(
                識別子=f"gpqa:{index:03d}",
                問題文=question,
                選択肢={label: choice for label, choice in zip(gpqa.LABELS, choices)},
                gold=gold,
            )
            for index, (question, choices, gold) in enumerate(cases)
        )

        api_key = os.getenv("OPENALEX_API_KEY", "").strip() or None
        provider = 一般知識参照供給器(
            OpenAlex_API_key=api_key,
            Wikipedia言語=("en",),
            timeout=8.0,
            最大本文文字数=6000,
            並列=True,
            最大並列=4,
        )
        rows, stats = HDSChoiceReplay収録(
            problems,
            compiler=公開HDSコンパイラ(),
            provider=provider,
        )
        ReplayJSONL保存(rows, args.out)

        summary = {
            "schema": "minidora.gpqa.hds-replay.capture.v1",
            "benchmark": "GPQA Diamond",
            "dataset_zip_sha256": zip_hash,
            "dataset_csv_sha256": csv_hash,
            "choice_shuffle_seed": gpqa.SEED,
            "problem_count": stats.問題数,
            "choice_compile_count": stats.選択肢コンパイル数,
            "data_count": stats.Data件数,
            "data_compile_count": stats.Dataコンパイル数,
            "data_compile_failure_count": stats.Dataコンパイル失敗数,
            "openalex_enabled": api_key is not None,
            "wikipedia_languages": ["en"],
            "compiler": "MINIDORA public standard HDS Compiler",
            "gold_boundary": "gold stored only as scoring metadata after question/choice/Data HDS projection",
            "raw_external_data_stored": False,
            "replay_path": str(args.out),
        }
        args.stats.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
