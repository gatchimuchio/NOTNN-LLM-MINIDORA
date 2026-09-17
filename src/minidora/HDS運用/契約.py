"""HDS通常運用の資料・計画・成果境界。実行コードは保存形式へ入れない。"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from graphlib import TopologicalSorter, CycleError
import json
from hashlib import sha256
from typing import Mapping

from ..採否 import 実行状態
from ..能力合成 import 合成計画, 合成工程, 素材参照, _結果辞書, _符号化
from ..能力結果復元 import 能力結果を復元
from ..製品版.型 import 能力結果


運用版 = 'HDS-MINIDORA-通常運用-v1'
最大資料バイト = 2_000_000


def 内容署名(値):
    """輸送上同じ配列はlist/tupleで区別しない。真正性の認証ではない。"""
    return sha256(_符号化(値)).hexdigest()


def 名前を検査(値: object) -> str:
    if type(値) is not str or not 1 <= len(値) <= 128 or any(ord(c) < 32 for c in 値):
        raise ValueError('名前は制御文字を含まない1〜128文字が必要')
    return 値


def 成果を保存(値: 能力結果) -> dict:
    if type(値) is not 能力結果:
        raise TypeError('能力結果型が必要')
    if 値.成立 and (値.状態 != 実行状態.合格 or 値.保留理由):
        raise ValueError('成功と採否状態・保留理由の不一致')
    内容 = deepcopy(_結果辞書(値))
    if len(_符号化(内容)) > 最大資料バイト:
        raise ValueError('能力成果の容量上限')
    return {'結果': 内容, '採否': 値.状態.value}


def 成果を復元(値: dict) -> 能力結果:
    if type(値) is not dict or set(値) != {'結果', '採否'}:
        raise ValueError('保存成果の項目不一致')
    from dataclasses import replace
    結果 = replace(能力結果を復元(値['結果']), 採否状態=実行状態(値['採否']))
    成果を保存(結果)
    return 結果


def 資料を正規化(資料: Mapping[str, str | 能力結果]) -> dict[str, dict]:
    if not isinstance(資料, Mapping) or len(資料) > 32:
        raise ValueError('資料は32件以下の名前付き写像が必要')
    結果 = {}
    for 名, 値 in 資料.items():
        名前を検査(名)
        if type(値) is str:
            値 = 能力結果(True, 値, 根拠=('利用者提供資料。記載の真実性は未認定',))
        elif type(値) is not 能力結果:
            raise ValueError('資料は文字列又は能力結果が必要')
        if not 値.成立:
            raise ValueError('未成立成果は提供資料として使えない')
        結果[名] = 成果を保存(値)
    if len(_符号化(結果)) > 最大資料バイト:
        raise ValueError('資料集合の容量上限')
    return 結果


def JSONを読む(本文: str, *, 上限: int = 8_000_000):
    if type(本文) is not str or len(本文.encode('utf-8')) > 上限:
        raise ValueError('JSON入力の容量・型不正')
    def 一意(組):
        値 = {}
        for 鍵, 中身 in 組:
            if 鍵 in 値:
                raise ValueError('JSON鍵の重複')
            値[鍵] = 中身
        return 値
    def 不正数(_):
        raise ValueError('非有限数')
    try:
        値 = json.loads(本文, object_pairs_hook=一意, parse_constant=不正数)
        _符号化(値)  # 指数表記から生じた非有限floatも拒否。
        return 値
    except RecursionError as exc:
        raise ValueError('JSON入れ子の上限') from exc


def 計画を保存(計画: 合成計画, 資料: Mapping[str, 能力結果]) -> dict:
    if type(計画) is not 合成計画:
        raise TypeError('合成計画型が必要')
    return {'計画': asdict(計画), '資料': {k: 成果を保存(v) for k, v in 資料.items()}}


def 計画を復元(値: dict) -> tuple[合成計画, dict[str, 能力結果]]:
    if type(値) is not dict or set(値) != {'計画', '資料'}:
        raise ValueError('計画保存の項目不一致')
    構造 = 値['計画']
    if type(構造) is not dict or set(構造) != {'工程', '出力工程'}:
        raise ValueError('計画構造の項目不一致')
    工程 = []
    for 項 in 構造['工程']:
        if type(項) is not dict or set(項) != set(合成工程.__dataclass_fields__):
            raise ValueError('工程の項目不一致')
        入力 = tuple(素材参照(**r) for r in 項['入力'])
        工程.append(合成工程(項['識別子'], tuple(項['能力候補']), 項['指示参照'], 入力, 項['設定参照']))
    return 合成計画(tuple(工程), tuple(構造['出力工程'])), {k: 成果を復元(v) for k, v in 値['資料'].items()}


def 計画を検査(計画: 合成計画, 資料: dict, 登録: dict, *, 外部許可: bool) -> None:
    """宣言の整合検査だけ。ここで実行・能力選択・最終採用はしない。"""
    if type(計画) is not 合成計画 or type(計画.工程) is not tuple or not 1 <= len(計画.工程) <= 64:
        raise ValueError('計画の型・工程数不正')
    if type(外部許可) is not bool or len(資料) > 256:
        raise ValueError('計画許可・資料数不正')
    for 名, 値 in 資料.items():
        名前を検査(名)
        成果を保存(値)
        if not 値.成立:
            raise ValueError('不成立の計画資料')
    構造 = {}
    for 項 in 計画.工程:
        if type(項) is not 合成工程:
            raise TypeError('工程型不正')
        名 = 名前を検査(項.識別子)
        if 名 in 構造:
            raise ValueError('工程ID重複')
        if type(項.能力候補) is not tuple or not 項.能力候補 or len(set(項.能力候補)) != len(項.能力候補):
            raise ValueError('能力候補の型・重複・欠落')
        for 能力名 in 項.能力候補:
            if 能力名 not in 登録:
                raise ValueError('未登録能力:' + 能力名)
            if 登録[能力名].外部読取 and not 外部許可:
                raise PermissionError('外部読取未許可:' + 能力名)
        if type(項.指示参照) is not str or 項.指示参照 not in 資料:
            raise ValueError('指示参照がない')
        for 参照 in (項.指示参照, 項.設定参照):
            if 参照 is not None and 参照 not in 資料:
                raise ValueError('指示・設定の資料欠落:' + str(参照))
        if type(項.入力) is not tuple:
            raise ValueError('入力役割はtupleが必要')
        親 = []
        for 入力 in 項.入力:
            if type(入力) is not 素材参照:
                raise ValueError('素材参照型不正')
            if 入力.領域 == '入力' and 入力.識別子 in 資料:
                continue
            if 入力.領域 == '工程':
                親.append(入力.識別子)
            else:
                raise ValueError('素材参照先不正')
        構造[名] = tuple(親)
    if any(p not in 構造 for 組 in 構造.values() for p in 組):
        raise ValueError('上流工程欠落')
    if type(計画.出力工程) is not tuple or not 計画.出力工程 or len(set(計画.出力工程)) != len(計画.出力工程):
        raise ValueError('出力工程の型・重複・欠落')
    if any(x not in 構造 for x in 計画.出力工程):
        raise ValueError('出力工程が未定義')
    try:
        tuple(TopologicalSorter(構造).static_order())
    except CycleError as exc:
        raise ValueError('計画依存循環') from exc
    必要, 待ち = set(), list(計画.出力工程)
    while 待ち:
        名 = 待ち.pop()
        if 名 not in 必要:
            必要.add(名)
            待ち.extend(構造[名])
    if 必要 != set(構造):
        raise ValueError('依頼成果へ寄与しない工程')
    if len(_符号化(計画を保存(計画, 資料))) > 最大資料バイト:
        raise ValueError('計画全体の容量上限')


@dataclass(frozen=True, slots=True)
class 運用応答:
    状態: str
    本文: str
    理由: tuple[str, ...]
    実行: object = None
    出力: tuple[tuple[str, 能力結果], ...] = ()

    @property
    def 成立(self) -> bool:
        return self.状態 == 'COMMIT'

    def 辞書化(self) -> dict:
        結果 = {'状態': self.状態, '本文': self.本文, '理由': list(self.理由),
                '出力': {k: 成果を保存(v) for k, v in self.出力}}
        if self.実行 is not None:
            結果['HDS'] = {'終端': self.実行.終端.value,
                '状態署名': self.実行.状態.状態署名,
                '作用履歴': [asdict(x) for x in self.実行.履歴],
                '計装': asdict(self.実行.計装),
                '残差': sorted(self.実行.状態.残差)}
        return 結果


def 組の位置(値, 経路=()):
    """既存能力のtuple契約を、コードを含まない型位置情報で保持する。"""
    結果 = [list(経路)] if type(値) is tuple else []
    if type(値) in (tuple, list):
        for i, 子 in enumerate(値):
            結果.extend(組の位置(子, (*経路, i)))
    elif type(値) is dict:
        for k in sorted(値):
            結果.extend(組の位置(値[k], (*経路, k)))
    return 結果


def 組を復元(値, 位置):
    """配列の組型だけを復元する。クラス名や関数名の復元は受け付けない。"""
    if type(位置) is not list or len(位置) > 100000:
        raise ValueError('型位置数の上限')
    既出 = set()
    for 経路 in 位置:
        if type(経路) is not list or len(経路) > 32 or any(type(x) not in (str, int) for x in 経路):
            raise ValueError('型位置の形式不正')
        if tuple(経路) in 既出:
            raise ValueError('型位置重複')
        既出.add(tuple(経路))
    値 = deepcopy(値)
    for 経路 in sorted(位置, key=len, reverse=True):
        親 = None
        対象 = 値
        for 鍵 in 経路:
            親 = 対象
            if type(親) is dict and type(鍵) is str and 鍵 in 親:
                対象 = 親[鍵]
            elif type(親) is list and type(鍵) is int and 0 <= 鍵 < len(親):
                対象 = 親[鍵]
            else:
                raise ValueError('型位置が資料外')
        if type(対象) is not list:
            raise ValueError('組の復元対象は配列が必要')
        if 親 is None:
            値 = tuple(対象)
        else:
            親[経路[-1]] = tuple(対象)
    if 組の位置(値) != 位置:
        raise ValueError('型位置の正準順不一致')
    return 値
