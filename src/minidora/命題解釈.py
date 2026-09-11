"""命題を再利用可能な節・接続・量化へ解析する。全文を消費し、未知尾部を捨てない。

日本語の所属記載、任意述語の関数形、否定、括弧、連言・選言・含意を構成する。
混在する接続詞の係り先と全称否定の作用域は候補を残す。自由な日本語理解器ではない。
"""
from __future__ import annotations

import itertools
import re
from .命題構造 import 命題項, 命題式, 命題候補, 命題記載, 原子, 結合, 反対, 文脈を付す

_名前 = re.compile(r'[^\s「」（）()、。，,；;：:！？!?]{1,80}\Z')
_予約語 = ('ならば', 'かつ', 'または', 'である', 'ではない', 'について', '可能性', 'わけでは', 'ただし')


def _名(text):
    text = text.strip()
    if not _名前.fullmatch(text) or any(w in text for w in _予約語):
        raise ValueError('未解釈の命題名・修飾:' + text[:80])
    return text


def _外側(text):
    if not text or text[0] not in '(（':
        return None
    stack = []
    for i, c in enumerate(text):
        if c in '(（':
            stack.append(c)
        elif c in ')）':
            if not stack or (stack.pop(), c) not in (('(', ')'), ('（', '）')):
                raise ValueError('命題の括弧が不整合')
            if not stack:
                return text[1:-1] if i == len(text) - 1 else None
    raise ValueError('命題の括弧が閉じていない')


def _接続位置(text):
    stack = []; out = []; i = 0
    while i < len(text):
        c = text[i]
        if c in '(（':
            stack.append(c)
        elif c in ')）':
            if not stack or (stack.pop(), c) not in (('(', ')'), ('（', '）')):
                raise ValueError('命題の括弧が不整合')
        if not stack:
            for word, kind in (('ならば', '含意'), ('かつ', '連言'), ('または', '選言')):
                if text.startswith(word, i):
                    out.append((i, word, kind)); i += len(word) - 1; break
        i += 1
    if stack:
        raise ValueError('命題の括弧が閉じていない')
    return out


def 命題を読む(text: str, *, 最大候補=8) -> tuple[命題候補, ...]:
    if type(text) is not str or not 0 < len(text) <= 4096:
        raise ValueError('命題原文の型・上限')
    if type(最大候補) is not int or not 1 <= 最大候補 <= 16:
        raise ValueError('意味候補上限不正')
    expanded = 0

    def unique(values):
        found = {}
        for x in values:
            found.setdefault(x.鍵(), x)
            if len(found) > 最大候補:
                raise ValueError('意味候補の上限。括弧で作用域を指定する')
        return tuple(found.values())

    def parse(raw, variables=frozenset(), depth=0):
        nonlocal expanded
        expanded += 1
        if expanded > 512 or depth > 24:
            raise ValueError('命題解析の展開・深さ上限')
        s = raw.strip()
        if not s:
            raise ValueError('空の命題節')
        inside = _外側(s)
        if inside is not None:
            return parse(inside, variables, depth + 1)
        context = re.fullmatch(r'(?:時点「([^「」]+)」では|([0-9]{4})年では)([（(].*[）)])', s, re.S)
        if context:
            time = context[1] or context[2] + '年'
            return tuple(文脈を付す(e, 時点=time) for e in parse(context[3], variables, depth + 1))
        modal = re.fullmatch(r'(可能性として|義務として)([（(].*[）)])', s, re.S)
        if modal:
            mood = '可能' if modal[1] == '可能性として' else '義務'
            return tuple(文脈を付す(e, 様相=mood) for e in parse(modal[2], variables, depth + 1))
        if s.startswith('否定') and _外側(s[2:].strip()) is not None:
            return tuple(反対(e) for e in parse(s[2:], variables, depth + 1))
        scoped = re.fullmatch(r'(すべての|ある)([A-Za-z][A-Za-z0-9_]*)について([（(].*[）)])', s, re.S)
        if scoped:
            word, var, body = scoped.groups()
            if var in variables:
                raise ValueError('量化変数の二重束縛')
            kind = '全称' if word == 'すべての' else '存在'
            return tuple(結合(kind, e, 変数=var) for e in parse(body, variables | {var}, depth + 1))
        operators = _接続位置(s)
        implications = [r for r in operators if r[2] == '含意']
        if implications:
            if len(implications) != 1:
                raise ValueError('含意の作用域を括弧で指定する')
            pos, word, kind = implications[0]
            return unique(結合(kind, a, b) for a in parse(s[:pos], variables, depth + 1)
                          for b in parse(s[pos + len(word):], variables, depth + 1))
        if operators:
            # 一種類の結合は平坦化する。混在時は勝手に優先順位を設定しない。
            if len({r[2] for r in operators}) == 1:
                pieces = []; start = 0
                for pos, word, kind in operators:
                    pieces.append(s[start:pos]); start = pos + len(word)
                pieces.append(s[start:])
                if len(pieces) > 8:
                    raise ValueError('一つの連言・選言の節数上限')
                alternatives = [parse(p, variables, depth + 1) for p in pieces]
                return unique(結合(kind, *row) for row in itertools.product(*alternatives))
            values = []
            for pos, word, kind in operators:
                for a in parse(s[:pos], variables, depth + 1):
                    for b in parse(s[pos + len(word):], variables, depth + 1):
                        values.append(結合(kind, a, b))
                        if len(values) > 32:
                            raise ValueError('係り受け候補上限')
            return unique(values)
        categorical = re.fullmatch(r'(すべての|一部の)(.+?)は(.+?)(である|です|ではない|ではありません)', s)
        if categorical:
            quantifier, subject, predicate, end = categorical.groups()
            subject, predicate = _名(subject), _名(predicate)
            var = '_対象' + str(depth)
            t = 命題項(var, '変数')
            left, right = 原子(subject, t), 原子(predicate, t)
            negative = end in ('ではない', 'ではありません')
            if quantifier == '一部の':
                return (結合('存在', 結合('連言', left, 反対(right) if negative else right), 変数=var),)
            universal = 結合('全称', 結合('含意', left, right), 変数=var)
            if negative:
                return (結合('全称', 結合('含意', left, 反対(right)), 変数=var), 反対(universal))
            return (universal,)
        copula = re.fullmatch(r'(.+?)は(.+?)(である|です|ではない|ではありません)', s)
        if copula:
            subject, predicate, end = copula.groups()
            subject, predicate = _名(subject), _名(predicate)
            if subject in ('それ', 'これ', 'あれ'):
                raise ValueError('命題の指示対象を明示する')
            atom = 原子(predicate, 命題項(subject, '変数' if subject in variables else '定数'))
            return (反対(atom) if end in ('ではない', 'ではありません') else atom,)
        functional = re.fullmatch(r'([^()（）]+)[(（]([^()（）]*)[)）]', s)
        if functional:
            predicate = _名(functional[1]); args = functional[2]
            names = [] if not args.strip() else [_名(v) for v in re.split('[,、]', args)]
            if len(names) > 4:
                raise ValueError('述語の項数上限')
            return (原子(predicate, *(命題項(v, '変数' if v in variables else '定数') for v in names)),)
        if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,79}', s):
            return (原子(s),)
        raise ValueError('未対応の命題節:' + s[:100])

    rows = unique(parse(text.strip()))
    for row in rows:
        row.検査()
    return tuple(命題候補(e, text, (0, len(text)), 命題を表現(e)) for e in rows)


