"""人工の証拠資料を比較し、一致・競合・留保を利用者向け文章へ構成する。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from minidora.能力合成 import 能力合成器, 合成計画, 合成工程, 素材参照
from minidora.証拠統合接続 import 証拠統合Module
from minidora.応答構成接続 import 応答構成Module
from minidora.応答構成 import 応答記録整合
from minidora.製品版.型 import 能力結果, 参照資料


def main() -> int:
    if hasattr(sys.stdout,"reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--値",type=int,default=120)
    parser.add_argument("--競合",action="store_true")
    parser.add_argument("--留保",action="store_true")
    parser.add_argument("--形式",choices=("段落","箇条書き"),default="段落")
    parser.add_argument("--詳細度",choices=("要点","詳細"),default="要点")
    parser.add_argument("--最大文字数",type=int,default=20000)
    args=parser.parse_args()
    if not 0<=args.値<=1000000:
        parser.error("--値は0〜1000000")
    first=f"装置Aの電圧は{args.値} Vです。"
    second=(f"装置Aの電圧は{args.値+1} Vです。" if args.競合 else f"装置Aの電圧は{args.値*1000} mVです。")
    if args.留保:
        second+="ただしこれは仮定です。"
    refs=(参照資料("a","人工資料A","局所デモ",本文=first),参照資料("b","人工資料B","局所デモ",本文=second))
    data={"資料":能力結果(True,"",参照=refs),"比較指示":能力結果(True,"数値主張を比較"),
          "比較設定":能力結果(True,"",データ={"対象":"装置A","属性":"電圧","単位":"V"}),
          "回答指示":能力結果(True,"比較結果を回答へ構成"),
          "回答設定":能力結果(True,"",データ={"形式":args.形式,"詳細度":args.詳細度,"最大文字数":args.最大文字数})}
    plan=合成計画((合成工程("証拠",("証拠統合",),"比較指示",(素材参照("入力","資料"),),"比較設定"),
                   合成工程("回答",("応答構成",),"回答指示",(素材参照("工程","証拠"),),"回答設定")),("回答",))
    result=能力合成器((証拠統合Module().登録(),応答構成Module().登録())).実行(plan,data)
    answer=result.出力[0][1] if result.成立 else None
    print(json.dumps({"範囲":"人工資料の数値比較からの回答構成。自由作文・LIVE評価ではない。",
                      "状態":result.状態,"理由":result.理由,
                      "回答":answer.本文 if answer else "",
                      "項目状態":answer.データ["項目状態"] if answer else [],
                      "実行能力":[x.能力 for x in result.履歴],
                      "合成監査":result.監査整合(),"回答監査":応答記録整合(answer) if answer else False},ensure_ascii=False,indent=2))
    return 0 if answer is not None and 応答記録整合(answer) else 2


if __name__=="__main__":
    raise SystemExit(main())
