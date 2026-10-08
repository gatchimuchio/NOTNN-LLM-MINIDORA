from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

対象問題 = (7, 13, 89, 116, 117, 121, 124, 163, 167, 173, 176, 186)


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


def _refs(root):
    out = {}
    for path in root.rglob("*.json"):
        if ".checkpoints" not in str(path.parent):
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            index = payload.get("完了問題番号")
            if index not in 対象問題:
                continue
            state = _decode(payload["状態"])
            normalized = []
            for source in state.get("継続参照記憶", ()):
                if not isinstance(source, dict):
                    continue
                row = dict(source)
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
            if index not in out or len(normalized) > len(out[index]):
                out[index] = normalized
        except Exception:
            continue
    return out


def _observed(root):
    rows = {}
    for path in root.rglob("gpqa_parallel_*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        for row in payload.get("個票", ()):
            if row.get("番号") in 対象問題:
                rows[row["番号"]] = row
    return rows


def _cases(source):
    source = source.resolve()
    path = source / "tools" / "GPQA現行測定.py"
    spec = importlib.util.spec_from_file_location("gpqa_loader", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.path.insert(0, str(source / "tools"))
    try:
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            csv_path, _zh, _ch = module._download_dataset(Path(directory))
            return module._load_cases(csv_path)
    finally:
        sys.path.pop(0)


def _write(path, cases, refs, evidence):
    rows = []
    for index in 対象問題:
        q, choices, gold = cases[index]
        rows.append({"index": index, "question": q, "choices": list(choices), "gold": gold,
                     "references": refs[index], "evidence_set": evidence})
    path.write_text(json.dumps({"revision": evidence, "cases": rows}, ensure_ascii=False), encoding="utf-8")


def _run(source, worker, input_path, output_path):
    source, worker = source.resolve(), worker.resolve()
    env = dict(os.environ)
    env["PYTHONPATH"] = str(source / "src")
    subprocess.run([sys.executable, str(worker), "--input", str(input_path.resolve()),
                    "--output", str(output_path.resolve())], cwd=str(source), env=env, check=True)
    return json.loads(output_path.read_text(encoding="utf-8"))["rows"]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--best-source", type=Path, required=True)
    p.add_argument("--current-source", type=Path, required=True)
    p.add_argument("--best-evidence", type=Path, required=True)
    p.add_argument("--current-evidence", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    best_refs, current_refs = _refs(a.best_evidence.resolve()), _refs(a.current_evidence.resolve())
    missing = {"best": sorted(set(対象問題)-set(best_refs)), "current": sorted(set(対象問題)-set(current_refs))}
    if missing["best"] or missing["current"]:
        raise RuntimeError("checkpoint不足:" + repr(missing))
    cases = _cases(a.current_source)
    observed = {"best42": _observed(a.best_evidence.resolve()), "current38": _observed(a.current_evidence.resolve())}
    worker = Path(__file__).with_name("GPQA固定資料高速worker.py")
    with tempfile.TemporaryDirectory() as directory:
        d = Path(directory)
        inputs = {"best42": d/"best.json", "current38": d/"current.json"}
        _write(inputs["best42"], cases, best_refs, "best42")
        _write(inputs["current38"], cases, current_refs, "current38")
        result = {}
        for code, source in (("best42-code", a.best_source), ("current-code", a.current_source)):
            for evidence in ("best42", "current38"):
                result[f"{code}|{evidence}"] = _run(source, worker, inputs[evidence], d/(code+"-"+evidence+".json"))
    maps = {name: {(r["資料系列"], r["番号"]): r for r in rows} for name, rows in result.items()}
    details = []
    for i in 対象問題:
        row = {"番号":i, "正解":cases[i][2],
               "best42観測":observed["best42"].get(i,{}).get("予測ラベル"),
               "current38観測":observed["current38"].get(i,{}).get("予測ラベル")}
        for name, m in maps.items():
            ev=name.split("|",1)[1]; v=m[(ev,i)]
            row[name]={"評価":v["評価ラベル"],"正答":v["評価正答"],"資料件数":v["資料件数"]}
        details.append(row)
    def diff(left,right,evidence):
        return [i for i in 対象問題 if maps[left][(evidence,i)]["評価ラベル"] != maps[right][(evidence,i)]["評価ラベル"]]
    summary={
        "コード差_best42資料":diff("best42-code|best42","current-code|best42","best42"),
        "コード差_current38資料":diff("best42-code|current38","current-code|current38","current38"),
        "入力差_best42code":[i for i in 対象問題 if maps["best42-code|best42"][("best42",i)]["評価ラベル"] != maps["best42-code|current38"][("current38",i)]["評価ラベル"]],
        "入力差_currentcode":[i for i in 対象問題 if maps["current-code|best42"][("best42",i)]["評価ラベル"] != maps["current-code|current38"][("current38",i)]["評価ラベル"]],
    }
    a.out.resolve().write_text(json.dumps({"summary":summary,"details":details},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__ == "__main__":
    main()
