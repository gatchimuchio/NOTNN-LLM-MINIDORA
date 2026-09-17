"""人工資料でHDS全体運用を実演する。外部ベンチの点数とは扱わない。"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from minidora.HDS運用 import HDS運用セッション


def main():
    parser = argparse.ArgumentParser(description="HDS全体運用の同期実演")
    parser.add_argument("--output",type=Path)
    args = parser.parse_args()
    for stream in (sys.stdout,sys.stderr):
        if hasattr(stream,"reconfigure"):
            stream.reconfigure(encoding="utf-8",errors="strict")
    会話 = HDS運用セッション("全体運用実演")
    入力 = (
        "2+3",
        '資料「A」を登録:{"内訳":{"売上":75,"費用":50,"単位":"円"}}',
        '資料「B」を登録:{"内訳":{"売上":60,"費用":40,"単位":"円"}}',
        "この2つの売上を比較して",
        "訂正:属性は費用です",
        "詳しく説明して",
        '資料「A」を更新:{"内訳":{"売上":75,"費用":70,"単位":"円"}}',
        "再計算して",
        "知識「基礎」を登録:太郎は猫です。すべての猫は哺乳類です。",
        "資料「基礎」から「太郎は哺乳類である」の根拠を説明して",
        "短く説明して",
    )
    記録 = []
    for 文 in 入力:
        結果 = 会話.応答(文)
        記録.append({"入力":文,**結果.辞書化()})
        print(f"[{結果.状態}] {文}\n{結果.本文}\n")
        if not 結果.成立:
            raise RuntimeError("実演依頼が不成立:"+結果.本文)
    保存 = 会話.保存()
    復元 = HDS運用セッション.復元(保存)
    結果 = 復元.応答("詳しく説明して")
    if not 結果.成立:
        raise RuntimeError("保存復元後の説明が不成立")
    記録.append({"入力":"保存復元後の詳細説明",**結果.辞書化()})
    出力 = {"種類":"人工資料による全体運用の実動作", "成立数":len(記録),"記録":記録,
            "限界":"公開Web・GPT-4比較・任意自然言語の性能値ではない"}
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(出力,ensure_ascii=False,indent=2),encoding="utf-8")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
