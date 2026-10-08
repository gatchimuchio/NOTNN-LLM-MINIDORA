from __future__ import annotations

import argparse
import json
from pathlib import Path

対象問題=(7,13,89,116,117,121,124,163,167,173,176,186)


def main():
    p=argparse.ArgumentParser();p.add_argument("--dir",type=Path,required=True);p.add_argument("--out",type=Path,required=True)
    a=p.parse_args();maps={}
    for path in a.dir.rglob("*.json"):
        payload=json.loads(path.read_text(encoding="utf-8"))
        if not {"code","evidence","rows"}<=set(payload):continue
        name=payload["code"]+"|"+payload["evidence"]
        maps[name]={r["番号"]:r for r in payload["rows"]}
    expected={"best42-code|best42","best42-code|current38","current-code|best42","current-code|current38"}
    if set(maps)!=expected:raise RuntimeError("四象限不足:"+repr(sorted(set(maps)^expected)))
    def diff(left,right):return [i for i in 対象問題 if maps[left][i]["評価ラベル"]!=maps[right][i]["評価ラベル"]]
    summary={
      "コード差_best42資料":diff("best42-code|best42","current-code|best42"),
      "コード差_current38資料":diff("best42-code|current38","current-code|current38"),
      "入力差_best42code":diff("best42-code|best42","best42-code|current38"),
      "入力差_currentcode":diff("current-code|best42","current-code|current38"),
    }
    details=[]
    for i in 対象問題:
        details.append({"番号":i,**{name:{"評価":m[i]["評価ラベル"],"正答":m[i]["評価正答"],"資料件数":m[i]["資料件数"]}for name,m in maps.items()}})
    a.out.write_text(json.dumps({"summary":summary,"details":details},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=="__main__":main()
