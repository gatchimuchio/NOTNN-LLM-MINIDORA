from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


反転問題 = (7, 13, 89, 116, 117, 121, 124, 163, 167, 173, 176, 186)
対照問題 = (0, 1, 2, 3, 4, 5, 6, 8, 9, 10, 20, 40, 60, 80, 100, 120, 140, 160, 180, 197)
対象問題 = tuple(sorted(set((*反転問題, *対照問題))))


def _decode(value):
    if value is None or type(value) in (str, int, bool):
        return value
    if isinstance(value, list):
        return [_decode(x) for x in value]
    if not isinstance(value, dict):
        return value
    if set(value) == {"float"}:
        return float.fromhex(value["float"])
    if set(value) == {"tuple"}:
        return tuple(_decode(x) for x in value["tuple"])
    if set(value) == {"dict"}:
        return {_decode(k): _decode(v) for k, v in value["dict"]}
    if "fields" in value and "type" in value:
        return {k: _decode(v) for k, v in value["fields"].items()}
    return {k: _decode(v) for k, v in value.items()}


def _checkpoint_references(root: Path):
    out = {}
    for path in root.rglob("*.json"):
        if ".checkpoints" not in str(path.parent):
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            index = payload.get("完了問題番号")
            if type(index) is not int:
                continue
            state = _decode(payload["状態"])
            refs = state.get("継続参照記憶", ())
            normalized = []
            for row in refs:
                if not isinstance(row, dict):
                    continue
                row = dict(row)
                history = tuple(row.get("観測経路履歴", ()))
                conditions = [tuple(x) for x in row.get("条件", ())]
                for group in history:
                    for item in group:
                        item = tuple(item)
                        if str(item[0]).startswith(("hds_query_", "hds_observation_", "observed_by_")) and item not in conditions:
                            conditions.append(item)
                row["条件"] = conditions
                row["観測経路履歴"] = history
                row["旧版"] = []
                normalized.append(row)
            # shardは問題独立なので、同じ番号は一つだけ。重複時は資料数の多い方を保持する。
            if index not in out or len(normalized) > len(out[index]):
                out[index] = normalized
        except Exception:
            continue
    return out


def _observed_rows(root: Path):
    out = {}
    for path in root.rglob("gpqa_parallel_*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        for row in payload.get("個票", ()):
            index = row.get("番号")
            if type(index) is int:
                out[index] = row
    return out


def _load_cases(source: Path):
    path = source / "tools" / "GPQA現行測定.py"
    spec = importlib.util.spec_from_file_location("gpqa_dataset_loader", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.path.insert(0, str(source / "tools"))
    try:
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory(prefix="gpqa-fixed-replay-") as directory:
            csv_path, _zip_hash, _csv_hash = module._download_dataset(Path(directory))
            return module._load_cases(csv_path)
    finally:
        sys.path.pop(0)


def _write_input(path, cases, refs, observed, evidence_set, revision):
    rows = []
    for index in 対象問題:
        question, choices, gold = cases[index]
        rows.append({
            "index": index,
            "question": question,
            "choices": list(choices),
            "gold": gold,
            "references": refs[index],
            "evidence_set": evidence_set,
            "observed_label": observed.get(index, {}).get("予測ラベル"),
            "observed_correct": observed.get(index, {}).get("正答"),
        })
    path.write_text(json.dumps({"revision": revision, "cases": rows}, ensure_ascii=False), encoding="utf-8")


def _run_worker(source, worker, input_path, output_path):
    env = dict(os.environ)
    env["PYTHONPATH"] = str(source / "src")
    subprocess.run(
        [sys.executable, str(worker), "--input", str(input_path), "--output", str(output_path)],
        cwd=source,
        env=env,
        check=True,
    )
    return json.loads(output_path.read_text(encoding="utf-8"))["rows"]


def _map(rows):
    return {(row["資料系列"], row["番号"]): row for row in rows}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--best-source", type=Path, required=True)
    parser.add_argument("--current-source", type=Path, required=True)
    parser.add_argument("--best-evidence", type=Path, required=True)
    parser.add_argument("--current-evidence", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    best_refs = _checkpoint_references(args.best_evidence)
    current_refs = _checkpoint_references(args.current_evidence)
    missing_best = sorted(set(対象問題) - set(best_refs))
    missing_current = sorted(set(対象問題) - set(current_refs))
    if missing_best or missing_current:
        raise RuntimeError(f"checkpoint不足 best={missing_best} current={missing_current}")

    best_observed = _observed_rows(args.best_evidence)
    current_observed = _observed_rows(args.current_evidence)
    cases = _load_cases(args.current_source)
    worker = Path(__file__).with_name("GPQA固定資料再生worker.py").resolve()

    with tempfile.TemporaryDirectory(prefix="gpqa-code-evidence-matrix-") as directory:
        directory = Path(directory)
        best_input = directory / "best-evidence.json"
        current_input = directory / "current-evidence.json"
        _write_input(best_input, cases, best_refs, best_observed, "best42", "evidence-best42")
        _write_input(current_input, cases, current_refs, current_observed, "current38", "evidence-current38")

        combinations = {}
        for code_name, source in (("best42-code", args.best_source), ("current-code", args.current_source)):
            for evidence_name, input_path in (("best42", best_input), ("current38", current_input)):
                output = directory / f"{code_name}-{evidence_name}.json"
                combinations[f"{code_name}|{evidence_name}"] = _run_worker(source, worker, input_path, output)

    maps = {name: _map(rows) for name, rows in combinations.items()}
    details = []
    for index in 対象問題:
        row = {
            "番号": index,
            "反転問題": index in 反転問題,
            "best42観測": best_observed.get(index, {}).get("予測ラベル"),
            "current38観測": current_observed.get(index, {}).get("予測ラベル"),
            "正解": cases[index][2],
        }
        for name, mapping in maps.items():
            evidence = name.split("|", 1)[1]
            value = mapping[(evidence, index)]
            row[name] = {
                "生評価": value["生評価ラベル"],
                "生評価正答": value["生評価正答"],
                "採用": value["採用ラベル"],
                "採用正答": value["採用正答"],
                "資料件数": value["資料件数"],
            }
        details.append(row)

    def differences(left, right, evidence, key):
        return [
            i for i in 対象問題
            if maps[left][(evidence, i)][key] != maps[right][(evidence, i)][key]
        ]

    summary = {
        "対象問題": list(対象問題),
        "反転問題": list(反転問題),
        "コード差_best42資料_生評価": differences("best42-code|best42", "current-code|best42", "best42", "生評価ラベル"),
        "コード差_best42資料_採用": differences("best42-code|best42", "current-code|best42", "best42", "採用ラベル"),
        "コード差_current38資料_生評価": differences("best42-code|current38", "current-code|current38", "current38", "生評価ラベル"),
        "コード差_current38資料_採用": differences("best42-code|current38", "current-code|current38", "current38", "採用ラベル"),
        "入力差_best42code_生評価": [
            i for i in 対象問題
            if maps["best42-code|best42"][("best42", i)]["生評価ラベル"]
            != maps["best42-code|current38"][("current38", i)]["生評価ラベル"]
        ],
        "入力差_currentcode_生評価": [
            i for i in 対象問題
            if maps["current-code|best42"][("best42", i)]["生評価ラベル"]
            != maps["current-code|current38"][("current38", i)]["生評価ラベル"]
        ],
    }
    args.out.write_text(
        json.dumps({"summary": summary, "details": details}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
