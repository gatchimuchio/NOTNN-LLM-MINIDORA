"""比較・記載照会と確認／訂正の意味入口。目的と能力名を分離する。

対象・属性・単位・条件・時点を組み合わせる有限の日本語文法。
任意の日本語理解ではない。全文消費できない条件を捨てない。
"""
from __future__ import annotations
from dataclasses import dataclass, replace
from datetime import date
import re
from .hds_ir import HDSIR
from .HDS目的射影 import _HDS照合
from .証拠統合 import 証拠照合要求

会話要求版 = 'MINIDORA-会話要求-v0.1'
# 語彙は会話行為・成果に結び付ける。能力名や実行工程を含めない。
_述語 = {'比較して': ('依頼', '比較'), '比較してください': ('依頼', '比較'),
          '比べて': ('依頼', '比較'), '比べてください': ('依頼', '比較'),
          'どちらが大きい': ('質問', '比較'), 'どちらが小さい': ('質問', '比較'),
          'どちらが高い': ('質問', '比較'), 'どちらが低い': ('質問', '比較'),
          '調べて': ('依頼', '照会'), '調べてください': ('依頼', '照会'),
          '教えて': ('依頼', '照会'), '教えてください': ('依頼', '照会')}
_引用 = re.compile(r'「([^「」\r\n]{1,80})」')
_補充 = {'単位': re.compile(r'単位は([A-Za-z%個人円]+)(?:です)?\Z'),
         '時点': re.compile(r'時点は([0-9]{4}-[0-9]{2}-[0-9]{2})(?:です)?\Z'),
         '条件': re.compile(r'条件は「([^「」\r\n]{1,80})」(?:です)?\Z')}

@dataclass(frozen=True, slots=True)
class 会話要求:
    種別: str
    対象: tuple[str, ...]
    属性: str
    単位: str | None = None
    条件: str | None = None
    時点: str | None = None

    def 検証(self, *, 不足許容=False):
        if self.種別 not in ('比較', '照会') or type(self.対象) is not tuple:
            raise ValueError('未対応の会話目的')
        if len(self.対象) != (2 if self.種別 == '比較' else 1) or len(set(self.対象)) != len(self.対象):
            raise ValueError('対象数・重複が不正')
        if self.単位 is None and not 不足許容:
            raise ValueError('単位が未指定')
        for target in self.対象:
            証拠照合要求(target, self.属性, 'V' if self.単位 is None else self.単位, self.条件, self.時点).検証()

    def 補充(self, 項目: str, 値: str):
        if 項目 not in ('単位', '条件', '時点'):
            raise ValueError('補充できない項目')
        result = replace(self, **{項目: 値})
        result.検証(不足許容=True)
        return result

@dataclass(frozen=True, slots=True)
class 会話解釈:
    行為: str
    要求: 会話要求 | None = None
    項目: str = ''
    値: str = ''
    理由: str = ''
    既存候補: bool = False


def 会話を解釈(ir: HDSIR) -> 会話解釈:
    """実HDSとの不一致・未解釈は結果に残す。対応外を既存入口へ盲目的に通さない。"""
    try:
        if type(ir) is not HDSIR or type(ir.原文) is not str or not 0 < len(ir.原文) <= 8192:
            raise ValueError('実HDSと有限の原文が必要')
        text = ir.原文.strip()
        if text.endswith(('。', '？', '?')):
            text = text[:-1].rstrip()
        if text in ('取り消して', '取り消し', 'キャンセル', '続けて', '再開して', 'もう一度'):
            _HDS照合(ir, (), (), ())
            return 会話解釈('取消' if text in ('取り消して', '取り消し', 'キャンセル') else '再開')
        correction = text.startswith(('訂正：', '訂正:'))
        if correction: text = text[3:].strip()
        for key, pattern in _補充.items():
            match = pattern.fullmatch(text)
            if match:
                _HDS照合(ir, tuple(x.span() for x in _引用.finditer(ir.原文)), (), ())
                if key == '時点': date.fromisoformat(match[1])
                return 会話解釈('訂正' if correction else '補充', 項目=key, 値=match[1])
        if correction:
            return 会話解釈('保留', 理由='訂正できる項目は単位・条件・時点です')
        scope = {}
        while True:
            moment = re.match(r'([0-9]{4}-[0-9]{2}-[0-9]{2})時点[、,]\s*', text)
            condition = re.match(r'条件「([^「」\r\n]{1,80})」で[、,]\s*', text)
            match, key = (moment, '時点') if moment else (condition, '条件')
            if not match: break
            if key in scope: raise ValueError('適用範囲の重複指定')
            scope[key], text = match[1], text[match.end():]
        endings = [x for x in _述語 if text.endswith(x)]
        if not endings:
            return 会話解釈('未対応', 既存候補=not scope)
        ending = max(endings, key=len)
        act, kind = _述語[ending]
        head = text[:-len(ending)].strip()
        targets, first = [], _引用.match(head)
        if first:
            targets.append(first[1]); head = head[first.end():]
            if head.startswith('と'):
                other = _引用.match(head, 1)
                if not other: raise ValueError('比較対象の引用が不完全')
                targets.append(other[1]); head = head[other.end():]
        if not targets or not head.startswith('の'):
            raise ValueError('「対象」の属性を明示してください')
        match = re.fullmatch(r'([^\s「」、。！？]{1,80}?)(?:を|は)(?:([A-Za-z%個人円]+)で)?', head[1:])
        if not match: raise ValueError('属性・単位又は条件に未解釈部分があります')
        request = 会話要求(kind, tuple(targets), match[1], match[2], **scope)
        request.検証(不足許容=True)
        _HDS照合(ir, tuple(x.span() for x in _引用.finditer(ir.原文)), (), ())
        return 会話解釈(act, request)
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError) as exc:
        return 会話解釈('保留', 理由=str(exc))
