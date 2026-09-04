from __future__ import annotations
import ast
import operator as op
import re
from .型 import 能力結果

計算版 = "safe-arithmetic-v1"
_OPS = {ast.Add:op.add, ast.Sub:op.sub, ast.Mult:op.mul, ast.Div:op.truediv, ast.FloorDiv:op.floordiv, ast.Mod:op.mod, ast.Pow:op.pow, ast.USub:op.neg, ast.UAdd:op.pos}

def _eval(node):
    if isinstance(node, ast.Expression): return _eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int,float)): return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        a, b = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Pow) and abs(b) > 12: raise ValueError("指数が大きすぎる")
        return _OPS[type(node.op)](a,b)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS: return _OPS[type(node.op)](_eval(node.operand))
    raise ValueError("許可されていない式")

def _extract(text: str) -> str:
    s = text.replace("×","*").replace("÷","/").replace("^","**").replace("％","%").replace("，",",")
    m = re.search(r"[-+*/%().\d\s]+", s)
    return m.group(0).strip() if m else ""

class 計算Module:
    版 = 計算版
    def 実行(self, text: str) -> 能力結果:
        expr = _extract(text)
        if not expr:
            return 能力結果(False, "", 保留理由="計算式を抽出できない")
        if len(expr) > 120:
            return 能力結果(False, "", 保留理由="式が長すぎる")
        try:
            value = _eval(ast.parse(expr, mode="eval"))
        except Exception as exc:
            return 能力結果(False, "", 保留理由=f"計算不能:{exc}")
        return 能力結果(True, f"{expr} = {value}", 根拠=("決定論的算術実行",), データ={"式":expr,"値":value})
