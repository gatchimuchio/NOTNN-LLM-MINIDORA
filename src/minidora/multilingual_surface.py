from __future__ import annotations

from typing import Any


def 表面化(値: Any, 状態: str, 理由: tuple[str, ...], 言語: str = "ja") -> str:
    language = (言語 or "ja").casefold()
    if language.startswith("en"):
        if 状態 == "保留":
            return "I don't know. I don't have verified grounds."
        if 状態 == "失敗":
            return "I can't process that."
        if 値 is None:
            return "I don't know."
        if isinstance(値, bool):
            return "Yes." if 値 else "No."
        if isinstance(値, float) and 値.is_integer():
            値 = int(値)
        if isinstance(値, str) and 値.endswith((".", "!", "?")):
            return 値
        return f"{値}."

    if language.startswith("zh"):
        if 状態 == "保留":
            return "不知道。没有可确认的依据。"
        if 状態 == "失敗":
            return "无法处理。"
        if 値 is None:
            return "不知道。"
        if isinstance(値, bool):
            return "是。" if 値 else "否。"
        if isinstance(値, float) and 値.is_integer():
            値 = int(値)
        if isinstance(値, str) and 値.endswith(("。", "！", "？", "!", "?")):
            return 値
        return f"{値}。"

    if 状態 == "保留":
        return "判断を保留します。未解消の矛盾があります。" if "未解消矛盾" in 理由 else "分かりません。確認できる根拠がありません。"
    if 状態 == "失敗":
        return "処理できません。"
    if 値 is None:
        return "分かりません。"
    if isinstance(値, bool):
        return "はい。" if 値 else "いいえ。"
    if isinstance(値, float) and 値.is_integer():
        値 = int(値)
    if isinstance(値, (int, float)):
        return f"{値}です。"
    if isinstance(値, str):
        return 値 if 値.endswith(("。", "！", "？", "!", "?")) else f"{値}。"
    return f"{値}。"


__all__ = ["表面化"]
