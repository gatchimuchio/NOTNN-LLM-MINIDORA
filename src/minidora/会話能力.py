"""既存の証拠・関係能力を役割付き比較と回答意味へ接続する。

資料の真偽を認定しない。未解釈・競合を新しい資料で隠さず、記載報告として返す。
"""
from __future__ import annotations
from copy import deepcopy
from fractions import Fraction
from hashlib import sha256
from .能力合成 import 登録能力, _結果辞書, _符号化, _参照結合
from .製品版.型 import 能力結果, 参照資料
from .製品版.能力契約 import 能力文脈
from .証拠統合 import 証拠統合器, 証拠照合要求, _数表記
from .関係制約接続 import 数値報告を関係化
from .関係制約 import 関係式, 関係問題を復元, 関係制約器, 関係記録整合
from .応答構成 import 能力結果を復元, _報告を確認, _表示値, _理由文, _適用範囲, _共通域文
from .会話失敗 import 不成立

会話能力版 = 'MINIDORA-会話能力-v0.1'


def _入力(context):
    if type(context) is not 能力文脈 or type(context.補助) is not dict:
        raise ValueError('合成文脈が必要')
    inputs = context.補助.get('合成入力', ())
    settings = context.補助.get('合成設定', {})
    if type(inputs) is not tuple or not 1 <= len(inputs) <= 8 or type(settings) is not dict:
        raise ValueError('入力又は設定の型不正')
    results = tuple(能力結果を復元(r['結果']) for r in inputs)
    if any(not r.成立 for r in results): raise ValueError('上流不成立')
    return results, settings


def _正規結果(result):
    raw = _結果辞書(result)
    raw['参照'] = [s.辞書化() for s in sorted(_参照結合(result.参照), key=lambda s: s.識別子)]
    return raw


class 会話記載解釈:
    名前 = '会話記載解釈'
    版 = 会話能力版
    優先度 = 0
    def 判定(self, context): return 1.0
    def 実行(self, context):
        target = ''
        try:
            values, settings = _入力(context)
            if len(values) != 1 or set(settings) != {'対象', '属性', '単位', '条件', '時点', '取得済'}:
                raise ValueError('単一素材と完全な記載設定が必要')
            if type(settings['取得済']) is not bool: raise ValueError('取得区分不正')
            target = settings['対象']
            request = 証拠照合要求(**{k: v for k, v in settings.items() if k != '取得済'})
            request.検証()
            value = values[0]
            if settings['取得済']:
                refs = value.参照
                if not refs: return 不成立('資料不足', target, '取得本文がありません')
            else:
                if value.データ or value.参照:
                    raise ValueError('ローカル素材は未加工の本文を渡してください')
                if not value.本文.strip(): return 不成立('資料不足', target, '指定対象のローカル資料がありません')
                identity = sha256(_符号化([target, value.本文])).hexdigest()
                refs = (参照資料('会話資料:' + identity, target, '利用者提供', 本文=value.本文),)
            result = 証拠統合器().実行(request, refs)
            if not result.成立: return 不成立('入力不正', target, '既存の証拠契約を満たしません')
            # 報告は未解釈・競合も保持する。採用値の存在とは区別する。
            return result
        except (ValueError, TypeError, KeyError, AttributeError, RecursionError) as exc:
            return 不成立('入力不正', target if type(target) is str else '', str(exc)[:1024])
    def 登録(self): return 登録能力(self)


def 比較問題を作る(reports):
    if len(reports) != 2: raise ValueError('比較には二つの数値報告が必要')
    left, right = tuple(_報告を確認(x) for x in reports)
    a, b = left.データ['要求']['対象'], right.データ['要求']['対象']
    if a == b: raise ValueError('同じ対象を別対象として比較しません')
    questions = tuple(関係式(k, a, op, b) for k, op in (('大', '超'), ('同', '一致'), ('小', '未満')))
    result = 数値報告を関係化((left, right), questions)
    if not result.成立: raise ValueError('属性・単位・条件・時点が揃わないか、適用群を選べません')
    return result


