"""目的から導出された中間関係を、既存の外部観測要求へ射影する。

検索文は知識ではない。元の関係・極性・条件・利用先を別途保持し、検索結果は
既存Compilerで再構文化・検証する。未完了の計画を具体的な観測要求へ偽装しない。
"""
from __future__ import annotations
import json
from ..駆動系.目的不足 import 関係不足


def _表層(値,意味集合=False):
    if not 意味集合:
        return str(値)
    try:
        群=json.loads(値)
    except (TypeError,ValueError):
        raise ValueError('Compiler意味集合の符号化が不正')
    if not isinstance(群,list) or any(not isinstance(x,str) for x in 群):
        raise ValueError('Compiler意味集合は文字列列である必要がある')
    return ' '.join(群)


def 不足観測内容(不足,*,候補ラベル,言語):
    if not isinstance(不足,関係不足):
        raise TypeError('目的・利用先付きの関係不足が必要')
    if 不足.状態 in ('停止','予算未完了'):
        raise ValueError('未完了の計画は外部観測へ進めない')
    if not isinstance(言語,str) or not 言語.strip():
        raise ValueError('外部言語の指定が必要')
    節=不足.対象
    既知=tuple(_表層(x.名前,x.型=='意味端点') for _,x in 節.引数 if not x.変数)
    役割=tuple(k for k,x in 節.引数 if x.変数)
    述語=節.述語
    種別,区切り,意味述語=述語.partition(':')
    if 区切り and 意味述語.startswith('['):
        述語=_表層(意味述語,True) or 種別
    # 極性を失った検索語だけから肯定/否定を認定しない。両方を検証する。
    条件=tuple(('意味条件',x) for x in 節.条件)+(
        ('極性','肯定' if 節.肯定 else '否定'),('範囲',節.範囲),
        ('時点',節.時点),('様相',節.様相),('量化',節.量化))
    return dict(ID=不足.ID,関係ID=不足.ID,関係種別=節.述語,
        未知位置=役割[0] if len(役割)==1 else None,既知端点=既知,
        条件範囲=条件,候補ラベル=候補ラベル,候補表層=None,
        外部言語=言語,外部検索表層=' '.join((*既知,述語)),必須被覆=True,
        外部文脈アンカー=既知,段階='primary',優先度=0,
        provenance=('目的:'+不足.目的ID,'不足:'+不足.署名,
            *('利用先:'+x for x in 不足.利用先),*('変換:'+x for x in 不足.経路)))


def 不足から観測要求(不足,*,候補ラベル,言語):
    from ..HDS観測計画 import HDS参照観測要求
    return HDS参照観測要求(**不足観測内容(不足,候補ラベル=候補ラベル,言語=言語))