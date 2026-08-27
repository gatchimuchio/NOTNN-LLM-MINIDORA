"""互換窓口。

現行正本は ``hds入力参照境界.py``。この旧名は、過去の誤った「後段HDSへ参照を渡す」
命名とのAPI互換だけを保持し、新規コードでは使用しない。
"""

from .hds入力参照境界 import HDS入力Data束, HDS入力Data整列, HDS入力出典ID

HDS判断Data束 = HDS入力Data束
HDS判断Data整列 = HDS入力Data整列
HDS判断出典ID = HDS入力出典ID

__all__ = ["HDS判断Data束", "HDS判断Data整列", "HDS判断出典ID"]
