"""既存能力をHDS通常循環へ個別に接続する。独立の実行・監督ループは作らない。"""
from __future__ import annotations
from copy import deepcopy
from dataclasses import asdict, replace
import math

from ..HDS実行主体 import HDS作用機会, HDS作用結果, HDS作用状態
from ..採否 import 実行状態
from ..製品版.型 import 能力結果
from ..製品版.能力契約 import 能力文脈
from ..能力合成 import _結果辞書, _参照結合, _符号化
from ..会話意味 import 意味目的
from ..会話回答 import 回答記録整合, 会話回答版
from ..実行回復 import 失敗を分類, 回復方針を決定
from .契約 import 内容署名 as 署名
from .契約 import 成果を保存, 成果を復元, 計画を復元, 計画を検査, 資料を正規化, 運用版
from .要求構成 import 会話要求を復元

入力名 = '運用入力'
回答名 = '運用回答'
完了状態 = '依頼成果成立'
未完残差 = '依頼未完了'


def 現在案(状態):
    成果 = dict(状態.成果)
    番号 = [int(k.split(':')[1]) for k in 成果 if k.startswith('運用計画:')]
    if not 番号:
        return None
    版 = max(番号)
    return 版, 成果[f'運用計画:{版}']


def 工程鍵(版, 工程):
    return f'運用工程:{版}:{工程}'


def 試行鍵(版, 工程, 能力):
    return f'運用試行:{版}:{工程}:{能力}'


def 機会を作る(作用ID, 状態, 読取, 差別, *, 完了=False, 優先度=1.0, 権限=(), 種別='通常'):
    成果 = dict(状態.成果)
    if any(k not in 成果 for k in 読取):
        return None
    return HDS作用機会(作用ID, 署名((差別, tuple((k, 成果[k]) for k in 読取))),
        出力状態=frozenset({完了状態}) if 完了 else frozenset(),
        解消対象=frozenset({未完残差}) if 完了 else frozenset(),
        優先度=優先度, 読取成果=tuple(読取), 必要権限=tuple(権限), 種別=種別,
        契約版=運用版, 根拠=('依頼・意味計画・実成果に基づく作用',))


def 診断結果(理由, *, 成果=(), 失敗=False):
    return HDS作用結果(HDS作用状態.失敗 if 失敗 else HDS作用状態.保留,
        成果=tuple(成果), 理由=(理由,), 停止要求=True)


class 要求構成作用:
    作用ID = 'HDS運用/要求構成'

    def __init__(self, 構成器):
        self.構成器 = 構成器

    def 機会(self, 状態):
        if 現在案(状態) is not None or '要求診断' in dict(状態.成果):
            return None
        return 機会を作る(self.作用ID, 状態, (入力名,), 運用版, 種別='意味構成')

    def 実行(self, 状態):
        入力 = dict(状態.成果)[入力名]
        try:
            案 = self.構成器.構成する(deepcopy(入力))
            return HDS作用結果(HDS作用状態.成立, 成果=(('運用計画:0', 案),),
                                理由=('原要求から意味目的・能力計画を構成',))
        except (ValueError, TypeError, KeyError, PermissionError) as exc:
            診断 = {'理由': str(exc), '例外': type(exc).__name__, '原文': 入力['原文']}
            要求 = getattr(exc, '要求', None)
            if 要求 is not None:
                診断['保留要求'] = asdict(要求)
            return 診断結果(str(exc), 成果=(('要求診断', 診断),))


def 次工程(状態, 能力名):
    現在 = 現在案(状態)
    if 現在 is None:
        return None
    版, 案 = 現在
    if 案['種別'] != '処理':
        return None
    成果 = dict(状態.成果)
    計画, _ = 計画を復元(案['実行計画'])
    for 項 in 計画.工程:
        if 工程鍵(版, 項.識別子) in 成果:
            continue
        親 = tuple(工程鍵(版, r.識別子) for r in 項.入力 if r.領域 == '工程')
        if not all(k in 成果 for k in 親):
            continue
        for 候補 in 項.能力候補:
            試行 = 試行鍵(版, 項.識別子, 候補)
            if 試行 in 成果:
                if not 成果[試行].get('代替可', False):
                    break
                continue
            if 候補 == 能力名:
                return 版, 案, 項, 親
            break
    return None


