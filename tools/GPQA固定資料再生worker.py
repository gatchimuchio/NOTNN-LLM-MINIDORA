from __future__ import annotations

import argparse
import inspect
import json
from pathlib import Path


def _json_value(value):
    if value is None or type(value) in (str, int, float, bool):
        return value
    if isinstance(value, dict):
        return {str(k): _json_value(v) for k, v in value.items()}
    if isinstance(value, (tuple, list, set, frozenset)):
        return [_json_value(x) for x in value]
    if hasattr(value, "value") and type(getattr(value, "value", None)) in (str, int, float, bool):
        return value.value
    if hasattr(value, "__dataclass_fields__"):
        return {k: _json_value(getattr(value, k)) for k in value.__dataclass_fields__}
    return repr(value)


def _record(row, record_type):
    params = inspect.signature(record_type).parameters
    values = dict(row)
    values["条件"] = tuple(tuple(x) for x in values.get("条件", ()))
    values["観測経路履歴"] = tuple(
        tuple(tuple(x) for x in group) for group in values.get("観測経路履歴", ())
    )
    values["旧版"] = ()
    return record_type(**{k: values[k] for k in params if k in values})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    from minidora.HDS構文化器_v1 import 公開HDSコンパイラ
    from minidora.HDS駆動コア import HDS駆動コア
    from minidora.HDS選択継承循環 import HDS選択継承供給, HDS選択継承設定, 回答成果名, 現行結果成果名
    from minidora.参照 import 参照記録

    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    compiler = 公開HDSコンパイラ()
    rows = []
    for case in payload["cases"]:
        refs = tuple(_record(x, 参照記録) for x in case["references"])
        kernel = compiler.問題コンパイル束(case["question"], tuple(case["choices"]))
        supply = HDS選択継承供給(
            kernel,
            compiler,
            refs,
            既存能力継承=True,
            参照供給器=None,
            設定=HDS選択継承設定(0),
        )
        raw = supply._評価(refs)
        relation = supply._目的関係評価(refs)

        core = HDS駆動コア(HDSコンパイラ=compiler, 最大作用回数=40)
        run = core.選択実行(
            case["question"],
            tuple(case["choices"]),
            初期参照=refs,
            参照供給器=None,
            最大回復回数=0,
            カーネル正本=kernel,
        )
        products = run.状態.成果辞書()
        current = products.get(現行結果成果名)
        rows.append({
            "番号": case["index"],
            "資料系列": case["evidence_set"],
            "正解ラベル": case["gold"],
            "資料件数": len(refs),
            "生評価状態": getattr(raw, "状態", None),
            "生評価ラベル": getattr(raw, "回答ラベル", None),
            "生評価正答": getattr(raw, "回答ラベル", None) == case["gold"],
            "関係一意成立": getattr(relation, "一意成立", None),
            "関係照合数": getattr(relation, "照合数", None),
            "終端": getattr(run.終端, "value", str(run.終端)),
            "採用ラベル": products.get(回答成果名),
            "採用正答": products.get(回答成果名) == case["gold"],
            "現行ラベル": getattr(current, "回答ラベル", None),
            "理由": list(getattr(run, "理由", ())),
            "残差": sorted(run.状態.残差),
        })

    Path(args.output).write_text(
        json.dumps({"revision": payload["revision"], "rows": rows}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
