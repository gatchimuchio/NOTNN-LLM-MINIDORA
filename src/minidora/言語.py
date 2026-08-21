from __future__ import annotations

import ast
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

from .命令 import 作用, 命令, 手順


@dataclass(frozen=True, slots=True)
class 言語計画:
    手順: 手順
    初期状態: dict[str, Any] = field(default_factory=dict)
    参照必須: bool = False
    種別: str = "一般"


class 自然言語器:
    """自然言語要求を明示Pへ縮約し、構造化結果を自然言語へ戻す決定論的境界。"""

    _二項作用 = {
        ast.Add: 作用.加算,
        ast.Sub: 作用.減算,
        ast.Mult: 作用.乗算,
        ast.Div: 作用.除算,
    }
    _比較作用 = {
        ast.Eq: "同値",
        ast.NotEq: "不同",
        ast.Gt: "大",
        ast.Lt: "小",
        ast.GtE: "以上",
        ast.LtE: "以下",
    }

    def 計画(self, 問合せ: str) -> 言語計画:
        normalized = unicodedata.normalize("NFKC", 問合せ).strip()
        if not normalized:
            return self._参照計画("空入力")

        phrase = self._日本語算術(normalized)
        if phrase is not None:
            return phrase

        expression = self._式候補(normalized)
        if expression is not None:
            compiled = self._式計画(expression)
            if compiled is not None:
                return compiled

        count = re.search(
            r"[「『\"](.+?)[」』\"](?:の)?文字数(?:を)?(?:数えて|教えて|は)",
            normalized,
        )
        if count:
            initial = {"入力0": count.group(1)}
            proc = 手順(
                "文字数計数",
                (
                    命令(
                        "文字数",
                        作用.計数,
                        引数=("$入力0",),
                        更新先="結果",
                        根拠=("自然言語入力",),
                    ),
                ),
                由来="自然言語器",
            )
            return 言語計画(proc, initial, False, "計数")

        return self._参照計画("外部参照")

    def _参照計画(self, reason: str) -> 言語計画:
        proc = 手順(
            "参照回答",
            (
                命令(
                    "参照列取得",
                    作用.取得,
                    対象="参照",
                    更新先="参照列",
                    根拠=(reason,),
                ),
                命令(
                    "先頭参照抽出",
                    作用.抽出,
                    引数=("$参照列", 0),
                    更新先="参照候補",
                    根拠=(reason,),
                ),
                命令(
                    "参照内容抽出",
                    作用.抽出,
                    引数=("$参照候補", "内容"),
                    更新先="結果",
                    根拠=(reason,),
                ),
            ),
            由来="自然言語器",
        )
        return 言語計画(proc, {}, True, "参照")

    def _日本語算術(self, text: str) -> 言語計画 | None:
        number = r"(-?\d+(?:\.\d+)?)"
        patterns = (
            (
                rf"{number}\s*(?:と|に)\s*{number}\s*を?\s*(?:足して|加えて|足す)",
                作用.加算,
                "加算",
            ),
            (
                rf"{number}\s*から\s*{number}\s*を?\s*(?:引いて|引く)",
                作用.減算,
                "減算",
            ),
            (
                rf"{number}\s*(?:と|に)\s*{number}\s*を?\s*(?:掛けて|かけて|掛ける|かける|乗じて)",
                作用.乗算,
                "乗算",
            ),
            (
                rf"{number}\s*を\s*{number}\s*で\s*(?:割って|割る|除して)",
                作用.除算,
                "除算",
            ),
        )
        for pattern, op, name in patterns:
            match = re.search(pattern, text)
            if not match:
                continue
            values = tuple(self._数値(x) for x in match.groups())
            initial = {f"入力{i}": value for i, value in enumerate(values)}
            proc = 手順(
                name,
                (
                    命令(
                        name,
                        op,
                        引数=("$入力0", "$入力1"),
                        更新先="結果",
                        根拠=("自然言語入力",),
                    ),
                ),
                由来="自然言語器",
            )
            return 言語計画(proc, initial, False, "算術")
        return None

    def _式候補(self, text: str) -> str | None:
        text = text.replace("×", "*").replace("÷", "/")
        trimmed = re.sub(r"(?:は)?[?？。!！]+$", "", text).strip()
        trimmed = re.sub(
            r"(?:を)?(?:計算して|計算|求めて|求める)$",
            "",
            trimmed,
        ).strip()
        if re.fullmatch(r"[\d\s.+\-*/()<>!=]+", trimmed) and any(
            op in trimmed for op in "+-*/<>=!"
        ):
            return trimmed

        candidates = re.findall(
            r"[-+]?\d+(?:\.\d+)?(?:\s*[+\-*/<>=!]\s*[-+]?\d+(?:\.\d+)?)+",
            text,
        )
        return max(candidates, key=len).strip() if candidates else None

    def _式計画(self, expression: str) -> 言語計画 | None:
        try:
            tree = ast.parse(expression, mode="eval")
        except SyntaxError:
            return None

        commands: list[命令] = []
        initial: dict[str, Any] = {}
        counter = {"data": 0, "tmp": 0}

        def data_ref(value: int | float) -> str:
            key = f"入力{counter['data']}"
            counter["data"] += 1
            initial[key] = value
            return f"${key}"

        def compile_node(node: ast.AST, target: str | None = None) -> str | None:
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, (int, float))
                and not isinstance(node.value, bool)
            ):
                return data_ref(node.value)
            if (
                isinstance(node, ast.UnaryOp)
                and isinstance(node.op, (ast.USub, ast.UAdd))
                and isinstance(node.operand, ast.Constant)
                and isinstance(node.operand.value, (int, float))
            ):
                value = -node.operand.value if isinstance(node.op, ast.USub) else node.operand.value
                return data_ref(value)
            if isinstance(node, ast.BinOp) and type(node.op) in self._二項作用:
                left = compile_node(node.left)
                right = compile_node(node.right)
                if left is None or right is None:
                    return None
                out = target or f"中間{counter['tmp']}"
                counter["tmp"] += 1
                commands.append(
                    命令(
                        f"式{len(commands) + 1}",
                        self._二項作用[type(node.op)],
                        引数=(left, right),
                        更新先=out,
                        根拠=("自然言語入力",),
                    )
                )
                return f"${out}"
            if (
                isinstance(node, ast.Compare)
                and len(node.ops) == 1
                and len(node.comparators) == 1
                and type(node.ops[0]) in self._比較作用
            ):
                left = compile_node(node.left)
                right = compile_node(node.comparators[0])
                if left is None or right is None:
                    return None
                out = target or f"中間{counter['tmp']}"
                counter["tmp"] += 1
                commands.append(
                    命令(
                        f"比較{len(commands) + 1}",
                        作用.比較,
                        引数=(left, self._比較作用[type(node.ops[0])], right),
                        更新先=out,
                        根拠=("自然言語入力",),
                    )
                )
                return f"${out}"
            return None

        root_ref = compile_node(tree.body, "結果")
        if root_ref is None:
            return None
        if not commands:
            commands.append(
                命令(
                    "結果取得",
                    作用.取得,
                    対象=root_ref[1:],
                    更新先="結果",
                    根拠=("自然言語入力",),
                )
            )
        return 言語計画(
            手順("数式計算", tuple(commands), 由来="自然言語器"),
            initial,
            False,
            "算術",
        )

    def _数値(self, raw: str) -> int | float:
        value = float(raw)
        return int(value) if value.is_integer() else value

    def 表面化(self, 値: Any, 状態: str, 理由: tuple[str, ...]) -> str:
        if 状態 == "保留":
            if "未解消矛盾" in 理由:
                return "判断を保留します。未解消の矛盾があります。"
            return "分かりません。確認できる根拠がありません。"
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
