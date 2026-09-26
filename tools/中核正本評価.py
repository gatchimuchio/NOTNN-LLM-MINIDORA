from __future__ import annotations

from collections import Counter
import json
import os
from pathlib import Path
import subprocess
import tempfile
from threading import Lock

from GPQA現行測定 import _download_dataset, _load_cases
from minidora.HDS参照 import HDS参照検索
from minidora.HDS構文化器_v1 import 公開HDSコンパイラ
from minidora.HDS実行主体 import HDS終端
from minidora.HDS選択実行系 import HDS選択実行結果
from minidora.HDS選択継承循環 import (
    回答成果名,
    参照成果名,
    基準結果主体名,
    現行結果成果名,
    非退行判定成果名,
)
from minidora.HDS駆動コア import HDS駆動コア
from minidora.標準参照 import 一般知識参照供給器
from minidora.計算実行器 import 計算実行器


GPQA正本資料集合CSV_SHA256 = "41d1213cd7a4998605a26c2798500652572007161b3a92817ba46b35befcd305"


class _記録参照供給器:
    並列安全 = True
    名称 = "MINIDORA_GPQA正本記録"

    def __init__(self, base) -> None:
        self.base = base
        self.calls: list[str] = []
        self.lock = Lock()

    def 検索(self, query: str, limit: int = 8):
        normalized = " ".join(str(query).split())
        with self.lock:
            self.calls.append(normalized)
        return self.base.検索(query, limit)


def _候補ラベル群(records) -> tuple[str, ...]:
    return tuple(sorted({
        str(value)
        for record in records
        for key, value in record.条件
        if str(key) == "hds_query_選択肢" and str(value)
    }))


def _採用回答(結果: object) -> bool:
    return isinstance(結果, HDS選択実行結果) and 結果.状態 == "APPROVE" and 結果.回答ラベル is not None


def _リポジトリ版() -> str:
    env_sha = os.getenv("GITHUB_SHA", "").strip()
    if env_sha:
        return env_sha
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    return completed.stdout.strip() if completed.returncode == 0 else "未知"


def _一問を実行(index: int, question: str, choices: tuple[str, ...], gold: str) -> dict[str, object]:
    provider_base = 一般知識参照供給器(
        OpenAlex_API_key=None,
        EuropePMC有効=True,
        EuropePMC同義語展開=False,
        Crossref有効=True,
        Wikipedia言語=("en",),
        timeout=8.0,
        最大本文文字数=6000,
        並列=True,
        最大並列=4,
    )
    provider = _記録参照供給器(provider_base)
    構文化器 = 公開HDSコンパイラ()

    kernel_count = 0
    original_kernel = 構文化器.問題コンパイル束

    def counted_kernel(*args, **kwargs):
        nonlocal kernel_count
        kernel_count += 1
        return original_kernel(*args, **kwargs)

    構文化器.問題コンパイル束 = counted_kernel
    kernel = 構文化器.問題コンパイル束(question, choices)
    question_ir = kernel.意味IR
    requests = tuple(kernel.参照観測要求)
    initial_refs = tuple(HDS参照検索(provider, question_ir, 観測要求=requests))
    initial_query_count = len(provider.calls)

    中核 = HDS駆動コア(HDSコンパイラ=構文化器, 最大作用回数=40)
    run = 中核.選択実行(
        question,
        choices,
        初期参照=initial_refs,
        参照供給器=provider,
        計算実行器_=計算実行器(),
        既存能力継承=True,
        最大回復回数=6,
        カーネル正本=kernel,
    )
    if kernel_count != 1:
        raise RuntimeError(f"問題束の形成回数が1ではない: index={index} count={kernel_count}")

    products = run.状態.成果辞書()
    subjects = run.状態.主体辞書()
    current = products.get(現行結果成果名)
    baseline = subjects.get(基準結果主体名)
    final_refs = products.get(参照成果名, initial_refs)
    answer = products.get(回答成果名)
    judge = products.get(非退行判定成果名)
    if not isinstance(current, HDS選択実行結果):
        raise RuntimeError(f"現行結果欠落: index={index}")
    if not isinstance(baseline, HDS選択実行結果):
        raise RuntimeError(f"基準結果欠落: index={index}")
    if not isinstance(final_refs, tuple):
        raise RuntimeError(f"最終参照形式不正: index={index}")

    committed = run.終端 == HDS終端.採用
    predicted = answer if committed and answer in {"A", "B", "C", "D"} else None
    baseline_answered = _採用回答(baseline)
    baseline_predicted = baseline.回答ラベル if baseline_answered else None
    if baseline_answered and predicted is not None and predicted != baseline_predicted:
        if not bool(getattr(judge, "拡張採用", False)):
            raise RuntimeError(f"非退行証明なしの既存回答変更: index={index}")

    initial_labels = _候補ラベル群(initial_refs)
    final_labels = _候補ラベル群(final_refs)
    return {
        "番号": index,
        "正解ラベル": gold,
        "予測ラベル": predicted,
        "正答": predicted == gold,
        "回答済み": predicted is not None,
        "終端": run.終端.value,
        "初期予測ラベル": baseline_predicted,
        "初期正答": baseline_predicted == gold,
        "初期回答済み": baseline_answered,
        "初期参照件数": len(initial_refs),
        "最終参照件数": len(final_refs),
        "初期候補ラベル群": list(initial_labels),
        "最終候補ラベル群": list(final_labels),
        "初期全候補被覆": len(initial_labels) == len(choices),
        "最終全候補被覆": len(final_labels) == len(choices),
        "初期参照問合せ数": initial_query_count,
        "全参照問合せ数": len(provider.calls),
        "参照拡張": len(final_refs) > len(initial_refs),
        "拡張採用": bool(getattr(judge, "拡張採用", False)),
        "問題束形成回数": kernel_count,
        "問題束署名": str(getattr(kernel, "カーネル署名", "")),
        "中核理由": list(run.理由),
    }