def 工程文脈(状態, 版, 案, 項):
    成果 = dict(状態.成果)
    _, 資料 = 計画を復元(案['実行計画'])
    素材 = []
    for r in 項.入力:
        値 = 資料[r.識別子] if r.領域 == '入力' else 成果を復元(成果[工程鍵(版, r.識別子)]['成果'])
        素材.append((r, 値))
    補助 = {'合成入力': tuple({'参照': asdict(r), '結果': _結果辞書(v)} for r, v in 素材),
            '合成設定': deepcopy(資料[項.設定参照].データ) if 項.設定参照 else {}}
    参照 = _参照結合(r for _, v in 素材 for r in v.参照)
    文脈 = 能力文脈(資料[項.指示参照].本文, 成果[入力名]['セッションID'],
        '\n\n'.join(v.本文 for _, v in 素材), 参照, (), 補助)
    return 文脈, 参照


class 能力実行作用:
    def __init__(self, 目録, 能力名):
        self.目録, self.能力名 = 目録, 能力名
        self.作用ID = 'HDS運用/能力/' + 能力名

    def 機会(self, 状態):
        次 = 次工程(状態, self.能力名)
        if 次 is None:
            return None
        版, 案, 項, 親 = 次
        登録 = self.目録.登録[self.能力名]
        権限 = ('外部読取',) if 登録.外部読取 else ()
        return 機会を作る(self.作用ID, 状態, (入力名, f'運用計画:{版}', *親),
            (項.識別子, self.能力名, 登録.モジュール.版), 権限=権限)

    def 実行(self, 状態):
        self.目録.契約を検査()
        次 = 次工程(状態, self.能力名)
        if 次 is None:
            raise ValueError('作用時に実行可能な工程がない')
        版, 案, 項, _ = 次
        登録 = self.目録.登録[self.能力名]
        if 登録.外部読取 and not 案['外部許可']:
            return 診断結果('外部読取の許可なし', 失敗=True)
        文脈, 参照 = 工程文脈(状態, 版, 案, 項)
        元 = deepcopy(文脈)
        入力印 = 署名((文脈.入力文, 文脈.セッションID, 文脈.直前応答,
                         文脈.補助, tuple(r.識別子 for r in 参照)))
        記録 = {'工程': 項.識別子, '能力': self.能力名, '能力版': 登録.モジュール.版,
                '入力印': 入力印, '計画印': 署名(案['実行計画']), '代替可': False}
        try:
            判定 = 登録.モジュール.判定(文脈)
            if 文脈 != 元:
                raise ValueError('能力判定が入力を変更した')
            if type(判定) not in (int, float) or not math.isfinite(判定) or not 0 <= 判定 <= 1:
                raise ValueError('能力判定は0..1の有限数が必要')
            if 判定 == 0:
                結果 = 能力結果(False, '', 保留理由='能力非適用', 採否状態=実行状態.非適用)
                記録['代替可'] = True
            else:
                結果 = 登録.モジュール.実行(文脈)
                if 文脈 != 元:
                    raise ValueError('能力実行が入力を変更した')
                成果を保存(結果)
                結果 = replace(結果, 参照=_参照結合((*参照, *結果.参照)))
                記録['代替可'] = 結果.状態 == 実行状態.非適用
            記録['成果'] = 成果を保存(結果)
            記録['理由'] = 結果.保留理由
        except Exception as exc:
            # 例外・型破損は、外部副作用の有無を勝手に判定せず停止する。
            記録['理由'] = f'{type(exc).__name__}: {exc}'
            return 診断結果(記録['理由'], 成果=((試行鍵(版, 項.識別子, self.能力名), 記録),), 失敗=True)
        if 結果.成立:
            return HDS作用結果(HDS作用状態.成立,
                成果=((工程鍵(版, 項.識別子), 記録),),
                理由=(f'能力成果:{self.能力名}/{項.識別子}',))
        return HDS作用結果(HDS作用状態.保留,
            成果=((試行鍵(版, 項.識別子, self.能力名), 記録),),
            理由=(結果.保留理由 or 結果.状態.value,))


def 失敗工程(状態):
    現在 = 現在案(状態)
    if 現在 is None or 現在[1]['種別'] != '処理':
        return None
    版, 案 = 現在
    成果 = dict(状態.成果)
    計画, _ = 計画を復元(案['実行計画'])
    for 項 in 計画.工程:
        if 工程鍵(版, 項.識別子) in 成果:
            continue
        for 名 in 項.能力候補:
            鍵 = 試行鍵(版, 項.識別子, 名)
            if 鍵 in 成果 and not 成果[鍵]['代替可']:
                return 版, 案, 項, 鍵, 成果[鍵]
        if all(試行鍵(版, 項.識別子, x) in 成果 for x in 項.能力候補):
            鍵 = 試行鍵(版, 項.識別子, 項.能力候補[-1])
            return 版, 案, 項, 鍵, 成果[鍵]
    return None


