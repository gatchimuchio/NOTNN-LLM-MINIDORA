"""目的の関係節から、不足する中間関係と観測の利用先を構成する。

既存規則の逆向き探索は、世界関係の逆命題を作ることではない。
未知規則を事実へ捏造せず、観測対象・未束縛変数・予算残差として返す。
"""
from __future__ import annotations
from dataclasses import dataclass, replace
from .契約 import 関係節, 関係項, 関係要求, 演算予算, 関係資源超過, 関係演算停止
from ..コア.値 import 署名, 文字, 文字列組


@dataclass(frozen=True, slots=True)
class 関係不足:
    ID: str
    目的ID: str
    対象: 関係節
    利用先: tuple[str, ...]
    経路: tuple[str, ...] = ()
    状態: str = "未観測"
    理由: str = "目的に必要な関係が現在の証拠から未成立"

    def __post_init__(self):
        文字(self.ID); 文字(self.目的ID); 文字(self.理由)
        if not isinstance(self.対象, 関係節): raise TypeError("不足対象は関係節")
        文字列組(self.利用先); 文字列組(self.経路, 一意=False)
        if not self.利用先: raise ValueError("利用先のない探索要求")
        if self.状態 not in ("未観測", "経路未構成", "予算未完了", "停止"):
            raise ValueError("不足の状態不正")

    @property
    def 署名(self): return 署名(self)


@dataclass(frozen=True, slots=True)
class 目的関係計画:
    要求署名: str
    不足: tuple[関係不足, ...]
    候補経路: tuple[tuple[str, ...], ...]
    完了: bool
    照合数: int
    理由: tuple[str, ...] = ()


def _解決(項, 環境):
    訪問 = set()
    while 項 in 環境:
        if 項 in 訪問: raise ValueError("束縛循環")
        訪問.add(項); 項 = 環境[項]
    return 項


def _単一化(左, 右, 環境):
    if 左.骨格 != 右.骨格: return None
    結果 = dict(環境)
    for (_, 甲), (_, 乙) in zip(左.引数, 右.引数):
        甲, 乙 = _解決(甲, 結果), _解決(乙, 結果)
        if (甲.型, 甲.単位) != (乙.型, 乙.単位): return None
        if 甲 == 乙: continue
        if 甲.変数: 結果[甲] = 乙
        elif 乙.変数: 結果[乙] = 甲
        else: return None
    return 結果


def _具体化(節, 環境):
    return replace(節, 引数=tuple((役割, _解決(項, 環境)) for 役割, 項 in 節.引数))


def _再帰鍵(節):
    変数 = {}
    引数 = []
    for 役割, 項 in 節.引数:
        if 項.変数:
            if 項 not in 変数: 変数[項] = len(変数)
            値 = ("変数", 変数[項], 項.型, 項.単位)
        else: 値 = ("定数", 項.名前, 項.型, 項.単位)
        引数.append((役割, 値))
    return 署名((節.骨格, tuple(引数)))


