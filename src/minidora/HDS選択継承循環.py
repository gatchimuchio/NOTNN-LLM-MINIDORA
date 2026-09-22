from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

from .HDS実行主体 import HDS実行状態, HDS作用結果, HDS作用状態, HDS関数作用
from .HDS実行系射影 import HDSR質問射影
from .HDS選択実行系 import HDS選択実行結果, HDS選択推論実行
from .HDS非退行包絡 import HDS非退行判定, HDS非退行包絡
from .HDS既存能力継承 import (
    HDS既存能力結果証明済み,
    HDS既存能力選択評価,
    HDS多重解釈選択評価,
)
from .hds参照拡張 import HDS参照履歴統合, HDS観測窓更新, HDS追加参照検索
from .参照 import 参照供給器, 参照記録
from .模型 import MINIDORA模型核
from .能力状態差循環 import 標準能力模型核
from .計算実行器 import 計算実行器
from .コア.値 import 署名 as _意味署名


HDS選択継承循環版 = "HDS-MINIDORA-SELECTION-INHERITANCE-v2"

参照成果名 = "HDS選択:参照"
参照履歴成果名 = "HDS選択:参照履歴"
参照世代成果名 = "HDS選択:参照世代"
計算済み成果名 = "HDS選択:計算済み"
基準結果主体名 = "HDS選択:基準結果"
現行結果成果名 = "HDS選択:現行結果"
評価参照署名成果名 = "HDS選択:評価参照署名"
非退行判定成果名 = "HDS選択:非退行判定"
影結果成果名 = "HDS選択:影結果"
回答成果名 = "HDS選択:回答ラベル"
入力残差影成果名 = "HDS選択:入力残差影"
観測計画主体名 = "HDS選択:観測計画"
影結果主体名 = "HDS選択:影結果保持"
非退行判定主体名 = "HDS選択:非退行判定保持"
選択閉包状態 = "HDS選択:閉包"

残差_未評価 = "HDS選択:未評価"
残差_再検証要求 = "HDS選択:再検証要求"
残差_観測不足 = "HDS選択:観測不足"
残差_問題意味損失 = "HDS選択:問題意味損失"
残差_候補意味損失 = "HDS選択:候補意味損失"
残差_資料意味損失 = "HDS選択:資料意味損失"
残差_候補競合 = "HDS選択:候補競合"
残差_候補識別不足 = "HDS選択:候補識別不足"
残差_状態差未消費 = "HDS選択:状態差未消費"
残差_計算要求 = "HDS選択:計算要求"
残差_未解 = "HDS選択:未解残差"
残差_証明不足 = "HDS選択:拡張採用証明不足"
残差_観測無進展 = "HDS選択:追加観測無進展"

選択残差集合 = frozenset({
    残差_未評価,
    残差_再検証要求,
    残差_観測不足,
    残差_問題意味損失,
    残差_候補意味損失,
    残差_資料意味損失,
    残差_候補競合,
    残差_候補識別不足,
    残差_状態差未消費,
    残差_計算要求,
    残差_未解,
    残差_証明不足,
    残差_観測無進展,
})
回復可能残差 = frozenset({
    残差_再検証要求,
    残差_観測不足,
    残差_資料意味損失,
    残差_候補競合,
    残差_候補識別不足,
    残差_証明不足,
    残差_観測無進展,
})


def _署名(値: object) -> str:
    return _意味署名(値)


def _参照署名(参照群: Sequence[参照記録]) -> str:
    # query provenanceは「どう見つけたか」の履歴であり、証拠内容の状態差ではない。
    # 同じ資料を別queryで再発見しただけで学習世代を進展扱いしない。
    検索経路鍵 = frozenset({"hds_query_kind", "hds_query_選択肢"})
    return _署名(tuple(
        (
            x.識別子,
            x.供給器,
            x.由来,
            float(x.信頼),
            tuple((str(k), str(v)) for k, v in x.条件 if str(k) not in 検索経路鍵),
            x.意味キー,
            x.表示値,
        )
        for x in 参照群
    ))


def _承認済み(結果: object) -> bool:
    return bool(
        isinstance(結果, HDS選択実行結果)
        and 結果.状態 == "APPROVE"
        and 結果.回答ラベル is not None
    )


def _一致能力数(結果: HDS選択実行結果) -> int:
    最大 = 0
    for raw in 結果.理由:
        text_ = str(raw)
        prefix = "AGREEING_EXISTING_CAPABILITIES:"
        if not text_.startswith(prefix):
            continue
        try:
            最大 = max(最大, int(text_[len(prefix):]))
        except ValueError:
            continue
    return 最大