def 命題を表現(e: 命題式) -> str:
    def term(t):
        if t.種別 == '存在証人': return '資料内のある個体'
        if t.種別 == '任意個体': return '任意の個体'
        return t.名前
    if e.種別 == '原子':
        body = f'{term(e.項[0])}は{e.述語}である' if len(e.項) == 1 else (
            e.述語 + '(' + '、'.join(term(t) for t in e.項) + ')' if e.項 else e.述語)
        if e.時点 != '未指定': body = f'時点「{e.時点}」では（{body}）'
        if e.様相 != '記載': body = ('可能性として' if e.様相 == '可能' else '義務として') + f'（{body}）'
        return body
    if e.種別 == '否定': return '否定（' + 命題を表現(e.子[0]) + '）'
    if e.種別 in ('全称', '存在'):
        body = e.子[0]
        if (body.種別 == ('含意' if e.種別 == '全称' else '連言') and len(body.子) == 2):
            a, b = body.子
            negative = b.種別 == '否定'
            right = b.子[0] if negative else b
            if (a.種別 == right.種別 == '原子' and len(a.項) == len(right.項) == 1
                    and a.項 == right.項 == (命題項(e.変数, '変数'),)
                    and a.時点 == right.時点 == '未指定' and a.様相 == right.様相 == '記載'):
                if e.種別 == '全称':
                    return (f'{a.述語}である任意の個体は{right.述語}ではない' if negative else
                            f'すべての{a.述語}は{right.述語}である')
                return f'{a.述語}であり{right.述語}' + ('ではない' if negative else 'である') + '個体が存在する'
        return ('すべての' if e.種別 == '全称' else 'ある') + e.変数 + 'について（' + 命題を表現(e.子[0]) + '）'
    word = {'連言': 'かつ', '選言': 'または', '含意': 'ならば'}[e.種別]
    return '（' + (' ' + word + ' ').join(命題を表現(c) for c in e.子) + '）'


def 命題資料を読む(text: str, name: str) -> tuple[命題記載, ...]:
    if type(text) is not str or not text.strip() or len(text) > 32000:
        raise ValueError('命題資料の型・サイズ')
    if type(name) is not str or not 0 < len(name) <= 128 or any(ord(c) < 32 for c in name):
        raise ValueError('命題資料名の型・上限')
    rows = []; start = 0; stack = []
    for i, char in enumerate(text + '\n'):
        if char in '(（': stack.append(char)
        elif char in ')）':
            if not stack or (stack.pop(), char) not in (('(', ')'), ('（', '）')):
                raise ValueError('資料の括弧不整合')
        if not stack and char in '。\n；;':
            fragment = text[start:i]
            if fragment.strip():
                candidates = 命題を読む(fragment)
                if len(candidates) != 1:
                    raise ValueError('資料「' + name + '」の意味が複数。括弧・明示否定で原資料を確定する:' + fragment)
                rows.append(命題記載(name + ':' + str(len(rows)), candidates[0].式, name, fragment, (start, i)))
                if len(rows) > 128: raise ValueError('資料の命題数上限')
            start = i + 1
    if stack: raise ValueError('資料の括弧が閉じていない')
    if not rows: raise ValueError('資料に命題がない')
    return tuple(rows)
