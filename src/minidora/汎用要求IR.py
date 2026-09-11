"""目的と素材を能力名から分離する局所IR。種別は型宣言であり事実認定ではない。"""
from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass
from .能力合成 import _結果辞書, _符号化
from .製品版.型 import 能力結果

@dataclass(frozen=True, slots=True)
class 目的指定:
    識別子: str
    対象: str  # 名前付き素材、又は同じ要求中の目的ID
    成果種別: str
    引数参照: str
    原文範囲: tuple[int, int]

@dataclass(frozen=True, slots=True)
class 汎用要求IR:
    原文: str
    素材: dict[str, 能力結果]
    素材種別: dict[str, str]
    目的: tuple[目的指定, ...]
    引数Data: dict[str, dict]
    出力目的: tuple[str, ...]
    残差: tuple[str, ...] = ()

    def 固定複製(self):
        """型・参照・規模を検査してから複製。外部作用は起こさない。"""
        if type(self.原文) is not str or not self.原文.strip() or len(self.原文) > 8192:
            raise ValueError('要求原文の範囲外')
        if type(self.残差) is not tuple or any(type(x) is not str for x in self.残差):
            raise ValueError('残差型不正')
        if self.残差:
            raise ValueError('未解消の要求残差')
        if type(self.素材) is not dict or type(self.素材種別) is not dict or set(self.素材) != set(self.素材種別):
            raise ValueError('素材の型宣言不一致')
        if type(self.目的) is not tuple or not 1 <= len(self.目的) <= 16 or len(self.素材) > 32:
            raise ValueError('目的又は素材の数が範囲外')
        def 名前(x):
            if type(x) is not str or not x.strip() or len(x) > 128:
                raise ValueError('識別子不正')
        for name, value in self.素材.items():
            名前(name); 名前(self.素材種別[name]); _結果辞書(value)
            if not value.成立:
                raise ValueError('不成立の素材')
        if type(self.引数Data) is not dict or any(type(v) is not dict for v in self.引数Data.values()):
            raise ValueError('引数Data不正')
        names = set(self.素材)
        for goal in self.目的:
            if type(goal) is not 目的指定:
                raise ValueError('目的型不正')
            for x in (goal.識別子, goal.対象, goal.成果種別, goal.引数参照): 名前(x)
            if goal.識別子 in names or goal.引数参照 not in self.引数Data:
                raise ValueError('目的重複又は引数Data欠落')
            names.add(goal.識別子)
            span = goal.原文範囲
            if (type(span) is not tuple or len(span) != 2 or any(type(x) is not int for x in span)
                    or not 0 <= span[0] < span[1] <= len(self.原文)):
                raise ValueError('原文範囲不正')
        goals = {g.識別子 for g in self.目的}
        if any(g.対象 not in names for g in self.目的):
            raise ValueError('対象参照欠落')
        if (type(self.出力目的) is not tuple or not self.出力目的
                or any(type(x) is not str or x not in goals for x in self.出力目的)
                or len(set(self.出力目的)) != len(self.出力目的)):
            raise ValueError('出力目的不正')
        if set(self.引数Data) != {g.引数参照 for g in self.目的}:
            raise ValueError('未使用の引数Data')
        raw = {'素材': {k: _結果辞書(v) for k, v in self.素材.items()}, '引数': self.引数Data}
        if len(_符号化(raw)) > 2000000:
            raise ValueError('要求Dataのサイズ上限')
        return deepcopy(self)
