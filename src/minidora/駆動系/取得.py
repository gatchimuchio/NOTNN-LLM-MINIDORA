"""駆動系の取得。外部構文化を複製せず、既存の読取専用境界を保持する。"""
from __future__ import annotations
from copy import deepcopy


def 作用供給を取得(主体, 現在, 政策):
    """許可された供給器の作用を取得する。容量不足は所有主体へ返す。"""
    供給 = []
    for 供給器 in 主体.作用供給器:
        if getattr(供給器, "入力不変保証", False):
            候補 = 供給器.構成(現在)
        else:
            写し = deepcopy(現在)
            前署名 = 写し.状態署名
            候補 = 供給器.構成(写し)
            if 写し.状態署名 != 前署名:
                raise ValueError("作用供給器が状態を変更した")
        if type(候補) is not tuple:
            raise TypeError("作用供給器の返却はtupleが必要")
        if len(供給) + len(候補) > 政策.最大内部生成:
            return None
        for a in 候補:
            if (not isinstance(getattr(a, "作用ID", None), str) or not a.作用ID.strip()
                    or a.作用ID.startswith("内的/")
                    or not callable(getattr(a, "機会", None))
                    or not callable(getattr(a, "実行", None))):
                raise ValueError("供給作用の契約不正")
        供給.extend(候補)
    利用作用群 = (*主体.作用群, *供給)
    if len({a.作用ID for a in 利用作用群}) != len(利用作用群):
        raise ValueError("供給作用IDの重複")
    return 利用作用群


def 作用機会を取得(作用, 現在):
    """状態複製へだけ作用機会を問い合わせ、入力書換えと型の逸脱を拒否する。"""
    from ..HDS実行主体 import HDS作用機会
    if getattr(getattr(作用, "計画仕様", None), "入力不変保証", False):
        o = 作用.機会(現在)
    else:
        写し = deepcopy(現在)
        写し署名 = 写し.状態署名
        o = 作用.機会(写し)
        if 写し.状態署名 != 写し署名:
            raise ValueError("機会観測が主体状態を書換えた")
    if o is None:
        return None
    if not isinstance(o, HDS作用機会) or o.作用ID != 作用.作用ID:
        raise ValueError("作用機会の型/ID契約違反")
    return o


def 関係を取得(要求, 追加契約=()):
    """目標の依存述語から必要な既存関係を取得する。反対極性と条件を捨てない。"""
    from .契約 import 関係要求, 関係取得結果, 関係変換契約
    from .契約 import 構造要求,構造取得結果
    if isinstance(要求,構造要求):
        return 構造取得結果(要求)
    if not isinstance(要求,関係要求): raise TypeError('構造化された関係要求が必要')
    all_rules=tuple(追加契約)+要求.変換
    if any(not isinstance(x,関係変換契約) for x in all_rules): raise TypeError('変換契約型が必要')
    if len({x.ID for x in all_rules})!=len(all_rules): raise ValueError('変換契約IDが競合')
    # 極性を除いたキー。否定を見落として肯定を採用しない。
    def key(atom): return (atom.骨格[0],atom.骨格[1],*atom.骨格[3:])
    needed={key(要求.問い)}; selected={}; changed=True
    while changed:
        changed=False
        for goal in tuple(sorted(needed)):
            候補=tuple(r for r in all_rules if r.ID not in selected and key(r.結論)==goal)
            if not 候補: continue
            # 有効形成から来た依存契約付きmacroは、元規則列と証明上同値な短縮経路である。
            # 同じ結論についてmacroが存在する時は元経路を重複選択せず、macroの前提だけを展開する。
            macros=tuple(r for r in 候補 if r.依存契約)
            採用群=macros or 候補
            for rule in 採用群:
                selected[rule.ID]=rule
                needed.update(key(p) for p in rule.前提)
                changed=True
    rules=tuple(sorted(selected.values(),key=lambda r:(not bool(r.依存契約),r.ID)))
    facts=tuple(sorted((x for x in 要求.証拠 if key(x.節) in needed),key=lambda x:x.ID))
    return 関係取得結果(要求.署名,facts,rules,tuple(sorted({x[0] for x in needed})))