def 被覆範囲(案, 対象):
    地図 = {x['目的鍵']: x for x in 案['要求被覆']}
    訪問, 待ち = set(), [対象]
    while 待ち:
        k = 待ち.pop()
        if k in 訪問:
            continue
        if k not in 地図:
            raise ValueError('回復対象の要求被覆欠落')
        訪問.add(k)
        待ち.extend(x[1] for x in 地図[k]['入力役割'])
    return 地図, 訪問


class 計画修復作用:
    作用ID = 'HDS運用/計画修復'

    def __init__(self, 構成器):
        self.構成器 = 構成器

    def 機会(self, 状態):
        次 = 失敗工程(状態)
        if 次 is None:
            return None
        版, _, 項, 鍵, _ = 次
        return 機会を作る(self.作用ID, 状態, (入力名, f'運用計画:{版}', 鍵),
            (版, 項.識別子), 優先度=2.0, 種別='修復')

    def 実行(self, 状態):
        版, 案, 項, 鍵, 失敗 = 失敗工程(状態)
        if '役割目的' not in 案 or 版 >= 8:
            return 診断結果('回復契約又は回復予算なし：' + 失敗['理由'])
        self.構成器.目録.契約を検査()
        種別 = 失敗['理由'].split(':', 2)
        種別 = 種別[1] if len(種別) == 3 and 種別[0] == '会話失敗' else '能力不成立'
        地図 = {sid: (key, 作用仕様) for sid, key, 作用仕様 in 案['工程作用']}
        発生目的, 発生作用 = 地図[項.識別子]
        契約 = next(x for x in self.構成器.目録.役割作用 if x.識別子 == 発生作用)
        規則 = next((x for x in 契約.回復 if x.失敗種別 == 種別), None)
        再開放 = None
        if 規則 is not None:
            if 規則.対象 == '自己':
                再開放 = (発生目的, 発生作用)
            else:
                親 = dict(dict(案['入力役割'])[項.識別子]).get(規則.入力役割)
                if 親 and 親['領域'] == '工程':
                    候補 = 地図[親['識別子']]
                    if 候補[1] in 規則.対象作用:
                        再開放 = 候補
        方針 = 回復方針を決定(種別=種別, 分類=失敗を分類(種別), 発生目的=発生目的,
            発生作用=発生作用, 規則=規則, 再開放=再開放, 契約=署名(asdict(規則)) if 規則 else '')
        if not 方針.自動実行 or 方針.動作 == '同一作用再試行':
            return 診断結果(方針.理由 + '：' + 失敗['理由'])
        入力 = dict(状態.成果)[入力名]
        資料 = {k: 成果を復元(v) for k, v in 入力['資料'].items()}
        禁止 = tuple(tuple(x) for x in 案['禁止']) + 方針.禁止
        if len(set(禁止)) != len(禁止):
            return 診断結果('同一失敗の回復反復を停止')
        try:
            新 = self.構成器._役割案(
                {k: deepcopy(案[k]) for k in ('原文', '構文化', '目録印')},
                意味目的(**案['役割目的']), 資料,
                会話要求を復元(案['意味']) if 案['意味'] else None, 入力, 禁止=禁止)
            旧地図, 旧範囲 = 被覆範囲(案, 方針.対象目的)
            新地図, 新範囲 = 被覆範囲(新, 方針.対象目的)
            if any(新地図.get(k) != v for k, v in 旧地図.items() if k not in 旧範囲):
                raise ValueError('修復が対象外の要求被覆を変更')
            if any(旧地図.get(k) != v for k, v in 新地図.items() if k not in 新範囲):
                raise ValueError('修復が対象外へ経路拡張')
            # 読取済み外部作用の再実行を一般的に安全とはしない。
            if any(self.構成器.目録.登録[x].外部読取
                   for s in 計画を復元(新['実行計画'])[0].工程 for x in s.能力候補):
                raise ValueError('外部読取を含む計画の再実行はこの回復契約の対象外')
            新['回復理由'] = asdict(方針)
            return HDS作用結果(HDS作用状態.成立,
                成果=((f'運用計画:{版 + 1}', 新),), 理由=(方針.理由,))
        except (ValueError, TypeError, KeyError, PermissionError) as exc:
            return 診断結果('回復保留：' + str(exc))


