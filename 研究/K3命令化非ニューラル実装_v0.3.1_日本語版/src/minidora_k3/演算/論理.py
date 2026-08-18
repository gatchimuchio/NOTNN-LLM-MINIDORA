from __future__ import annotations
import re
from .基礎 import OperatorError, OperatorResult

class _BooleanParser:
    TOKEN = re.compile(r"True|False|not|and|or|\(|\)")

    def __init__(self, text: str) -> None:
        self.tokens = self.TOKEN.findall(text)
        self.index = 0
        if not self.tokens:
            raise OperatorError("真偽tokenがありません")

    def parse(self) -> bool:
        value = self._or()
        if self.index != len(self.tokens):
            raise OperatorError("真偽式に未消費tokenがあります")
        return value

    def _peek(self) -> str | None:
        return self.tokens[self.index] if self.index < len(self.tokens) else None

    def _take(self, expected: str | None = None) -> str:
        token = self._peek()
        if token is None or (expected is not None and token != expected):
            raise OperatorError(f"token不一致: expected={expected}, actual={token}")
        self.index += 1
        return token

    def _or(self) -> bool:
        value = self._and()
        while self._peek() == "or":
            self._take("or")
            value = value or self._and()
        return value

    def _and(self) -> bool:
        value = self._not()
        while self._peek() == "and":
            self._take("and")
            value = value and self._not()
        return value

    def _not(self) -> bool:
        if self._peek() == "not":
            self._take("not")
            return not self._not()
        return self._atom()

    def _atom(self) -> bool:
        token = self._take()
        if token == "True":
            return True
        if token == "False":
            return False
        if token == "(":
            value = self._or()
            self._take(")")
            return value
        raise OperatorError(f"不正な真偽atom: {token}")


def solve_boolean(text: str) -> OperatorResult:
    expression = re.sub(r"\s+は\s*$", "", text.strip())
    value = _BooleanParser(expression).parse()
    answer = "True" if value else "False"
    return OperatorResult(
        answer,
        (
            {"opcode": "論理式読込", "expression": expression},
            {"opcode": "論理式評価", "precedence": ["not", "and", "or"], "result": answer},
        ),
        {"reparse": answer, "type": "論理式"},
    )
