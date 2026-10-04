from __future__ import annotations

from dataclasses import dataclass, replace
from .参照 import 参照全保持を統合
from time import perf_counter_ns, process_time_ns
from .統合駆動_v2.計画 import HDS作用仕様, HDS探索契約
from typing import Callable, Sequence

from .HDS実行主体 import HDS実行状態, HDS作用結果, HDS作用状態, HDS関数作用
from .HDS構文化処理系列_v1_4 import HDSカーネル束
from .HDS観測計画 import (
    HDS追加観測要求群,
    HDS候補関係観測計画,
    HDS候補関係観測計画を構成,
)
from .HDS選択実行系 import HDS選択実行結果, HDS選択推論実行
from .HDS非退行包絡 import HDS非退行包絡, HDS証拠優越包絡
from .HDS既存能力継承 import HDS既存能力結果証明済み, HDS既存能力選択評価, HDS既存能力直接反証評価
from .HDS模型射影 import HDS内部言語状態
from .HDS選択仮説 import HDS候補代入仮説群
from .能力作用則 import 証拠状態照合
from .hds入力参照境界 import HDS入力資料本文
from .hds参照拡張 import HDS候補被覆優先統合, HDS追加参照統合上限, HDS追加参照検索, HDS参照検索強化
from .参照 import 参照供給器, 参照記録, 参照取得診断, 参照記録群を統合
from .模型 import MINIDORA模型核
from .能力状態差循環 import 標準能力模型核
from .計算実行器 import 計算実行器
from .コア.値 import 署名 as _意味署名

@dataclass(frozen=True, slots=True)
class HDS関係選択結果(HDS選択実行結果):
    関係証明: object = None


HDS選択継承循環版 = "HDS-MINIDORA-SELECTION-INHERITANCE-v12-purpose-relations"

参照成果名 = "HDS選択:参照"
参照世代成果名 = "HDS選択:参照世代"
計算済み成果名 = "HDS選択:計算済み"
基準結果主体名 = "HDS選択:基準結果"
現行結果成果名 = "HDS選択:現行結果"
評価参照署名成果名 = "HDS選択:評価参照署名"
評価観測署名成果名 = "HDS選択:評価観測署名"
初回評価参照成果名 = "HDS選択:初回評価参照"
非退行判定成果名 = "HDS選択:非退行判定"
影結果成果名 = "HDS選択:影結果"
回答成果名 = "HDS選択:回答ラベル"
入力残差影成果名 = "HDS選択:入力残差影"
選択閉包状態 = "HDS選択:閉包"
参照記憶成果名 = "HDS選択:参照記憶"
参照取得診断成果名 = "HDS選択:参照取得診断"
関係観測消費成果名 = "HDS選択:関係観測消費"
関係観測世代成果名 = "HDS選択:関係観測世代"
採用監査成果名 = "HDS選択:採用監査"

残差_未評価 = "HDS選択:未評価"
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
残差_基準反証検証 = "HDS選択:基準反証検証"  # 旧公開名互換。active pathでは生成しない。
残差_数量法則不足 = "HDS選択:数量法則不足"
残差_参照取得障害 = "HDS選択:参照取得障害"
残差_候補証拠未閉包 = "HDS選択:候補証拠未閉包"
残差_候補証拠矛盾 = "HDS選択:候補証拠矛盾"

選択残差集合 = frozenset({
    残差_未評価, 残差_観測不足, 残差_問題意味損失, 残差_候補意味損失,
    残差_資料意味損失, 残差_候補競合, 残差_候補識別不足, 残差_状態差未消費,
    残差_計算要求, 残差_未解, 残差_証明不足, 残差_観測無進展,
    残差_数量法則不足, 残差_参照取得障害, 残差_候補証拠未閉包, 残差_候補証拠矛盾,
})
回復可能残差 = frozenset({
    残差_観測不足, 残差_資料意味損失, 残差_候補競合, 残差_候補識別不足,
    残差_数量法則不足, 残差_証明不足, 残差_観測無進展, 残差_未解,
    残差_参照取得障害, 残差_候補証拠未閉包, 残差_候補証拠矛盾,
})


def _署名(値: object) -> str:
    return _意味署名(値)


def _参照署名(参照群: Sequence[参照記録]) -> str:
    # 本文・対象・時点・範囲・証拠境界の変更を再評価へ反映する。
    return _署名(tuple(参照群))


def _型付き関係承認(結果: object) -> bool:
    from .駆動系.選択関係 import 選択関係結果
    return bool(isinstance(結果, HDS関係選択結果)
                and isinstance(結果.関係証明, 選択関係結果)
                and 結果.関係証明.一意成立 == 結果.回答ラベル)


def _旧直接根拠承認(結果: object) -> bool:
    if not (_承認済み(結果) and getattr(結果, "回答内容", None) is not None):
        return False
    if "DIRECTED_関係_VERIFIED" in tuple(getattr(結果, "理由", ())):
        return True
    K3結果 = getattr(結果, "K3結果", None)
    if K3結果 is not None and int(getattr(K3結果, "根拠事実数", 0)) > 0:
        return True
    return int(getattr(結果, "K証拠事実数", 0)) > 0


def _根拠付き承認(結果: object) -> bool:
    return bool(_型付き関係承認(結果) or _旧直接根拠承認(結果))


def _暫定採用可能(結果: object) -> bool:
    return bool(_承認済み(結果) and getattr(結果, "回答内容", None) is not None
                and HDS既存能力結果証明済み(結果))