def _参照根拠情報源数(結果: HDS選択実行結果) -> int:
    模型結果 = getattr(結果, "MINIDORA模型結果", None)
    label = 結果.回答ラベル
    if 模型結果 is None or label is None:
        return 0
    row = next((x for x in getattr(模型結果, "候補差", ()) if getattr(x, "候補ID", None) == label), None)
    if row is None:
        return 0
    ids: set[str] = set()
    for contribution in getattr(row, "寄与", ()):
        for raw in getattr(contribution, "根拠", ()):
            text_ = str(raw)
            if text_.startswith("参照:"):
                payload = text_[len("参照:"):]
                情報源 = payload.rsplit(":", 1)[0] if ":" in payload else payload
                if 情報源:
                    ids.add(情報源)
            elif text_.startswith("再照合:"):
                payload = text_[len("再照合:"):]
                parts = payload.rsplit(":", 2)
                情報源 = parts[0] if parts else payload
                if 情報源:
                    ids.add(情報源)
    return len(ids)


def _参照得点差(結果: HDS選択実行結果) -> float:
    模型結果 = getattr(結果, "MINIDORA模型結果", None)
    label = 結果.回答ラベル
    if 模型結果 is None or label is None:
        return 0.0
    fn = getattr(模型結果, "参照候補辞書", None)
    if not callable(fn):
        return 0.0
    得点群 = {str(k): float(v) for k, v in dict(fn()).items()}
    自分 = float(得点群.get(str(label), 0.0))
    他 = max((v for k, v in 得点群.items() if k != str(label)), default=0.0)
    return 自分 - 他


def _K3独立証拠強度(結果: HDS選択実行結果) -> tuple[int, int, float]:
    K3結果 = getattr(結果, "K3結果", None)
    回答 = 結果.回答ラベル
    if K3結果 is None or 回答 is None:
        return (0, 0, 0.0)
    診断群 = tuple(getattr(K3結果, "候補診断", ()))
    if not 診断群:
        return (0, 0, 0.0)
    採用 = next((item for item in 診断群 if str(getattr(item, "候補", "")) == str(回答)), None)
    if 採用 is None:
        return (0, 0, 0.0)
    他得点 = max(
        (float(getattr(item, "合計得点", 0.0)) for item in 診断群 if item is not 採用),
        default=0.0,
    )
    return (
        max(0, int(getattr(採用, "独立出典数", 0))),
        max(0, int(getattr(採用, "識別一致出典数", 0))),
        float(getattr(採用, "合計得点", 0.0)) - 他得点,
    )


def _結果証拠強度(結果: HDS選択実行結果) -> tuple[int, int, int, int, int, int, float]:
    理由群 = {str(x) for x in 結果.理由}
    直接 = int("DIRECTED_関係_VERIFIED" in 理由群 or "EXISTING_DIRECT_関係_VERIFIED" in 理由群)
    多重 = int("HDS_MULTI_INTERPRETATION_AGREEMENT" in 理由群)
    一致 = _一致能力数(結果)
    情報源数 = _参照根拠情報源数(結果)
    K3独立出典数, K3識別一致出典数, K3候補差 = _K3独立証拠強度(結果)
    差 = max(_参照得点差(結果), K3候補差)
    return (直接, 多重, 一致, 情報源数, K3独立出典数, K3識別一致出典数, 差)


def _強固定可能(結果: HDS選択実行結果) -> bool:
    直接, 多重, 一致, 情報源数, K3独立出典数, K3識別一致出典数, 差 = _結果証拠強度(結果)
    return bool(
        直接
        or 多重
        or 一致 >= 2
        or (情報源数 >= 2 and 差 > 0)
        or (K3独立出典数 >= 2 and K3識別一致出典数 >= 1 and 差 > 0)
    )


def _再検証更新可能(基準: HDS選択実行結果, 現在: HDS選択実行結果) -> bool:
    if not _承認済み(現在) or not HDS既存能力結果証明済み(現在):
        return False
    if 現在.回答ラベル == 基準.回答ラベル:
        return True
    if not _強固定可能(現在):
        return False
    return _結果証拠強度(現在) > _結果証拠強度(基準)


@dataclass(frozen=True, slots=True)
class HDS選択観測計画:
    基準参照署名: str
    世代: int
    解釈番号: int
    検索IR: object
    対象残差: tuple[str, ...]
    探索種別: str = "標準"
    理由: tuple[str, ...] = ()


