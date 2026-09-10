"""直近範囲外の原文を再参照し、改訂と未保存の対照を示す局所デモ。"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from minidora.長文脈管理 import 長文脈庫, 文脈登録, 文脈選択要求
from minidora.長文脈接続 import 長文脈選択Module, 長文脈要求Data
from minidora.能力合成 import 能力合成器, 合成計画, 合成工程, 素材参照
from minidora.能力合成_局所接続 import 局所能力群
from minidora.製品版.型 import 能力結果, 参照資料
from minidora.製品版.能力契約 import 能力文脈


def 原文(value):
    text = f"売上は{value}です。費用は75です。利益は45です。"
    return 能力結果(True, text, 参照=(参照資料("資料:" + str(value), "人工資料", "局所試験", 本文=text),))


def 用意(value=120):
    archive = 長文脈庫("長文脈デモ")
    rows = [文脈登録("原資料", 原文(value))]
    rows.extend(文脈登録(f"雑談:{i}", 能力結果(True, "別件の記録です。" * 30)) for i in range(100))
    archive.更新(archive.起点(), tuple(rows))
    return archive


def 抽出(archive, key="原資料"):
    request = 文脈選択要求((key,), 直近件数=0, 最大バイト数=4096)
    plan = 合成計画((
        合成工程("文脈", ("長文脈選択",), "i", (素材参照("入力", "要求"),)),
        合成工程("抽出", ("情報抽出",), "i", (素材参照("工程", "文脈"),), "抽出設定"),
    ), ("抽出",))
    data = {"要求": 長文脈要求Data(archive, request), "i": 能力結果(True, "指定処理"),
            "抽出設定": 能力結果(True, "", データ={"種別": "数字"})}
    result = 能力合成器((長文脈選択Module(archive).登録(), *局所能力群())).実行(
        plan, data, 文脈=能力文脈("", archive.起点().セッションID))
    return result


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--値", type=int, default=120)
    args = parser.parse_args()
    if not 0 <= args.値 <= 1_000_000:
        parser.error("--値は0〜1000000")
    archive = 用意(args.値)
    old = archive.選択(文脈選択要求(("原資料",), 直近件数=0, 最大バイト数=4096))
    first = 抽出(archive)
    saved = archive.保存文字列()
    restored = 長文脈庫.復元(saved)
    after_restore = 抽出(restored)
    archive.更新(archive.起点(), (文脈登録("改訂資料", 原文(731)),), 失効ID=("原資料",), 理由="利用者の明示改訂")
    stale = archive.資料化(old)
    second = 抽出(archive, "改訂資料")
    missing = 抽出(長文脈庫("長文脈デモ"))
    ok = (first.成立 and second.成立 and after_restore.成立 and not stale.成立 and not missing.成立
          and first.出力[0][1].本文 == after_restore.出力[0][1].本文 == f"{args.値}、75、45"
          and second.出力[0][1].本文 == "731、75、45")
    print(json.dumps({"範囲": "101原記録の局所対照。自由な長会話理解の評価ではない。",
        "原記録数": 101, "選択数": len(old.選択ID), "省略数": len(old.省略ID),
        "保存バイト数": len(saved.encode()), "選択包バイト数": old.バイト数,
        "初回抽出": first.出力[0][1].本文 if first.成立 else first.理由,
        "復元後抽出": after_restore.出力[0][1].本文 if after_restore.成立 else after_restore.理由,
        "改訂後抽出": second.出力[0][1].本文 if second.成立 else second.理由,
        "旧選択の利用": stale.成立, "記録なし対照": missing.成立,
        "旧原文保持": archive.原記録("原資料")["内容"]["本文"],
        "合成監査": all(r.監査整合() for r in (first, second, after_restore, missing)),
        "対照成立": ok}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