def 不足関係を構成(要求: 関係要求, 追加契約=(), *, 利用先=("関係回答",), 停止要求=None):
    """型・条件を保つ部分束縛で中間目標を作る。結果は採用証明ではない。"""
    if not isinstance(要求, 関係要求): raise TypeError("関係要求が必要")
    文字列組(tuple(利用先))
    from .取得 import 関係を取得
    取得 = 関係を取得(要求, 追加契約)
    予算 = 演算予算(要求.資源, 停止要求)
    証拠索引, 規則索引 = {}, {}
    for 項 in 取得.証拠: 証拠索引.setdefault(項.節.骨格, []).append(項.節)
    for 項 in 取得.変換: 規則索引.setdefault(項.結論.骨格, []).append(項)
    不足記録, 経路記録, 未完理由 = {}, set(), []

    def 不足を追加(節, 経路, 状態="未観測", 理由="目的に必要な関係が現在の証拠から未成立"):
        ID = "関係不足:" + 署名((要求.ID, 節, 利用先, 経路, 状態))[:24]
        不足記録[ID] = 関係不足(ID, 要求.ID, 節, tuple(利用先), 経路, 状態, 理由)
        return ID

    def 解く(目標, 環境, 経路, 訪問, 深さ):
        予算.消費()
        対象 = _具体化(目標, 環境)
        鍵 = _再帰鍵(対象)
        if 鍵 in 訪問:
            return [(環境, (不足を追加(対象, 経路, "経路未構成", "循環経路だけでは成立を証明しない"),))]
        if 深さ > 要求.資源.最大深さ:
            raise 関係資源超過("不足関係の展開深さ")
        結果 = []
        for 事実 in 証拠索引.get(対象.骨格, ()):
            予算.消費()
            束縛 = _単一化(対象, 事実, 環境)
            if 束縛 is not None: 結果.append((束縛, ()))
        # 直接の証拠がある前提は、その証拠を利用する。代替規則は取得元に保持。
        if 結果: return 結果
        for 規則 in 規則索引.get(対象.骨格, ()):
            予算.消費()
            接続ID = 署名((規則.ID, 鍵, 深さ, 経路))[:24]
            変数 = {項: replace(項, 束縛域="不足:" + 接続ID)
                    for 節 in (*規則.前提, 規則.結論) for _, 項 in 節.引数 if 項.変数}
            def 改名(節):
                return replace(節, 引数=tuple((役割, 変数.get(項, 項)) for 役割, 項 in 節.引数))
            束縛 = _単一化(改名(規則.結論), 対象, 環境)
            if 束縛 is None: continue
            次経路 = (*経路, 規則.ID)
            経路記録.add(次経路)
            組 = [(束縛, ())]
            # 束縛可能な前提を先に使う。既知事実との照合は型付きであり、
            # 統計順位や正解情報による枝削除はしない。
            前提 = tuple(改名(節) for 節 in 規則.前提)
            前提 = tuple(sorted(enumerate(前提), key=lambda 組:
                (not bool(証拠索引.get(組[1].骨格)), 組[0])))
            for _, 節 in 前提:
                新組 = []
                for 既環境, 不足ID in 組:
                    for 新環境, 新不足 in 解く(節, 既環境, 次経路, 訪問 | {鍵}, 深さ + 1):
                        新組.append((新環境, (*不足ID, *新不足)))
                        if len(新組) > 要求.資源.最大写像:
                            raise 関係資源超過("不足関係の対応容量")
                組 = 新組
            結果.extend(組)
        if not 結果:
            結果.append((環境, (不足を追加(対象, 経路),)))
        return 結果

    完了 = True
    try:
        結果 = 解く(要求.問い, {}, (), frozenset(), 0)
        使用不足 = {ID for _, 群 in 結果 for ID in 群}
        # 探索途中で作られた仮の不足も記録は残し、現行の要求群と分ける。
        不足群 = tuple(不足記録[ID] for ID in sorted(使用不足))
    except (関係資源超過, 関係演算停止) as 例外:
        完了 = False; 未完理由.append(str(例外))
        状態 = "停止" if isinstance(例外, 関係演算停止) else "予算未完了"
        不足を追加(要求.問い, (), 状態, str(例外))
        不足群 = tuple(不足記録[ID] for ID in sorted(不足記録))
    return 目的関係計画(要求.署名, 不足群, tuple(sorted(経路記録)), 完了, 予算.照合数, tuple(未完理由))


def 不足を検索表層へ(不足: 関係不足):
    """意味上既知の端点と述語だけを外部検索へ写す。条件・極性は別途保持する。"""
    節 = 不足.対象
    既知 = tuple(項.名前 for _, 項 in 節.引数 if not 項.変数)
    return {
        "目的ID": 不足.目的ID, "不足ID": 不足.ID, "述語": 節.述語,
        "既知端点": 既知, "未知役割": tuple(役割 for 役割, 項 in 節.引数 if 項.変数),
        "検索表層": " ".join((*既知, 節.述語)),
        "肯定": 節.肯定, "条件": 節.条件, "範囲": 節.範囲, "時点": 節.時点,
        "様相": 節.様相, "量化": 節.量化, "利用先": 不足.利用先,
    }