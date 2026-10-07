from __future__ import annotations

from collections import Counter
from dataclasses import asdict, is_dataclass
from enum import Enum
from time import perf_counter_ns, process_time_ns
import json
import os
from pathlib import Path
import subprocess
import tempfile
from threading import Lock

try:
    from .GPQA現行測定 import _download_dataset, _load_cases
except ImportError:
    from GPQA現行測定 import _download_dataset, _load_cases
from minidora.HDS参照 import HDS参照検索
from minidora.参照 import 参照取得診断, 参照検索を診断
from minidora.HDS構文化器_v1 import 公開HDSコンパイラ
from minidora.HDS実行主体 import HDS終端
from minidora.HDS選択実行系 import HDS選択実行結果
from minidora.HDS選択継承循環 import (
    回答成果名,
    参照成果名,
    初回評価参照成果名,
    基準結果主体名,
    現行結果成果名,
    非退行判定成果名,
)
from minidora.HDS駆動コア import HDS駆動コア
from minidora.標準参照 import 一般知識参照供給器
from minidora.計算実行器 import 計算実行器


GPQA正本資料集合CSV_SHA256 = "41d1213cd7a4998605a26c2798500652572007161b3a92817ba46b35befcd305"


class _記録参照供給器:
    並列安全 = False
    診断内再試行 = True
    名称 = "MINIDORA_GPQA正本記録"

    def __init__(self, base) -> None:
        self.base = base
        self.calls: list[str] = []
        self.lock = Lock()
        self.実取得回数 = self.再利用回数 = self.延期回数 = 0
        self.外部時間ns = 0
        期限 = os.getenv("GPQA_DEADLINE_EPOCH", "")
        if 期限 and hasattr(base, "締切epoch"): base.締切epoch = float(期限)

    @property
    def 全観測記録(self):
        return tuple(getattr(self.base, "全観測記録", ()))

    def _記録(self, query: str) -> str:
        normalized = " ".join(str(query).split())
        with self.lock:
            self.calls.append(normalized)
        return normalized

    def 検索診断(self, query: str, limit: int = 8):
        self._記録(query)
        direct = getattr(self.base, "検索診断", None)
        開始 = perf_counter_ns()
        try:
            記録群, 診断 = direct(query, limit) if callable(direct) else 参照検索を診断(self.base, query, limit)
            with self.lock:
                self.実取得回数 += 診断.実取得回数
                self.再利用回数 += int(診断.再利用)
                self.延期回数 += int(bool(診断.延期理由))
            return 記録群, 診断
        finally:
            with self.lock: self.外部時間ns += perf_counter_ns() - 開始

    def 検索(self, query: str, limit: int = 8):
        return self.検索診断(query, limit)[0]


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