def _選択残差(結果: HDS選択実行結果, 参照群: Sequence[参照記録]) -> frozenset[str]:
    if _承認済み(結果):
        return frozenset()

    joined = "\n".join(str(x) for x in 結果.理由)
    out: set[str] = set()
    if any(x in joined for x in ("QUESTION_意味_LOSS", "QUESTION_SEMANTIC_LOSS", "HDS_K_QUESTION_意味_LOSS", "HDS_K_QUESTION_SEMANTIC_LOSS")):
        out.add(残差_問題意味損失)
    if any(x in joined for x in ("選択肢_意味_LOSS", "CHOICE_SEMANTIC_LOSS")):
        out.add(残差_候補意味損失)
    if any(x in joined for x in ("資料_COMPILE_PARTIAL", "DATA_COMPILE_PARTIAL")) or 結果.資料コンパイル失敗数 > 0:
        out.add(残差_資料意味損失)
    if any(x in joined for x in (
        "NO_KNOWLEDGE_証拠",
        "NO_KNOWLEDGE_EVIDENCE",
        "NO_候補",
        "NO_CANDIDATE",
        "MINIDORA_OUTPUT_ABSENT",
        "NO_GUESS",
        "証拠_INSUFFICIENT",
        "EVIDENCE_INSUFFICIENT",
        "MINIDORA_模型_模型核_NO_参照_CONTRIBUTION",
        "MINIDORA_MODEL_CORE_NO_REFERENCE_CONTRIBUTION",
    )):
        out.add(残差_観測不足)
    if any(x in joined for x in (
        "AMBIGUOUS_証拠",
        "AMBIGUOUS_EVIDENCE",
        "EXCEPTION_NOT_RESOLVED",
        "参照_DIFFERENCE_NOT_UNIQUE",
        "REFERENCE_DIFFERENCE_NOT_UNIQUE",
    )):
        out.add(残差_候補競合)
    if (
        ("HDS_作用_DELTA_ATTACHED" in joined or "HDS_ACTION_DELTA_ATTACHED" in joined)
        and not ("HDS_作用_DELTA_CONSUMED" in joined or "HDS_ACTION_DELTA_CONSUMED" in joined)
    ):
        out.add(残差_状態差未消費)
    if not tuple(参照群):
        out.add(残差_観測不足)
    if 結果.状態 == "FAIL":
        out.add(残差_未解)
    if not out:
        out.add(残差_候補識別不足)
    return frozenset(out)


def _標準追加採用証明(
    基準: HDS選択実行結果,
    拡張: HDS選択実行結果,
    *,
    初期参照署名: str,
    現在参照署名: str,
) -> bool:
    """HDS-MINIDORA受入正本の「追加成果は証明付きだけ昇格」を汎用選択へ射影する。

    goldや問題IDは使わない。初期参照から実観測が変化し、拡張側の通常模型核自身が
    一意な正の参照寄与でAPPROVEした場合だけ追加採用証明とする。
    """
    if _承認済み(基準) or not _承認済み(拡張):
        return False
    if 初期参照署名 == 現在参照署名:
        return False
    return HDS既存能力結果証明済み(拡張)


@dataclass(frozen=True, slots=True)
class HDS選択継承設定:
    最大回復回数: int = 6
    基準承認再検証: bool = True

    def __post_init__(self) -> None:
        if type(self.最大回復回数) is not int or not 0 <= self.最大回復回数 <= 64:
            raise ValueError("最大回復回数は0..64の整数である必要がある")
        if type(self.基準承認再検証) is not bool:
            raise TypeError("基準承認再検証はboolである必要がある")


