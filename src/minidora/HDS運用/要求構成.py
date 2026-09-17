"""依頼から必要な成果を構成するHDS下位作用。実行・採否は行わない。

既存の有限日本語解釈・意味計画を再利用する。未知条件を削って受理しない。
原文、構文化結果、意味目的、計画、提供資料の由来を別々に保持する。
"""
from __future__ import annotations
from copy import deepcopy
from dataclasses import asdict, replace
import re
import json

from ..会話解釈 import 会話を解釈, HDS会話を照合
from ..会話意味 import 会話要求, 比較対象, 意味目的
from ..HDS構文化器 import 公開HDSコンパイラ
from ..HDS目的射影 import HDSから目的要求, _HDS照合
from ..能力合成 import 合成計画, 合成工程, 素材参照
from ..製品版.型 import 能力結果
from ..命題解釈 import 命題を読む
from ..命題会話解釈 import HDS命題を照合
from .契約 import 内容署名 as 署名
from .契約 import 成果を復元, 計画を保存, 計画を検査, 名前を検査


def 会話要求を復元(値):
    if type(値) is not dict or set(値) != set(会話要求.__dataclass_fields__):
        raise ValueError('保存された会話要求の型不正')
    値 = deepcopy(値)
    値['対象'] = tuple(比較対象(x['資料'], tuple(tuple(y) for y in x['行条件'])) for x in 値['対象'])
    値['対応'] = tuple(tuple(x) for x in 値['対応'])
    return 会話要求(**値).固定複製()


def _形式(値):
    指定 = 値.データ.get('形式')
    if 指定 in ('JSON', 'CSV'):
        return 指定
    本文 = 値.本文.lstrip()
    if 本文.startswith(('{', '[')):
        return 'JSON'
    if ',' in 本文.split('\n', 1)[0]:
        return 'CSV'
    raise ValueError('比較資料の形式が未確定')


def _改訂(要求, 前回):
    if 前回 is None:
        raise ValueError('訂正・確認返答の対象がない')
    元 = 会話要求を復元(前回)
    if 元.行為 not in ('比較', '集合', '取得'):
        raise ValueError('この目的のスロット訂正は未対応')
    欄, 値 = 要求.補助['欄'], 要求.補助['値']
    変更 = {}
    if 欄 in ('単位', '属性'):
        変更[欄] = 値
    elif 欄 in ('年', '左の年', '右の年') and 元.行為 in ('比較', '集合'):
        if not re.fullmatch(r'[0-9]{4}', 値):
            raise ValueError('年は4桁が必要')
        対象 = list(元.対象)
        番号 = range(len(対象)) if 欄 == '年' else (0 if 欄 == '左の年' else 1,)
        for i in 番号:
            if i >= len(対象):
                raise ValueError('改訂する対象役割がない')
            対象[i] = replace(対象[i], 行条件=tuple({**dict(対象[i].行条件), '年': 値}.items()))
        変更 = {'対象': tuple(対象), '時点差': 欄 != '年'}
    else:
        raise ValueError('対象に適用できない改訂')
    return replace(元, 原文=要求.原文,
        補助={**元.補助, '改訂元': 元.補助.get('改訂元', 元.原文)},
        対応=(('目的の明示改訂', 0, len(要求.原文)),), **変更).固定複製()


class 要求不足(ValueError):
    def __init__(self, 理由, 要求):
        super().__init__(理由)
        self.要求 = 要求