class 会話比較接続:
    名前 = '会話比較接続'
    版 = 会話能力版
    優先度 = 0
    def 判定(self, context): return 1.0
    def 実行(self, context):
        try:
            values, settings = _入力(context)
            if settings: raise ValueError('比較接続に追加設定は不要')
            return 比較問題を作る(values)
        except (ValueError, TypeError, KeyError, AttributeError, RecursionError) as exc:
            return 不成立('適用範囲不一致', '', str(exc)[:1024])
    def 登録(self): return 登録能力(self)


def _記載を節へ(report, index, node):
    """報告本文の貼付ではなく、採用値・範囲・反対記載・残差を意味単位にする。"""
    data, req = report.データ, report.データ['要求']
    subject = _表示値(req['対象']) + 'の' + _表示値(req['属性'])
    if data['採用可']:
        node('記載値', subject + f'の記載値は{data["採用値"]} {data["採用単位"]}です。'
             + _適用範囲(data['採用条件'], data['採用時点']) + 'の記載に限ります。',
             ((index, '採用値'), (index, '採用条件・採用時点')))
    else:
        node('記載値保留', subject + 'は一つの値として採用できません。', ((index, '採用可'),))
    for reason in data['理由']:
        node('留保', subject + ': ' + _理由文[reason], ((index, '理由/' + reason),))
    claims = {c['主張ID']: c for c in data['主張']}
    for gi, group in enumerate(data['群']):
        selected = ((req['条件'] is None or group['条件'] == req['条件'])
                    and (req['時点'] is None or group['時点'] == req['時点']))
        # 一点の採用時は上で記述済み。それ以外の範囲・別条件は明示して残す。
        if data['採用可'] and selected:
            continue
        members = [claims[k] for k in group['主張ID']]
        scope = _適用範囲(group['条件'], group['時点'])
        node('記載範囲', subject + ': ' + scope + ('（照合範囲）' if selected else '（指定範囲外）')
             + _共通域文(group, members[0]['単位']), ((index, f'群/{gi}'),))
        # 否定・不等号・反対値は原文位置に接続したまま示す。
        for claim in members:
            node('根拠引用', _表示値(claim['原文']),
                 ((index, '主張/' + claim['主張ID']),
                  ('参照', claim['参照ID'], claim['開始'], claim['終了'])))
    for j, residual in enumerate(data['残差']):
        node('未解釈', '未解釈の記載: ' + _表示値(residual['原文']),
             ((index, f'残差/{j}'), ('参照', residual['参照ID'], residual['開始'], residual['終了'])))


