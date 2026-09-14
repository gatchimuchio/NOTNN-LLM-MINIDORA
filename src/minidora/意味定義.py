from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import re

from .計算中間表現 import 計算中間表現, 計算作用, 計算値, 計算命令


意味定義版 = "MINIDORA-意味定義-v0.1"


class 定義作用種別(StrEnum):
    乗算 = "乗算"
    加算 = "加算"
    減算 = "減算"
    除算 = "除算"


@dataclass(frozen=True, slots=True)
class 定義作用:
    種別: 定義作用種別
    値: int | float


@dataclass(frozen=True, slots=True)
class 単項計算定義:
    名称: str
    作用列: tuple[定義作用, ...]
    原文: str
    根拠: tuple[str, ...] = ()
    版: str = 意味定義版

    def __post_init__(self):
        if not self.名称.strip() or not self.作用列:
            raise ValueError("定義名称と作用列は必須")

    def 計算化(self) -> 計算中間表現:
        current = "入力"
        rows = []
        opmap = {
            定義作用種別.乗算: 計算作用.乗算,
            定義作用種別.加算: 計算作用.加算,
            定義作用種別.減算: 計算作用.減算,
            定義作用種別.除算: 計算作用.除算,
        }
        for index, item in enumerate(self.作用列, 1):
            output = "結果" if index == len(self.作用列) else f"中間{index}"
            rows.append(
                計算命令(
                    f"定義作用:{index}",
                    f"{self.名称}:{item.種別.value}",
                    opmap[item.種別],
                    (計算値.状態値(current), 計算値.即値(item.値)),
                    出力住所=output,
                    根拠=(self.原文, *self.根拠),
                    境界=("入力内定義", "決定論的計算"),
                )
            )
            current = output
        return 計算中間表現(
            f"定義:{self.名称}",
            tuple(rows),
            "結果",
            由来=self.原文,
            由来参照=self.根拠,
            境界=("入力内定義", "外部知識不使用"),
            検証=("作用順序保持",),
        )


_KANJI = {"零": 0, "〇": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
          "六": 6, "七": 7, "八": 8, "九": 9}


def _number(text: str) -> int | float:
    text = text.strip()
    if re.fullmatch(r"-?\d+(?:\.\d+)?", text):
        return float(text) if "." in text else int(text)
    if text == "十":
        return 10
    match = re.fullmatch(r"([一二三四五六七八九])?十([一二三四五六七八九])?", text)
    if match:
        return (_KANJI.get(match.group(1), 1) * 10) + _KANJI.get(match.group(2), 0)
    if text in _KANJI:
        return _KANJI[text]
    raise ValueError("数値表現を解釈できない: " + text)


_NUM = r"-?\d+(?:\.\d+)?|[零〇一二三四五六七八九十]+"
_OP_PATTERNS = (
    (re.compile(rf"(?P<n>{_NUM})倍(?:にする|する|して|し)?"), 定義作用種別.乗算),
    (re.compile(rf"(?P<n>{_NUM})を(?:掛ける|かける)"), 定義作用種別.乗算),
    (re.compile(rf"(?P<n>{_NUM})を(?:足す|加える)"), 定義作用種別.加算),
    (re.compile(rf"(?P<n>{_NUM})を引く"), 定義作用種別.減算),
    (re.compile(rf"(?P<n>{_NUM})で割る"), 定義作用種別.除算),
)


def 単項計算定義を読む(text: str) -> 単項計算定義:
    if type(text) is not str or not text.strip() or len(text) > 4096:
        raise ValueError("定義文の型・長さ不正")
    raw = text.strip()
    match = re.fullmatch(
        r"[「『\"]?(?P<name>[^」』\"\s]+)[」』\"]?は(?P<body>.+?)(?:という意味|を意味する)[。．.]?",
        raw,
    )
    if not match:
        raise ValueError("単項計算定義として解釈できない")
    name = match.group("name").strip()
    body = match.group("body").strip()
    found = []
    spans = []
    for pattern, kind in _OP_PATTERNS:
        for item in pattern.finditer(body):
            found.append((item.start(), 定義作用(kind, _number(item.group("n")))))
            spans.append((item.start(), item.end()))
    found.sort(key=lambda x: x[0])
    if not found:
        raise ValueError("定義内に既知の汎用計算作用がない")
    mask = list(body)
    for start, end in spans:
        for index in range(start, end):
            mask[index] = " "
    residue = "".join(mask)
    residue = re.sub(r"(?:して|し|さらに|その後|次に|、|,|\s)+", "", residue)
    if residue:
        raise ValueError("定義の未解釈残差: " + residue)
    return 単項計算定義(
        name,
        tuple(item for _, item in found),
        raw,
        ("自然言語定義",),
    )


def 定義適用要求を読む(text: str) -> tuple[str, int | float]:
    if type(text) is not str or not text.strip() or len(text) > 4096:
        raise ValueError("適用要求の型・長さ不正")
    raw = text.strip()
    match = re.fullmatch(
        rf"(?P<x>{_NUM})を[「『\"]?(?P<name>[^」』\"\s]+)[」』\"]?(?:した|する)(?:結果)?(?:は|を求めて|を計算して)?[？?。．.]?",
        raw,
    )
    if not match:
        raise ValueError("定義適用要求として解釈できない")
    return match.group("name"), _number(match.group("x"))


def 定義を実行(定義: 単項計算定義, 入力値, 計算実行器_):
    ir = 定義.計算化()
    return 計算実行器_.計算実行(ir, {"入力": 入力値})


__all__ = [
    "意味定義版",
    "定義作用種別",
    "定義作用",
    "単項計算定義",
    "単項計算定義を読む",
    "定義適用要求を読む",
    "定義を実行",
]
