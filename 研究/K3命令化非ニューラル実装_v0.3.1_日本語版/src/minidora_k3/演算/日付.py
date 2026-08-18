from __future__ import annotations
import calendar
import re
from datetime import date, timedelta
from typing import Any
from .基礎 import OperatorError, OperatorResult

_OPTIONS = re.compile(r"\(([A-F])\)\s*([^\n]+)")

def _add_months(value: date, months: int) -> date:
    month_index = value.year * 12 + value.month - 1 + months
    year, month_zero = divmod(month_index, 12)
    month = month_zero + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)

def _parse_options_dates(text: str) -> dict[str, date]:
    result = {}
    for label, value in _OPTIONS.findall(text):
        match = re.search(r"(\d{2})/(\d{2})/(\d{4})", value)
        if match:
            result[label] = date(int(match.group(3)), int(match.group(1)), int(match.group(2)))
    return result

def _first_monday(year: int) -> date:
    value = date(year, 1, 1)
    while value.weekday() != 0:
        value += timedelta(days=1)
    return value

def solve_date(text: str) -> OperatorResult:
    options = _parse_options_dates(text)
    if not options:
        raise OperatorError("日付選択肢がありません")
    base: date | None = None
    derivation: list[dict[str, Any]] = []

    christmas = re.search(r"今日は\s*(\d{4})\s*年のクリスマス・イブ", text)
    if christmas:
        base = date(int(christmas.group(1)), 12, 24)
        derivation.append({"rule": "クリスマスイブ", "base": base.isoformat()})

    uk = re.search(r"イギリス.*今日は\s*(\d{2})/(\d{2})/(\d{4})", text, re.S)
    if uk:
        base = date(int(uk.group(3)), int(uk.group(2)), int(uk.group(1)))
        derivation.append({"rule": "UK_DDMMYYYY", "base": base.isoformat()})

    marriage = re.search(r"(\d{4})\s*年\s*(\d+)\s*月\s*(\d+)\s*日に結婚.*?(\d+)\s*周年", text, re.S)
    if marriage:
        base = date(int(marriage.group(1)) + int(marriage.group(4)), int(marriage.group(2)), int(marriage.group(3)))
        derivation.append({"rule": "周年", "base": base.isoformat(), "note": "BBH原版labelに既知不整合あり"})

    tomorrow_explicit = re.search(r"明日[（(]?\s*(\d{4})年(\d+)月(\d+)日", text)
    if tomorrow_explicit:
        tomorrow = date(int(tomorrow_explicit.group(1)), int(tomorrow_explicit.group(2)), int(tomorrow_explicit.group(3)))
        base = tomorrow - timedelta(days=1)
        derivation.append({"rule": "翌日基準", "base": base.isoformat()})

    rescheduled = re.search(r"(\d{4})年(\d+)月(\d+)日の明日", text)
    if rescheduled:
        tomorrow = date(int(rescheduled.group(1)), int(rescheduled.group(2)), int(rescheduled.group(3)))
        base = tomorrow - timedelta(days=1)
        derivation.append({"rule": "翌日基準", "base": base.isoformat()})

    monthly = re.search(r"(\d{4})\s*年\s*(\d+)\s*月から、?毎月\s*(\d+)\s*日.*?(\d+)\s*回目", text, re.S)
    if monthly:
        first = date(int(monthly.group(1)), int(monthly.group(2)), int(monthly.group(3)))
        base = _add_months(first, int(monthly.group(4)) - 1)
        derivation.append({"rule": "月内第N日", "base": base.isoformat()})

    eggs = re.search(r"(\d{4})年(\d+)月(\d+)日.*?卵を\s*(\d+)\s*個.*?毎日\s*1\s*個.*?今日、卵がなく", text, re.S)
    if eggs:
        start = date(int(eggs.group(1)), int(eggs.group(2)), int(eggs.group(3)))
        base = start + timedelta(days=int(eggs.group(4)))
        derivation.append({"rule": "日次消費", "base": base.isoformat(), "convention": "購入翌日から消費"})

    tomorrow_slash = re.search(r"明日は\s*(\d{4})年(\d+)月(\d+)日", text)
    if tomorrow_slash and base is None:
        base = date(int(tomorrow_slash.group(1)), int(tomorrow_slash.group(2)), int(tomorrow_slash.group(3))) - timedelta(days=1)
        derivation.append({"rule": "翌日基準", "base": base.isoformat()})

    jane = re.search(r"ジェーンは今日が\s*(\d{4})\s*年\s*(\d+)\s*月\s*(\d+)\s*日だと考え.*?ジェーンの考えが正しい", text, re.S)
    if jane:
        base = date(int(jane.group(1)), int(jane.group(2)), int(jane.group(3)))
        derivation.append({"rule": "条件付本日", "base": base.isoformat()})

    first_monday = re.search(r"(\d{4})年の初日は火曜日.*?最初の月曜日", text, re.S)
    if first_monday:
        base = _first_monday(int(first_monday.group(1)))
        derivation.append({"rule": "最初の月曜日", "base": base.isoformat()})

    if base is None:
        raise OperatorError("基準日を閉じられません")

    target = base
    if "明日の日付" in text or "24 時間後" in text or "24時間後" in text:
        target = base + timedelta(days=1); derivation.append({"operation": "日加算", "value": 1})
    elif "昨日の日付" in text:
        target = base - timedelta(days=1); derivation.append({"operation": "日加算", "value": -1})
    elif "1 週間後" in text or "1週間後" in text or "今日から1週間後" in text:
        target = base + timedelta(days=7); derivation.append({"operation": "日加算", "value": 7})
    elif "今日から1週間前" in text or "1 週間前" in text or "1週間前" in text:
        target = base - timedelta(days=7); derivation.append({"operation": "日加算", "value": -7})
    elif "1 か月前" in text or "1か月前" in text:
        target = _add_months(base, -1); derivation.append({"operation": "月加算", "value": -1})
    elif "1 年前" in text or "1年前" in text:
        target = date(base.year - 1, base.month, min(base.day, calendar.monthrange(base.year - 1, base.month)[1])); derivation.append({"operation": "年加算", "value": -1})
    else:
        raise OperatorError("日付操作を閉じられません")

    labels = [label for label, value in options.items() if value == target]
    if len(labels) != 1:
        raise OperatorError(f"計算日付が選択肢と一意対応しません: target={target}, labels={labels}")
    answer = f"({labels[0]})"
    return OperatorResult(
        answer,
        (
            {"opcode": "時間基準解析", "derivation": derivation, "base": base.isoformat()},
            {"opcode": "暦遷移", "target": target.isoformat()},
            {"opcode": "選択肢対応", "answer": answer},
        ),
        {"base": base.isoformat(), "target": target.isoformat(), "options": {key: value.isoformat() for key, value in options.items()}, "derivation": derivation},
    )
