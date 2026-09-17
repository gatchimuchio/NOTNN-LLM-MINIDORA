"""人工資料で、知識形成・手順再現・原記録同期を通常入口から実演する。"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from minidora.HDS運用 import HDS運用セッション


def main():
    parser = argparse.ArgumentParser(description="HDS全体運用v2の人工資料実演")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="strict")
    記録 = []
    def 実行(会話, 入力, 必須=()):
        起点 = time.monotonic()
        結果 = 会話.応答(入力)
        if not 結果.成立 or any(語 not in 結果.本文 for 語 in 必須):
            raise RuntimeError("実演不成立:" + 結果.本文)
        記録.append({"会話": 会話.ID, "入力": 入力, "秒": time.monotonic() - 起点, **結果.辞書化()})
        print(f"[{結果.状態}] {入力}\n{結果.本文}\n")
        return 結果
    知識 = HDS運用セッション("知識実演", 手順形成=False)
    実行(知識, "知識「観測」を登録:太郎は猫です。")
    実行(知識, "知識「規則」を登録:すべての猫は哺乳類です。")
    実行(知識, "知識から「太郎は哺乳類です」の根拠を説明して", ("「支持」",))
    実行(知識, "知識「反証」を登録:太郎は哺乳類ではない。")
    if 知識.状態()["前回有効"]:
        raise RuntimeError("知識追加後に古い結論が有効")
    実行(知識, "再計算して", ("反証",))
    知識 = HDS運用セッション.復元(知識.保存())
    実行(知識, "資料「規則」の原文を再参照して", ("すべての猫",))

    計算 = HDS運用セッション("手順実演", 再利用=False)
    実行(計算, '資料「A」を登録:{"売上":75,"単位":"円"}')
    実行(計算, '資料「B」を登録:{"売上":60,"単位":"円"}')
    初回 = 実行(計算, "この2つの売上を比較して", ("-15円",))
    if not 初回.追跡["手順形成"]["再現工程数"] or 計算.状態()["形成手順数"] != 1:
        raise RuntimeError("成功した純粋手順が形成されていない")
    実行(計算, '資料「A」を更新:{"売上":90,"単位":"円"}')
    if 計算.状態()["前回有効"]:
        raise RuntimeError("元資料更新後に古い成果が有効")
    更新 = 実行(計算, "再計算して", ("-30円",))
    if not 更新.追跡["手順形成"]["手順再利用"] or any(行["再利用"] for 行 in 更新.追跡["能力試行"]):
        raise RuntimeError("手順再利用と回答値のキャッシュが分離されていない")
    計算 = HDS運用セッション.復元(計算.保存())
    復元 = 実行(計算, "再計算して", ("-30円",))
    if not 復元.追跡["手順形成"]["手順再利用"]:
        raise RuntimeError("保存復元後に手順が使われない")
    実行(計算, "資料「A」の原文を再参照して", ("90",))
    出力 = {"種類": "人工資料の通常運用実演", "成立数": len(記録), "記録": 記録,
            "知識資産数": 知識.状態()["知識資産数"], "形成手順数": 計算.状態()["形成手順数"],
            "限界": "有限構文と純粋作用の接続検証。GPT-4比較・公開Web性能・新しい一般法則の獲得ではない"}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(出力, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
