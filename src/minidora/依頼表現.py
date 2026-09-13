"""依頼行為と表示条件の表層文法。引用内容や資料本文を置換しない。

語尾・語順の違いを有限な行為へ接続する。未知の条件を捨てない。
"""
from __future__ import annotations

import re
from .命題句 import 構成句を分ける, 引用を切り出す

依頼表現版 = 'MINIDORA-依頼表現-v0.1'
依頼語尾 = r'(?:して|してください|してくれる|してくれますか|してもらえる|してもらえますか|してほしい)'


def 依頼節を読む(原文: str) -> tuple[tuple[int, int, str], ...]:
    """引用・括弧の外でのみ区切る。位置は原文のUnicode文字オフセット。"""
    if type(原文) is not str or not 原文.strip() or len(原文) > 8192:
        raise ValueError('依頼原文の型・上限')
    結果 = []
    for 開始, 終了 in 構成句を分ける(原文, ('、', '。', '？', '?', '！', '!', '\n', '；')):
        while 開始 < 終了 and 原文[開始].isspace():
            開始 += 1
        while 終了 > 開始 and 原文[終了 - 1].isspace():
            終了 -= 1
        if 開始 < 終了:
            結果.append((開始, 終了, 原文[開始:終了]))
    if not 結果:
        raise ValueError('依頼行為がない')
    return tuple(結果)


def 説明指定を読む(本文: str) -> dict | None:
    """表示要求を意味フィールドへ分離する。程度は二段階の既存説明契約。"""
    詳細 = re.fullmatch(r'(?:もう少し)?(短く|簡潔に|詳しく|詳細に)(?:説明|教示)(?:' + 依頼語尾 + '|をお願いします)', 本文)
    if 詳細:
        return {'詳細': 詳細[1] in ('詳しく', '詳細に')}
    if 本文 in ('短く', '簡潔に', '詳しく', '詳細に'):
        return {'詳細': 本文 in ('詳しく', '詳細に')}
    if re.fullmatch(r'(?:根拠|手順)(?:を|も)説明(?:' + 依頼語尾 + '|をお願いします)', 本文):
        return {'手順': True}
    if 本文 in ('表で', '表で説明して', '表にして'):
        return {'形式': '表'}
    if 本文 in ('文章で', '文章で説明して'):
        return {'形式': '文章'}
    return None


def 説明指定を統合(節: tuple[tuple[int, int, str], ...], *, 許可=('詳細', '手順', '形式')) -> dict:
    指定 = {}
    for _, _, 本文 in 節:
        値 = 説明指定を読む(本文)
        if 値 is None or not set(値) <= set(許可):
            raise ValueError('未解釈の表示条件:' + 本文)
        for 名前, 内容 in 値.items():
            if 名前 in 指定 and 指定[名前] != 内容:
                raise ValueError('矛盾する表示条件:' + 名前)
            指定[名前] = 内容
    return 指定


def 命題依頼を読む(本文: str) -> tuple[str, int, int]:
    """命題と依頼述語を分離する。命題の真偽や語義は判定しない。"""
    末尾 = r'(?:を(?:判定|判断|検証|検討)' + 依頼語尾 + r'|の(?:判定|判断|検証|検討)をお願いします|(?:は|と)言える(?:の|か)?|は正しい(?:の|か)?)'
    余白 = len(本文) - len(本文.lstrip())
    if 本文[余白:].startswith(('「', '『')):
        命題, 終了 = 引用を切り出す(本文, 余白)
        if re.fullmatch(末尾, 本文[終了:].strip()) is None:
            raise ValueError('命題依頼の未解釈末尾')
        return 命題, 余白 + 1, 終了 - 1
    対応 = re.fullmatch(r'(.+?)' + 末尾, 本文)
    if 対応 is None:
        raise ValueError('命題と依頼述語を分離できない')
    命題 = 対応[1].strip()
    if not 命題:
        raise ValueError('問いが空')
    開始 = 対応.start(1) + len(対応[1]) - len(対応[1].lstrip())
    return 命題, 開始, 開始 + len(命題)