def 回答意味を作る(values, settings):
    if type(values) is not tuple or not 1 <= len(values) <= 8:
        raise ValueError('回答元成果の範囲外')
    if type(settings) is not dict or set(settings) - {'種別', '形式', '最大文字数'} or '種別' not in settings:
        raise ValueError('回答仕様不正')
    kind, style, limit = settings['種別'], settings.get('形式', '段落'), settings.get('最大文字数', 20000)
    if style not in ('段落', '箇条書き') or type(limit) is not int or not 1 <= limit <= 100000:
        raise ValueError('回答形式又は予算不正')
    if len(_符号化([_結果辞書(v) for v in values])) > 1000000:
        raise ValueError('回答入力予算超過')
    nodes = []
    def node(role, text, origins):
        nodes.append({'役割': role, '本文': text, '由来': origins})
    if kind == '比較':
        if len(values) != 3: raise ValueError('比較報告と両方の証拠を保持する')
        result, left, right = values
        problem = 比較問題を作る((left, right))
        replay = 関係制約器().実行(関係問題を復元(problem.データ['関係問題']), problem.参照)
        if not 関係記録整合(result) or _符号化(_正規結果(result)) != _符号化(_正規結果(replay)):
            raise ValueError('比較結論と元証拠からの導出が一致しません')
        req = left.データ['要求']; a, b = req['対象'], right.データ['要求']['対象']
        derived = [r['問い']['識別子'] for r in result.データ['回答'] if r['判定'] == '導出']
        if len(derived) > 1: raise ValueError('大小判定が競合')
        if derived:
            conclusion = {'大': 'より大きい', '小': 'より小さい', '同': 'と等しい'}[derived[0]]
            text = f'資料の記載から、{_表示値(a)}の{_表示値(req["属性"])}は{_表示値(b)}{conclusion}と判断できます。'
        elif not result.データ['前提整合']:
            text = '資料の記載が矛盾しているため、大小・等値の結論を採用できません。'
        else:
            text = '資料に未解釈部分があるか、値の範囲だけでは大小・等値を一つに決められません。'
        node('結論', text, ((0, '回答'),))
        for index, report in enumerate((left, right), 1):
            _記載を節へ(report, index, node)
        if left.データ['採用可'] and right.データ['採用可']:
            if req['単位'] != right.データ['要求']['単位']: raise ValueError('表示単位不一致')
            delta = Fraction(left.データ['採用値']) - Fraction(right.データ['採用値'])
            node('差分', f'記載値の差（{_表示値(a)}−{_表示値(b)}）は{_数表記(delta)} {req["単位"]}です。',
                 ((1, '採用値'), (2, '採用値')))
        p = result.データ['問題']
        node('適用範囲', f'条件={_表示値(p["条件"]) if p["条件"] is not None else "未記載"}、時点={p["時点"] or "未記載"}の記載比較です。', ((0, '問題'),))
    elif kind == '記載':
        if len(values) != 1: raise ValueError('単一の証拠報告が必要')
        report = _報告を確認(values[0])
        _記載を節へ(report, 0, node)
    elif kind == '既存成果':
        if any(not v.成立 for v in values): raise ValueError('成立した能力成果が必要')
        for i, result in enumerate(values):
            node('処理結果', result.本文, ((i, '本文'),))
    else:
        raise ValueError('未対応の回答意味')
    if kind != '既存成果':
        node('限界', '資料の真偽と出典の独立性は未確認です。未記載の条件・時点を、現実の同一条件や最新情報とは認定しません。', ())
    refs = tuple(sorted(_参照結合(s for v in values for s in v.参照), key=lambda s: s.識別子))
    for i, ref in enumerate(refs, 1):
        node('出典', f'[{i}] {_表示値(ref.題名)} / {_表示値(ref.出典)}' + (f' / {_表示値(ref.URL)}' if ref.URL else ''),
             (('参照', ref.識別子),))
    data = {'版': 会話能力版, '種別': kind, '形式': style, '最大文字数': limit, '節': nodes,
            '元成果': [_正規結果(v) for v in values], '仕様': deepcopy(settings)}
    data['意味SHA256'] = sha256(_符号化(data)).hexdigest()
    return 能力結果(True, '回答の意味と由来を構成しました。', 参照=refs, データ=data)


class 会話回答意味:
    名前 = '会話回答意味'
    版 = 会話能力版
    優先度 = 0
    def 判定(self, context): return 1.0
    def 実行(self, context):
        try:
            values, settings = _入力(context)
            return 回答意味を作る(values, settings)
        except (ValueError, TypeError, KeyError, AttributeError, RecursionError) as exc:
            return 不成立('入力不正', '', str(exc)[:1024])
    def 登録(self): return 登録能力(self)


class 会話文章化:
    名前 = '会話文章化'
    版 = 会話能力版
    優先度 = 0
    def 判定(self, context): return 1.0
    def 実行(self, context):
        try:
            values, settings = _入力(context)
            if len(values) != 1 or settings: raise ValueError('回答意味だけを入力する')
            value, raw = values[0], values[0].データ
            # hash一致だけでなく元成果から意味・条件・否定・留保を再構成する。
            original = tuple(能力結果を復元(r) for r in raw['元成果'])
            rebuilt = 回答意味を作る(original, raw['仕様'])
            if _符号化(_正規結果(value)) != _符号化(_正規結果(rebuilt)):
                raise ValueError('回答意味の再構成不一致')
            sep, prefix = ('\n', '- ') if raw['形式'] == '箇条書き' else ('\n\n', '')
            body = sep.join(prefix + n['本文'] for n in raw['節'])
            if len(body) > raw['最大文字数']: raise ValueError('回答予算不足。必須内容を切断しません')
            return 能力結果(True, body, 参照=rebuilt.参照,
                データ={'版': 会話能力版, '回答意味': deepcopy(raw), '本文SHA256': sha256(body.encode()).hexdigest()})
        except (ValueError, TypeError, KeyError, AttributeError, RecursionError) as exc:
            return 不成立('入力不正', '', str(exc)[:1024])
    def 登録(self): return 登録能力(self)


def 会話追加能力():
    return tuple(c().登録() for c in (会話記載解釈, 会話比較接続, 会話回答意味, 会話文章化))
