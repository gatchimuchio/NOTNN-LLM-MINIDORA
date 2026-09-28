from __future__ import annotations

from typing import Callable, Mapping, Sequence

from .HDS実行主体 import HDS実行主体, HDS実行状態, HDS作用器, HDS実行結果, HDS作用供給器, HDS終端
from .統合駆動_v2.政策 import HDS運用政策
from .統合駆動_v2.認識 import HDS認識項目
from .統合駆動_v2.観測 import HDS観測器, HDS観測要求
from .統合駆動_v2.仮説 import HDS仮説, HDS仮説雛型, HDS作業枝
from .統合駆動_v2.依存 import HDS依存辺
from .統合駆動_v2.記憶 import HDS記憶
from .統合駆動_v2.検証 import HDS検証器, HDS草案
from .統合駆動_v2.形成 import HDS形成関係
from .統合駆動_v2.一時適応 import HDS適応記憶
from .統合駆動_v2.入力境界 import HDS異種表象, HDS異種入力作用
from .HDSコア入力 import HDSコア入力束
from .HDS構文化処理系列_v1_4 import HDSカーネル束, HDS意味専用計画器
from .HDS非退行包絡 import HDS非退行判定, HDS非退行包絡
from .参照 import 参照取得診断, 参照記録, 参照記録群を統合, 固定参照供給器

HDS駆動コア版 = "MINIDORA-HDS-FIRST-v6"
HDS継承基準版 = "HDS-MINIDORA-63d5d7e7"

