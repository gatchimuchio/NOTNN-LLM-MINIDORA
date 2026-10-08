from __future__ import annotations

import argparse
import inspect
import json
from pathlib import Path


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
    from minidora.HDS選択継承循環 import HDS選択継承供給, HDS選択継承設定
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
        rows.append({
            "番号": case["index"],
            "資料系列": case["evidence_set"],
            "正解ラベル": case["gold"],
            "資料件数": len(refs),
            "評価状態": getattr(raw, "状態", None),
            "評価ラベル": getattr(raw, "回答ラベル", None),
            "評価正答": getattr(raw, "回答ラベル", None) == case["gold"],
            "理由": list(getattr(raw, "理由", ())),
        })

    Path(args.output).write_text(
        json.dumps({"revision": payload["revision"], "rows": rows}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
