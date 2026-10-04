"""原文を残して九座標を27の操作面へ射影する。座標数は保証強度ではない。

この版の既定は9根×取得・変換・射影の27面。原入力の個別座標、条件、
由来は別に全保持する。展開は要求された局所だけに行い、全対照合しない。
この方針はMINIDORAの実装設定であり、HDSの固定次元の定義ではない。
"""
from __future__ import annotations
from dataclasses import dataclass, replace
from functools import lru_cache
from .値 import 文字, 文字列組, 不変値, 署名
from .指示関係 import HDS指示関係, HDS指示座標, 座標状態, 三組九座標, 九座標を用意

@lru_cache(maxsize=8192)
def _座標場署名を取得(値):
    return 署名(値)


操作面 = ("取得", "変換", "射影")
座標展開版 = "目的関係座標-v1"


@dataclass(frozen=True, slots=True)
class 座標面:
    ID: str
    親: str
    役割: str
    内容: object = None
    状態: 座標状態 = 座標状態.未観測
    元座標: tuple[str, ...] = ()
    利用先: tuple[str, ...] = ()
    由来: tuple[str, ...] = ()
    版: int = 0

    def __post_init__(self):
        for 名 in ("ID", "親", "役割"): 文字(getattr(self, 名), 名)
        if self.役割 not in 操作面: raise ValueError("未知の操作面")
        if not isinstance(self.状態, 座標状態): raise TypeError("座標状態が必要")
        if type(self.版) is not int or self.版 < 0: raise ValueError("版が不正")
        for 名 in ("元座標", "利用先", "由来"): 文字列組(getattr(self, 名), 名)
        不変値(self.内容)
        if self.状態 in (座標状態.確定値, 座標状態.推定値) and not self.由来:
            raise ValueError("内容の確定には由来が必要")


@dataclass(frozen=True, slots=True)
class 座標帰還:
    対象: str
    前版: int
    後版: int
    前内容署名: str
    後内容署名: str
    理由: str
    根拠: tuple[str, ...]
    影響先: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class HDS座標場:
    原指示: HDS指示関係
    面: tuple[座標面, ...]
    # (元面ID, 消費面ID, 意味)。親子関係は各面の親に別途保持する。
    関係: tuple[tuple[str, str, str], ...] = ()
    履歴: tuple[座標帰還, ...] = ()
    旧面: tuple[座標面, ...] = ()
    版: str = 座標展開版

    def __post_init__(self):
        if not isinstance(self.原指示, HDS指示関係): raise TypeError("原指示が必要")
        文字列組(tuple(x.ID for x in self.面), "操作面ID")
        既知 = set(self.原指示.座標辞書()) | {x.ID for x in self.面}
        面辞書 = {x.ID: x for x in self.面}
        for 項 in self.面:
            if 項.親 not in 既知: raise ValueError("親面が不存在")
            if not set(項.元座標) <= 既知: raise ValueError("原座標が不存在")
            訪問, 親 = {項.ID}, 項.親
            while 親 in 面辞書:
                if 親 in 訪問: raise ValueError("操作面の親が循環")
                訪問.add(親); 親 = 面辞書[親].親
        for 元, 先, 意味 in self.関係:
            if 元 not in 既知 or 先 not in 既知: raise ValueError("関係面が不存在")
            文字(意味)

    @property
    def 署名(self): return _座標場署名を取得(self)

    def __deepcopy__(self, memo): return self

    @property
    def 末端面(self):
        親集合 = {x.親 for x in self.面}
        return tuple(x for x in self.面 if x.ID not in 親集合)

    def 影響範囲(self, 起点):
        """意味上宣言された辺だけを走査する。N×Nの総当たりは行わない。"""
        起点 = tuple(起点)
        既知 = set(self.原指示.座標辞書()) | {x.ID for x in self.面}
        if not set(起点) <= 既知: raise ValueError("未知の起点")
        索引 = {}
        for 元, 先, _ in self.関係: 索引.setdefault(元, set()).add(先)
        for 項 in self.面: 索引.setdefault(項.親, set()).add(項.ID)
        訪問 = set(起点); 待ち = list(起点)
        while 待ち:
            for 先 in 索引.get(待ち.pop(), ()):
                if 先 not in 訪問: 訪問.add(先); 待ち.append(先)
        return frozenset(訪問)

    def 必要面(self, 利用先):
        """保持物を削除せず、宣言された利用先へ至る前提面を取得する。"""
        要求 = frozenset(利用先)
        必要 = {x.ID for x in self.面 if 要求 & set(x.利用先)}
        逆索引 = {}
        for 元, 先, _ in self.関係: 逆索引.setdefault(先, set()).add(元)
        待ち = list(必要)
        while 待ち:
            for 元 in 逆索引.get(待ち.pop(), ()):
                if 元 not in 必要: 必要.add(元); 待ち.append(元)
        return tuple(x for x in self.面 if x.ID in 必要)

    def 展開(self, 面ID, *, 理由, 利用先, 内容群=(), 最大追加面=None):
        """一面を三面へ展開。未知を空欄補完せず、上限到達は原場を保持して返す。"""
        文字(理由); 文字列組(tuple(利用先), "局所展開の利用先")
        if not 利用先: raise ValueError("利用先のない深掘りは禁止")
        親 = next((x for x in self.面 if x.ID == 面ID), None)
        if 親 is None: raise KeyError(面ID)
        if any(x.親 == 面ID for x in self.面): return self
        if 最大追加面 is not None and (type(最大追加面) is not int or 最大追加面 < 3):
            raise ValueError("局所展開容量不足。元の場は変更されていない")
        内容 = dict(内容群)
        if not set(内容) <= set(操作面): raise ValueError("未知の展開役割")
        子 = tuple(座標面(面ID + "/" + 役割, 面ID, 役割, 内容.get(役割),
                     座標状態.未確定 if 役割 in 内容 else 座標状態.未観測,
                     (面ID,), tuple(利用先), (理由,)) for 役割 in 操作面)
        return replace(self, 面=(*self.面, *子), 関係=(*self.関係,
            (子[0].ID, 子[1].ID, "取得内容を変換へ"), (子[1].ID, 子[2].ID, "変換内容を利用先へ")))

    def 帰還(self, 面ID, 内容, *, 状態, 根拠, 理由, 期待版):
        """内容訂正を旧版付きで反映。目的原本の変更APIではない。"""
        文字(理由); 文字列組(tuple(根拠), "帰還根拠")
        if not 根拠: raise ValueError("帰還根拠が必要")
        前 = next((x for x in self.面 if x.ID == 面ID), None)
        if 前 is None: raise KeyError(面ID)
        if 前.版 != 期待版: raise ValueError("座標版が競合")
        後 = replace(前, 内容=内容, 状態=状態, 由来=tuple(根拠), 版=前.版 + 1)
        影響 = self.影響範囲((面ID,)) - {面ID}
        記録 = 座標帰還(面ID, 前.版, 後.版, 署名(前.内容), 署名(内容), 理由, tuple(根拠), tuple(sorted(影響)))
        面群 = tuple(後 if x.ID == 面ID else replace(x, 状態=座標状態.未確定, 版=x.版 + 1)
                       if x.ID in 影響 else x for x in self.面)
        変更前 = tuple(x for x in self.面 if x.ID == 面ID or x.ID in 影響)
        return replace(self, 面=面群, 履歴=(*self.履歴, 記録), 旧面=(*self.旧面, *変更前))


