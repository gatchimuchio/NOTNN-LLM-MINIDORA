from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .命令 import 作用, 命令, 手順


@dataclass(slots=True)
class 実行文脈:
    状態: dict[str, Any] = field(default_factory=dict)
    履歴: list[dict[str, Any]] = field(default_factory=list)
    停止済み: bool = False


class Layer0:
    """実装非依存の最小命令実行機構。K3固有構造を責任として持たない。"""

    def 実行(self, 手順_: 手順, 初期状態: dict[str, Any] | None = None) -> 実行文脈:
        文脈 = 実行文脈(dict(初期状態 or {}))
        for 命令_ in 手順_.命令列:
            if 文脈.停止済み:
                break
            self._適用(文脈, 命令_)
        return 文脈

    def _値(self, 文脈: 実行文脈, value: Any) -> Any:
        if isinstance(value, str) and value.startswith("$"):
            return 文脈.状態.get(value[1:])
        return value

    def _適用(self, 文脈: 実行文脈, 命令_: 命令) -> None:
        args = tuple(self._値(文脈, value) for value in 命令_.引数)
        op = 命令_.作用
        result: Any = None

        if op == 作用.設定:
            if 命令_.更新先 is None or not args:
                raise ValueError("設定には更新先と値が必要")
            result = args[0]
            文脈.状態[命令_.更新先] = result
        elif op == 作用.取得:
            if 命令_.対象 is None:
                raise ValueError("取得には対象が必要")
            result = 文脈.状態.get(命令_.対象)
            if 命令_.更新先:
                文脈.状態[命令_.更新先] = result
        elif op in {作用.加算, 作用.減算, 作用.乗算, 作用.除算}:
            if len(args) < 2:
                raise ValueError(f"{op}には2値以上が必要")
            result = args[0]
            for value in args[1:]:
                if op == 作用.加算:
                    result += value
                elif op == 作用.減算:
                    result -= value
                elif op == 作用.乗算:
                    result *= value
                else:
                    result /= value
            if 命令_.更新先:
                文脈.状態[命令_.更新先] = result
        elif op == 作用.比較:
            if len(args) != 3:
                raise ValueError("比較は 左, 演算子, 右 を取る")
            左, 演算子, 右 = args
            比較表 = {"同値": 左 == 右, "不同": 左 != 右, "大": 左 > 右, "小": 左 < 右, "以上": 左 >= 右, "以下": 左 <= 右}
            if 演算子 not in 比較表:
                raise ValueError(f"未対応比較: {演算子}")
            result = 比較表[演算子]
            if 命令_.更新先:
                文脈.状態[命令_.更新先] = result
        elif op == 作用.計数:
            if len(args) != 1:
                raise ValueError("計数には一対象が必要")
            result = len(args[0])
            if 命令_.更新先:
                文脈.状態[命令_.更新先] = result
        elif op == 作用.結合:
            result = tuple(args)
            if 命令_.更新先:
                文脈.状態[命令_.更新先] = result
        elif op == 作用.交換:
            if len(args) != 2 or not all(isinstance(x, str) for x in args):
                raise ValueError("交換は状態キー2個を取る")
            a, b = args
            文脈.状態[a], 文脈.状態[b] = 文脈.状態.get(b), 文脈.状態.get(a)
            result = (文脈.状態[a], 文脈.状態[b])
        elif op == 作用.反転:
            if len(args) != 1:
                raise ValueError("反転には一値が必要")
            result = not bool(args[0])
            if 命令_.更新先:
                文脈.状態[命令_.更新先] = result
        elif op == 作用.停止:
            文脈.停止済み = True
            result = True
        else:
            raise ValueError(f"未対応作用: {op}")

        文脈.履歴.append({"名称": 命令_.名称, "作用": op.value, "対象": 命令_.対象, "引数": args, "結果": result, "根拠": 命令_.根拠})
