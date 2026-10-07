from __future__ import annotations

from collections import deque
from dataclasses import dataclass, replace

from ..コア.効果 import 期待効果
from ..選択観測学習 import HDS観測経路鍵, HDS観測経路鍵を構成


@dataclass(frozen=True, slots=True)
class _作用文脈:
    作用定義ID: str
    意味入力署名: str
    種別: str
    契約版: str


@dataclass(frozen=True, slots=True)
class HDS観測経路経験:
    鍵: HDS観測経路鍵
    成功: bool

    def __post_init__(self):
        if not isinstance(self.鍵, HDS観測経路鍵) or type(self.成功) is not bool:
            raise TypeError("観測経路経験の型不正")


@dataclass(frozen=True, slots=True)
class _経験:
    文脈: _作用文脈
    成立: bool
    変化有無: bool
    追加状態: frozenset[str]
    削除状態: frozenset[str]
    解消残差: frozenset[str]
    追加残差: frozenset[str]
    反証: bool = False


def _文脈(機会) -> _作用文脈:
    # 旧作用機会は作用定義ID/意味入力署名を持たないため、宣言済みの旧契約へ縮退する。
    作用ID = str(getattr(機会, "作用ID"))
    作用定義ID = str(getattr(機会, "作用定義ID", "") or 作用ID)
    意味入力署名 = getattr(機会, "意味入力署名", "")
    if not 意味入力署名:
        意味入力署名 = getattr(機会, "作用入力署名", "")
    if not 意味入力署名:
        from ..コア.値 import 署名
        意味入力署名 = 署名((
            作用定義ID,
            tuple(sorted(getattr(機会, "入力状態", ()))),
            tuple(getattr(機会, "読取認識", ())),
            tuple(getattr(機会, "読取成果", ())),
        ))
    return _作用文脈(
        作用定義ID,
        str(意味入力署名),
        str(getattr(機会, "種別")),
        str(getattr(機会, "契約版")),
    )


def _成立か(結果) -> bool:
    状態 = getattr(結果, "状態", None)
    return getattr(状態, "value", 状態) == "成立"


def _既に満たす(機会, 前状態) -> bool:
    if 前状態 is None:
        return False
    出力済み = 機会.出力状態 <= 前状態.成立状態
    解消済み = not bool(機会.解消対象 & 前状態.残差)
    return 出力済み and 解消済み