def 指示を座標場へ(指示: HDS指示関係) -> HDS座標場:
    """同一の原指示から、取得元・変換関係・利用先の三つの異なる操作面を作る。"""
    根群 = 九座標を用意(指示.座標)
    if 根群 != 指示.座標: 指示 = replace(指示, 座標=根群)
    面群, 辺群 = [], []
    for 組, 名 in 三組九座標:
        根 = 組 + "/" + 名
        原 = 指示.座標辞書()[根]
        子ID = tuple(x.ID for x in 指示.座標 if x.ID == 根 or x.親 == 根)
        関係 = tuple((始, 終, 意味) for 始, 終, 意味 in 指示.関係 if 始 in 子ID or 終 in 子ID)
        利用 = tuple(dict.fromkeys(x.ノード for x in (*指示.条件, *指示.帰還先)
                                 if x.座標ID in 子ID or any(k in 子ID for k in getattr(x, "参照座標", ()))))
        内容群 = (原.内容, 関係 or None, 利用 or None)
        for 役割, 内容 in zip(操作面, 内容群):
            # 接続先がある事実と、先の条件の成立は別。変換/射影は未確定から始める。
            状態 = 原.状態 if 役割 == "取得" else 座標状態.未確定 if 内容 is not None else 座標状態.未観測
            面群.append(座標面(根 + "/" + 役割, 根, 役割, 内容, 状態, 子ID, 利用, 原.由来))
        辺群.extend(((根 + "/取得", 根 + "/変換", "入力の意味関係を操作へ"),
                     (根 + "/変換", 根 + "/射影", "変換結果を後続へ")))
    # 原指示の横断関係も、射影→取得の有向辺として残す。
    根ID = {組 + "/" + 名 for 組, 名 in 三組九座標}
    辺群.extend((始 + "/射影", 終 + "/取得", 意味) for 始, 終, 意味 in 指示.関係
                if 始 in 根ID and 終 in 根ID)
    return HDS座標場(指示, tuple(面群), tuple(dict.fromkeys(辺群)))