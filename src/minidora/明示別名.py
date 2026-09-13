"""提供資料の明示した別名定義を、同じ検討内の述語・定数へ作用させる。

世界知識・読みから同一視しない。定義の原位置と適用経路を残す。
帰属命題は不透明とし、他者の発言・信念の内部には外側の別名を適用しない。
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import re
from .命題句 import 最上位位置
from .命題構造 import 命題式, 命題項, 命題を復元
from .命題解釈 import 命題を表現

別名版 = 'MINIDORA-明示別名-v0.1'


def 別名宣言を分離(本文: str, 資料名: str):
    """独立行の明示宣言だけを分離し、残りの原文オフセットを保持する。"""
    if type(本文) is not str or not 本文.strip() or len(本文) > 32000:
        raise ValueError('別名資料の型・サイズ不正')
    rows, cuts, pos = [], [], 0
    for i, marker in 最上位位置(本文, ('\n',)):
        cuts.append((pos, i)); pos = i + len(marker)
    cuts.append((pos, len(本文)))
    chars = list(本文)
    for start, end in cuts:
        raw = 本文[start:end]
        if not raw.strip().startswith('別名'):
            continue
        match = re.fullmatch(r'\s*別名[:：]\s*(述語|実体)「([^「」\r\n]{1,80})」[=＝]「([^「」\r\n]{1,80})」[。]?\s*', raw)
        if not match:
            raise ValueError('別名宣言は独立行の 別名：述語/実体「別名」=「正規名」に限定する')
        kind, alias, target = match.groups()
        if (alias != alias.strip() or target != target.strip()
                or any(ord(c) < 32 for c in alias + target) or alias == target):
            raise ValueError('別名の名前が不正又は自己参照')
        rows.append({'種別': kind, '別名': alias, '正規名': target,
                     '資料': 資料名, '範囲': [start, end], '原文': raw})
        if len(rows) > 32:
            raise ValueError('一資料の別名定義上限')
        # 改行を含む原位置を保つ。本文中の語を文字列置換しない。
        chars[start:end] = [' '] * (end - start)
    return ''.join(chars), rows


def 別名対応を構成(宣言: list[dict]):
    if type(宣言) is not list or len(宣言) > 64:
        raise ValueError('別名宣言全体の上限')
    direct, origins = {}, {}
    for row in 宣言:
        key = (row['種別'], row['別名'])
        target = row['正規名']
        if key in direct and direct[key] != target:
            raise ValueError('同じ別名の正規名が競合している')
        direct[key] = target
        origins.setdefault(key, []).append(deepcopy(row))
    mapped = {}
    for key in sorted(direct):
        kind, alias = key
        cursor, seen, proof = alias, set(), []
        while (kind, cursor) in direct:
            if cursor in seen:
                raise ValueError('別名定義が循環している')
            seen.add(cursor)
            proof.extend(origins[(kind, cursor)])
            cursor = direct[(kind, cursor)]
        mapped[key] = (cursor, proof)
    return mapped


def 別名を適用(式: 命題式, 対応: dict):
    式.検査(自由変数=True)
    applied = []

    def name(kind, old, position):
        if (kind, old) not in 対応:
            return old
        new, proof = 対応[(kind, old)]
        applied.append({'種別': kind, '元': old, '先': new,
                        '位置': list(position), '根拠定義': deepcopy(proof)})
        return new

    def visit(e, path):
        if e.種別 == '帰属':
            # 同じ指示対象でも、発言・信念内の置換可能性は別問題。
            return e
        if e.種別 == '原子':
            return replace(e, 述語=name('述語', e.述語, (*path, '述語')),
                           項=tuple(命題項(name('実体', t.名前, (*path, '項', i)), t.種別)
                                    if t.種別 == '定数' else t for i, t in enumerate(e.項)))
        return replace(e, 子=tuple(visit(c, (*path, '子', i)) for i, c in enumerate(e.子)))

    result = visit(式, ())
    result.検査(自由変数=True)
    return result, applied


def 資料候補の別名を接続(資料: dict, 対応: dict):
    doc = deepcopy(資料)
    trace = []
    for row in doc['記載候補']:
        for number, candidate in enumerate(row['候補'], 1):
            expression, changes = 別名を適用(命題を復元(candidate['式']), 対応)
            if not changes:
                continue
            candidate['式'] = expression.辞書()
            # 射影文と元の読みは消さず、別名接続を独立した条件として保持する。
            candidate['別名接続'] = changes
            candidate['正規命題'] = 命題を表現(expression)
            trace.append({'記載': row['識別子'], '候補': number, '適用': changes})
    return doc, trace
