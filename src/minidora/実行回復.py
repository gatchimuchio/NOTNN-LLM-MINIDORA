"""実行失敗の分類と開発時の回復契約。監督器に特定能力の名前を埋め込まない。

分類は観測の整理であり、回復可能性の推定ではない。明示契約のない失敗は停止する。
資料や利用者の本文から回復権限を追加しない。
"""
from __future__ import annotations
from dataclasses import dataclass

実行回復版 = 'MINIDORA-実行回復-v0.1'

_分類 = {
    '構造未到達': '情報不足', '取得不足': '情報不足', '情報不足': '情報不足',
    '入力不足': '入力不足', '意味未確定': '意味未確定', '未解釈注記': '意味未確定',
    '前提矛盾': '前提矛盾', '能力非対応': '能力非対応', '能力不成立': '能力非対応',
    '検証失敗': '検証失敗', '入力不正': '入力不正',
    '実行環境': '実行環境', '環境失敗': '実行環境', '停止': '停止', '権限不足': '権限不足',
}
# これらを別経路へ逃がすと、要求・証拠・権限の意味が変わり得る。
_自動回復不可 = frozenset({'入力不足', '意味未確定', '前提矛盾', '入力不正', '停止', '権限不足'})


def 失敗を分類(種別: str) -> str:
    return _分類.get(種別, '未分類')


@dataclass(frozen=True, slots=True)
class 回復規則:
    """失敗工程自身又は名付けられた直接入力役割の経路を再開放する。"""
    失敗種別: str
    対象: str = '自己'
    入力役割: str = ''
    対象作用: tuple[str, ...] = ()

    def 検証(self):
        if (type(self.失敗種別) is not str or self.失敗種別 not in _分類
                or 失敗を分類(self.失敗種別) in _自動回復不可):
            raise ValueError('自動回復を許可できない失敗種別')
        if self.対象 not in ('自己', '入力役割'):
            raise ValueError('回復対象は自己又は直接入力役割')
        if type(self.入力役割) is not str or type(self.対象作用) is not tuple:
            raise ValueError('回復役割・作用の型不正')
        if self.対象 == '自己':
            if self.入力役割 or self.対象作用:
                raise ValueError('自己回復に別役割を指定しない')
        elif (not self.入力役割 or len(self.入力役割) > 128 or not self.対象作用
                or len(self.対象作用) > 16 or len(set(self.対象作用)) != len(self.対象作用)
                or any(type(x) is not str or not x for x in self.対象作用)):
            raise ValueError('入力回復には役割名と対象作用の許可列が必要')
        return self
