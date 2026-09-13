"""引用・資料本文を変更せず、有限な依頼語尾と表示指定を分離する。

表層射影を自由な言い換え器として扱わない。未対応の条件は削除せず後段で拒否する。
"""
from __future__ import annotations

import re
from .命題句 import 最上位位置, 引用を切り出す

依頼表層版 = 'MINIDORA-依頼表層-v0.1'
_依頼語尾 = ('してください', 'して下さい', 'してくれますか', 'してもらえますか',
             'していただけますか', 'してもらえる', 'してくれる', 'してほしい', 'して')
_動詞 = {'判断': '判定', '判定': '判定', '検討': '検討', '比較': '比較', '説明': '説明'}


def _句末(text: str) -> str:
    # 句読点以外の条件・否定・例外を消さない。連続する疑問符も未対応として残す。
    return text[:-1].rstrip() if text.endswith(('。', '？', '?')) else text


def _依頼形(text: str) -> str:
    text = _句末(text.strip())
    for ending in _依頼語尾:
        if text.endswith(ending):
            stem = text[:-len(ending)]
            for verb, normal in _動詞.items():
                if stem.endswith(verb):
                    return stem[:-len(verb)] + normal + 'して'
    return text


def _表示(text: str):
    plain = _依頼形(text)
    hit = re.fullmatch(r'(もう少し)?(短く|簡潔に|詳しく|詳細に)説明して', plain)
    if not hit:
        return None
    return {'詳細': hit[2] in ('詳しく', '詳細に'), '相対表示': bool(hit[1])}


def 依頼外形を分離(原文: str) -> dict:
    if type(原文) is not str or not 原文.strip() or len(原文) > 8192:
        raise ValueError('依頼表層の原文型・長さ不正')
    原文.encode('utf-8', errors='strict')
    # 登録文のコロン以降は自由な資料Data。この関数では全文に一切作用しない。
    if 原文.strip().startswith(('命題資料', '仮説資料', '介入資料')):
        return {'射影文': 原文, '表示': None, '対応': [], '版': 依頼表層版}
    spans = []
    pos = 0
    for i, word in 最上位位置(原文, ('、', ',', '。', '\n')):
        if word in ('、', ',') and not 原文[i + len(word):].strip():
            raise ValueError('依頼末尾の空の節を捨てない')
        if 原文[pos:i].strip():
            spans.append((pos, i))
        elif word != '\n':
            raise ValueError('依頼に空の節がある')
        pos = i + len(word)
    if 原文[pos:].strip():
        spans.append((pos, len(原文)))
    if not spans or len(spans) > 3:
        raise ValueError('依頼節の数が未対応')
    tasks, presentation, trace = [], None, []
    for start, end in spans:
        raw = 原文[start:end]
        display = _表示(raw)
        if display is not None:
            if presentation is not None:
                raise ValueError('表示条件の重複又は競合を勝手に解決しない')
            presentation = display
            projected = ('詳しく' if display['詳細'] else '短く') + '説明して'
            role = '表示条件'
        else:
            projected = _依頼形(raw)
            # 資料接続の外側だけを置換。引用名・問いの内容には触らない。
            if projected.startswith(('資料「', '資料『')):
                _, finish = 引用を切り出す(projected, 2)
                tail = projected[finish:]
                for marker in ('に基づいて', 'に基づき', 'をもとに', 'を基に'):
                    if tail.startswith(marker):
                        projected = projected[:finish] + 'から' + tail[len(marker):]
                        break
            tasks.append(projected)
            role = '処理依頼'
        trace.append({'役割': role, '開始': start, '終了': end, '原文': raw, '射影': projected})
    if len(tasks) > 1:
        raise ValueError('複数の処理目的を一つへ落とさない')
    if tasks:
        if presentation and presentation['相対表示']:
            raise ValueError('新しい検討に相対的な表示量は指定できない。短く又は詳しくを明示する')
        projected = tasks[0]
    elif presentation:
        projected = ('詳しく' if presentation['詳細'] else '短く') + '説明して'
    else:
        raise ValueError('処理又は表示の目的がない')
    return {'射影文': projected, '表示': presentation, '対応': trace, '版': 依頼表層版}


def 表層対応を検査(原文: str, 対応: dict) -> bool:
    """原文との再構成照合。外から渡された射影だけを信用しない。"""
    try:
        return type(対応) is dict and 対応 == 依頼外形を分離(原文)
    except (ValueError, TypeError, UnicodeError):
        return False
