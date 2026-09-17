from __future__ import annotations

"""MINIDORA30互換経路とHDS内包統合v3を同一GPQA LIVE入力で比較する評価専用入口。

正本値の自動置換は行わない。goldは両経路の推論完了後にのみ採点へ使用する。
"""

import argparse
from collections import Counter
from dataclasses import asdict, replace
import hashlib
import json
import os
from pathlib import Path
import random
import sys
import tempfile

根 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(根 / "src"))
sys.path.insert(0, str(根 / "tools"))

from GPQA現行測定 import _download_dataset as 資料集合取得, _load_cases as 問題群読込
from minidora.HDS実行主体 import HDS実行主体, HDS実行状態, HDS関数作用, HDS作用結果, HDS作用状態, HDS終端
from minidora.HDS構文化器_v1 import 公開HDSコンパイラ
from minidora.HDS参照 import HDS参照検索
from minidora.HDS監督選択実行系 import HDS監督選択実行
from minidora.HDS選択実行系 import HDS選択推論実行
from minidora.hds介入制御 import 標準HDS介入制御
from minidora.hds参照拡張 import HDS候補被覆優先統合, HDS追加参照検索
from minidora.参照 import 参照記録
from minidora.標準参照 import 一般知識参照供給器
from minidora.能力状態差循環 import 標準能力模型核
from minidora.計算実行器 import 計算実行器
from minidora.統合駆動_v2 import HDS検証器

選択肢ラベル = ("A", "B", "C", "D")
選択肢シャッフル種 = 0
HDS外部作用予算 = 6


def _模型評価(質問中間表現, 参照群, 構文化器):
    return HDS選択推論実行(
        質問中間表現,
        tuple(参照群),
        コンパイル=構文化器.コンパイル,
        基礎能力核=None,
        模型核=標準能力模型核(),
        正式模型評価=True,
    )


def _承認済み(選択結果) -> bool:
    return 選択結果.状態 == "APPROVE" and 選択結果.回答ラベル in 選択肢ラベル


def _計算計画(質問中間表現, 構文化器):
    構文化本体 = getattr(構文化器, "HDSコンパイラ", None)
    if 構文化本体 is None and callable(getattr(構文化器, "計算コンパイル", None)):
        構文化本体 = 構文化器
    計算コンパイル = getattr(構文化本体, "計算コンパイル", None)
    if not callable(計算コンパイル):
        return None
    try:
        計画 = 計算コンパイル(質問中間表現.原文)
    except (ValueError, TypeError):
        return None
    計算中間表現 = getattr(計画, "計算IR", None)
    if bool(getattr(計画, "参照必須", True)) or not tuple(getattr(計算中間表現, "命令列", ())):
        return None
    return 計画


def _参照署名(参照群) -> str:
    材料 = repr(tuple((項目.識別子, 項目.信頼, 項目.条件) for 項目 in 参照群)).encode("utf-8")
    return hashlib.sha256(材料).hexdigest()


