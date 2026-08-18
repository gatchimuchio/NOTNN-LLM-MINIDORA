from __future__ import annotations
from pathlib import Path
import json,sys
from .reference import 外部参照R
from .instruction import 命令形P
from .layer0 import Layer0
from .surface import 表層Adapter
from .runtime import ミニドラ

def main():
    if len(sys.argv)<2: raise SystemExit('使い方: python -m minidora.cli "日本の首都は？"')
    base=Path(__file__).resolve().parents[2]; P=命令形P.JSON(base/"p"/"命令形P.json"); R=外部参照R.JSONL(base/"data"/"参照R.jsonl"); S=表層Adapter.JSON(base/"data"/"概念語彙.json"); m=ミニドラ(Layer0(),P,R,S); out=m.問う(sys.argv[1])
    print(json.dumps({"値":out.値,"表出":out.表出,"状態":out.状態,"理由":out.理由,"参照":out.参照,"履歴":out.履歴,"未解":out.未解,"矛盾":out.矛盾},ensure_ascii=False,indent=2,default=str))

if __name__=="__main__": main()
