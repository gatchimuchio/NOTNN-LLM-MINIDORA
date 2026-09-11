"""既存会話へ命題検討・意味候補選択・問い訂正を追加する境界。"""
from __future__ import annotations

import re
from .会話句 import 句を分割
from .会話意味 import 会話要求, 比較対象
from .命題解釈 import 命題を読む


_資料列 = r'資料「[^「」\n]+」(?:と資料「[^「」\n]+」)*'


def 命題会話を解釈(original, material_names):
    text = original.strip().rstrip('。？?')
    selection = re.fullmatch(r'解釈は([0-9]+)(?:です)?', text)
    if selection:
        return 会話要求(original, '命題選択', 補助={'番号': int(selection[1])}).固定複製()
    correction = re.fullmatch(r'(?:主張|問い)を「([^「」]+)」に訂正して', text)
    if correction:
        命題を読む(correction[1])
        pos = original.index('「') + 1
        return 会話要求(original, '命題訂正', 補助={'問い': correction[1], '命題範囲': (pos, pos + len(correction[1]))}).固定複製()
    if text in ('根拠を説明して', 'その根拠を説明して', 'なぜそう言える', 'なぜそう言えるの'):
        return 会話要求(original, '再表現', 詳細=True, 補助={'手順': True}).固定複製()
    if not (text.startswith(('資料「', 'この資料から', '全資料から')) and 'から「' in text):
        return None
    clauses = [original[a:b].strip() for a, b in 句を分割(original)]
    if not clauses: return None
    match = re.fullmatch(r'(' + _資料列 + r'|この資料|全資料)から「([^「」]+)」(は言える|と言える|は正しい|を検証して|を判定して)', clauses[0])
    if not match:
        raise ValueError('命題検討の資料・問い・末尾を解釈できない')
    source, query, _ = match.groups()
    names = tuple(re.findall(r'資料「([^「」]+)」', source))
    if source == 'この資料':
        if len(material_names) != 1: raise ValueError('この資料の参照先が一意でない')
        names = material_names
    elif source == '全資料': names = material_names
    if not 1 <= len(names) <= 8 or len(set(names)) != len(names):
        raise ValueError('命題検討の資料は重複のない1〜8件')
    if any(n not in material_names for n in names): raise ValueError('命題検討の資料が未登録')
    detailed = False; steps = False; format_ = '文章'
    for clause in clauses[1:]:
        if clause in ('詳しく', '詳しく説明して'): detailed = True; steps = True
        elif clause in ('根拠を説明して', '手順も説明して'): steps = True
        elif clause in ('表で', '表で説明して'): format_ = '表'
        else: raise ValueError('未解釈の命題検討条件:' + clause)
    命題を読む(query)
    pos = original.index('から「') + len('から「')
    return 会話要求(original, '命題照合', tuple(比較対象(n) for n in names), 詳細=detailed,
        補助={'問い': query, '候補': 0, '形式': format_, '手順': steps,
              '命題範囲': (pos, pos + len(query)),
              '資料参照解消': ((original.index('この'), original.index('この')+2),) if source=='この資料' else ()},
        対応=(('命題検討', 0, len(original)),)).固定複製()


def HDS命題を照合(ir, request):
    """実HDSを保持・照合。引用内の否定・条件を局所解析へ束縛し、無関係な残差は止める。"""
    from .hds_ir import HDSIR, 値状態
    if (type(ir) is not HDSIR or ir.原文 != request.原文 or ir.入力言語 != 'ja'
            or ir.出力言語 not in (None, 'ja')):
        raise ValueError('命題要求と実HDSの原文・言語不一致')
    coords = ir.座標辞書()
    if len(coords) != len(ir.座標): raise ValueError('HDS座標重複')
    source = [x for x in ir.座標 if x.種別 == 'source_text']
    if len(source) != 1 or source[0].内容 != request.原文:
        raise ValueError('HDS原文座標不一致')
    neutral = {'source_text', 'language.normalized', '文脈.言語', '制御.選択意図',
               '値.数量', '属性.単位', '対象.主題語', '目的.検索焦点'}
    # この入口は文法全体を解析済み。局所の引用名と命題の範囲を分けて監査記録に残す。
    spans = tuple(m.span() for m in re.finditer(r'「[^「」]*」', request.原文))
    mapped = []
    for c in ir.座標:
        if c.値状態 != 値状態.確定: raise ValueError('未確定のHDS座標')
        if c.種別 in neutral:
            if c.種別 == '制御.選択意図' and c.内容 != '通常':
                raise ValueError('未解消のHDS選択意図')
            continue
        if c.種別 not in ('状態.否定', '条件.前提') or type(c.内容) is not str or not c.内容:
            raise ValueError('命題へ未接続のHDS座標:' + c.種別)
        if c.内容 not in ir.正規化文 and c.内容 not in ir.原文:
            raise ValueError('HDS条件の原文対応がない')
        triggers = ('ではない', 'ではありません', '否定') if c.種別 == '状態.否定' else ('ならば', '前提', '条件')
        hits = [m for word in triggers for m in re.finditer(re.escape(word), request.原文)]
        if not hits or any(not any(a <= m.start() and m.end() <= b for a, b in spans) for m in hits):
            raise ValueError('引用範囲外の否定・条件が未解消')
        mapped.append((c.座標ID, c.種別, '解析済み引用の作用域として保持'))
    if ir.関係:
        raise ValueError('命題入口に未接続のHDS関係')
    resolved_reasons=set()
    bound=request.補助.get('資料参照解消',())
    for r in ir.残差:
        occurrences=tuple(re.finditer(re.escape(r.原文),request.原文)) if r.原文 else ()
        if (r.種別!='未解共参照' or r.影響座標 or len(request.対象)!=1 or not occurrences
                or not all(any(a<=m.start() and m.end()<=b for a,b in bound) for m in occurrences)):
            raise ValueError('命題入口に未解消のHDS残差')
        mapped.append((r.残差ID,r.種別,'一意な提供資料へ束縛'))
        resolved_reasons.add(r.理由)
    if any(loss not in resolved_reasons for a in ir.意味作用履歴 for loss in a.損失):
        raise ValueError('命題入口に未解消のHDS意味損失')
    return tuple(mapped)
