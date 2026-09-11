"""役割を束縛した複数入力の後方計画。予定状態を観測結果にしない。

開発時登録作用を合成し、外部読取数・費用・工程数の順に最小化する。
同順位の異なる計画は保留。事実認定・任意意味探索・隔離実行の代替ではない。
"""
from __future__ import annotations
from dataclasses import dataclass
from copy import deepcopy
from itertools import product
from typing import Callable
from .能力合成 import 合成計画, 合成工程, 素材参照, _符号化, _結果辞書
from .製品版.型 import 能力結果

@dataclass(frozen=True, slots=True)
class 役割状態:
    種別: str
    対象: tuple[str, ...]

    def 検証(self):
        if type(self.対象) is not tuple or not 1 <= len(self.対象) <= 8:
            raise ValueError('役割列の範囲外')
        for text in (self.種別, *self.対象):
            if type(text) is not str or not text.strip() or len(text) > 128:
                raise ValueError('役割状態の文字列不正')

@dataclass(frozen=True, slots=True)
class 結合作用:
    識別子: str
    能力: str
    入力: tuple[役割状態, ...]
    出力: 役割状態
    設定: Callable[[dict, dict], dict]
    外部読取: bool = False
    費用: int = 1
    回復可能: tuple[str, ...] = ()

@dataclass(frozen=True, slots=True)
class 計画節:
    状態: 役割状態
    作用: str = ''
    親: tuple['計画節', ...] = ()

@dataclass(frozen=True, slots=True)
class 結合計画結果:
    計画: 合成計画
    Data: dict[str, 能力結果]
    工程意味: dict[str, tuple[str, 役割状態]]
    費用: tuple[int, int, int]
    展開数: int


class 複数素材計画器:
    def __init__(self, 作用: tuple[結合作用, ...], *, 最大深さ=12, 最大展開数=2048, 最大候補数=64):
        if type(作用) is not tuple or not 1 <= len(作用) <= 128:
            raise ValueError('作用列の範囲外')
        for n, upper in ((最大深さ, 24), (最大展開数, 8192), (最大候補数, 256)):
            if type(n) is not int or not 1 <= n <= upper: raise ValueError('探索予算不正')
        for rule in 作用:
            if type(rule) is not 結合作用 or type(rule.外部読取) is not bool or type(rule.費用) is not int or rule.費用 < 0:
                raise ValueError('作用契約不正')
            if type(rule.入力) is not tuple or not 1 <= len(rule.入力) <= 8 or type(rule.出力) is not 役割状態:
                raise ValueError('作用の入出力不正')
            rule.出力.検証()
            for state in rule.入力:
                if type(state) is not 役割状態: raise ValueError('入力状態不正')
                state.検証()
            for text in (rule.識別子, rule.能力):
                if type(text) is not str or not text.strip() or len(text) > 128: raise ValueError('作用名不正')
            if len(rule.出力.対象) != len(set(rule.出力.対象)) or not callable(rule.設定):
                raise ValueError('出力役割不正')
            if any(not set(i.対象) <= set(rule.出力.対象) for i in rule.入力):
                raise ValueError('入力役割は出力役割から束縛する')
            if type(rule.回復可能) is not tuple or any(type(x) is not str for x in rule.回復可能):
                raise ValueError('回復契約不正')
        self.作用 = {r.識別子: r for r in 作用}
        if len(self.作用) != len(作用): raise ValueError('作用ID重複')
        self.上限 = (最大深さ, 最大展開数, 最大候補数)

    def 計画する(self, 目的: 役割状態, 素材: dict[役割状態, 能力結果], 設定: dict, *, 外部読取許可=False, 禁止=()):
        if type(目的) is not 役割状態 or type(素材) is not dict or type(設定) is not dict or type(外部読取許可) is not bool:
            raise ValueError('目的又は素材の型不正')
        目的.検証()
        for state, value in 素材.items():
            if type(state) is not 役割状態: raise ValueError('素材状態不正')
            state.検証(); _結果辞書(value)
            if not value.成立: raise ValueError('未成立素材')
        if len(素材) > 32 or len(_符号化([[_結果辞書(v) for v in 素材.values()], 設定])) > 1000000:
            raise ValueError('素材・設定予算超過')
        if type(禁止) is not tuple or any(type(x) is not tuple or len(x) != 2 or x[0] not in self.作用 or type(x[1]) is not 役割状態 for x in 禁止):
            raise ValueError('禁止経路不正')
        blocked, count = set(禁止), 0
        def solve(want, visiting, depth):
            nonlocal count
            count += 1
            if count > self.上限[1]: raise ValueError('探索展開予算超過')
            if want in 素材: return (計画節(want),)
            if want in visiting or depth >= self.上限[0]: return ()
            candidates = []
            for rule in self.作用.values():
                if rule.出力.種別 != want.種別 or len(rule.出力.対象) != len(want.対象): continue
                if (rule.識別子, want) in blocked or rule.外部読取 and not 外部読取許可: continue
                binding = dict(zip(rule.出力.対象, want.対象))
                children = []
                for req in rule.入力:
                    state = 役割状態(req.種別, tuple(binding[k] for k in req.対象))
                    choices = solve(state, visiting | {want}, depth + 1)
                    if not choices: break
                    children.append(choices)
                else:
                    for combination in product(*children):
                        candidates.append(計画節(want, rule.識別子, tuple(combination)))
                        if len(candidates) > self.上限[2]: raise ValueError('計画候補予算超過')
            return tuple(candidates)
        def nodes(node):
            out = {node}
            for parent in node.親: out.update(nodes(parent))
            return out
        def cost(node):
            actions = [self.作用[n.作用] for n in nodes(node) if n.作用]
            return sum(x.外部読取 for x in actions), sum(x.費用 for x in actions), len(actions)
        candidates = set(solve(目的, frozenset(), 0))
        if not candidates: raise ValueError('必要な作用経路がありません')
        minimum = min(cost(x) for x in candidates)
        best = [x for x in candidates if cost(x) == minimum]
        if len(best) != 1: raise ValueError('同順位の計画が複数あり未確定です')
        data, meanings, steps, refs = {}, {}, [], {}
        def emit(node):
            if node in refs: return refs[node]
            if not node.作用:
                name = f'結合素材:{len(data)}'
                data[name] = deepcopy(素材[node.状態])
                ref = 素材参照('入力', name)
            else:
                parents = tuple(emit(p) for p in node.親)
                rule = self.作用[node.作用]
                bound = dict(zip(rule.出力.対象, node.状態.対象))
                settings = rule.設定(bound, deepcopy(設定))
                if type(settings) is not dict: raise ValueError('作用設定は辞書')
                sid = f'結合工程:{len(steps):03d}'
                inst, conf = '指示:' + sid, '設定:' + sid
                data[inst] = 能力結果(True, '指定した役割と適用範囲の成果を求める')
                data[conf] = 能力結果(True, '', データ=settings)
                steps.append(合成工程(sid, (rule.能力,), inst, parents, conf))
                meanings[sid] = (rule.識別子, node.状態)
                ref = 素材参照('工程', sid)
            refs[node] = ref
            return ref
        root = emit(best[0])
        if root.領域 != '工程' or len(steps) > 64: raise ValueError('実行工程不成立')
        return 結合計画結果(合成計画(tuple(steps), (root.識別子,)), data, meanings, minimum, count)