def _一問を実行(
    index: int,
    question: str,
    choices: tuple[str, ...],
    gold: str,
    *,
    構文化器: 公開HDSコンパイラ,
    中核: HDS駆動コア,
    記録=None,
) -> dict[str, object]:
    開始ns = perf_counter_ns()
    開始CPU = process_time_ns()
    def 進行(段階):
        if 記録 is not None:
            記録({"段階": 段階})
    進行("問題束形成")
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

    kernel_count = 0
    original_kernel = 構文化器.問題コンパイル束

    def counted_kernel(*args, **kwargs):
        nonlocal kernel_count
        kernel_count += 1
        return original_kernel(*args, **kwargs)

    構文化器.問題コンパイル束 = counted_kernel
    try:
        kernel = 構文化器.問題コンパイル束(question, choices)
    finally:
        構文化器.問題コンパイル束 = original_kernel
    question_ir = kernel.意味IR
    requests = tuple(中核.選択観測要求を適応(kernel.参照観測要求))
    構文化終了ns = perf_counter_ns()
    構文化終了CPU = process_time_ns()
    進行("初期参照取得")
    initial_diagnostics: list[参照取得診断] = []
    from minidora.入力系.選択契約 import 選択入力を接続
    入力接続 = 選択入力を接続(kernel.コア入力)
    initial_refs = tuple(HDS参照検索(
        provider, question_ir, 観測要求=requests, 診断収集=initial_diagnostics,
    )) if 入力接続.外部読取可 else ()
    initial_query_count = len(provider.calls)
    参照終了ns = perf_counter_ns()
    参照終了CPU = process_time_ns()
    進行("中核実行")

    前状態署名 = 中核.継続状態署名
    前継続記憶資料件数 = 中核.継続記憶資料件数
    前継続認識件数 = 中核.継続認識件数
    前継続形成関係件数 = 中核.継続形成関係件数
    前適応経験数 = 中核.適応経験数
    前観測経路経験数 = 中核.観測経路経験数
    前継続参照件数 = 中核.継続参照件数
    run = 中核.選択実行(
        question,
        choices,
        初期参照=initial_refs,
        初期参照診断=tuple(initial_diagnostics),
        参照供給器=provider,
        計算実行器_=計算実行器(),
        既存能力継承=True,
        最大回復回数=6,
        カーネル正本=kernel,
    )
    中核終了ns = perf_counter_ns()
    中核終了CPU = process_time_ns()
    進行("個票形成")
    if kernel_count != 1:
        raise RuntimeError(f"問題束の形成回数が1ではない: index={index} count={kernel_count}")

    後状態署名 = 中核.継続状態署名
    後継続記憶資料件数 = 中核.継続記憶資料件数
    後継続認識件数 = 中核.継続認識件数
    後継続形成関係件数 = 中核.継続形成関係件数
    後適応経験数 = 中核.適応経験数
    後観測経路経験数 = 中核.観測経路経験数
    後継続参照件数 = 中核.継続参照件数
    products = run.状態.成果辞書()
    subjects = run.状態.主体辞書()
    current = products.get(現行結果成果名)
    baseline = subjects.get(基準結果主体名)
    final_refs = products.get(参照成果名, initial_refs)
    初回評価参照 = products.get(初回評価参照成果名, ())
    answer = products.get(回答成果名)
    judge = products.get(非退行判定成果名)
    if not isinstance(current, HDS選択実行結果):
        履歴要約 = tuple(x.作用ID for x in run.履歴)
        停止 = run.停止種別.value if run.停止種別 is not None else None
        raise RuntimeError(
            f"現行結果欠落: index={index}; terminal={run.終端.value}; stop={停止}; "
            f"reason={tuple(run.理由)}; residual={tuple(sorted(run.状態.残差))}; "
            f"actions={履歴要約}; excluded={tuple(run.指示除外)}; "
            f"reeval={tuple(sorted(run.状態.再評価待ち))}; products={tuple(sorted(products))}"
        )
    if not isinstance(baseline, HDS選択実行結果):
        raise RuntimeError(f"基準結果欠落: index={index}")
    if not isinstance(final_refs, tuple):
        raise RuntimeError(f"最終参照形式不正: index={index}")
    if not isinstance(初回評価参照, tuple):
        raise RuntimeError(f"初回評価参照形式不正: index={index}")

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
        "初期参照取得障害数": sum(x.状態 in {"失敗", "縮退"} for x in initial_diagnostics),
        "全参照問合せ数": len(provider.calls),
        "参照拡張": len(final_refs) > len(initial_refs),
        "拡張採用": bool(getattr(judge, "拡張採用", False)),
        "問題束形成回数": kernel_count,
        "問題束署名": str(getattr(kernel, "カーネル署名", "")),
        "処理前継続状態署名": 前状態署名,
        "処理後継続状態署名": 後状態署名,
        "処理前継続記憶資料件数": 前継続記憶資料件数,
        "処理後継続記憶資料件数": 後継続記憶資料件数,
        "処理前継続認識件数": 前継続認識件数,
        "処理後継続認識件数": 後継続認識件数,
        "処理前継続形成関係件数": 前継続形成関係件数,
        "処理後継続形成関係件数": 後継続形成関係件数,
        "処理前適応経験数": 前適応経験数,
        "処理後適応経験数": 後適応経験数,
        "処理前観測経路経験数": 前観測経路経験数,
        "処理後観測経路経験数": 後観測経路経験数,
        "処理前継続参照件数": 前継続参照件数,
        "処理後継続参照件数": 後継続参照件数,
        "初回評価参照件数": len(初回評価参照),
        "中核理由": list(run.理由),
        "座標面数": len(run.状態.操作座標.面) if run.状態.操作座標 else 0,
        "末端座標面数": len(run.状態.操作座標.末端面) if run.状態.操作座標 else 0,
        "未接続座標": list(run.状態.指示関係.未接続座標) if run.状態.指示関係 else ["未形成"],
        "外部取得計装": {"実取得回数": provider.実取得回数,
                         "計測対象": "供給器の取得呼出。内部の物理HTTP要求数ではない",
                         "物理HTTP要求数": None, "I/O待機単独秒": None,
                         "再利用回数": provider.再利用回数,
                         "延期回数": provider.延期回数, "待機を含む秒": provider.外部時間ns / 1e9},
        "目的関係判定": _JSON化(products.get("HDS選択:目的関係判定")),
        "停止種別": run.停止種別.value if run.停止種別 is not None else None,
        "最終残差": sorted(run.状態.残差),
        "計装": asdict(run.計装),
        "作用履歴": [{"作用ID": h.作用ID, "理由": list(h.理由),
                        "進展根拠": list(h.進展根拠), "目的進展": h.目的進展,
                        "使用座標面": list(h.使用座標面), "目的条件判定": list(h.目的条件判定),
                        "目的進展対応": _JSON化(h.目的進展対応),
                        "内容進展": list(h.内容進展ノード), "管理進展": list(h.管理進展ノード)}
                       for h in run.履歴],
        "採用監査": _JSON化(products.get("HDS選択:採用監査")),
        "CPU時間内訳秒": {"問題束形成": (構文化終了CPU - 開始CPU) / 1e9,
                          "初期参照取得": (参照終了CPU - 構文化終了CPU) / 1e9,
                          "中核実行": (中核終了CPU - 参照終了CPU) / 1e9,
                          "個票形成": (process_time_ns() - 中核終了CPU) / 1e9},
        "CPU計測範囲": "当該ワーカープロセス。経過時間との差はI/O待機だけを意味しない",
        "時間内訳秒": {"問題束形成": (構文化終了ns - 開始ns) / 1e9,
                      "初期参照取得": (参照終了ns - 構文化終了ns) / 1e9,
                      "中核実行": (中核終了ns - 参照終了ns) / 1e9,
                      "個票形成": (perf_counter_ns() - 中核終了ns) / 1e9},
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
        "初期参照取得障害数": sum(int(x["初期参照取得障害数"]) for x in rows),
        "全参照問合せ数": sum(int(x["全参照問合せ数"]) for x in rows),
        "参照拡張問題数": sum(bool(x["参照拡張"]) for x in rows),
        "拡張採用問題数": sum(bool(x["拡張採用"]) for x in rows),
        "問題束形成総数": sum(int(x["問題束形成回数"]) for x in rows),
        "最終継続記憶資料件数": int(rows[-1]["処理後継続記憶資料件数"]) if rows else 0,
        "最終継続認識件数": int(rows[-1]["処理後継続認識件数"]) if rows else 0,
        "最終継続形成関係件数": int(rows[-1]["処理後継続形成関係件数"]) if rows else 0,
        "最終適応経験数": int(rows[-1]["処理後適応経験数"]) if rows else 0,
        "最終継続参照件数": int(rows[-1]["処理後継続参照件数"]) if rows else 0,
        "継続状態変化問題数": sum(x["処理前継続状態署名"] != x["処理後継続状態署名"] for x in rows),
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


