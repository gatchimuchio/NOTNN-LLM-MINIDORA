"""会話の対象・属性から役割グラフへ。外部取得は別許可でのみ計画する。"""
from __future__ import annotations
from dataclasses import asdict
from .複数素材計画 import 役割状態, 結合作用
from .会話要求 import 会話要求
from .製品版.型 import 能力結果
from .知識取得 import 知識取得要求


def _記載設定(binding, settings, fetched=False):
    return {**{k: settings[k] for k in ('属性', '単位', '条件', '時点')},
            '対象': binding['対象'], '取得済': fetched}


def _検索設定(binding, settings):
    # 明示した対象・属性・範囲だけ。添付本文や過去会話を検索先へ送らない。
    words = [binding['対象'], settings['属性']]
    if settings['条件']: words.append(settings['条件'])
    if settings['時点']: words.append(settings['時点'])
    query = ' '.join(words + [settings['単位']])
    request = 知識取得要求(query, tuple(dict.fromkeys(words)), 最大検索回数=2, 最大取得数=4)
    request.検証()
    return asdict(request)


def 会話計画作用():
    one, pair, state = ('対象',), ('左', '右'), 役割状態
    def rule(name, module, inputs, output, config=lambda b, s: {}, **kw):
        return 結合作用(name, module, tuple(inputs), output, config, **kw)
    return (
        rule('ローカル記載', '会話記載解釈', (state('素材', one),), state('証拠', one), _記載設定, 回復可能=('資料不足',)),
        rule('目的から取得', '知識取得', (state('検索起点', one),), state('取得資料', one), _検索設定, 外部読取=True),
        rule('取得記載', '会話記載解釈', (state('取得資料', one),), state('証拠', one),
             lambda b, s: _記載設定(b, s, True)),
        rule('二対象関係化', '会話比較接続', (state('証拠', ('左',)), state('証拠', ('右',))), state('比較問題', pair)),
        rule('比較導出', '関係制約', (state('比較問題', pair),), state('比較報告', pair)),
        rule('比較意味', '会話回答意味', (state('比較報告', pair), state('証拠', ('左',)), state('証拠', ('右',))),
             state('回答意味', pair), lambda b, s: {'種別': '比較', '形式': s['形式'], '最大文字数': s['最大文字数']}),
        rule('照会意味', '会話回答意味', (state('証拠', one),), state('回答意味', one),
             lambda b, s: {'種別': '記載', '形式': s['形式'], '最大文字数': s['最大文字数']}),
        rule('比較文章化', '会話文章化', (state('回答意味', pair),), state('回答', pair)),
        rule('照会文章化', '会話文章化', (state('回答意味', one),), state('回答', one)),
    )


def 会話目的を準備(request: 会話要求, materials, *, 形式='段落', 最大文字数=20000):
    if type(request) is not 会話要求: raise ValueError('会話要求が必要')
    request.検証()
    if type(materials) is not dict or len(materials) > 32: raise ValueError('資料は名前付きの辞書')
    if 形式 not in ('段落', '箇条書き') or type(最大文字数) is not int or not 1 <= 最大文字数 <= 100000:
        raise ValueError('応答形式又は予算不正')
    values = {}
    for target in request.対象:
        value = materials.get(target, 能力結果(True, ''))
        if type(value) is not 能力結果 or value.データ or value.参照:
            raise ValueError('比較素材は未加工の本文だけを渡してください')
        values[役割状態('素材', (target,))] = value
        values[役割状態('検索起点', (target,))] = 能力結果(True, '明示された照会対象')
    settings = {**asdict(request), '形式': 形式, '最大文字数': 最大文字数}
    return 役割状態('回答', request.対象), values, settings
