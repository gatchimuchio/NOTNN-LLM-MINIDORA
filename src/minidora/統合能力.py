"""既存能力の共通登録と、純粋な処理結果だけを再利用する統合側の調整。"""
from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
from threading import RLock
import re

from .能力合成 import 登録能力, _文脈辞書, _結果辞書, _符号化
from .能力合成_局所接続 import 局所能力群, 文脈変換接続
from .製品版.型 import 能力結果

統合能力版 = "MINIDORA-統合能力-v0.1"


class 完全文脈変換(文脈変換接続):
    """旧入口を変えず、統合経路の箇条書きだけを全項目保持へ変更する。"""
    版 = 統合能力版 + "/全項目変換"

    def 実行(self, 文脈):
        settings = (文脈.補助 or {}).get("合成設定", {})
        if settings == {"形式": "箇条書き"}:
            items = [s.strip() for s in re.split(r"[。\n]+", 文脈.直前応答) if s.strip()]
            if not items:
                return 能力結果(False, "", 保留理由="変換対象がない")
            body = "\n".join("- " + item for item in items)
            if len(body) > 100000:
                return 能力結果(False, "", 保留理由="全項目変換の上限。切断せず保留")
            return 能力結果(True, body, 根拠=("全項目の箇条書き化",),
                            データ={"形式": "箇条書き", "項目数": len(items), "省略数": 0})
        return super().実行(文脈)


class 純粋結果庫:
    """セッション内LRU。上限は保存するJSONバイト数で、OSメモリ上限ではない。"""
    def __init__(self, *, 有効=True, 最大件数=64, 最大バイト数=4000000):
        if type(有効) is not bool:
            raise ValueError("再利用指定はbool")
        for value, maximum in ((最大件数, 256), (最大バイト数, 16000000)):
            if type(value) is not int or not 1 <= value <= maximum:
                raise ValueError("再利用上限不正")
        self.有効 = 有効
        self._限度 = (最大件数, 最大バイト数)
        self._値 = OrderedDict()
        self._サイズ = 0
        self._統計 = {}
        self._ロック = RLock()

    def 計数(self, 名前, 項目):
        with self._ロック:
            row = self._統計.setdefault(名前, {"要求": 0, "再利用": 0, "原実行": 0})
            row[項目] += 1

    def 取得(self, key):
        with self._ロック:
            if not self.有効 or key not in self._値:
                return None
            value, size = self._値.pop(key)
            self._値[key] = (value, size)
            return deepcopy(value)

    def 保存(self, key, value):
        raw = _符号化(_結果辞書(value))
        size = len(raw) + len(key.encode())
        with self._ロック:
            if not self.有効 or not value.成立 or size > self._限度[1]:
                return
            if key in self._値:
                self._サイズ -= self._値.pop(key)[1]
            while self._値 and (len(self._値) >= self._限度[0] or self._サイズ+size > self._限度[1]):
                self._サイズ -= self._値.popitem(last=False)[1][1]
            self._値[key] = (deepcopy(value), size)
            self._サイズ += size

    def 統計(self):
        with self._ロック:
            return {"能力別": deepcopy(self._統計), "件数": len(self._値), "保存バイト数": self._サイズ}

    def 消去(self):
        with self._ロック:
            self._値.clear()
            self._サイズ = 0
            self._統計.clear()


class _再利用能力:
    def __init__(self, module, cache):
        self._本体, self._庫 = module, cache
        self.名前, self.版 = module.名前, module.版
        self.優先度 = module.優先度

    def _版確認(self):
        if (self._本体.名前, self._本体.版) != (self.名前, self.版):
            raise ValueError("登録後の能力変更")

    def 判定(self, context):
        self._版確認()
        return self._本体.判定(context)

    def 実行(self, context):
        self._版確認()
        # 全入力・文脈・設定・参照・版を含める。本文だけのキーで取り違えない。
        key = sha256(_符号化({"名前": self.名前, "版": self.版, "入力": _文脈辞書(context)})).hexdigest()
        self._庫.計数(self.名前, "要求")
        result = self._庫.取得(key)
        if result is not None:
            self._庫.計数(self.名前, "再利用")
            return result
        self._庫.計数(self.名前, "原実行")
        result = self._本体.実行(deepcopy(context))
        self._版確認()
        _結果辞書(result)
        self._庫.保存(key, result)
        return result


def 統合能力群(庫, 再利用庫, *, 外部読取許可=False, 取得器=None, 閲覧器=None):
    """全15領域の制御器と部品を接続する。領域数とModule数は別。"""
    from .証拠統合接続 import 証拠統合Module, 記載値採用Module
    from .応答構成接続 import 応答構成Module
    from .関係制約接続 import 関係制約Module, 数値関係化Module, 関係判定採用Module
    from .コード能力接続 import コード能力群
    from .数学能力接続 import 数学能力群
    from .多言語接続 import 多言語変換Module
    from .構造化文書接続 import 構造化文書能力群
    from .文章能力接続 import 文章能力群
    from .多段解決接続 import 解決補助能力群, 多段解決Module
    from .長文脈接続 import 長文脈選択Module
    from .知識取得接続 import 知識取得Module
    from .知識取得 import 知識取得器
    from .製品版.検索 import SearXNG検索供給器
    from .ブラウザ閲覧 import ブラウザ閲覧器
    from .ブラウザ接続 import ブラウザ閲覧Module
    if type(外部読取許可) is not bool or not isinstance(再利用庫, 純粋結果庫):
        raise ValueError("登録条件不正")
    local = tuple(replace(r, Module=完全文脈変換()) if r.Module.名前 == "文脈変換" else r for r in 局所能力群())
    pure = (*local, *(m.登録() for m in (証拠統合Module(), 記載値採用Module(), 応答構成Module(),
            関係制約Module(), 数値関係化Module(), 関係判定採用Module())),
            *コード能力群(), *数学能力群(), 多言語変換Module().登録(),
            *構造化文書能力群(), *文章能力群(), *解決補助能力群())
    # 再利用はこの明示した純粋部品だけ。外部取得・可変文脈・探索全体は含めない。
    cached = tuple(登録能力(_再利用能力(r.Module, 再利用庫)) for r in pure)
    search = 取得器 if 取得器 is not None else 知識取得器(SearXNG検索供給器())
    browser = 閲覧器 if 閲覧器 is not None else ブラウザ閲覧器()
    return (*cached, 多段解決Module(cached, 純粋作用確認=True).登録(), 長文脈選択Module(庫).登録(),
            知識取得Module(search, 外部読取許可=外部読取許可).登録(),
            ブラウザ閲覧Module(browser, 外部読取許可=外部読取許可).登録())
