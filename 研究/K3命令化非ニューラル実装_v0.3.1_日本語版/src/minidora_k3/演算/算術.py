from __future__ import annotations
import ast
import re
from .基礎 import OperatorError, OperatorResult

_ALLOWED_BIN = {ast.Add: lambda a, b: a + b, ast.Sub: lambda a, b: a - b, ast.Mult: lambda a, b: a * b}
_ALLOWED_UNARY = {ast.USub: lambda a: -a, ast.UAdd: lambda a: a}


def _eval_ast(node: ast.AST) -> int:
    if isinstance(node, ast.Expression):
        return _eval_ast(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BIN:
        return _ALLOWED_BIN[type(node.op)](_eval_ast(node.left), _eval_ast(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_UNARY:
        return _ALLOWED_UNARY[type(node.op)](_eval_ast(node.operand))
    raise OperatorError(f"許可されていない算術node: {ast.dump(node)}")


def solve_arithmetic(text: str) -> OperatorResult:
    expression = text.strip().rstrip("=").strip()
    expression = expression.translate(str.maketrans({"×": "*", "−": "-", "–": "-", "—": "-", "＋": "+"}))
    if re.search(r"[^0-9+\-*()\s]", expression):
        raise OperatorError("算術式に許可外文字があります")
    tree = ast.parse(expression, mode="eval")
    value = _eval_ast(tree)
    return OperatorResult(
        str(value),
        (
            {"opcode": "整数式解析", "expression": expression},
            {"opcode": "安全構文木実行", "result": value},
        ),
        {"ast": ast.dump(tree, include_attributes=False), "result": value},
    )