def 回答束を構成(状態, 目録):
    版, 案 = 現在案(状態)
    成果 = dict(状態.成果)
    入力 = 成果[入力名]
    目録.契約を検査()
    if 案['目録印'] != 目録.契約印:
        raise ValueError('計画と現行能力の契約不一致')
    束 = {'種別': 案['種別'], '原文': 入力['原文'], '入力印': 署名(入力),
          '計画印': 署名(案), '版': 版, '意味': 案.get('意味'),
          '出力': {}, '内容成果': [], '依存資料': 案.get('依存資料', {})}
    if 案['種別'] in ('登録', '更新'):
        値 = 案.get('資料成果') or 資料を正規化({案['資料名']: 案['本文']})[案['資料名']]
        全資料 = {**入力['資料'], 案['資料名']: 値}
        資料を正規化({k: 成果を復元(v) for k, v in 全資料.items()})
        束.update(資料変更={案['資料名']: 値}, 本文=f'資料「{案["資料名"]}」を{案["種別"]}しました。')
    elif 案['種別'] in ('会話', '初期化'):
        束['本文'] = 案['本文']
    elif 案['種別'] == '処理':
        計画, 資料 = 計画を復元(案['実行計画'])
        計画を検査(計画, 資料, 目録.登録, 外部許可=案['外部許可'])
        for 項 in 計画.工程:
            記録 = 成果[工程鍵(版, 項.識別子)]
            登録 = 目録.登録[記録['能力']]
            if 記録['能力'] not in 項.能力候補 or 記録['能力版'] != 登録.モジュール.版:
                raise ValueError('実成果と計画・能力版が不一致')
            if 記録['計画印'] != 署名(案['実行計画']):
                raise ValueError('別計画の中間成果')
            文脈, 参照 = 工程文脈(状態, 版, 案, 項)
            印 = 署名((文脈.入力文, 文脈.セッションID, 文脈.直前応答, 文脈.補助,
                        tuple(r.識別子 for r in 参照)))
            if 印 != 記録['入力印']:
                raise ValueError('工程入力と実行成果の対応不一致')
            結果 = 成果を復元(記録['成果'])
            if not 結果.成立:
                raise ValueError('不成立の中間成果')
            if 結果.データ.get('版') == 会話回答版 and not 回答記録整合(結果):
                raise ValueError('回答内容と実成果の再構成不一致')
        束['出力'] = {k: 成果[工程鍵(版, k)]['成果'] for k in 計画.出力工程}
        束['本文'] = '\n\n'.join(成果を復元(v).本文 for v in 束['出力'].values())
        if 案.get('再表現元'):
            束['内容成果'] = deepcopy(案['再表現元']['内容成果'])
        else:
            束['内容成果'] = [(k, 成果[工程鍵(版, k)]['成果']) for k in 案['内容出力']]
        if len(束['出力']) == 1:
            束['回答成果'] = next(iter(束['出力'].values()))
    else:
        raise ValueError('未定義の回答種別')
    if 案.get('資料要求'):
        束['資料要求'] = deepcopy(案['資料要求'])
    if not 束['本文'] or len(束['本文']) > 100000 or len(_符号化(束)) > 4_000_000:
        raise ValueError('最終回答の欠落又は容量上限')
    return 束


class 回答確定作用:
    作用ID = 'HDS運用/回答構成照合'

    def __init__(self, 目録):
        self.目録 = 目録

    def 機会(self, 状態):
        現在 = 現在案(状態)
        if 現在 is None or 回答名 in dict(状態.成果):
            return None
        版, 案 = 現在
        読取 = [入力名, f'運用計画:{版}']
        if 案['種別'] == '処理':
            計画, _ = 計画を復元(案['実行計画'])
            読取.extend(工程鍵(版, x.識別子) for x in 計画.工程)
        return 機会を作る(self.作用ID, 状態, 読取, 版, 完了=True, 優先度=2.0)

    def 実行(self, 状態):
        束 = 回答束を構成(状態, self.目録)
        return HDS作用結果(HDS作用状態.成立, 追加状態=frozenset({完了状態}),
            解消残差=frozenset({未完残差}), 成果=((回答名, 束),),
            理由=('依頼と全工程成果・能力契約・回答内容の対応を照合',))


def 最終回答を検査(状態, 目録):
    try:
        束 = dict(状態.成果)[回答名]
        return 署名(束) == 署名(回答束を構成(状態, 目録))
    except (ValueError, TypeError, KeyError):
        return False


class 停止対応作用:
    """作用境界で停止する適合器。実行順は引き続き既存HDS通常循環が決める。"""
    def __init__(self, 作用, 停止確認):
        self.作用, self.停止確認 = 作用, 停止確認
        self.作用ID = 作用.作用ID

    def 機会(self, 状態):
        return self.作用.機会(状態)

    def 実行(self, 状態):
        停止 = self.停止確認()
        if type(停止) is not bool:
            raise TypeError('停止確認はboolを返す必要がある')
        if 停止:
            return 診断結果('利用者による停止要求。実行済みの外部作用は取り消していない')
        return self.作用.実行(状態)