def _承認済み(結果: object) -> bool:
    return bool(
        isinstance(結果, HDS選択実行結果)
        and 結果.状態 == "APPROVE"
        and 結果.回答ラベル is not None
    )


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
        "NO_KNOWLEDGE_証拠", "NO_KNOWLEDGE_EVIDENCE", "NO_候補", "NO_CANDIDATE",
        "MINIDORA_OUTPUT_ABSENT", "NO_GUESS", "証拠_INSUFFICIENT", "EVIDENCE_INSUFFICIENT",
        "MINIDORA_模型_模型核_NO_参照_CONTRIBUTION", "MINIDORA_MODEL_CORE_NO_REFERENCE_CONTRIBUTION",
    )):
        out.add(残差_観測不足)
    if any(x in joined for x in (
        "AMBIGUOUS_証拠", "AMBIGUOUS_EVIDENCE", "EXCEPTION_NOT_RESOLVED",
        "参照_DIFFERENCE_NOT_UNIQUE", "REFERENCE_DIFFERENCE_NOT_UNIQUE",
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
    if _根拠付き承認(基準) or not _根拠付き承認(拡張) or 初期参照署名 == 現在参照署名:
        return False
    return True


def _観測要求鍵(要求) -> str:
    return _署名((
        str(getattr(要求, "候補ラベル", "")),
        str(getattr(要求, "関係種別", "")),
        str(getattr(要求, "外部検索表層", "")).casefold(),
    ))


def _候補対象関係群(question_ir: object, 候補意味IR, label: str) -> tuple[object, ...]:
    if not 候補意味IR:
        return ()
    hypotheses = HDS候補代入仮説群(question_ir, 候補意味IR)
    候補IR = hypotheses.get(str(label))
    if 候補IR is None:
        return ()
    対象言語体系 = (
        "自然言語:ja"
        if str(getattr(question_ir, "入力言語", "ja") or "ja").casefold().startswith("ja")
        else "自然言語:en"
    )
    out: list[object] = []
    for 関係 in tuple(getattr(候補IR, "関係", ())):
        if str(getattr(関係, "由来", "")) != "HDS候補代入仮説":
            continue
        projected = HDS内部言語状態(
            replace(候補IR, 関係=(関係,)),
            識別子=f"候補証拠:{label}:{getattr(関係, '関係ID', '')}",
            言語体系=対象言語体系,
        )
        out.extend(tuple(projected.関係構造))
    return tuple(out)


def _候補証拠優越(
    question_ir: object,
    候補意味IR,
    結果: object,
    *,
    基準ラベル: str,
    新ラベル: str,
    最小独立支持数: int = 2,
) -> bool:
    """回答変更の採否だけを証拠で監査する。学習開始条件には使わない。"""
    if not 候補意味IR or str(基準ラベル) == str(新ラベル):
        return False
    模型 = getattr(結果, "MINIDORA模型結果", None)
    文脈 = getattr(模型, "文脈", None)
    if 文脈 is None:
        return False
    new_targets = _候補対象関係群(question_ir, 候補意味IR, str(新ラベル))
    old_targets = _候補対象関係群(question_ir, 候補意味IR, str(基準ラベル))
    if not new_targets or not old_targets:
        return False
    new_support = new_refute = old_refute = 0
    出典集合 = set()
    内容集合 = set()
    for ref in tuple(getattr(文脈, "参照状態", ())):
        if not bool(getattr(ref, "証拠利用可", False)):
            continue
        relations = tuple(getattr(ref, "関係構造", ()))
        出典鍵 = str(getattr(ref, "識別子", "")) or _署名(relations)
        内容鍵 = _署名(relations)
        if 出典鍵 in 出典集合 or 内容鍵 in 内容集合: continue
        出典集合.add(出典鍵)
        内容集合.add(内容鍵)
        新状態 = 証拠状態照合(new_targets, relations)
        旧状態 = 証拠状態照合(old_targets, relations)
        if bool(getattr(新状態, "完全支持", False)) and not int(getattr(新状態, "反証", 0)) and not int(getattr(新状態, "矛盾", 0)):
            new_support += 1
        if int(getattr(新状態, "反証", 0)) > 0 or int(getattr(新状態, "矛盾", 0)) > 0:
            new_refute += 1
        if int(getattr(旧状態, "反証", 0)) > 0 or int(getattr(旧状態, "矛盾", 0)) > 0:
            old_refute += 1
    return new_support >= 最小独立支持数 and new_refute == 0 and old_refute >= 1


@dataclass(frozen=True, slots=True)
class HDS選択継承設定:
    最大回復回数: int = 6

    def __post_init__(self) -> None:
        if type(self.最大回復回数) is not int or not 0 <= self.最大回復回数 <= 64:
            raise ValueError("最大回復回数は0..64の整数である必要がある")


class HDS選択継承供給:
    """現在状態から観測不足を推論し、同じ通常循環へ適応してから選択評価する。"""

    def __init__(
        self,
        カーネル束: HDSカーネル束,
        コンパイラ,
        初期参照: Sequence[参照記録],
        *,
        模型核: MINIDORA模型核 | None = None,
        基礎能力核=None,
        既存能力継承: bool = True,
        参照供給器: 参照供給器 | None = None,
        計算実行器_: 計算実行器 | None = None,
        設定: HDS選択継承設定 | None = None,
        拡張採用証明: Callable[[HDS選択実行結果, HDS選択実行結果], bool] | None = None,
        入力残差非阻害対象: Sequence[str] = (),
        意味変換契約=(), 関係学習状態=None,
    ) -> None:
        if not isinstance(カーネル束, HDSカーネル束):
            raise TypeError("選択継承循環にはHDSカーネル束が必要")
        self.カーネル束 = カーネル束
        self.質問IR = カーネル束.意味IR
        self.参照観測要求 = tuple(カーネル束.参照観測要求)
        self.候補意味IR = カーネル束.候補意味IR辞書 or None
        self.数量計算契約 = カーネル束.数量計算契約
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
            for x in self.質問IR.座標
            if x.座標ID.startswith("選択肢:")
        )
        self._計算降下済み = None
        from .駆動系.学習 import 関係学習状態 as 学習型
        self.意味変換契約 = tuple(意味変換契約)
        self.関係学習状態 = 関係学習状態 or 学習型()

    @staticmethod
    def _成果(状態: HDS実行状態) -> dict[str, object]:
        # 読取専用。状態は不変データ契約であり、全成果のdeepcopyを毎作用で繰り返さない。
        return {k: v for k, v in 状態.成果 if k.startswith("HDS選択:")}

    def _参照(self, 状態: HDS実行状態) -> tuple[参照記録, ...]:
        value = self._成果(状態).get(参照成果名, self.初期参照)
        if not isinstance(value, tuple) or any(not isinstance(x, 参照記録) for x in value):
            raise TypeError("HDS選択の参照成果は参照記録tupleである必要がある")
        return value

    def _評価(self, 参照群: tuple[参照記録, ...]) -> HDS選択実行結果:
        compile_fn = self._共通構文化()
        if not callable(compile_fn):
            raise TypeError("選択継承循環には外部資料をコンパイル可能なHDSコンパイラが必要")
        if not self.既存能力継承:
            return HDS選択推論実行(
                self.質問IR, 参照群, コンパイル=compile_fn, 基礎能力核=None,
                候補意味IR=self.候補意味IR, 模型核=self.模型核, 正式模型評価=True,
            )
        return HDS既存能力選択評価(
            self.質問IR, 参照群, コンパイル=compile_fn, 模型核=self.模型核,
            基礎能力核=self.基礎能力核, 候補意味IR=self.候補意味IR,
        )

    def _共通構文化(self):
        from .コア.構文化再利用 import 構文化再利用
        共有 = getattr(self, "_共有構文化", None)
        元 = getattr(self, "_共有構文化元", None)
        if 共有 is None or 元 is not self.コンパイラ:
            対象 = self.コンパイラ
            if hasattr(対象, "構文化文脈署名"):
                適合器 = 対象
            else:
                # 汎用cacheは明示文脈がない解析器を再利用しない。
                # 選択循環では同一供給器内のCompiler実装・版を明示文脈として固定する。
                class 選択構文化文脈:
                    def __init__(self, 本体): self.本体 = 本体
                    def コンパイル(self, 本文): return self.本体.コンパイル(本文)
                    def 構文化文脈署名(self):
                        関数 = getattr(self.本体, "コンパイル", None)
                        実体 = getattr(関数, "__func__", 関数)
                        return (type(self.本体).__module__, type(self.本体).__qualname__,
                                id(実体), str(getattr(self.本体, "版", "")),
                                str(getattr(self.本体, "構造版", "")),
                                str(getattr(self.本体, "処理系列版", "")))
                適合器 = 選択構文化文脈(対象)
            共有 = 構文化再利用(適合器)
            self._共有構文化 = 共有
            self._共有構文化元 = 対象
        return 共有

    def _資料IR群(self, 参照群):
        共有 = self._共通構文化()
        出力, 診断 = [], []
        for 記録 in 参照群:
            try: 出力.append(共有(HDS入力資料本文(記録)))
            except Exception as 例外:
                診断.append((str(記録.識別子), type(例外).__name__ + ": " + str(例外)))
        self._資料診断 = tuple(診断)
        self._構文化実行数, self._構文化再利用数, self._構文化時間ns = 共有.実行数, 共有.再利用数, 共有.時間ns
        return tuple(出力)

    def _関係観測計画(self, 参照群: tuple[参照記録, ...]) -> HDS候補関係観測計画:
        資料群 = self._資料IR群(参照群)
        鍵 = _署名((self.質問IR, self.候補意味IR, 資料群))
        if getattr(self, "_関係計画鍵", None) != 鍵:
            self._関係計画値 = HDS候補関係観測計画を構成(self.質問IR, self.候補意味IR, 資料群)
            self._関係計画鍵 = 鍵
        return self._関係計画値

    def _選択反転(self):
        意図 = {str(c).split("=", 1)[1] for x in getattr(self.質問IR, "関係", ())
                for c in getattr(x, "条件", ()) if str(c).startswith("選択意図=")}
        if "反転" in 意図 and "通常" in 意図: raise ValueError("選択意図が競合")
        return "反転" in 意図

    def _目的関係評価(self, 参照群):
        from .駆動系.選択関係 import 選択関係を評価
        from .駆動系.学習 import 関係学習状態
        言語 = "自然言語:ja" if str(getattr(self.質問IR, "入力言語", "ja")).casefold().startswith("ja") else "自然言語:en"
        観測 = []
        # 失敗した構文化を抜いた順序から出典を推定せず、個々の資料を対応させる。
        for 記録 in 参照群:
            for IR in self._資料IR群((記録,)):
                状態 = HDS内部言語状態(IR, 識別子=str(記録.識別子), 言語体系=言語, 証拠境界=True)
                if 状態.証拠利用可:
                    観測.append((str(記録.識別子) or _署名(記録), tuple(状態.関係構造)))
        self._今回観測関係 = tuple(観測)
        対象 = tuple((ラベル, _候補対象関係群(self.質問IR, self.候補意味IR, ラベル)) for ラベル in self.選択肢)
        return 選択関係を評価("選択目的:" + _署名(self.質問IR)[:24], self.質問IR.認知世界ID,
            対象, tuple(観測), 変換=getattr(self, "意味変換契約", ()),
            学習状態=getattr(self, "関係学習状態", 関係学習状態()),反転=self._選択反転())

    def _認識へ射影(self, 状態, 参照群):
        from .統合駆動_v2.記憶 import HDS資料
        from .統合駆動_v2.認識 import HDS認識項目, 認識区分
        from .駆動系.選択関係 import 言語関係を節へ
        資料辞書 = {}
        for 記録 in 参照群:
            if not str(記録.内容).strip(): continue
            ID = "参照記憶:" + str(記録.識別子 or _署名(記録))
            資料辞書[str(記録.識別子) or _署名(記録)] = HDS資料(ID,
                _署名((記録.内容, 記録.対象, 記録.範囲, 記録.時点)), str(記録.内容),
                str(記録.由来 or 記録.供給器), str(記録.時点 or "未指定"))
        認識 = []
        for 出典, 関係群 in getattr(self, "_今回観測関係", ()):
            資料 = 資料辞書.get(出典)
            if 資料 is None: continue
            for 項 in 関係群:
                try:
                    節 = 言語関係を節へ(項)
                except (TypeError, ValueError):
                    continue
                # 確認できたのは資料に記述された関係。世界の真理・一般法則へ昇格しない。
                認識.append(HDS認識項目("資料関係:" + _署名((資料.ID, 節))[:24],
                    資料.ID, "観測された記述関係",
                    (節.述語, tuple((役割, 項.名前, 項.型, 項.単位, 項.変数, 項.束縛域) for 役割, 項 in 節.引数),
                     節.肯定, 節.条件, 節.範囲, 節.時点, 節.様相, 節.量化), 認識区分.確定,
                    根拠=(資料.出典(),), 範囲="資料記述", 時点=資料.時点,
                    検証契約="既存Compiler関係の由来付き射影-v1"))
        記憶 = 状態.記憶.更新(tuple(資料辞書.values())) if 資料辞書 else None
        return tuple({x.ID: x for x in 認識}.values()), 記憶

    def _順位根拠(self, 結果):
        模型 = getattr(結果, "MINIDORA模型結果", None)
        辞書化 = getattr(模型, "参照候補辞書", None)
        得点 = dict(辞書化()) if callable(辞書化) else {}
        return {"候補差": tuple(sorted(得点.items())), "保証": "相対候補順位。関係証明ではない",
            "寄与": tuple(getattr(模型, "候補差", ()))}

    def _観測状態署名(self, 状態):
        値 = self._成果(状態)
        return _署名((int(値.get(参照世代成果名, 0)), int(値.get(関係観測世代成果名, 0)),
                      tuple(値.get(関係観測消費成果名, ())), bool(値.get(計算済み成果名, False))))

    def _必要観測(self, 状態, 判定, 結果):
        if self.参照供給器 is None or self.設定.最大回復回数 == 0: return ()
        値 = self._成果(状態)
        if int(値.get(関係観測世代成果名, 0)) >= self.設定.最大回復回数: return ()
        不足候補 = {x.ラベル for x in 判定.候補 if x.状態 in ("未観測", "競合", "対象未構成")}
        # 一意の暫定候補がある場合は、その採否に必要な関係の検証から始める。
        if _承認済み(結果) and 結果.回答ラベル in 不足候補:
            不足候補 = {結果.回答ラベル}
        if not 不足候補: return ()
        消費 = set(値.get(関係観測消費成果名, ()))
        from .入力系.不足観測 import 不足から観測要求
        動的 = []
        動的候補 = set()
        for 候補 in 判定.候補:
            if 候補.ラベル not in 不足候補: continue
            for 不足 in 候補.不足:
                if 不足.状態 in ("停止", "予算未完了"): continue
                動的候補.add(候補.ラベル)
                要求 = 不足から観測要求(不足, 候補ラベル=候補.ラベル,
                    言語=str(getattr(self.質問IR, "入力言語", "ja")))
                if _観測要求鍵(要求) not in 消費: 動的.append(要求)
        # 型付き不足を導出できた候補は、その関係を先に観測する。
        # 元の静的要求は保持し、意味関係を未構成の候補だけの接続に使う。
        静的 = ()
        if 不足候補 - 動的候補:
            計画 = self._関係観測計画(self._参照(状態))
            静的 = tuple(x for x in 計画.観測要求
                if getattr(x, "候補ラベル", None) in 不足候補 - 動的候補
                and _観測要求鍵(x) not in 消費)
        return tuple(動的) + 静的

    def _品質残差(self, 状態, 参照群, 結果=None) -> frozenset[str]:
        """根拠成立は既存評価器、反証監査は採用する候補に限定する。"""
        if not _暫定採用可能(結果) or str(結果.回答ラベル) not in self.選択肢:
            return frozenset({残差_証明不足})
        if (isinstance(結果, HDS関係選択結果)
                and 結果.関係証明 is getattr(self, "_現在関係判定", None)
                and 結果.関係証明.一意成立 == 結果.回答ラベル):
            return frozenset()
        対象 = _候補対象関係群(self.質問IR, self.候補意味IR, str(結果.回答ラベル))
        if not 対象:
            # 旧能力の採用可否と、対象関係を証明できたことを混同しない。
            return frozenset()
        証拠 = []
        言語 = "自然言語:ja" if str(getattr(self.質問IR, "入力言語", "ja")).casefold().startswith("ja") else "自然言語:en"
        for 番号, 資料 in enumerate(self._資料IR群(tuple(参照群))):
            値 = HDS内部言語状態(資料, 識別子=f"採用監査:{番号}", 言語体系=言語, 証拠境界=True)
            if 値.証拠利用可:
                証拠.extend(値.関係構造)
        照合 = 証拠状態照合(対象, tuple(証拠))
        阻害 = (bool(getattr(照合, "完全支持", False)) if self._選択反転() else bool(getattr(照合, "反証", 0)))
        if 阻害 or int(getattr(照合, "矛盾", 0)):
            return frozenset({残差_候補証拠矛盾})
        # 未観測の他候補や任意取得失敗は、成立済み回答の反証ではない。
        return frozenset()

    def _基準資料を照合(self, 状態, 現参照):
        原資料 = self._成果(状態).get(初回評価参照成果名, self.初期参照)
        原資料 = 原資料 if isinstance(原資料, tuple) else self.初期参照
        def 鍵(記録):
            return (str(記録.供給器), str(記録.識別子))
        def 内容署名(記録):
            条件 = tuple((k, v) for k, v in 記録.条件 if not str(k).startswith("hds_"))
            return _署名((記録.対象, 記録.内容, 記録.由来, 記録.信頼, 記録.意味キー, 記録.値,
                          記録.時点, 記録.範囲, 条件, 記録.意味確定))
        元 = {鍵(x): x for x in 原資料}
        現 = {鍵(x): x for x in 現参照}
        訂正 = any(k in 現 and 内容署名(v) != 内容署名(現[k]) for k, v in 元.items())
        元.update(現)
        return 訂正, tuple(元.values())

    def _操作仕様(self, ID, *, 生成=(), 観測入力=(), 読取成果=(), 解消=(), 探索=None, 資源=1):
        評価作用 = ID == "HDS継承/模型再評価"
        return HDS作用仕様(ID,
            追加状態=frozenset({選択閉包状態}) if 評価作用 else frozenset(),
            解消残差=frozenset(解消), 生成成果=tuple(生成), 観測入力=tuple(観測入力), 読取成果=tuple(読取成果),
            目的依存=(("状態:" + 選択閉包状態,) if 評価作用 else ()),
            資源負荷=資源, 版=HDS選択継承循環版, 観測専用=探索 is not None, 探索=探索, 入力不変保証=True)

    def _観測探索(self, ID):
        return HDS探索契約(ID, "選択を成立させる関係・証拠の不足を観測する",
            ("成果:" + 参照成果名,), ("状態:" + 選択閉包状態,),
            最大試行=self.設定.最大回復回数, 最大資源=4 * self.設定.最大回復回数, 再観測=True)

    @staticmethod
    def _取得障害(診断群: Sequence[参照取得診断]) -> bool:
        return any(x.状態 in {"失敗", "縮退"} for x in 診断群)

    @staticmethod
    def _診断成果(values: dict[str, object], 診断群: Sequence[参照取得診断]):
        existing = values.get(参照取得診断成果名, ())
        if not isinstance(existing, tuple) or any(not isinstance(x, 参照取得診断) for x in existing):
            existing = ()
        return (参照取得診断成果名, tuple((*existing, *tuple(診断群))))

    def _関係観測作用(self, 状態: HDS実行状態):
        if self.参照供給器 is None:
            return None
        values = self._成果(状態)
        generation = int(values.get(関係観測世代成果名, 0))
        if generation >= self.設定.最大回復回数:
            return None
        refs = self._参照(状態)
        if values.get(評価参照署名成果名) != _参照署名(refs):
            return None
        if values.get(評価観測署名成果名) != self._観測状態署名(状態): return None
        判定 = values.get("HDS選択:目的関係判定")
        if 判定 is None: return None
        必要 = self._必要観測(状態, 判定, values.get(現行結果成果名))
        plan = HDS候補関係観測計画(必要, len(必要), 0)
        consumed_raw = values.get(関係観測消費成果名, ())
        consumed = set(str(x) for x in consumed_raw if str(x)) if isinstance(consumed_raw, tuple) else set()
        pending = tuple(x for x in plan.観測要求 if _観測要求鍵(x) not in consumed)
        if not pending:
            return None
        優先度 = min(int(x.優先度) for x in pending)
        selected = tuple(x for x in pending if int(x.優先度) == 優先度)

        def 実行(s: HDS実行状態):
            current_values = self._成果(s)
            current_refs = self._参照(s)
            level = int(current_values.get(関係観測世代成果名, 0)) + 1
            diagnostics: list[参照取得診断] = []
            observed = HDS参照検索強化(
                self.参照供給器,
                self.質問IR,
                上限=min(32, max(8, len(selected) * 4)),
                一問合せ上限=4,
                観測要求=selected,
                診断収集=diagnostics,
            )
            memory_raw = current_values.get(参照記憶成果名, current_refs)
            memory = 参照全保持を統合(memory_raw if isinstance(memory_raw, tuple) else current_refs, observed)
            limit = HDS追加参照統合上限(len(current_refs), len(observed))
            merged = HDS候補被覆優先統合(observed, current_refs, self.選択肢, limit)
            before = _参照署名(current_refs)
            after = _参照署名(merged)
            diag_out = self._診断成果(current_values, diagnostics)
            transport_bad = self._取得障害(diagnostics)

            old_consumed = current_values.get(関係観測消費成果名, ())
            old_consumed = tuple(str(x) for x in old_consumed if str(x)) if isinstance(old_consumed, tuple) else ()
            new_consumed = tuple(dict.fromkeys((*old_consumed, *(_観測要求鍵(x) for x in selected))))

            outputs = [
                (関係観測世代成果名, level),
                (参照記憶成果名, memory),
                diag_out,
            ]
            if after != before:
                outputs.append((参照成果名, tuple(merged)))
            # 観測した要求は成功・部分失敗を問わず消費済みにする。
            # 子供給器の制限・再試行時点は参照取得側が管理し、全検索を巻き戻さない。
            outputs.append((関係観測消費成果名, new_consumed))

            clearable = {残差_参照取得障害} if (not transport_bad and 残差_参照取得障害 in s.残差) else set()
            add = {残差_参照取得障害} if transport_bad else set()
            reason = (
                "HDS_CANDIDATE_RELATION_OBSERVATION_ADAPTED"
                if after != before else
                "HDS_CANDIDATE_RELATION_OBSERVATION_NO_PROGRESS"
            )
            if transport_bad:
                reason += "_WITH_TRANSPORT_DEGRADED"
            return HDS作用結果(
                HDS作用状態.成立,
                解消残差=frozenset(clearable),
                追加残差=frozenset(add.difference(s.残差)),
                成果=tuple(outputs),
                理由=(reason, f"関係観測世代:{level}", f"観測方法優先度:{優先度}", f"件数:{len(merged)}"),
            )

        return HDS関数作用(
            "HDS継承/候補関係観測",
            実行,
            解消対象=tuple(sorted({
                残差_観測不足, 残差_候補証拠未閉包,
                残差_候補証拠矛盾, 残差_観測無進展, 残差_参照取得障害,
            })),
            資源負荷=4,
            優先度=12.0,
            読取成果=(),
            入力署名=lambda s: _署名((
                _参照署名(self._参照(s)),
                int(self._成果(s).get(関係観測世代成果名, 0)),
                tuple(self._成果(s).get(関係観測消費成果名, ())),
            )),
            契約版=HDS選択継承循環版,
            作用定義ID="HDS継承/候補関係観測",
            計画仕様=self._操作仕様("HDS継承/候補関係観測",
                生成=(参照成果名, 関係観測世代成果名, 参照記憶成果名, 参照取得診断成果名),
                観測入力=("成果:" + 参照成果名,),
                探索=self._観測探索("HDS継承/候補関係観測探索"), 資源=4),
        )

    def _評価作用(self, 状態: HDS実行状態):
        値 = self._成果(状態)
        # 評価署名だけが残っていても、評価の必須成果である現行結果が失効済みなら
        # 「評価済み」とは扱わない。同じ通常循環で再評価を供給して成果を再構成する。
        現行 = 値.get(現行結果成果名)
        if (isinstance(現行, HDS選択実行結果)
                and 値.get(評価参照署名成果名) == _参照署名(self._参照(状態))
                and 値.get(評価観測署名成果名) == self._観測状態署名(状態)):
            return None

        def 実行(s: HDS実行状態):
            参照群 = self._参照(s)
            現署名 = _参照署名(参照群)
            開始 = perf_counter_ns()
            CPU開始 = process_time_ns()
            結果 = self._評価(参照群)
            関係判定 = self._目的関係評価(参照群)
            self._現在関係判定 = 関係判定
            構造ラベル = 関係判定.一意成立
            if 構造ラベル is not None:
                # 既存結果型と説明情報を保持し、証明された関係から回答候補を形成する。
                候補座標 = next((x for x in self.質問IR.座標 if x.座標ID == "選択肢:" + 構造ラベル), None)
                if 候補座標 is None: raise ValueError("関係出力の候補対応が不存在")
                from dataclasses import fields
                引数 = {x.name: getattr(結果, x.name) for x in fields(HDS選択実行結果)}
                引数.update(状態="APPROVE", 回答ラベル=構造ラベル, 回答内容=str(候補座標.内容),
                    理由=tuple(dict.fromkeys((*結果.理由, "HDS_TYPED_RELATION_PROVED"))))
                結果 = HDS関係選択結果(**引数, 関係証明=関係判定)
            評価時間 = perf_counter_ns() - 開始
            self._累積評価時間ns = getattr(self, "_累積評価時間ns", 0) + 評価時間
            self._累積評価CPU時間ns = getattr(self, "_累積評価CPU時間ns", 0) + process_time_ns() - CPU開始
            値 = self._成果(s)
            基準 = s.主体辞書().get(基準結果主体名)
            初回 = not isinstance(基準, HDS選択実行結果)
            基準差分 = ()
            if 初回:
                基準 = 結果
                基準差分 = ((基準結果主体名, 基準),)
            選択解消 = frozenset(set(s.残差).intersection(選択残差集合))
            入力解消 = frozenset(set(s.残差).intersection(self.入力残差非阻害対象))
            出力 = {現行結果成果名: 結果, 評価参照署名成果名: 現署名,
                    評価観測署名成果名: self._観測状態署名(s)}
            カーネル = getattr(self, "カーネル束", None)
            コア入力 = getattr(カーネル, "コア入力", None)
            入力残差正本 = tuple(getattr(コア入力, "残差", ()))
            if 入力残差正本:
                # 入力由来の未解消事項は、非阻害化しなくても監査影として必ず保持する。
                出力[入力残差影成果名] = 入力残差正本
            if 初回:
                出力[初回評価参照成果名] = 参照群
            訂正, 基準資料 = self._基準資料を照合(s, 参照群)
            基準阻害 = self._品質残差(s, 基準資料, 基準)
            現行阻害 = self._品質残差(s, 参照群, 結果)
            採用, 判定, 理由 = None, None, ()
            認識射影, 記憶射影 = self._認識へ射影(s, 参照群)
            候補判定 = {x.ラベル: x for x in 関係判定.候補}
            基準関係 = 候補判定.get(str(getattr(基準, "回答ラベル", "")))
            基準強証明 = (_根拠付き承認(基準) and not 基準阻害 and not 訂正)
            if 構造ラベル is not None and not 現行阻害 and not 基準強証明:
                証明可 = self.拡張採用証明 is None or bool(self.拡張採用証明(基準, 結果))
                if 証明可:
                    判定 = HDS非退行包絡(基準, 基準承認判定=lambda _前: False,
                        拡張実行=lambda: 結果, 拡張承認判定=_根拠付き承認,
                        拡張採用証明=lambda _前, _後: 関係判定.一意成立 == _後.回答ラベル)
                    if 判定.拡張採用: 採用, 理由 = 結果, ("HDS_PURPOSE_RELATION_ADOPTED",)
            # 相対順位しかない基準を、将来の関係証明より上位へ固定しない。
            if 採用 is None and _暫定採用可能(基準) and not 初回 and 現署名 != self.初期参照署名:
                反証 = HDS既存能力直接反証評価(
                    self.質問IR, 参照群, コンパイル=self._共通構文化(),
                    基礎能力核=self.基礎能力核, 候補意味IR=self.候補意味IR,
                    基準ラベル=str(基準.回答ラベル), 最小独立証拠数=2)
                if 反証 is not None and not self._品質残差(s, 参照群, 反証):
                    採用, 理由 = 反証, ("HDS_DIRECT_COUNTEREVIDENCE_REVERIFIED",)
                elif not 現行阻害 and 結果.回答ラベル != 基準.回答ラベル and _候補証拠優越(
                    self.質問IR, self.候補意味IR, 結果, 基準ラベル=str(基準.回答ラベル),
                    新ラベル=str(結果.回答ラベル), 最小独立支持数=2):
                    採用, 理由 = 結果, ("HDS_SUPERIOR_EVIDENCE_ADOPTED",)
                if 採用 is not None:
                    判定 = HDS証拠優越包絡(基準, 採用, 基準承認判定=_根拠付き承認,
                        拡張承認判定=_根拠付き承認, 証拠優越証明=lambda _前, _後: True)
            # 新しい関係観測は既存能力を上書きする根拠ではない。明示反証・訂正がない限り、
            # 既存MINIDORAが一意閉包した基準回答を非退行で保持する。
            if 採用 is None and _暫定採用可能(基準) and not 基準阻害 and not 訂正:
                採用, 理由 = 基準, ("HDS_BASELINE_APPROVAL_KEPT", "HDS_MINIDORA_CANONICAL_INHERITED")
            elif 採用 is None and not 基準強証明 and not 現行阻害 and 現署名 != self.初期参照署名:
                # 相対順位の更新は真理保証の昇格ではない。証明を拒否した場合も
                # 候補は影結果として監査保存し、採用だけを止める。
                追加証明 = self.拡張採用証明 is None or bool(self.拡張採用証明(基準, 結果))
                判定 = HDS非退行包絡(基準, 基準承認判定=lambda _前: False,
                    拡張実行=lambda: 結果, 拡張承認判定=_根拠付き承認,
                    拡張採用証明=lambda _前, _後: bool(追加証明 and 現署名 != self.初期参照署名 and not 現行阻害))
                if 判定.拡張採用: 採用, 理由 = 結果, ("HDS_TENTATIVE_SELECTION_REVISED",)
            elif 採用 is None and 訂正 and not 現行阻害 and 結果.回答ラベル == 基準.回答ラベル:
                採用, 理由 = 結果, ("HDS_BASELINE_EVIDENCE_REVALIDATED",)
            elif 採用 is None and not _根拠付き承認(基準) and not 現行阻害 and not 初回:
                証明 = bool(self.拡張採用証明(基準, 結果)) if self.拡張採用証明 is not None else _標準追加採用証明(
                    基準, 結果, 初期参照署名=self.初期参照署名, 現在参照署名=現署名)
                判定 = HDS非退行包絡(基準, 基準承認判定=_根拠付き承認, 拡張実行=lambda: 結果,
                    拡張承認判定=_根拠付き承認, 拡張採用証明=lambda _前, _後: 証明)
                if 判定.拡張採用:
                    採用, 理由 = 結果, ("HDS_MINIDORA_CANONICAL_INHERITED",)
            強候補数 = sum(x.状態 == "成立" for x in 関係判定.候補)
            必要観測 = self._必要観測(s, 関係判定, 結果) if 構造ラベル is None else ()
            明示優越 = bool(採用 is not None and any(x in 理由 for x in (
                "HDS_DIRECT_COUNTEREVIDENCE_REVERIFIED", "HDS_SUPERIOR_EVIDENCE_ADOPTED")))
            基準保持 = bool(採用 is 基準 and _暫定採用可能(基準) and not 基準阻害 and not 訂正)
            # 未観測の新関係や他候補の競合だけで、成立済みの基準回答を降格させない。
            # 推測禁止など入力契約の強い制約は、この後の入力接続検査で別途適用する。
            if (強候補数 > 1 or 必要観測) and not 明示優越 and not 基準保持:
                採用 = None
            if 判定 is not None:
                出力[非退行判定成果名] = 判定
                出力[影結果成果名] = 結果
            接続 = getattr(self, "入力接続", None)
            if 接続 is not None:
                from .入力系.選択契約 import 選択入力の実結果
                if 採用 is not None and not 接続.暫定採用可 and 構造ラベル != 採用.回答ラベル:
                    採用 = None
                if 接続.参照必須 and not 参照群: 採用 = None
                出力.update(選択入力の実結果(self.カーネル束.コア入力, 接続, 採用=採用,
                    参照=参照群, 関係判定=関係判定,
                    外部取得回数=sum(getattr(x, "実取得回数", 0) for x in 値.get(参照取得診断成果名, ()))))
            出力["HDS選択:目的関係判定"] = 関係判定
            出力["HDS選択:関係学習提案"] = 関係判定.学習提案
            出力[採用監査成果名] = {
                "関係保証": ("型付き関係証明" if _型付き関係承認(採用) else
                    "旧直接根拠" if _旧直接根拠承認(採用) else
                    "暫定順位" if _暫定採用可能(採用) else "未採用"),
                "順位根拠": self._順位根拠(結果),
                "候補関係": tuple((x.ラベル, x.状態, len(x.対象), len(x.証明), len(x.反証)) for x in 関係判定.候補),
                "関係照合数": 関係判定.照合数, "関係未完了": 関係判定.未完了,
                "次の必要観測": tuple(_観測要求鍵(x) for x in 必要観測),
                "基準根拠成立": 基準強証明, "基準採用可能": _根拠付き承認(基準), "基準資料訂正": 訂正,
                "基準阻害": tuple(sorted(基準阻害)), "現行阻害": tuple(sorted(現行阻害)),
                "採用ラベル": 採用.回答ラベル if 採用 is not None else None,
                "取得診断": tuple(値.get(参照取得診断成果名, ())),
                "資料解釈診断": getattr(self, "_資料診断", ()), "評価時間ns": 評価時間,
                "累積評価時間ns": self._累積評価時間ns, "累積評価CPU時間ns": self._累積評価CPU時間ns,
                "構文化実行数": getattr(self, "_構文化実行数", 0),
                "構文化再利用数": getattr(self, "_構文化再利用数", 0)}
            if 採用 is not None:
                if 採用 is not 結果:
                    出力[影結果成果名] = 結果
                出力[現行結果成果名], 出力[回答成果名] = 採用, 採用.回答ラベル
                if 入力解消:
                    出力[入力残差影成果名] = tuple(sorted(入力解消))
                return HDS作用結果(HDS作用状態.成立, 追加状態=frozenset({選択閉包状態}),
                    解消残差=frozenset((*選択解消, *入力解消)), 成果=tuple(出力.items()),
                    主体状態差分=基準差分, 理由=理由,
                    認識更新=認識射影, 記憶更新=記憶射影)
            残差 = set(_選択残差(結果, 参照群))
            if 必要観測: 残差.add(残差_候補証拠未閉包)
            if 強候補数 > 1: 残差.add(残差_候補競合)
            if _承認済み(結果):
                残差.update(現行阻害 or {残差_証明不足})
            if _根拠付き承認(基準):
                残差.update(基準阻害)
                if 訂正:
                    残差.add(残差_証明不足)
            if self.数量計算契約.状態 == "法則不足":
                残差.add(残差_数量法則不足)
            if self._計算計画() is not None and not bool(値.get(計算済み成果名, False)):
                残差.add(残差_計算要求)
            return HDS作用結果(HDS作用状態.成立,
                解消残差=frozenset(set(選択解消).difference(残差)),
                追加残差=frozenset(残差.difference(s.残差)), 成果=tuple(出力.items()),
                主体状態差分=基準差分, 理由=("HDS_SELECTION_NOT_CLOSED", *tuple(結果.理由)),
                認識更新=認識射影, 記憶更新=記憶射影)

        return HDS関数作用("HDS継承/模型再評価", 実行, 出力状態=(選択閉包状態,),
            解消対象=tuple(sorted(選択残差集合 | self.入力残差非阻害対象)), 資源負荷=2, 優先度=10.0,
            入力署名=lambda s: _署名((_参照署名(self._参照(s)), self._観測状態署名(s))), 契約版=HDS選択継承循環版,
            作用定義ID="HDS継承/模型再評価",
            計画仕様=self._操作仕様("HDS継承/模型再評価",
                生成=(現行結果成果名, 評価参照署名成果名, 評価観測署名成果名, 初回評価参照成果名, 回答成果名, 採用監査成果名,
                    "HDS選択:目的関係判定", "HDS選択:関係学習提案",
                    *(x.ノード.removeprefix("成果:") for x in getattr(getattr(self, "入力接続", None), "条件", ())
                      if x.ノード.startswith("成果:"))),
                読取成果=(参照成果名,),
                観測入力=("成果:" + 参照世代成果名, "成果:" + 関係観測世代成果名,
                          "成果:" + 関係観測消費成果名, "成果:" + 計算済み成果名), 解消=選択残差集合 | self.入力残差非阻害対象, 資源=2))

    def _計算計画(self):
        if self.計算実行器 is None:
            return None
        if self._計算降下済み is not None:
            return self._計算降下済み
        lower = getattr(self.コンパイラ, "計算降下", None)
        if not callable(lower):
            return None
        try:
            plan = lower(self.カーネル束)
        except (ValueError, TypeError):
            return None
        compute_ir = getattr(plan, "計算IR", None)
        if bool(getattr(plan, "参照必須", True)) or not tuple(getattr(compute_ir, "命令列", ())):
            return None
        self._計算降下済み = plan
        return plan

    def _計算作用(self, 状態: HDS実行状態):
        if (
            残差_計算要求 not in 状態.残差
            or self.計算実行器 is None
            or bool(self._成果(状態).get(計算済み成果名, False))
        ):
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
                解消残差=frozenset(set(s.残差).intersection({残差_計算要求})),
                成果=((参照成果名, tuple(merged)), (計算済み成果名, True)),
                理由=("HDS_INHERITED_COMPUTE_EXECUTED",),
            )

        return HDS関数作用(
            "HDS継承/計算",
            実行,
            解消対象=(残差_計算要求,),
            資源負荷=1,
            優先度=8.0,
            読取成果=(),
            計画仕様=self._操作仕様("HDS継承/計算",
                生成=(参照成果名, 計算済み成果名),
                観測入力=("成果:" + 参照成果名, "成果:" + 計算済み成果名), 解消=(残差_計算要求,)),
            入力署名=lambda s: _署名((_参照署名(self._参照(s)), bool(self._成果(s).get(計算済み成果名, False)))),
            契約版=HDS選択継承循環版,
            作用定義ID="HDS継承/計算",
        )

    def _参照作用(self, 状態: HDS実行状態):
        if self.参照供給器 is None or not 回復可能残差.intersection(状態.残差):
            return None
        values = self._成果(状態)
        refs_now = self._参照(状態)
        if values.get(評価参照署名成果名) != _参照署名(refs_now):
            return None
        if values.get(評価観測署名成果名) != self._観測状態署名(状態): return None
        判定 = values.get("HDS選択:目的関係判定")
        if 判定 is not None and any(x.対象 for x in 判定.候補):
            # 型付き関係の直接観測を第一手にする。そこで空振りした後だけ、
            # 同じ目的の別観測手段として段階検索へ広げる。関係構成済みを理由に
            # 観測そのものを打ち切らない。
            関係世代 = int(values.get(関係観測世代成果名, 0))
            if 関係世代 <= 0 or 残差_観測不足 not in 状態.残差:
                return None
        generation = int(values.get(参照世代成果名, 0))
        if generation >= self.設定.最大回復回数:
            return None

        def 実行(s: HDS実行状態):
            values_now = self._成果(s)
            refs = self._参照(s)
            level = int(values_now.get(参照世代成果名, 0)) + 1
            diagnostics: list[参照取得診断] = []
            observed = HDS追加参照検索(
                self.参照供給器,
                self.質問IR,
                段階=level,
                観測要求=self.参照観測要求,
                残差群=s.残差,
                診断収集=diagnostics,
            )
            limit = HDS追加参照統合上限(len(refs), len(observed))
            merged = HDS候補被覆優先統合(refs, observed, self.選択肢, limit)
            before = _参照署名(refs)
            after = _参照署名(merged)
            memory_raw = values_now.get(参照記憶成果名, refs)
            memory = 参照全保持を統合(memory_raw if isinstance(memory_raw, tuple) else refs, observed)
            diag_out = self._診断成果(values_now, diagnostics)
            recover = frozenset(set(s.残差).intersection(回復可能残差))
            transport_bad = self._取得障害(diagnostics)

            if after == before and transport_bad:
                return HDS作用結果(
                    HDS作用状態.成立,
                    解消残差=frozenset(),
                    追加残差=frozenset() if 残差_参照取得障害 in s.残差 else frozenset({残差_参照取得障害}),
                    成果=((参照世代成果名, level), (参照記憶成果名, memory), diag_out),
                    理由=("HDS_REFERENCE_TRANSPORT_RETRY", f"世代:{level}"),
                )

            if after == before:
                next_layer = (
                    HDS追加観測要求群(self.参照観測要求, 残差群=s.残差, 世代=level + 1)
                    if level < self.設定.最大回復回数 else ()
                )
                if next_layer:
                    return HDS作用結果(
                        HDS作用状態.成立,
                        成果=((参照世代成果名, level), (参照記憶成果名, memory), diag_out),
                        理由=("HDS_INHERITED_REFERENCE_LAYER_NO_PROGRESS_CONTINUE", f"世代:{level}"),
                    )
                # 観測方法を尽くしても、意味上の未閉包・矛盾は「無進展」に潰さない。
                # 無進展は観測経路の状態、候補証拠未閉包/矛盾は意味状態として併存させる。
                final_add = frozenset() if 残差_観測無進展 in s.残差 else frozenset({残差_観測無進展})
                return HDS作用結果(
                    HDS作用状態.成立,
                    解消残差=frozenset({残差_参照取得障害} if 残差_参照取得障害 in s.残差 else ()),
                    追加残差=final_add,
                    成果=((参照世代成果名, level), (参照記憶成果名, memory), diag_out),
                    理由=("HDS_INHERITED_REFERENCE_NO_PROGRESS",),
                )

            add = {残差_参照取得障害} if transport_bad else set()
            clear = {残差_参照取得障害} if (not transport_bad and 残差_参照取得障害 in s.残差) else set()
            return HDS作用結果(
                HDS作用状態.成立,
                解消残差=frozenset(clear),
                追加残差=frozenset(add.difference(s.残差)),
                成果=((参照成果名, tuple(merged)), (参照世代成果名, level), (参照記憶成果名, memory), diag_out),
                理由=(
                    "HDS_INHERITED_REFERENCE_EXPANDED_WITH_TRANSPORT_DEGRADED"
                    if transport_bad else "HDS_INHERITED_REFERENCE_EXPANDED",
                    f"世代:{level}",
                    f"件数:{len(merged)}",
                ),
            )

        return HDS関数作用(
            "HDS継承/追加参照",
            実行,
            解消対象=tuple(sorted(回復可能残差)),
            資源負荷=4,
            優先度=6.0,
            読取成果=(),
            入力署名=lambda s: _署名((
                _参照署名(self._参照(s)),
                int(self._成果(s).get(参照世代成果名, 0)),
            )),
            契約版=HDS選択継承循環版,
            作用定義ID="HDS継承/追加参照",
            計画仕様=self._操作仕様("HDS継承/追加参照",
                生成=(参照成果名, 参照世代成果名, 参照記憶成果名, 参照取得診断成果名),
                観測入力=("成果:" + 参照成果名,),
                探索=self._観測探索("HDS継承/追加参照探索"), 資源=4),
        )

    def 構成(self, 状態: HDS実行状態):
        # 供給器は候補を隠して順序を決めない。現在目的への寄与判定と選択は通常循環へ委ねる。
        evaluation = self._評価作用(状態)
        compute = self._計算作用(状態)
        関係観測 = self._関係観測作用(状態)
        参照作用 = self._参照作用(状態)
        return tuple(x for x in (evaluation, compute, 関係観測, 参照作用) if x is not None)


__all__ = [
    "HDS選択継承循環版",
    "HDS選択継承設定",
    "HDS選択継承供給",
    "参照成果名",
    "参照世代成果名",
    "計算済み成果名",
    "基準結果主体名",
    "現行結果成果名",
    "評価参照署名成果名",
    "初回評価参照成果名",
    "非退行判定成果名",
    "影結果成果名",
    "回答成果名",
    "入力残差影成果名",
    "参照記憶成果名",
    "参照取得診断成果名",
    "関係観測消費成果名",
    "関係観測世代成果名",
    "選択閉包状態",
    "残差_未評価",
    "残差_基準反証検証",
    "残差_参照取得障害",
    "残差_候補証拠未閉包",
    "残差_候補証拠矛盾",
]