class HDS適応記憶:
    """作用効果の全経験を保持し、主演算は最新窓と反証後の安定効果だけを見る。"""

    __slots__ = ("_経験列", "_保管経験", "_最大経験数", "_安定索引", "_観測経路経験")

    def __init__(self, 最大経験数: int = 256) -> None:
        if type(最大経験数) is not int or not 1 <= 最大経験数 <= 4096:
            raise ValueError("最大経験数は1..4096の整数が必要")
        self._最大経験数 = 最大経験数
        self._経験列 = deque()
        self._保管経験 = []
        self._安定索引 = {}
        self._観測経路経験 = []

    @property
    def 全経験(self):
        return (*self._保管経験, *tuple(self._経験列))

    @property
    def 経験数(self) -> int:
        return len(self._保管経験) + len(self._経験列)

    @property
    def 保管経験数(self) -> int:
        return len(self._保管経験)

    @property
    def 観測経路経験数(self) -> int:
        return len(self._観測経路経験)

    @property
    def 観測経路経験(self) -> tuple[HDS観測経路経験, ...]:
        return tuple(self._観測経路経験)


    def _再索引(self) -> None:
        索引 = {}
        文脈群 = {x.文脈 for x in self.全経験}
        for 文脈 in 文脈群:
            対象 = [x for x in self.全経験 if x.文脈 == 文脈]
            最後の反証 = max((i for i, x in enumerate(対象) if x.反証), default=-1)
            有効 = tuple(x for x in 対象[最後の反証 + 1:] if x.成立 and x.変化有無)
            if 有効:
                索引[文脈] = len(有効)
        self._安定索引 = 索引

    def _追加(self, 経験: _経験) -> None:
        if not isinstance(経験, _経験):
            raise TypeError("適応経験型が不正")
        if len(self._経験列) >= self._最大経験数:
            self._保管経験.append(self._経験列.popleft())
        self._経験列.append(経験)
        self._再索引()

    @property
    def 状態署名(self) -> str:
        from ..コア.値 import 署名
        return 署名((self._最大経験数, self.全経験, tuple(self._観測経路経験)))

    def 初期化(self) -> None:
        self._経験列.clear()
        self._保管経験.clear()
        self._安定索引 = {}
        self._観測経路経験.clear()

    def スナップショット(self):
        return {
            "最大経験数": self._最大経験数,
            "経験": tuple(self._経験列),
            "保管経験": tuple(self._保管経験),
            "観測経路経験": tuple(self._観測経路経験),
        }

    def 復元(self, 記録) -> None:
        許可 = (
            {"最大経験数", "経験"},
            {"最大経験数", "経験", "保管経験"},
            {"最大経験数", "経験", "保管経験", "観測経路経験"},
        )
        if not isinstance(記録, dict) or set(記録) not in 許可:
            raise ValueError("適応記憶スナップショット不正")
        最大 = 記録["最大経験数"]; 経験 = 記録["経験"]; 保管 = 記録.get("保管経験", ())
        経路 = 記録.get("観測経路経験", ())
        if (
            type(最大) is not int or not 1 <= 最大 <= 4096
            or not isinstance(経験, tuple) or not isinstance(保管, tuple) or not isinstance(経路, tuple)
        ):
            raise ValueError("適応記憶スナップショット不正")
        if any(not isinstance(x, _経験) for x in (*保管, *経験)):
            raise TypeError("適応経験型が不正")
        if any(not isinstance(x, HDS観測経路経験) for x in 経路):
            raise TypeError("観測経路経験型が不正")
        if len(経験) > 最大:
            raise ValueError("適応記憶の最新窓が上限を超える")
        self._最大経験数 = 最大
        self._経験列 = deque(経験)
        self._保管経験 = list(保管)
        self._観測経路経験 = list(経路)
        self._再索引()

    def 観測経路を記録(self, 試行要求群, 成功要求群=()) -> None:
        試行 = {HDS観測経路鍵を構成(x) for x in tuple(試行要求群)}
        成功 = {HDS観測経路鍵を構成(x) for x in tuple(成功要求群)} & 試行
        for 鍵 in sorted(試行):
            self._観測経路経験.append(HDS観測経路経験(鍵, 鍵 in 成功))

    def 観測経路成績(self, 鍵: HDS観測経路鍵) -> tuple[int, int]:
        if not isinstance(鍵, HDS観測経路鍵):
            raise TypeError("HDS観測経路鍵型が必要")
        rows = tuple(x for x in self._観測経路経験 if x.鍵 == 鍵)
        return len(rows), sum(x.成功 for x in rows)

    def 観測要求を適応(self, 要求群):
        """同一観測IDの候補対称な検索表層だけを、過去成功率でprimaryへ入替える。"""
        rows = list(tuple(要求群))
        if not rows or not self._観測経路経験:
            return tuple(rows)
        by_id = {}
        for index, row in enumerate(rows):
            by_id.setdefault(str(getattr(row, "ID", "")), []).append((index, row))
        for group in by_id.values():
            primary = [(i, x) for i, x in group if str(getattr(x, "段階", "")) == "primary"]
            縮退候補 = [(i, x) for i, x in group if str(getattr(x, "段階", "")) == "fallback"]
            if not primary or not 縮退候補:
                continue
            p_key = HDS観測経路鍵を構成(primary[0][1])
            p_trials, p_success = self.観測経路成績(p_key)
            候補 = []
            for index, row in 縮退候補:
                key = HDS観測経路鍵を構成(row)
                trials, success = self.観測経路成績(key)
                if trials >= 2 and success > 0:
                    候補.append((success, trials, -int(getattr(row, "優先度", 50)), index, row))
            if not 候補:
                continue
            候補.sort(key=lambda x: (-x[0] / x[1], -x[0], -x[2], x[3]))
            success, trials, _優先度, best_index, best = 候補[0]
            # primaryに十分な実績があり、同等以上なら経路を入れ替えない。
            if p_trials >= 2 and p_success * trials >= success * p_trials:
                continue
            主観測優先度 = min(int(getattr(x, "優先度", 50)) for _, x in primary)
            rows[best_index] = replace(
                best, 段階="primary", 優先度=主観測優先度,
                provenance=tuple(dict.fromkeys((*tuple(getattr(best, "provenance", ())), "経験優先経路"))),
            )
            for index, row in primary:
                rows[index] = replace(
                    row, 段階="fallback", 優先度=max(主観測優先度 + 10, int(getattr(row, "優先度", 50))),
                    provenance=tuple(dict.fromkeys((*tuple(getattr(row, "provenance", ())), "経験降格経路"))),
                )
        return tuple(sorted(rows, key=lambda x: (int(getattr(x, "優先度", 50)), str(getattr(x, "ID", "")), str(getattr(x, "外部検索表層", "")).casefold())))

    def 結果を受け取る(self, 機会, 結果, 状態差, 前状態=None) -> None:
        if str(機会.作用ID).startswith("内的/"):
            return
        成立 = _成立か(結果)
        変化 = bool(状態差.変化有無)
        反証 = (not 成立) or (成立 and not 変化 and not _既に満たす(機会, 前状態))
        self._追加(_経験(
            _文脈(機会), 成立, 変化,
            frozenset(getattr(状態差, "追加状態", ())),
            frozenset(getattr(状態差, "削除状態", ())),
            frozenset(getattr(状態差, "解消残差", ())),
            frozenset(getattr(状態差, "追加残差", ())),
            反証,
        ))

    def _安定効果(self, 機会) -> 期待効果:
        文脈 = _文脈(機会)
        対象 = [x for x in self.全経験 if x.文脈 == 文脈]
        if not 対象:
            return 期待効果()
        最後の反証 = max((i for i, x in enumerate(対象) if x.反証), default=-1)
        有効 = [x for x in 対象[最後の反証 + 1:] if x.成立 and x.変化有無]
        if not 有効:
            return 期待効果()
        追加 = set(有効[0].追加状態); 削除 = set(有効[0].削除状態)
        解消 = set(有効[0].解消残差); 追加残差 = set(有効[0].追加残差)
        for 経験 in 有効[1:]:
            追加.intersection_update(経験.追加状態); 削除.intersection_update(経験.削除状態)
            解消.intersection_update(経験.解消残差); 追加残差.intersection_update(経験.追加残差)
        return 期待効果(frozenset(追加), frozenset(削除), frozenset(解消), frozenset(追加残差), len(有効))

    def _構造安定効果(self, 機会) -> 期待効果:
        文脈 = _文脈(機会)
        同一定義 = [x for x in self.全経験
                    if (x.文脈.作用定義ID, x.文脈.種別, x.文脈.契約版)
                    == (文脈.作用定義ID, 文脈.種別, 文脈.契約版)]
        署名群 = sorted({x.文脈.意味入力署名 for x in 同一定義})
        if len(署名群) < 2:
            return 期待効果()
        効果群=[]
        for 入力署名 in 署名群:
            対象=[x for x in 同一定義 if x.文脈.意味入力署名==入力署名]
            最後=max((i for i,x in enumerate(対象) if x.反証),default=-1)
            有効=[x for x in 対象[最後+1:] if x.成立 and x.変化有無]
            if not 有効: continue
            a=set(有効[0].追加状態); d=set(有効[0].削除状態); r=set(有効[0].解消残差); ar=set(有効[0].追加残差)
            for e in 有効[1:]: a&=set(e.追加状態); d&=set(e.削除状態); r&=set(e.解消残差); ar&=set(e.追加残差)
            効果群.append((a,d,r,ar))
        if len(効果群)<2:
            return 期待効果()
        a,d,r,ar=map(set,効果群[0])
        for x in 効果群[1:]: a&=x[0];d&=x[1];r&=x[2];ar&=x[3]
        return 期待効果(frozenset(a),frozenset(d),frozenset(r),frozenset(ar),len(効果群))

    def 機会を補正(self, 機会):
        if str(機会.作用ID).startswith("内的/"):
            return 機会
        効果 = self._安定効果(機会)
        if 効果.空: 効果 = self._構造安定効果(機会)
        if 効果.空: return 機会
        return replace(機会, 期待=効果)


__all__ = ["HDS適応記憶", "HDS観測経路経験"]
