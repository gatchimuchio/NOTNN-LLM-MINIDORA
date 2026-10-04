"""Compilerが明示した意味文脈だけを鍵にする安全な構文化再利用。"""
from __future__ import annotations
from copy import deepcopy
from time import perf_counter_ns
from .値 import 署名


class 構文化再利用:
    def __init__(self, コンパイラ):
        self.コンパイラ = コンパイラ
        self._保持 = {}
        # 旧内部名との互換。正本は _保持。
        self._記憶 = self._保持
        self.実行数 = 0
        self.再利用数 = 0
        self.時間ns = 0

    def _文脈(self):
        """明示宣言だけをキャッシュ契約にする。推測した実装IDでは再利用しない。"""
        if not hasattr(self.コンパイラ, "構文化文脈署名"):
            return None
        値 = getattr(self.コンパイラ, "構文化文脈署名")
        if callable(値):
            値 = 値()
        return 値

    def __call__(self, 本文):
        関数 = getattr(self.コンパイラ, "コンパイル", None)
        if not callable(関数):
            raise TypeError("コンパイラにコンパイル関数が必要")
        前文脈 = self._文脈()
        鍵 = 署名((前文脈, 本文)) if 前文脈 is not None else None
        if 鍵 is not None and 鍵 in self._保持:
            self.再利用数 += 1
            return deepcopy(self._保持[鍵])
        開始 = perf_counter_ns()
        try:
            値 = 関数(本文)
        finally:
            self.時間ns += perf_counter_ns() - 開始
            self.実行数 += 1
        後文脈 = self._文脈()
        # 実行中に意味文脈が変わった結果は、どちらの版にも属さないため保持しない。
        if 鍵 is not None and 前文脈 == 後文脈:
            self._保持[鍵] = deepcopy(値)
            return deepcopy(値)
        return 値