def _JSON化(値):
    if isinstance(値, Enum): return 値.value
    if isinstance(値, (set, frozenset)): return [_JSON化(x) for x in sorted(値, key=str)]
    if is_dataclass(値):
        return _JSON化(asdict(値))
    if isinstance(値, dict):
        return {str(k): _JSON化(v) for k, v in 値.items()}
    if isinstance(値, (tuple, list)):
        return [_JSON化(v) for v in 値]
    if 値 is None or type(値) in (str, int, float, bool):
        return 値
    raise TypeError("個票へ未対応の値型が渡された: " + type(値).__name__)


def GPQA中核正本を実行(出力: Path) -> dict[str, object]:
    try:
        from .GPQA実測管理 import GPQAを測定, 原子的保存
    except ImportError:
        from GPQA実測管理 import GPQAを測定, 原子的保存
    内容 = GPQAを測定(出力, 方式="直列")
    if 内容.get("実測", {}).get("完走") is not True:
        raise RuntimeError("GPQA全数未完了。途中個票と停止箇所は出力済み")
    metrics, transition = _集計(内容["個票"])
    内容["指標"] = metrics
    内容["実行内状態遷移"] = transition
    原子的保存(出力, 内容)
    return 内容


__all__ = ["GPQA中核正本を実行"]