class HDS駆動コア:
    """Compiler Kernelを唯一の意味正本として消費するMINIDORA内部Core。"""

    def __init__(self, *, HDSコンパイラ=None, 最大作用回数: int = 32, 政策: HDS運用政策 | None = None,
                 観測器: Sequence[HDS観測器] = (), 仮説雛型: Sequence[HDS仮説雛型] = (),
                 検証器: Sequence[HDS検証器] = (), 最終検証器: Sequence[HDS検証器] = (),
                 関係規則=(), 未来制約=(), 作用供給器=(), 停止要求=None) -> None:
        self.HDSコンパイラ = HDSコンパイラ
        if type(最大作用回数) is not int or not 1 <= 最大作用回数 <= 4096:
            raise ValueError("最大作用回数は1..4096の整数が必要")
        self.最大作用回数 = 最大作用回数
        self.政策 = 政策
        self.観測器 = tuple(観測器); self.仮説雛型 = tuple(仮説雛型)
        self.検証器 = tuple(検証器); self.最終検証器 = tuple(最終検証器)
        self.関係規則 = tuple(関係規則); self.未来制約 = tuple(未来制約)
        self.作用供給器 = tuple(作用供給器); self.停止要求 = 停止要求
        # Core寿命を学習対象期間とする。結果ではなく通常循環が更新した状態だけを継承する。
        self._継続記憶 = HDS記憶()
        self._継続形成関係: tuple[HDS形成関係, ...] = ()
        self._継続参照記憶: tuple[参照記録, ...] = ()
        self._適応記憶 = HDS適応記憶(4096)

    @property
    def 継続状態署名(self) -> str:
        from .コア.値 import 署名
        return 署名((
            self._継続記憶,
            self._継続形成関係,
            tuple((x.識別子, x.供給器, x.由来, x.内容, x.条件, float(x.信頼)) for x in self._継続参照記憶),
            self._適応記憶.状態署名,
        ))

    @property
    def 継続参照件数(self) -> int:
        return len(self._継続参照記憶)

    def 継続状態を初期化(self) -> None:
        self._継続記憶 = HDS記憶()
        self._継続形成関係 = ()
        self._継続参照記憶 = ()
        self._適応記憶.初期化()

    def 実行(self, 問合せ: str, *, 目的: Sequence[str] = (), 要求状態: Sequence[str] = (),
           追加作用: Sequence[HDS作用器] = (), 追加作用供給器: Sequence[HDS作用供給器] = (),
           カーネル正本: HDSカーネル束 | None = None, 入力正本: HDSコア入力束 | None = None,
           初期成立状態: Sequence[str] = (), 初期残差: Sequence[str] | None = None,
           初期成果: Mapping[str, object] | None = None, 主体状態: Mapping[str, object] | None = None,
           前回結果: object = None, HDS履歴=(), 文脈=None,
           初期認識: Sequence[HDS認識項目] = (), 要求認識: Sequence[str] = (),
           初期依存: Sequence[HDS依存辺] = (), 観測要求: Sequence[HDS観測要求] = (),
           初期記憶: HDS記憶 | None = None, 初期仮説: Sequence[HDS仮説] = (),
           初期枝: Sequence[HDS作業枝] = (), 初期草案: Sequence[HDS草案] = (),
           形成関係: Sequence[HDS形成関係] | None = None, 異種表象: Sequence[HDS異種表象] = ()) -> HDS実行結果:
        if not isinstance(問合せ, str) or not 問合せ.strip():
            raise ValueError("HDS駆動コアの問合せは空でない文字列である必要がある")
        明示要求状態 = tuple(str(x) for x in 要求状態)
        明示残差 = tuple(str(x) for x in (初期残差 or ()))
        明示要求認識 = frozenset(要求認識)
        if not 明示要求状態 and not 明示残差 and not 明示要求認識:
            raise ValueError("HDS駆動コアには要求状態・初期残差・要求認識のいずれかによる明示的な完了条件が必要")

        作用群: list[HDS作用器] = []
        残差群 = set(明示残差)
        成果初期値 = dict(初期成果 or {})
        主体初期値 = dict(主体状態 or {})
        成立初期値 = set(str(x) for x in 初期成立状態)
        目的初期値 = list(str(x) for x in 目的)

        kernel = カーネル正本
        if kernel is not None and not isinstance(kernel, HDSカーネル束):
            raise TypeError("カーネル正本はHDSカーネル束である必要がある")
        コア入力 = 入力正本
        if コア入力 is not None and not isinstance(コア入力, HDSコア入力束):
            raise TypeError("入力正本はHDSコア入力束である必要がある")

        if kernel is None and self.HDSコンパイラ is not None:
            kernel_fn = getattr(self.HDSコンパイラ, "コンパイル束", None)
            if callable(kernel_fn):
                kernel = kernel_fn(問合せ, 前回結果=前回結果, HDS履歴=tuple(HDS履歴), 文脈=文脈)
                if not isinstance(kernel, HDSカーネル束):
                    raise TypeError("Compiler KernelがHDSカーネル束を返さなかった")
            elif コア入力 is None:
                コア関数 = getattr(self.HDSコンパイラ, "コア入力コンパイル", None)
                if callable(コア関数):
                    コア入力 = コア関数(問合せ, 前回結果=前回結果, HDS履歴=tuple(HDS履歴), 文脈=文脈)
                    if not isinstance(コア入力, HDSコア入力束):
                        raise TypeError("Legacy Core入力構文化器がHDSコア入力束を返さなかった")
                else:
                    from .HDS構文化作用 import HDS構文化作用
                    残差群.add("入力未構文化")
                    作用群.append(HDS構文化作用(self.HDSコンパイラ, 問合せ, 前回結果=前回結果, HDS履歴=tuple(HDS履歴), 文脈=文脈))

        if kernel is not None:
            if コア入力 is not None and コア入力.意味署名 != kernel.コア入力.意味署名:
                raise ValueError("Kernelと明示Core入力が同一意味正本からの射影ではない")
            コア入力 = kernel.コア入力
            if "HDSカーネル束" in 成果初期値 or "HDSカーネル署名" in 主体初期値:
                raise ValueError("HDSカーネルの予約初期キーは呼出側から上書きできない")
            成果初期値["HDSカーネル束"] = kernel
            主体初期値["HDSカーネル署名"] = kernel.カーネル署名
            成立初期値.add("HDSカーネル形成済み")

        if コア入力 is not None:
            if "HDSコア入力" in 成果初期値 or "HDSコア入力署名" in 主体初期値:
                raise ValueError("HDSコア入力の予約初期キーは呼出側から上書きできない")
            成果初期値["HDSコア入力"] = コア入力
            主体初期値["HDSコア入力署名"] = コア入力.意味署名
            成立初期値.add("HDSコア入力済み")
            残差群.update(f"HDS残差:{項目.種別}:{項目.理由}" for 項目 in コア入力.残差)
            目的初期値.extend(f"HDS目的:{項目.ID}:{項目.種別}" for 項目 in コア入力.目的)

        if 異種表象:
            残差群.add("異種入力未接続")
            作用群.append(HDS異種入力作用(tuple(異種表象)))
        作用群.extend(tuple(追加作用))

        初期 = HDS実行状態(
            tuple(dict.fromkeys(目的初期値)), frozenset(明示要求状態), frozenset(成立初期値),
            frozenset(残差群), tuple(sorted(成果初期値.items(), key=lambda 行: 行[0])),
            tuple(sorted(主体初期値.items(), key=lambda 行: 行[0])), 0,
            認識=tuple(初期認識), 要求認識=明示要求認識, 依存=tuple(初期依存), 観測要求=tuple(観測要求),
            記憶=初期記憶 if 初期記憶 is not None else self._継続記憶, 仮説=tuple(初期仮説),
            枝=tuple(初期枝), 草案=tuple(初期草案),
            形成関係=self._継続形成関係 if 形成関係 is None else tuple(形成関係),
        )
        結果 = HDS実行主体(
            tuple(作用群), 最大作用回数=self.最大作用回数, 政策=self.政策, 観測器=self.観測器,
            仮説雛型=self.仮説雛型, 検証器=self.検証器, 最終検証器=self.最終検証器,
            関係規則=self.関係規則, 未来制約=self.未来制約,
            作用供給器=(*self.作用供給器, *tuple(追加作用供給器)), 停止要求=self.停止要求,
            適応記憶=self._適応記憶,
        ).実行(初期)
        # SUSPEND/FAILを含め、通常循環で実際に保持・形成された状態は次回処理の前提へ継承する。
        self._継続記憶 = 結果.状態.記憶
        self._継続形成関係 = 結果.状態.形成関係
        return 結果

    def 非退行継承実行(self, 問合せ: str, *, 基準実行: Callable[[], object], 基準承認判定: Callable[[object], bool],
                   拡張採用証明: Callable[[object, object], bool], 拡張実行: Callable[[], object] | None = None,
                   拡張承認判定: Callable[[object], bool] | None = None, **実行引数) -> HDS非退行判定:
        基準結果 = 基準実行()
        実拡張実行 = 拡張実行 or (lambda: self.実行(問合せ, **実行引数))
        実拡張承認判定 = 拡張承認判定 or (lambda 結果: isinstance(結果, HDS実行結果) and 結果.終端 == HDS終端.採用)
        return HDS非退行包絡(基準結果, 基準承認判定=基準承認判定, 拡張実行=実拡張実行,
                         拡張承認判定=実拡張承認判定, 拡張採用証明=拡張採用証明)

    def 選択実行(self, 問合せ: str, 選択肢: Sequence[str], *, 初期参照=(), 初期参照診断=(), 参照供給器=None,
             計算実行器_=None, 模型核=None, 基礎能力核=None, 既存能力継承: bool = True,
             最大回復回数: int = 6, 拡張採用証明=None,
             カーネル正本: HDSカーネル束 | None = None) -> HDS実行結果:
        if self.HDSコンパイラ is None:
            raise ValueError("選択実行にはHDSコンパイラが必要")
        候補 = tuple(str(x) for x in 選択肢)
        if len(候補) < 2:
            raise ValueError("選択実行には2件以上の候補が必要")
        問題束 = カーネル正本
        if 問題束 is not None:
            if not isinstance(問題束, HDSカーネル束):
                raise TypeError("カーネル正本はHDSカーネル束である必要がある")
            束候補 = tuple(
                str(x.内容)
                for x in sorted(
                    (x for x in 問題束.意味IR.座標 if x.座標ID.startswith("選択肢:")),
                    key=lambda x: x.座標ID,
                )
            )
            if 束候補 and 束候補 != 候補:
                raise ValueError("カーネル正本の選択肢と実行引数が一致しない")
        else:
            問題束関数 = getattr(self.HDSコンパイラ, "問題コンパイル束", None)
            if callable(問題束関数):
                問題束 = 問題束関数(問合せ, 候補)
                if not isinstance(問題束, HDSカーネル束):
                    raise TypeError("問題コンパイル束がHDSカーネル束を返さなかった")
            else:
                問題IR関数 = getattr(self.HDSコンパイラ, "問題IR", None)
                問題入力関数 = getattr(self.HDSコンパイラ, "問題コア入力", None)
                if not callable(問題IR関数) or not callable(問題入力関数):
                    raise TypeError("選択実行には問題コンパイル束、または問題IRと問題コア入力が必要")
                from .HDS観測計画 import HDS参照観測要求群
                問題IR = 問題IR関数(問合せ, 候補)
                入力束 = 問題入力関数(問合せ, 候補)
                問題束 = HDSカーネル束(
                    意味IR=問題IR, 計算計画=HDS意味専用計画器().計画(問合せ), コア入力=入力束,
                    参照観測要求=HDS参照観測要求群(問題IR),
                )
        問題IR = 問題束.意味IR
        入力束 = 問題束.コア入力
        from .HDS選択継承循環 import (
            HDS選択継承供給, HDS選択継承設定, 参照成果名, 参照世代成果名,
            計算済み成果名, 参照記憶成果名, 参照取得診断成果名,
            関係観測消費成果名, 関係観測世代成果名, 選択閉包状態, 残差_未評価,
            残差_参照取得障害,
        )
        # 前回までの実観測を現在の問いで検索し直す。回答・採点結果は記憶へ入れない。
        記憶参照: tuple[参照記録, ...] = ()
        if self._継続参照記憶:
            from .HDS参照 import HDS参照検索
            記憶参照 = HDS参照検索(
                固定参照供給器(self._継続参照記憶, 名称="HDS継続参照記憶"),
                問題IR,
                上限=32,
                観測要求=tuple(問題束.参照観測要求),
            )
        初期参照群 = 参照記録群を統合(記憶参照, tuple(初期参照), 最大件数=64)

        入力残差非阻害対象 = tuple(
            f"HDS残差:{項目.種別}:{項目.理由}" for 項目 in 入力束.残差 if 項目.種別 == "未解共参照"
        )
        初期診断 = tuple(初期参照診断)
        if any(not isinstance(x, 参照取得診断) for x in 初期診断):
            raise TypeError("初期参照診断は参照取得診断tupleである必要がある")
        初期選択残差 = [残差_未評価]
        if any(x.状態 in {"失敗", "縮退"} for x in 初期診断):
            初期選択残差.append(残差_参照取得障害)
        供給 = HDS選択継承供給(
            問題束, self.HDSコンパイラ, 初期参照群, 模型核=模型核, 基礎能力核=基礎能力核,
            既存能力継承=既存能力継承, 参照供給器=参照供給器, 計算実行器_=計算実行器_,
            設定=HDS選択継承設定(最大回復回数), 拡張採用証明=拡張採用証明,
            入力残差非阻害対象=入力残差非阻害対象,
        )
        結果 = self.実行(
            問合せ, 目的=("選択問題を閉包する",), 要求状態=(選択閉包状態,), 初期残差=tuple(初期選択残差),
            初期成果={
                参照成果名: 初期参照群,
                参照世代成果名: 0,
                計算済み成果名: False,
                参照記憶成果名: 初期参照群,
                参照取得診断成果名: 初期診断,
                関係観測消費成果名: (),
                関係観測世代成果名: 0,
            },
            カーネル正本=問題束,
            追加作用供給器=(HDS作用供給器("HDS選択継承循環", 供給.構成, "v4"),),
        )
        最終参照 = 結果.状態.成果辞書().get(参照成果名, 初期参照群)
        if isinstance(最終参照, tuple) and all(isinstance(x, 参照記録) for x in 最終参照):
            self._継続参照記憶 = 参照記録群を統合(self._継続参照記憶, 最終参照)
        return 結果

__all__ = ["HDS駆動コア版", "HDS継承基準版", "HDS駆動コア"]