def _HDSv3実行(質問中間表現, 初期参照群, 初期選択, 構文化器, 参照供給器):
    初期成果 = (("参照群", tuple(初期参照群)), ("選択結果", 初期選択))
    if _承認済み(初期選択):
        初期状態 = HDS実行状態(
            目的=("GPQA選択肢回答を形成する",),
            要求状態=frozenset({"回答確定"}),
            成立状態=frozenset({"初期評価済み", "回答確定"}),
            成果=(*初期成果, ("回答ラベル", 初期選択.回答ラベル)),
        )
        実行主体 = HDS実行主体(
            (),
            最大作用回数=4,
            最終検証器=(HDS検証器("回答ラベル形式", lambda 状態, _草案: 状態.成果辞書().get("回答ラベル") in 選択肢ラベル),),
        )
        return 実行主体.実行(初期状態)

    初期状態 = HDS実行状態(
        目的=("GPQA選択肢回答を形成する",),
        要求状態=frozenset({"回答確定"}),
        成立状態=frozenset({"初期評価済み"}),
        残差=frozenset({"回答未閉包"}),
        成果=初期成果,
    )

    作用群 = []
    計算計画 = _計算計画(質問中間表現, 構文化器)
    計算実行器_ = 計算実行器()
    前段状態 = "初期評価済み"
    外部作用数 = 0

    if 計算計画 is not None and 外部作用数 < HDS外部作用予算:
        def 計算を実行(状態):
            参照群 = tuple(状態.成果辞書().get("参照群", ()))
            try:
                実行済み = 計算実行器_.計算実行(計算計画.計算IR, dict(計算計画.初期状態))
            except (ValueError, TypeError, ZeroDivisionError) as 例外:
                return HDS作用結果(
                    HDS作用状態.成立,
                    追加状態=frozenset({"計算試行済み"}),
                    理由=("計算試行不成立", type(例外).__name__),
                )
            if 実行済み.出力 is None:
                return HDS作用結果(HDS作用状態.成立, 追加状態=frozenset({"計算試行済み"}), 理由=("計算結果なし",))
            計算参照 = 参照記録(
                識別子="compute:" + hashlib.sha256(repr((計算計画.計算IR, 計算計画.初期状態, 実行済み.出力)).encode("utf-8")).hexdigest(),
                対象=質問中間表現.認知世界ID or "計算対象",
                内容=f"計算結果 {実行済み.出力}",
                由来="MINIDORA汎用計算実行",
                供給器="MINIDORA計算実行器",
                信頼=1.0,
                意味キー="計算結果",
                値=実行済み.出力,
                条件=(("hds_query_kind", "compute"),),
                意味確定=True,
            )
            更新参照群 = 参照群 if any(x.識別子 == 計算参照.識別子 for x in 参照群) else (*参照群, 計算参照)
            return HDS作用結果(
                HDS作用状態.成立,
                追加状態=frozenset({"計算試行済み"}),
                成果=(("参照群", tuple(更新参照群)),),
                理由=("決定論計算を実行",),
            )

        def 計算後評価(状態):
            参照群 = tuple(状態.成果辞書().get("参照群", ()))
            選択結果 = _模型評価(質問中間表現, 参照群, 構文化器)
            if _承認済み(選択結果):
                return HDS作用結果(
                    HDS作用状態.成立,
                    追加状態=frozenset({"計算後再評価済み", "回答確定"}),
                    解消残差=frozenset({"回答未閉包"}),
                    成果=(("選択結果", 選択結果), ("回答ラベル", 選択結果.回答ラベル)),
                    理由=("計算後再評価で閉包",),
                )
            return HDS作用結果(
                HDS作用状態.成立,
                追加状態=frozenset({"計算後再評価済み"}),
                成果=(("選択結果", 選択結果),),
                理由=("計算後再評価は未閉包",),
            )

        作用群.append(HDS関数作用(
            "決定論計算",
            計算を実行,
            入力状態=(前段状態,),
            出力状態=("計算試行済み",),
            読取成果=("参照群",),
            資源負荷=1,
            優先度=2.0,
            根拠=("HDS-v3通常作用",),
            純粋作用=True,
        ))
        作用群.append(HDS関数作用(
            "計算後模型再評価",
            計算後評価,
            入力状態=("計算試行済み",),
            出力状態=("計算後再評価済み", "回答確定"),
            解消対象=("回答未閉包",),
            読取成果=("参照群",),
            資源負荷=1,
            優先度=3.0,
            根拠=("HDS-v3通常作用",),
            純粋作用=True,
        ))
        前段状態 = "計算後再評価済み"
        外部作用数 += 1

    参照段階数 = max(0, HDS外部作用予算 - 外部作用数)
    for 段階 in range(1, 参照段階数 + 1):
        参照済み状態 = f"追加参照{段階}済み"
        再評価済み状態 = f"追加参照{段階}再評価済み"
        入力状態 = 前段状態

        def 参照を取得(状態, 段階_=段階, 参照済み状態_=参照済み状態):
            現在参照 = tuple(状態.成果辞書().get("参照群", ()))
            観測参照 = HDS追加参照検索(参照供給器, 質問中間表現, 段階=段階_)
            上限 = max(len(現在参照), len(観測参照))
            統合参照 = HDS候補被覆優先統合(現在参照, 観測参照, 選択肢ラベル, 上限)
            return HDS作用結果(
                HDS作用状態.成立,
                追加状態=frozenset({参照済み状態_}),
                成果=(("参照群", tuple(統合参照)),),
                理由=(f"追加参照段階:{段階_}", f"参照件数:{len(統合参照)}"),
            )

        def 参照後評価(状態, 段階_=段階, 再評価済み状態_=再評価済み状態):
            参照群 = tuple(状態.成果辞書().get("参照群", ()))
            選択結果 = _模型評価(質問中間表現, 参照群, 構文化器)
            if _承認済み(選択結果):
                return HDS作用結果(
                    HDS作用状態.成立,
                    追加状態=frozenset({再評価済み状態_, "回答確定"}),
                    解消残差=frozenset({"回答未閉包"}),
                    成果=(("選択結果", 選択結果), ("回答ラベル", 選択結果.回答ラベル)),
                    理由=(f"追加参照段階{段階_}で閉包",),
                )
            return HDS作用結果(
                HDS作用状態.成立,
                追加状態=frozenset({再評価済み状態_}),
                成果=(("選択結果", 選択結果),),
                理由=(f"追加参照段階{段階_}は未閉包",),
            )

        作用群.append(HDS関数作用(
            f"追加参照{段階}",
            参照を取得,
            入力状態=(入力状態,),
            出力状態=(参照済み状態,),
            読取成果=("参照群",),
            資源負荷=4,
            優先度=1.0,
            根拠=("HDS-v3通常作用",),
            純粋作用=False,
        ))
        作用群.append(HDS関数作用(
            f"追加参照{段階}後模型再評価",
            参照後評価,
            入力状態=(参照済み状態,),
            出力状態=(再評価済み状態, "回答確定"),
            解消対象=("回答未閉包",),
            読取成果=("参照群",),
            資源負荷=1,
            優先度=3.0,
            根拠=("HDS-v3通常作用",),
            純粋作用=True,
        ))
        前段状態 = 再評価済み状態

    実行主体 = HDS実行主体(
        tuple(作用群),
        最大作用回数=max(8, len(作用群) + 4),
        最終検証器=(HDS検証器("回答ラベル形式", lambda 状態, _草案: 状態.成果辞書().get("回答ラベル") in 選択肢ラベル),),
    )
    return 実行主体.実行(初期状態)