class 運用要求構成器:
    def __init__(self, 目録, *, 構文化器=None):
        self.目録 = 目録
        # 局所射影が受理する既存構文化契約。高度な構文化器は明示的に差し替え可能。
        self.構文化器 = 構文化器 if 構文化器 is not None else 公開HDSコンパイラ()

    def 構成する(self, 入力: dict) -> dict:
        原文 = 入力['原文']
        self.目録.契約を検査()
        if type(原文) is not str or not 原文.strip() or len(原文) > 8192:
            raise ValueError('依頼は1〜8192文字が必要')
        資料 = {k: 成果を復元(v) for k, v in 入力['資料'].items()}
        前回 = 入力.get('前回') or {}
        前回有効 = bool(前回) and all(k in 入力['資料'] and 署名(入力['資料'][k]) == v
                                         for k, v in 前回.get('依存資料', {}).items())
        過去成果 = tuple((k, 成果を復元(v)) for k, v in 前回.get('内容成果', ())) if 前回有効 else ()
        ir = self.構文化器.コンパイル(原文)
        if ir.原文 != 原文:
            raise ValueError('構文化の原文不一致')
        基礎 = {'原文': 原文, '構文化': json.loads(json.dumps(asdict(ir), ensure_ascii=False, allow_nan=False)), '目録印': self.目録.契約印}
        if 入力.get('明示計画') is not None:
            from .契約 import 計画を復元
            計画, 初期資料 = 計画を復元(入力['明示計画'])
            return self._計画案(基礎, 計画, 初期資料, None, tuple(資料), 入力, 計画.出力工程)
        if 入力.get('意味目的') is not None:
            p = 入力['意味目的']
            if type(p) is not dict or set(p) != {'種別', '引数'}:
                raise ValueError('意味目的の形式不正')
            return self._役割案(基礎, 意味目的(**p), 資料, None, 入力)
        科学要求 = re.fullmatch(r'資料「([^「」]+)」の科学候補を検討して[。]?', 原文)
        if 科学要求:
            return self._役割案(基礎, 意味目的('科学候補報告', {'資料': 科学要求[1]}), 資料, None, 入力)
        from .資料要求 import 資料要求を構成
        追加案 = 資料要求を構成(self, 入力, 基礎)
        if 追加案 is not None:
            return 追加案
        要求 = 会話を解釈(原文, tuple(資料))
        if 原文 in ('前回の依頼を再実行して', 'もう一度計算して'):
            if not 入力.get('最後要求'):
                raise ValueError('再実行する依頼がない')
            要求 = 会話要求を復元(入力['最後要求'])
            元IR = self.構文化器.コンパイル(要求.原文)
            基礎['再実行元'] = 要求.原文
            ir = 元IR
        if 要求.行為 in ('登録', '更新'):
            名 = 名前を検査(要求.対象[0].資料)
            if 要求.行為 == '登録' and 名 in 資料:
                raise ValueError('同名資料が存在。更新を明示する')
            if 要求.行為 == '更新' and 名 not in 資料:
                raise ValueError('更新対象の資料がない')
            return {**基礎, '種別': 要求.行為, '資料名': 名, '本文': 要求.補助['本文'],
                    '意味': asdict(要求)}
        if 要求.行為 in ('初期化', '会話'):
            本文 = '会話と資料を初期化しました。'
            if 要求.行為 == '会話':
                発話 = 要求.補助['発話']
                本文 = {'こんにちは': 'こんにちは。', 'こんばんは': 'こんばんは。',
                        'ありがとう': 'どういたしまして。', '外部禁止': 'この発話では外部取得しません。'}.get(発話)
                if 本文 is None:
                    本文 = 'HDSから呼べる登録能力：' + '、'.join(self.目録.登録) + '。自由文での対応範囲は要求解釈契約に従います。'
            return {**基礎, '種別': 要求.行為, '本文': 本文, '意味': asdict(要求)}
        if 要求.行為 in ('訂正', '確認返答'):
            HDS会話を照合(ir, 要求, 文脈解消=bool(入力.get('保留要求') or 入力.get('最後要求')))
            要求 = _改訂(要求, 入力.get('保留要求') or 入力.get('最後要求'))
        if 要求.行為 == '再表現':
            if not 前回有効 or not 前回.get('回答成果'):
                raise ValueError('再表現できる有効な前回成果がない。元の依頼を再実行する')
            HDS会話を照合(ir, 要求, 文脈解消=True)
            値 = 成果を復元(前回['回答成果'])
            初期 = {'元回答': 値, '指示': 能力結果(True, 原文),
                    '設定': 能力結果(True, '', データ={'詳細': 要求.詳細, **要求.補助})}
            計画 = 合成計画((合成工程('再表現', ('会話再表現',), '指示', (素材参照('入力', '元回答'),), '設定'),), ('再表現',))
            return self._計画案(基礎, 計画, 初期, 要求, tuple(前回.get('依存資料', {})), 入力, (), 前回=前回)
        if 要求.行為 == '既存目的':
            射影文 = 要求.補助['射影文']
            文脈参照 = bool(re.search(r'それ|その結果', 射影文))
            if 文脈参照 and 前回 and not 前回有効:
                raise ValueError('前回成果の依存資料が更新されたため照応を保留')
            目的IR = ir if 射影文 == ir.原文 else self.構文化器.コンパイル(射影文)
            射影 = HDSから目的要求(目的IR, 資料, 前回成果=過去成果)
            if not 射影.成立:
                raise ValueError(射影.理由)
            if 射影文 != ir.原文:
                引用 = tuple(m.span() for m in re.finditer(r'「[^「」]*」', ir.原文))
                参照 = tuple(m.span() for m in re.finditer(r'それ|その結果', ir.原文))
                _HDS照合(ir, 引用, 参照, tuple((a, b) for a, b in 引用 if '=' in ir.原文[a:b]))
            計画結果 = self.目録.目的計画.計画する(射影.要求)
            if not 計画結果.成立:
                raise ValueError(計画結果.理由)
            内容出力 = 計画結果.計画.出力工程
            工程 = list(計画結果.計画.工程)
            初期 = dict(計画結果.資料)
            初期['運用:回答指示'] = 能力結果(True, '依頼された成果を回答へ構成する')
            初期['運用:回答設定'] = 能力結果(True, '', データ={'詳細': 要求.詳細})
            工程.append(合成工程('運用:回答', ('会話回答構成',), '運用:回答指示',
                tuple(素材参照('工程', x) for x in 内容出力), '運用:回答設定'))
            名順 = tuple(資料)
            使用 = [名順[int(k.split(':')[1])] for k in 射影.要求.素材 if k.startswith('素材:')]
            if 文脈参照:
                使用.extend(前回.get('依存資料', {}))
            基礎.update({'射影文': 射影文, '要求被覆': [asdict(x) for x in 計画結果.要求被覆]})
            return self._計画案(基礎, 合成計画(tuple(工程), ('運用:回答',)), 初期,
                                   要求, tuple(dict.fromkeys(使用)), 入力, 内容出力)
        if 要求.行為 in ('命題照合', '命題取得'):
            HDS命題を照合(ir, 要求)
            候補 = 命題を読む(要求.補助['問い'])
            番号 = 要求.補助['候補']
            if 番号 == 0 and len(候補) != 1:
                raise ValueError('命題解釈が一意に確定しない')
            番号 = 番号 or 1
            if not 1 <= 番号 <= len(候補):
                raise ValueError('命題候補の範囲外')
            if 要求.行為 == '命題照合':
                目的 = 意味目的('命題回答', {'資料': [x.資料 for x in 要求.対象],
                    '問い': 要求.補助['問い'], '候補': 番号, '詳細': 要求.詳細,
                    '形式': 要求.補助['形式'], '手順': 要求.補助['手順']})
            else:
                目的 = 意味目的('取得命題回答', {k: 要求.補助[k] for k in ('問い', '取得要求', '形式', '手順')} |
                              {'候補': 番号, '詳細': 要求.詳細})
        elif 要求.行為 in ('比較', '集合'):
            if not 要求.単位:
                raise 要求不足('比較する単位が必要です。「単位は円です」のように指定してください。', 要求)
            if '改訂元' not in 要求.補助:
                HDS会話を照合(ir, 要求)
            対象 = []
            取得 = 要求.補助.get('供給') == '取得'
            for 項 in 要求.対象:
                if 取得:
                    対象.append({'主題': 項.資料, '属性': 要求.属性, '単位': 要求.単位})
                else:
                    if 項.資料 not in 資料:
                        raise ValueError('資料がない:' + 項.資料)
                    対象.append({'資料': 項.資料, '形式': _形式(資料[項.資料]),
                                 '属性': 要求.属性, '単位': 要求.単位, '行条件': dict(項.行条件)})
            if 要求.行為 == '比較':
                if len(対象) != 2:
                    raise ValueError('比較対象は二役割が必要')
                目的 = 意味目的('比較回答', {'左': 対象[0], '右': 対象[1], '時点差': 要求.時点差, '詳細': 要求.詳細})
            else:
                補助 = 要求.補助
                目的 = 意味目的('集合回答', {'対象': 対象, '供給': 補助.get('供給', '資料'),
                    '操作': list(補助['操作']), '時点差': 要求.時点差, '詳細': 要求.詳細,
                    '形式': 補助['形式'], '手順': 補助['手順'], '選別': 補助['選別'], '除外資料': list(補助['除外資料'])})
        elif 要求.行為 == '取得':
            if '改訂元' not in 要求.補助:
                HDS会話を照合(ir, 要求)
            目的 = 意味目的('取得回答', {'主題': 要求.補助['主題'], '属性': 要求.属性,
                                       '単位': 要求.単位, '詳細': 要求.詳細})
        else:
            raise ValueError('この会話行為はHDS運用の自然文入口へ未接続:' + 要求.行為)
        return self._役割案(基礎, 目的, 資料, 要求, 入力)

    def _役割案(self, 基礎, 目的, 資料, 要求, 入力, *, 禁止=()):
        許可 = 入力['外部許可'] and not (要求 and 要求.外部禁止)
        計画 = self.目録.役割計画.計画する(目的, 資料, 禁止=禁止, 外部許可=bool(許可))
        使用 = tuple(x.素材 for x in 計画.要求被覆 if x.解決 == '素材')
        # 内容成果は回答工程の直接入力。次turnの照応は表示本文でなく元成果へ戻す。
        出力工程 = {x.識別子: x for x in 計画.計画.工程}
        内容 = tuple(dict.fromkeys(r.識別子 for k in 計画.計画.出力工程
                    for r in 出力工程[k].入力 if r.領域 == '工程'))
        案 = self._計画案(基礎, 計画.計画, 計画.資料, 要求, 使用, 入力, 内容)
        案['役割目的'] = asdict(目的)
        案['工程作用'] = 計画.工程作用
        案['入力役割'] = [(k, [(名, asdict(r)) for 名, r in 組]) for k, 組 in 計画.入力役割]
        案['要求被覆'] = [asdict(x) for x in 計画.要求被覆]
        案['禁止'] = 禁止
        return 案

    def _計画案(self, 基礎, 計画, 資料, 要求, 使用, 入力, 内容出力, *, 前回=None):
        許可 = bool(入力['外部許可'] and not (要求 and 要求.外部禁止))
        計画を検査(計画, 資料, self.目録.登録, 外部許可=許可)
        案 = {**基礎, '種別': '処理', '実行計画': 計画を保存(計画, 資料),
              '意味': asdict(要求) if 要求 else None,
              '依存資料': {k: 署名(入力['資料'][k]) for k in 使用},
              '内容出力': tuple(内容出力), '外部許可': 許可}
        if 前回 is not None:
            案['再表現元'] = deepcopy(前回)
        return 案