class HDS選択継承供給:
    """HDS-MINIDORA受入正本の再観測・再評価・非退行を通常循環へ供給する。

    第二の実行主体や旧監督を起動しない。供給するのはHDS作用だけであり、
    選択・実行・停止・COMMITはHDS実行主体の通常循環が所有する。
    """

    def __init__(
        self,
        質問IR,
        コンパイラ,
        初期参照: Sequence[参照記録],
        *,
        質問IR群: Sequence[object] = (),
        模型核: MINIDORA模型核 | None = None,
        基礎能力核=None,
        既存能力継承: bool = True,
        参照供給器: 参照供給器 | None = None,
        計算実行器_: 計算実行器 | None = None,
        設定: HDS選択継承設定 | None = None,
        拡張採用証明: Callable[[HDS選択実行結果, HDS選択実行結果], bool] | None = None,
        入力残差非阻害対象: Sequence[str] = (),
    ) -> None:
        self.質問IR = 質問IR
        self.質問IR群 = tuple(質問IR群) or (質問IR,)
        if self.質問IR群[0] != 質問IR:
            self.質問IR群 = (質問IR, *tuple(x for x in self.質問IR群 if x != 質問IR))
        self.検索IR = HDSR質問射影(質問IR)
        検索view群 = tuple(HDSR質問射影(x) for x in self.質問IR群)
        一意view: list[object] = []
        view署名: set[str] = set()
        for view in 検索view群:
            sig = _署名((getattr(view, "原文", ""), getattr(view, "座標", ()), getattr(view, "関係", ())))
            if sig in view署名:
                continue
            view署名.add(sig)
            一意view.append(view)
        self.検索IR群 = tuple(一意view) or (self.検索IR,)
        self.コンパイラ = コンパイラ
        self.初期参照 = tuple(初期参照)
        self.初期参照署名 = _参照署名(self.初期参照)
        self.模型核 = 模型核 or 標準能力模型核()
        if 基礎能力核 is None and 既存能力継承:
            from .K3機能 import K3相当能力核
            基礎能力核 = K3相当能力核()
        self.基礎能力核 = 基礎能力核 if 既存能力継承 else None
        self.既存能力継承 = bool(既存能力継承)
        self.参照供給器 = 参照供給器
        self.計算実行器 = 計算実行器_
        self.設定 = 設定 or HDS選択継承設定()
        self.拡張採用証明 = 拡張採用証明
        self.入力残差非阻害対象 = frozenset(str(x) for x in 入力残差非阻害対象)
        self.選択肢 = tuple(
            x.座標ID.split(":", 1)[1]
            for x in 質問IR.座標
            if x.座標ID.startswith("選択肢:")
        )

    @staticmethod
    def _成果(状態: HDS実行状態) -> dict[str, object]:
        return 状態.成果辞書()

    def _参照(self, 状態: HDS実行状態) -> tuple[参照記録, ...]:
        value = self._成果(状態).get(参照成果名, self.初期参照)
        if not isinstance(value, tuple) or any(not isinstance(x, 参照記録) for x in value):
            raise TypeError("HDS選択の参照成果は参照記録tupleである必要がある")
        return value

    def _参照履歴(self, 状態: HDS実行状態) -> tuple[参照記録, ...]:
        value = self._成果(状態).get(参照履歴成果名, self.初期参照)
        if not isinstance(value, tuple) or any(not isinstance(x, 参照記録) for x in value):
            raise TypeError("HDS選択の参照履歴成果は参照記録tupleである必要がある")
        return value

    def _評価(self, 参照群: tuple[参照記録, ...]) -> HDS選択実行結果:
        compile_fn = getattr(self.コンパイラ, "コンパイル", None)
        if not callable(compile_fn):
            raise TypeError("選択継承循環にはコンパイル可能なHDSコンパイラが必要")
        if not self.既存能力継承:
            return HDS選択推論実行(
                self.質問IR,
                参照群,
                コンパイル=compile_fn,
                基礎能力核=None,
                模型核=self.模型核,
                正式模型評価=True,
            )
        return HDS多重解釈選択評価(
            tuple(self.質問IR群),
            参照群,
            コンパイル=compile_fn,
            模型核=self.模型核,
            基礎能力核=self.基礎能力核,
        )

    def _評価作用(self, 状態: HDS実行状態):
        成果 = self._成果(状態)
        参照群 = self._参照(状態)
        ref_sig = _参照署名(参照群)
        evaluated_sig = 成果.get(評価参照署名成果名)
        if evaluated_sig == ref_sig:
            return None

        def 実行(s: HDS実行状態):
            refs = self._参照(s)
            current_sig = _参照署名(refs)
            結果 = self._評価(refs)
            values = self._成果(s)
            主体値 = s.主体辞書()
            基準 = 主体値.get(基準結果主体名)
            初回 = not isinstance(基準, HDS選択実行結果)
            基準差分: tuple[tuple[str, object], ...] = ()
            if 初回:
                基準 = 結果
                # 非退行基準は可変参照の現行成果ではなく、同一入力の履歴基準として保持する。
                # 主体状態差分は成果の自動依存辺へ入らないため、追加観測で自己失効しない。
                基準差分 = ((基準結果主体名, 基準),)

            選択解消 = frozenset(set(s.残差).intersection(選択残差集合))
            承認時入力解消 = frozenset(set(s.残差).intersection(self.入力残差非阻害対象))
            成果群: list[tuple[str, object]] = [
                (現行結果成果名, 結果),
                (評価参照署名成果名, current_sig),
            ]

            if _承認済み(基準):
                継承理由 = (
                    "HDS_MINIDORA_EXISTING_CAPABILITIES_INHERITED"
                    if "HDS_EXISTING_CAPABILITY_INHERITED" in 基準.理由
                    else "HDS_MINIDORA_CANONICAL_INHERITED"
                )
                generation = int(values.get(参照世代成果名, 0))
                再検証可能 = bool(
                    self.設定.基準承認再検証
                    and self.参照供給器 is not None
                    and self.設定.最大回復回数 > 0
                    and not _強固定可能(基準)
                )
                if not 再検証可能:
                    成果群.extend(((回答成果名, 基準.回答ラベル),))
                    if 承認時入力解消:
                        成果群.append((入力残差影成果名, tuple(sorted(承認時入力解消))))
                    return HDS作用結果(
                        HDS作用状態.成立,
                        追加状態=frozenset({選択閉包状態}),
                        解消残差=frozenset((*選択解消, *承認時入力解消)),
                        成果=tuple(成果群),
                        主体状態差分=基準差分,
                        理由=("HDS_BASELINE_APPROVAL_LOCKED", 継承理由),
                    )

                # 弱い初期APPROVEは総暫定性に従い、一度は別観測へ戻す。
                if 初回:
                    return HDS作用結果(
                        HDS作用状態.成立,
                        解消残差=選択解消,
                        追加残差=frozenset({残差_再検証要求}),
                        成果=tuple(成果群),
                        主体状態差分=基準差分,
                        理由=("HDS_BASELINE_APPROVAL_PROVISIONAL", "HDS_REVALIDATION_REQUIRED", 継承理由),
                    )

                参照変化 = current_sig != self.初期参照署名
                if 参照変化 and _承認済み(結果) and 結果.回答ラベル == 基準.回答ラベル:
                    成果群.extend(((回答成果名, 結果.回答ラベル),))
                    if 承認時入力解消:
                        成果群.append((入力残差影成果名, tuple(sorted(承認時入力解消))))
                    成果群.extend(((非退行判定成果名, HDS非退行判定(
                        結果, 基準, 結果, True, False, ("HDS_BASELINE_REVALIDATED_STABLE",)
                    )), (影結果成果名, 結果)))
                    return HDS作用結果(
                        HDS作用状態.成立,
                        追加状態=frozenset({選択閉包状態}),
                        解消残差=frozenset((*選択解消, *承認時入力解消)),
                        成果=tuple(成果群),
                        主体状態差分=基準差分,
                        理由=("HDS_BASELINE_REVALIDATED_STABLE", 継承理由),
                    )

                if (
                    参照変化
                    and _承認済み(結果)
                    and 結果.回答ラベル != 基準.回答ラベル
                    and _再検証更新可能(基準, 結果)
                ):
                    成果群.extend(((回答成果名, 結果.回答ラベル),))
                    if 承認時入力解消:
                        成果群.append((入力残差影成果名, tuple(sorted(承認時入力解消))))
                    成果群.extend(((非退行判定成果名, HDS非退行判定(
                        結果, 基準, 結果, False, True, ("HDS_REVALIDATED_EXTENSION_ADOPTED",)
                    )), (影結果成果名, 結果)))
                    return HDS作用結果(
                        HDS作用状態.成立,
                        追加状態=frozenset({選択閉包状態}),
                        解消残差=frozenset((*選択解消, *承認時入力解消)),
                        成果=tuple(成果群),
                        主体状態差分=基準差分,
                        理由=("HDS_REVALIDATED_EXTENSION_ADOPTED", 継承理由),
                    )

                if generation >= self.設定.最大回復回数:
                    成果群.extend(((回答成果名, 基準.回答ラベル),))
                    if 承認時入力解消:
                        成果群.append((入力残差影成果名, tuple(sorted(承認時入力解消))))
                    return HDS作用結果(
                        HDS作用状態.成立,
                        追加状態=frozenset({選択閉包状態}),
                        解消残差=frozenset((*選択解消, *承認時入力解消)),
                        成果=tuple(成果群),
                        主体状態差分=基準差分,
                        理由=("HDS_REVALIDATION_EXHAUSTED_BASELINE_PRESERVED", 継承理由),
                    )

                residuals = _選択残差(結果, refs)
                residuals = frozenset((*residuals, 残差_再検証要求))
                解消差分 = frozenset(set(選択解消).difference(residuals))
                追加差分 = frozenset(set(residuals).difference(s.残差))
                return HDS作用結果(
                    HDS作用状態.成立,
                    解消残差=解消差分,
                    追加残差=追加差分,
                    成果=tuple(成果群),
                    主体状態差分=基準差分,
                    理由=("HDS_REVALIDATION_CONTINUES", 継承理由),
                )

            if not 初回 and _承認済み(結果):
                if self.拡張採用証明 is not None:
                    proof = bool(self.拡張採用証明(基準, 結果))
                else:
                    proof = _標準追加採用証明(
                        基準,
                        結果,
                        初期参照署名=self.初期参照署名,
                        現在参照署名=current_sig,
                    )
                判定 = HDS非退行包絡(
                    基準,
                    基準承認判定=_承認済み,
                    拡張実行=lambda: 結果,
                    拡張承認判定=_承認済み,
                    拡張採用証明=lambda _前, _後: proof,
                )
                成果群.extend(((非退行判定成果名, 判定), (影結果成果名, 結果)))
                if 判定.拡張採用:
                    成果群.append((回答成果名, 結果.回答ラベル))
                    if 承認時入力解消:
                        成果群.append((入力残差影成果名, tuple(sorted(承認時入力解消))))
                    return HDS作用結果(
                        HDS作用状態.成立,
                        追加状態=frozenset({選択閉包状態}),
                        解消残差=frozenset((*選択解消, *承認時入力解消)),
                        成果=tuple(成果群),
                        主体状態差分=基準差分,
                        理由=tuple(dict.fromkeys((*判定.理由, "HDS_MINIDORA_CANONICAL_INHERITED"))),
                    )
                return HDS作用結果(
                    HDS作用状態.成立,
                    解消残差=選択解消,
                    追加残差=frozenset({残差_証明不足}),
                    成果=tuple(成果群),
                    主体状態差分=tuple((
                        *基準差分,
                        (影結果主体名, 結果),
                        (非退行判定主体名, 判定),
                    )),
                    理由=tuple(dict.fromkeys((*判定.理由, "HDS_EXTENSION_SHADOW_ONLY"))),
                )

            residuals = _選択残差(結果, refs)
            # 計算可能性は評価後に追加する。旧正本の計算機会をHDS作用へ移したもの。
            if self._計算計画() is not None and not bool(values.get(計算済み成果名, False)):
                residuals = frozenset((*residuals, 残差_計算要求))
            # 同じ残差を一作用で解消・再追加しない。前状態との差だけを原子的に返す。
            解消差分 = frozenset(set(選択解消).difference(residuals))
            追加差分 = frozenset(set(residuals).difference(s.残差))
            return HDS作用結果(
                HDS作用状態.成立,
                解消残差=解消差分,
                追加残差=追加差分,
                成果=tuple(成果群),
                主体状態差分=基準差分,
                理由=tuple(dict.fromkeys(("HDS_SELECTION_NOT_CLOSED", *tuple(結果.理由)))),
            )

        return HDS関数作用(
            "HDS継承/模型再評価",
            実行,
            出力状態=(選択閉包状態,),
            解消対象=tuple(sorted(選択残差集合 | self.入力残差非阻害対象)),
            資源負荷=2,
            優先度=10.0,
            読取成果=(参照成果名,),
            入力署名=lambda s: _参照署名(self._参照(s)),
            契約版=HDS選択継承循環版,
            作用定義ID="HDS継承/模型再評価",
        )

    def _計算計画(self):
        if self.計算実行器 is None:
            return None
        compile_compute = getattr(self.コンパイラ, "計算コンパイル", None)
        if not callable(compile_compute):
            return None
        try:
            plan = compile_compute(self.質問IR.原文)
        except (ValueError, TypeError):
            return None
        compute_ir = getattr(plan, "計算IR", None)
        if bool(getattr(plan, "参照必須", True)) or not tuple(getattr(compute_ir, "命令列", ())):
            return None
        return plan

    def _計算作用(self, 状態: HDS実行状態):
        if 残差_計算要求 not in 状態.残差 or self.計算実行器 is None:
            return None
        if bool(self._成果(状態).get(計算済み成果名, False)):
            return None
        plan = self._計算計画()
        if plan is None:
            return None

        def 実行(s: HDS実行状態):
            refs = self._参照(s)
            try:
                executed = self.計算実行器.計算実行(plan.計算IR, dict(plan.初期状態))
            except Exception as exc:
                return HDS作用結果(
                    HDS作用状態.失敗,
                    追加残差=frozenset({残差_未解}),
                    理由=("HDS_INHERITED_COMPUTE_FAILED", type(exc).__name__),
                )
            output = executed.出力
            if output is None:
                return HDS作用結果(
                    HDS作用状態.保留,
                    追加残差=frozenset({残差_未解}),
                    理由=("HDS_INHERITED_COMPUTE_OUTPUT_ABSENT",),
                )
            record = 参照記録(
                識別子="compute:" + _署名((plan.計算IR.名称, plan.計算IR.版, plan.初期状態, output)),
                対象=self.質問IR.認知世界ID or "計算対象",
                内容=f"計算結果 {output}",
                由来="MINIDORA汎用計算実行",
                供給器="MINIDORA計算実行器",
                信頼=1.0,
                意味キー="計算結果",
                値=output,
                条件=(("hds_query_kind", "compute"),),
                意味確定=True,
            )
            merged = refs if any(x.識別子 == record.識別子 for x in refs) else (*refs, record)
            return HDS作用結果(
                HDS作用状態.成立,
                解消残差=frozenset(set(s.残差).intersection({
                    残差_計算要求, 残差_観測不足, 残差_候補識別不足,
                })),
                成果=((参照成果名, tuple(merged)), (計算済み成果名, True)),
                理由=("HDS_INHERITED_COMPUTE_EXECUTED",),
            )

        return HDS関数作用(
            "HDS継承/計算",
            実行,
            解消対象=(残差_計算要求, 残差_観測不足, 残差_候補識別不足),
            資源負荷=1,
            優先度=8.0,
            読取成果=(参照成果名, 計算済み成果名),
            入力署名=lambda s: _署名((_参照署名(self._参照(s)), bool(self._成果(s).get(計算済み成果名, False)))),
            契約版=HDS選択継承循環版,
            作用定義ID="HDS継承/計算",
        )

    def _観測計画作用(self, 状態: HDS実行状態):
        if self.参照供給器 is None or not 回復可能残差.intersection(状態.残差):
            return None
        成果 = self._成果(状態)
        generation = int(成果.get(参照世代成果名, 0))
        if generation >= self.設定.最大回復回数:
            return None
        refs = self._参照(状態)
        current_sig = _参照署名(refs)
        residuals = tuple(sorted(set(状態.残差).intersection(回復可能残差)))
        主体値 = 状態.主体辞書()
        existing = 主体値.get(観測計画主体名)
        next_generation = generation + 1
        if isinstance(existing, HDS選択観測計画):
            if (
                existing.基準参照署名 == current_sig
                and existing.世代 == next_generation
                and existing.対象残差 == residuals
            ):
                return None

        def 実行(s: HDS実行状態):
            values = self._成果(s)
            refs_now = self._参照(s)
            sig = _参照署名(refs_now)
            level = int(values.get(参照世代成果名, 0)) + 1
            active = tuple(sorted(set(s.残差).intersection(回復可能残差)))
            views = self.検索IR群
            if not views:
                return HDS作用結果(
                    HDS作用状態.保留,
                    追加残差=frozenset({残差_未解}),
                    理由=("HDS_OBSERVATION_PLAN_VIEW_ABSENT",),
                )
            # 初回再検証では第二viewを優先し、その後はviewを循環させる。
            offset = 1 if 残差_再検証要求 in active and len(views) > 1 else 0
            index = (level - 1 + offset) % len(views)
            reason = []
            if 残差_再検証要求 in active:
                reason.append("REVALIDATE_PROVISIONAL_APPROVAL")
            if 残差_候補競合 in active:
                reason.append("RESOLVE_CANDIDATE_CONFLICT")
            if 残差_観測不足 in active:
                reason.append("FILL_OBSERVATION_GAP")
            if 残差_証明不足 in active:
                reason.append("STRENGTHEN_ADOPTION_PROOF")
            if 残差_観測無進展 in active:
                reason.append("CHANGE_OBSERVATION_VIEW")
            if not reason:
                reason.append("REDUCE_SELECTION_RESIDUAL")

            if 残差_観測無進展 in active:
                探索種別 = "縮退"
            elif 残差_候補競合 in active or 残差_再検証要求 in active:
                探索種別 = "候補差"
            else:
                探索種別 = "標準"
            計画 = HDS選択観測計画(
                sig, level, index, views[index], active, 探索種別, tuple(reason)
            )
            return HDS作用結果(
                HDS作用状態.成立,
                主体状態差分=((観測計画主体名, 計画),),
                理由=(
                    "HDS_LEARNING_OBSERVATION_PLAN_DERIVED",
                    f"世代:{level}",
                    f"解釈:{index}",
                    f"探索種別:{探索種別}",
                    *tuple(reason),
                ),
            )

        return HDS関数作用(
            "HDS継承/観測計画導出",
            実行,
            資源負荷=1,
            優先度=7.0,
            入力署名=lambda s: _署名((
                _参照署名(self._参照(s)),
                int(self._成果(s).get(参照世代成果名, 0)),
                tuple(sorted(set(s.残差).intersection(回復可能残差))),
                tuple(getattr(self._成果(s).get(現行結果成果名), "理由", ())),
            )),
            契約版=HDS選択継承循環版,
            作用定義ID="HDS継承/観測計画導出",
        )

    def _参照作用(self, 状態: HDS実行状態):
        if self.参照供給器 is None or not 回復可能残差.intersection(状態.残差):
            return None
        成果 = self._成果(状態)
        generation = int(成果.get(参照世代成果名, 0))
        if generation >= self.設定.最大回復回数:
            return None
        plan = 状態.主体辞書().get(観測計画主体名)
        if not isinstance(plan, HDS選択観測計画):
            return None
        if plan.基準参照署名 != _参照署名(self._参照(状態)) or plan.世代 != generation + 1:
            return None

        def 実行(s: HDS実行状態):
            values = self._成果(s)
            refs = self._参照(s)
            level = int(values.get(参照世代成果名, 0)) + 1
            current_plan = s.主体辞書().get(観測計画主体名)
            if not isinstance(current_plan, HDS選択観測計画):
                return HDS作用結果(
                    HDS作用状態.保留,
                    理由=("HDS_OBSERVATION_PLAN_ABSENT",),
                )
            observed = HDS追加参照検索(
                self.参照供給器,
                current_plan.検索IR,
                段階=level,
                探索種別=current_plan.探索種別,
            )
            履歴 = HDS参照履歴統合(self._参照履歴(s), observed)
            limit = max(len(refs), len(observed))
            merged = HDS観測窓更新(refs, observed, self.選択肢, limit)
            before = _参照署名(refs)
            after = _参照署名(merged)
            解消 = frozenset(set(s.残差).intersection(回復可能残差))
            if after == before:
                no_progress_present = 残差_観測無進展 in s.残差
                主体 = s.主体辞書()
                保持成果: list[tuple[str, object]] = [
                    (参照履歴成果名, 履歴),
                    (参照世代成果名, level),
                ]
                if 影結果主体名 in 主体:
                    保持成果.append((影結果成果名, 主体[影結果主体名]))
                if 非退行判定主体名 in 主体:
                    保持成果.append((非退行判定成果名, 主体[非退行判定主体名]))
                return HDS作用結果(
                    HDS作用状態.成立,
                    解消残差=frozenset(set(解消).difference({残差_観測無進展})),
                    追加残差=(
                        frozenset()
                        if no_progress_present
                        else frozenset({残差_観測無進展})
                    ),
                    成果=tuple(保持成果),
                    理由=("HDS_INHERITED_REFERENCE_NO_PROGRESS", f"履歴件数:{len(履歴)}"),
                )
            return HDS作用結果(
                HDS作用状態.成立,
                解消残差=解消,
                成果=(
                    (参照成果名, tuple(merged)),
                    (参照履歴成果名, 履歴),
                    (参照世代成果名, level),
                ),
                理由=(
                    "HDS_INHERITED_REFERENCE_WINDOW_UPDATED",
                    f"世代:{level}",
                    f"評価窓:{len(merged)}",
                    f"履歴件数:{len(履歴)}",
                ),
            )

        return HDS関数作用(
            "HDS継承/追加参照",
            実行,
            解消対象=tuple(sorted(回復可能残差)),
            資源負荷=4,
            優先度=6.0,
            読取成果=(参照成果名, 参照履歴成果名, 参照世代成果名),
            入力署名=lambda s: _署名((
                _参照署名(self._参照(s)),
                _参照署名(self._参照履歴(s)),
                int(self._成果(s).get(参照世代成果名, 0)),
                s.主体辞書().get(観測計画主体名),
                s.主体辞書().get(影結果主体名),
                s.主体辞書().get(非退行判定主体名),
            )),
            契約版=HDS選択継承循環版,
            作用定義ID="HDS継承/追加参照",
        )

    def 構成(self, 状態: HDS実行状態):
        評価 = self._評価作用(状態)
        if 評価 is not None:
            return (評価,)
        計算 = self._計算作用(状態)
        観測計画 = self._観測計画作用(状態)
        参照 = self._参照作用(状態)
        return tuple(x for x in (計算, 観測計画, 参照) if x is not None)


__all__ = [
    "HDS選択継承循環版",
    "HDS選択継承設定",
    "HDS選択継承供給",
    "参照成果名",
    "参照履歴成果名",
    "参照世代成果名",
    "計算済み成果名",
    "基準結果主体名",
    "現行結果成果名",
    "評価参照署名成果名",
    "非退行判定成果名",
    "影結果成果名",
    "回答成果名",
    "入力残差影成果名",
    "観測計画主体名",
    "影結果主体名",
    "非退行判定主体名",
    "HDS選択観測計画",
    "選択閉包状態",
    "残差_未評価",
    "残差_再検証要求",
]