def _選択結果採点(選択結果, 正答ラベル):
    回答ラベル = 選択結果.回答ラベル
    回答済み = _承認済み(選択結果)
    return 回答ラベル, 回答済み, bool(回答済み and 回答ラベル == 正答ラベル)


def _HDS結果採点(実行結果, 正答ラベル):
    回答ラベル = 実行結果.状態.成果辞書().get("回答ラベル")
    回答済み = 実行結果.終端 == HDS終端.採用 and 回答ラベル in 選択肢ラベル
    return 回答ラベル, 回答済み, bool(回答済み and 回答ラベル == 正答ラベル)


def 評価する(出力先: Path) -> dict:
    with tempfile.TemporaryDirectory(prefix="minidora-gpqa-ab-") as 一時場所:
        資料CSV, ZIP署名, CSV署名 = 資料集合取得(Path(一時場所))
        問題群 = 問題群読込(資料CSV)
        if len(問題群) != 198:
            raise RuntimeError(f"GPQA Diamond expected 198 rows, got {len(問題群)}")

        参照供給器 = 一般知識参照供給器(
            OpenAlex_API_key=None,
            Wikipedia言語=("en",),
            timeout=8.0,
            最大本文文字数=6000,
            並列=True,
            最大並列=4,
        )
        構文化器 = 公開HDSコンパイラ()
        左正答 = 左回答 = 右正答 = 右回答 = 0
        初期正答 = 初期回答 = 0
        改善 = 退行 = 変更 = 同一 = 0
        左介入回数 = 0
        HDS終端集計: Counter[str] = Counter()
        HDS作用集計: Counter[str] = Counter()
        HDS計装合計: Counter[str] = Counter()
        詳細 = []

        for 番号, (質問, 選択肢, 正答ラベル) in enumerate(問題群):
            質問中間表現 = 構文化器.問題IR(質問, 選択肢)
            初期参照群 = HDS参照検索(参照供給器, 質問中間表現)
            初期選択 = _模型評価(質問中間表現, 初期参照群, 構文化器)
            初期ラベル, 初期回答済み, 初期正解 = _選択結果採点(初期選択, 正答ラベル)
            初期回答 += int(初期回答済み)
            初期正答 += int(初期正解)

            左実行 = HDS監督選択実行(
                質問中間表現,
                tuple(初期参照群),
                コンパイル=構文化器.コンパイル,
                基礎能力核=None,
                模型核=標準能力模型核(),
                参照供給器=参照供給器,
                計算実行器_=計算実行器(),
                HDS制御=標準HDS介入制御(),
                HDS介入予算=6,
                初期選択=初期選択,
            )
            左選択 = 左実行.選択
            左ラベル, 左回答済み, 左正解 = _選択結果採点(左選択, 正答ラベル)
            左回答 += int(左回答済み)
            左正答 += int(左正解)
            左介入回数 += int(左実行.HDS介入数)

            右実行 = _HDSv3実行(質問中間表現, 初期参照群, 初期選択, 構文化器, 参照供給器)
            右ラベル, 右回答済み, 右正解 = _HDS結果採点(右実行, 正答ラベル)
            右回答 += int(右回答済み)
            右正答 += int(右正解)
            HDS終端集計[str(右実行.終端)] += 1
            HDS作用集計.update(記録.作用ID for 記録 in 右実行.履歴)
            HDS計装合計.update({鍵: int(値) for 鍵, 値 in asdict(右実行.計装).items() if isinstance(値, int)})

            if 左ラベル == 右ラベル and 左回答済み == 右回答済み:
                同一 += 1
            else:
                変更 += 1
            if not 左正解 and 右正解:
                改善 += 1
            if 左正解 and not 右正解:
                退行 += 1

            詳細.append({
                "番号": 番号,
                "正答ラベル": 正答ラベル,
                "初期": {"回答": 初期ラベル, "回答済み": 初期回答済み, "正解": 初期正解, "参照件数": len(初期参照群)},
                "MINIDORA30互換": {"回答": 左ラベル, "回答済み": 左回答済み, "正解": 左正解, "介入回数": 左実行.HDS介入数},
                "HDSv3": {"回答": 右ラベル, "回答済み": 右回答済み, "正解": 右正解, "終端": str(右実行.終端), "作用列": [記録.作用ID for 記録 in 右実行.履歴], "計装": asdict(右実行.計装)},
            })
            print(
                f"CASE {番号 + 1:03d}/198 初期={初期ラベル or '-'} 左={左ラベル or '-'} 右={右ラベル or '-'} "
                f"左正解={左正解} 右正解={右正解} HDS終端={右実行.終端}",
                flush=True,
            )

        結果 = {
            "比較形式": "MINIDORA30互換経路_vs_HDS内包統合v3_same_run_live_v1",
            "protocol": {
                "問題数": 198,
                "資料集合ZIP_SHA256": ZIP署名,
                "資料集合CSV_SHA256": CSV署名,
                "選択肢シャッフル種": 選択肢シャッフル種,
                "OpenAlex有効": False,
                "Wikipedia言語群": ["en"],
                "参照方式": "LIVE_ONLY",
                "固定参照資料許可": False,
                "同一質問中間表現": True,
                "同一初期参照": True,
                "同一初期MINIDORA結果": True,
                "gold使用境界": "両経路の推論完了後の採点のみ",
                "MINIDORA30側": "現行互換HDS監督選択実行系・介入予算6",
                "HDSv3側": "外付け監督なし。HDS実行主体の通常循環で決定論計算と段階的追加参照を作用として選択し、各状態差後に同じMINIDORA能力模型を再評価",
                "HDSv3外部作用予算": HDS外部作用予算,
                "注意": "同一runの運用比較。追加LIVE参照は各経路が別々に取得するため、得点差をコード差だけの純粋因果としない",
            },
            "初期通常MINIDORA": {
                "正答": 初期正答,
                "回答": 初期回答,
                "保留": 198 - 初期回答,
                "正答率": 100.0 * 初期正答 / 198,
            },
            "MINIDORA30互換": {
                "正答": 左正答,
                "回答": 左回答,
                "保留": 198 - 左回答,
                "正答率": 100.0 * 左正答 / 198,
                "介入回数": 左介入回数,
            },
            "HDSv3": {
                "正答": 右正答,
                "回答": 右回答,
                "保留": 198 - 右回答,
                "正答率": 100.0 * 右正答 / 198,
                "終端集計": dict(sorted(HDS終端集計.items())),
                "作用集計": dict(sorted(HDS作用集計.items())),
                "計装合計": dict(sorted(HDS計装合計.items())),
            },
            "差分": {
                "正答差_HDSv3_minus_MINIDORA30": 右正答 - 左正答,
                "正答率差pt": 100.0 * (右正答 - 左正答) / 198,
                "回答差": 右回答 - 左回答,
                "変更ケース": 変更,
                "同一ケース": 同一,
                "改善": 改善,
                "退行": 退行,
                "純改善": 改善 - 退行,
            },
            "詳細": 詳細,
        }
        出力先.write_text(json.dumps(結果, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        要約 = {鍵: 結果[鍵] for 鍵 in ("初期通常MINIDORA", "MINIDORA30互換", "HDSv3", "差分")}
        print("MINIDORA30_HDSV3_AB_RESULT=" + json.dumps(要約, ensure_ascii=False, separators=(",", ":")), flush=True)
        print("RESULT_FILE=" + str(出力先), flush=True)
        return 結果


def main() -> int:
    解析器 = argparse.ArgumentParser(description="MINIDORA30互換経路とHDS-v3のGPQA LIVE同run比較")
    解析器.add_argument("--out", dest="出力先", type=Path, default=Path("gpqa_minidora30_hdsv3_ab.json"))
    引数 = 解析器.parse_args()
    評価する(引数.出力先)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