def _集計(rows: list[dict[str, object]]) -> tuple[dict[str, object], dict[str, object]]:
    correct = sum(bool(x["正答"]) for x in rows)
    answered = sum(bool(x["回答済み"]) for x in rows)
    baseline_correct = sum(bool(x["初期正答"]) for x in rows)
    baseline_answered = sum(bool(x["初期回答済み"]) for x in rows)
    improved = sum(bool(x["正答"]) and not bool(x["初期正答"]) for x in rows)
    regressed = sum(not bool(x["正答"]) and bool(x["初期正答"]) for x in rows)
    new_answers = sum(bool(x["回答済み"]) and not bool(x["初期回答済み"]) for x in rows)
    changed = sum(
        bool(x["初期回答済み"])
        and bool(x["回答済み"])
        and x["予測ラベル"] != x["初期予測ラベル"]
        for x in rows
    )
    terminal_counts = Counter(str(x["終端"]) for x in rows)
    metrics = {
        "正答": correct,
        "全数": len(rows),
        "正答率": 100.0 * correct / len(rows),
        "回答": answered,
        "回答率": 100.0 * answered / len(rows),
        "保留": len(rows) - answered,
        "COMMIT": terminal_counts.get("COMMIT", 0),
        "SUSPEND": terminal_counts.get("SUSPEND", 0),
        "FAIL": len(rows) - terminal_counts.get("COMMIT", 0) - terminal_counts.get("SUSPEND", 0),
        "初期参照件数": sum(int(x["初期参照件数"]) for x in rows),
        "最終参照件数": sum(int(x["最終参照件数"]) for x in rows),
        "初期全候補被覆問題数": sum(bool(x["初期全候補被覆"]) for x in rows),
        "最終全候補被覆問題数": sum(bool(x["最終全候補被覆"]) for x in rows),
        "初期参照問合せ数": sum(int(x["初期参照問合せ数"]) for x in rows),
        "全参照問合せ数": sum(int(x["全参照問合せ数"]) for x in rows),
        "参照拡張問題数": sum(bool(x["参照拡張"]) for x in rows),
        "拡張採用問題数": sum(bool(x["拡張採用"]) for x in rows),
        "問題束形成総数": sum(int(x["問題束形成回数"]) for x in rows),
    }
    transition = {
        "初期継承正答": baseline_correct,
        "初期継承回答": baseline_answered,
        "最終正答": correct,
        "最終回答": answered,
        "改善": improved,
        "退行": regressed,
        "新規回答": new_answers,
        "基準回答変更": changed,
    }
    return metrics, transition


def GPQA中核正本を実行(出力: Path) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="minidora-gpqa-canonical-") as td:
        csv_path, zip_hash, csv_hash = _download_dataset(Path(td))
        cases = _load_cases(csv_path)
    if len(cases) != 198 or csv_hash != GPQA正本資料集合CSV_SHA256:
        raise RuntimeError(f"GPQA正本資料不一致: n={len(cases)} sha={csv_hash}")

    rows: list[dict[str, object]] = []
    for index, (question, choices, gold) in enumerate(cases):
        row = _一問を実行(index, question, tuple(choices), gold)
        rows.append(row)
        print(
            f"CASE {index + 1:03d}/198 terminal={row['終端']} pred={row['予測ラベル']} "
            f"correct={row['正答']} refs={row['初期参照件数']}->{row['最終参照件数']}",
            flush=True,
        )

    metrics, transition = _集計(rows)
    if metrics["問題束形成総数"] != 198:
        raise RuntimeError("問題束一問一形成の総数が198ではない")
    payload: dict[str, object] = {
        "契約形式": "minidora.gpqa.current-kernel-run.v3",
        "評価条件": {
            "外部評価": "GPQA Diamond",
            "資料集合ZIP_SHA256": zip_hash,
            "資料集合CSV_SHA256": csv_hash,
            "全問題数": 198,
            "選択番号群": list(range(198)),
            "選択肢シャッフル種": 0,
            "OpenAlex有効": False,
            "EuropePMC有効": True,
            "Crossref有効": True,
            "Wikipedia言語群": ["en"],
            "参照方式": "LIVE_ONLY",
            "固定参照資料許可": False,
            "中核入口": "HDS駆動コア.選択実行",
            "既存能力継承": True,
            "学習循環": True,
            "外付け能力モジュール": False,
            "科学専門モジュール": False,
            "旧HDS監督": False,
            "問題束一問一形成": True,
            "正解利用境界": "中核実行後の採点のみ",
            "リポジトリ版": _リポジトリ版(),
        },
        "指標": metrics,
        "実行内状態遷移": transition,
        "個票": rows,
    }
    出力.parent.mkdir(parents=True, exist_ok=True)
    出力.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


__all__ = ["GPQA中核正本を実行"]
