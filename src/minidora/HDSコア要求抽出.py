"""利用者が明示した作用要求を能力名へ落とさずCore入力へ射影する。"""
from __future__ import annotations

from dataclasses import dataclass
import re

from .HDSコア入力 import HDSコア作用要求, HDSコア残差


@dataclass(frozen=True, slots=True)
class HDSコア要求抽出結果:
    作用要求: tuple[HDSコア作用要求, ...]
    残差: tuple[HDSコア残差, ...] = ()


_日本語規則 = (
    (re.compile(r"コードの構造を説明(?:して(?:ください|下さい|くれ)?|せよ|する)"), "説明", "コード構造報告"),
    (re.compile(r"(?:数字を抽出|数字抽出|数値を抽出)(?:して(?:ください|下さい|くれ)?|せよ|する)?"), "抽出", "数字列"),
    (re.compile(r"URLを抽出(?:して(?:ください|下さい|くれ)?|せよ|する)?", re.I), "抽出", "URL列"),
    (re.compile(r"キーワードを抽出(?:して(?:ください|下さい|くれ)?|せよ|する)?"), "抽出", "キーワード列"),
    (re.compile(r"JSONに変換(?:して(?:ください|下さい|くれ)?|せよ|する)?", re.I), "変換", "JSON変換文書"),
    (re.compile(r"箇条書きに(?:して(?:ください|下さい|くれ)?|せよ|する)"), "変換", "箇条書き文"),
    (re.compile(r"要約(?:して(?:ください|下さい|くれ)?|せよ|する)"), "要約", "要約結果"),
    (re.compile(r"微分(?:して(?:ください|下さい|くれ)?|せよ|する)"), "計算", "微分結果"),
    (re.compile(r"積分(?:して(?:ください|下さい|くれ)?|せよ|する)"), "計算", "積分結果"),
    (re.compile(r"(?:展開|整理)(?:して(?:ください|下さい|くれ)?|せよ|する)"), "計算", "正規化結果"),
    (re.compile(r"計算(?:して(?:ください|下さい|くれ)?|せよ|する)"), "計算", "計算結果"),
    (re.compile(r"一意解を求めて(?:ください|下さい)?"), "解法", "一意解"),
    (re.compile(r"解いて(?:ください|下さい)?"), "解法", "方程式結果"),
    (re.compile(r"比較(?:して(?:ください|下さい|くれ)?|せよ|する)"), "比較", "比較結果"),
    (re.compile(r"説明(?:して(?:ください|下さい|くれ)?|せよ|する)"), "説明", "説明結果"),
    (re.compile(r"(?:確認|検証)(?:して(?:ください|下さい|くれ)?|せよ|する)"), "検証", "検証結果"),
    (re.compile(r"(?:検索|調査)(?:して(?:ください|下さい|くれ)?|せよ|する)"), "取得", "取得結果"),
    (re.compile(r"調べて(?:ください|下さい)?"), "取得", "取得結果"),
    (re.compile(r"探して(?:ください|下さい)?"), "取得", "取得結果"),
    (re.compile(r"翻訳(?:して(?:ください|下さい|くれ)?|せよ|する)"), "翻訳", "翻訳結果"),
    (re.compile(r"(?:編集|修正|置換)(?:して(?:ください|下さい|くれ)?|せよ|する)"), "編集", "編集結果"),
    (re.compile(r"(?:作成|生成)(?:して(?:ください|下さい|くれ)?|せよ|する)"), "生成", "生成結果"),
    (re.compile(r"再表現(?:して(?:ください|下さい|くれ)?|せよ|する)"), "再表現", "再表現結果"),
    (re.compile(r"(?:登録|更新)(?:して(?:ください|下さい|くれ)?|せよ|する)"), "管理", "管理結果"),
)

_英語規則 = (
    (re.compile(r"(?:^|[.!?]\s*)(?:please\s+|can you\s+|could you\s+|would you\s+)?summarize\b", re.I), "要約", "要約結果"),
    (re.compile(r"(?:^|[.!?]\s*)(?:please\s+|can you\s+|could you\s+|would you\s+)?extract\b", re.I), "抽出", "抽出結果"),
    (re.compile(r"(?:^|[.!?]\s*)(?:please\s+|can you\s+|could you\s+|would you\s+)?compare\b", re.I), "比較", "比較結果"),
    (re.compile(r"(?:^|[.!?]\s*)(?:please\s+|can you\s+|could you\s+|would you\s+)?explain\b", re.I), "説明", "説明結果"),
    (re.compile(r"(?:^|[.!?]\s*)(?:please\s+|can you\s+|could you\s+|would you\s+)?(?:verify|validate|check)\b", re.I), "検証", "検証結果"),
    (re.compile(r"(?:^|[.!?]\s*)(?:please\s+|can you\s+|could you\s+|would you\s+)?(?:search|research|find)\b", re.I), "取得", "取得結果"),
    (re.compile(r"(?:^|[.!?]\s*)(?:please\s+|can you\s+|could you\s+|would you\s+)?translate\b", re.I), "翻訳", "翻訳結果"),
    (re.compile(r"(?:^|[.!?]\s*)(?:please\s+|can you\s+|could you\s+|would you\s+)?convert\b", re.I), "変換", "変換結果"),
    (re.compile(r"(?:^|[.!?]\s*)(?:please\s+|can you\s+|could you\s+|would you\s+)?(?:edit|replace|revise)\b", re.I), "編集", "編集結果"),
    (re.compile(r"(?:^|[.!?]\s*)(?:please\s+|can you\s+|could you\s+|would you\s+)?(?:create|generate|write)\b", re.I), "生成", "生成結果"),
    (re.compile(r"(?:^|[.!?]\s*)(?:please\s+|can you\s+|could you\s+|would you\s+)?(?:calculate|compute)\b", re.I), "計算", "計算結果"),
    (re.compile(r"(?:^|[.!?]\s*)(?:please\s+|can you\s+|could you\s+|would you\s+)?solve\b", re.I), "解法", "解法結果"),
)

_日本語命令終端 = re.compile(
    r"(?:して(?:ください|下さい|くれ)?|せよ|して|求めて(?:ください|下さい)?|解いて(?:ください|下さい)?)\s*[。！？!?]?$",
    re.I,
)


def 明示作用要求を抽出(原文: str) -> HDSコア要求抽出結果:
    本文 = str(原文)
    候補 = []
    for 規則, 種別, 成果 in (*_日本語規則, *_英語規則):
        for 一致 in 規則.finditer(本文):
            候補.append((一致.start(), -(一致.end() - 一致.start()), 一致.end(), 種別, 成果, 一致.group(0)))
    候補.sort()

    採用 = []
    占有 = []
    for 開始, 負長, 終了, 種別, 成果, 表層 in 候補:
        if any(not (終了 <= a or b <= 開始) for a, b in 占有):
            continue
        占有.append((開始, 終了))
        採用.append(HDSコア作用要求(
            ID=f"作用要求:{len(採用)}",
            種別=種別,
            対象参照=(),
            要求成果=(成果,),
            原文範囲=(開始, 終了),
        ))

    残差 = []
    if not 採用 and _日本語命令終端.search(本文.strip()):
        残差.append(HDSコア残差(
            ID="Core入力:作用要求未構文化",
            種別="作用要求未構文化",
            原文=本文,
            理由="利用者の命令形をCore作用意味へ安全に射影できない",
            解消条件=("作用意味と要求成果を明示する",),
        ))
    return HDSコア要求抽出結果(tuple(採用), tuple(残差))


__all__ = ["HDSコア要求抽出結果", "明示作用要求を抽出"]
