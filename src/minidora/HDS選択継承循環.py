from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

from .HDS実行主体 import HDS実行状態, HDS作用結果, HDS作用状態, HDS関数作用
from .HDS構文化処理系列_v1_4 import HDSカーネル束
from .HDS観測計画 import HDS追加観測要求群
from .HDS選択実行系 import HDS選択実行結果, HDS選択推論実行
from .HDS非退行包絡 import HDS非退行包絡, HDS証拠優越包絡
from .HDS既存能力継承 import HDS既存能力結果証明済み, HDS既存能力選択評価, HDS既存能力直接反証評価
from .hds参照拡張 import HDS候補被覆優先統合, HDS追加参照統合上限, HDS追加参照検索
from .参照 import 参照供給器, 参照記録
from .模型 import MINIDORA模型核
from .能力状態差循環 import 標準能力模型核
from .計算実行器 import 計算実行器
from .コア.値 import 署名 as _意味署名

HDS選択継承循環版 = "HDS-MINIDORA-SELECTION-INHERITANCE-v3"
参照成果名 = "HDS選択:参照"; 参照世代成果名 = "HDS選択:参照世代"; 計算済み成果名 = "HDS選択:計算済み"
基準結果主体名 = "HDS選択:基準結果"; 現行結果成果名 = "HDS選択:現行結果"; 評価参照署名成果名 = "HDS選択:評価参照署名"
非退行判定成果名 = "HDS選択:非退行判定"; 影結果成果名 = "HDS選択:影結果"; 回答成果名 = "HDS選択:回答ラベル"
入力残差影成果名 = "HDS選択:入力残差影"; 選択閉包状態 = "HDS選択:閉包"
残差_未評価 = "HDS選択:未評価"; 残差_観測不足 = "HDS選択:観測不足"; 残差_問題意味損失 = "HDS選択:問題意味損失"
残差_候補意味損失 = "HDS選択:候補意味損失"; 残差_資料意味損失 = "HDS選択:資料意味損失"; 残差_候補競合 = "HDS選択:候補競合"
残差_候補識別不足 = "HDS選択:候補識別不足"; 残差_状態差未消費 = "HDS選択:状態差未消費"; 残差_計算要求 = "HDS選択:計算要求"
残差_未解 = "HDS選択:未解残差"; 残差_証明不足 = "HDS選択:拡張採用証明不足"; 残差_観測無進展 = "HDS選択:追加観測無進展"
残差_基準反証検証 = "HDS選択:基準反証検証"

選択残差集合 = frozenset({残差_未評価, 残差_観測不足, 残差_問題意味損失, 残差_候補意味損失, 残差_資料意味損失,
    残差_候補競合, 残差_候補識別不足, 残差_状態差未消費, 残差_計算要求, 残差_未解, 残差_証明不足, 残差_観測無進展, 残差_基準反証検証})
回復可能残差 = frozenset({残差_観測不足, 残差_資料意味損失, 残差_候補競合, 残差_候補識別不足, 残差_基準反証検証})

def _署名(値: object) -> str: return _意味署名(値)
def _参照署名(参照群: Sequence[参照記録]) -> str:
    return _署名(tuple((x.識別子, x.供給器, x.由来, float(x.信頼), x.条件, x.意味キー, x.表示値) for x in 参照群))
def _承認済み(結果: object) -> bool:
    return bool(isinstance(結果, HDS選択実行結果) and 結果.状態 == "APPROVE" and 結果.回答ラベル is not None)

def _正式模型承認(結果: object) -> bool:
    if not _承認済み(結果):
        return False
    理由 = tuple(str(x) for x in getattr(結果, "理由", ()))
    return "FORMAL_模型_模型核_WITH_HDS_J" in 理由 or "FORMAL_MODEL_CORE_WITH_HDS_J" in 理由

def _選択残差(結果: HDS選択実行結果, 参照群: Sequence[参照記録]) -> frozenset[str]:
    if _承認済み(結果): return frozenset()
    joined = "\n".join(str(x) for x in 結果.理由); out: set[str] = set()
    if any(x in joined for x in ("QUESTION_意味_LOSS","QUESTION_SEMANTIC_LOSS","HDS_K_QUESTION_意味_LOSS","HDS_K_QUESTION_SEMANTIC_LOSS")): out.add(残差_問題意味損失)
    if any(x in joined for x in ("選択肢_意味_LOSS","CHOICE_SEMANTIC_LOSS")): out.add(残差_候補意味損失)
    if any(x in joined for x in ("資料_COMPILE_PARTIAL","DATA_COMPILE_PARTIAL")) or 結果.資料コンパイル失敗数 > 0: out.add(残差_資料意味損失)
    if any(x in joined for x in ("NO_KNOWLEDGE_証拠","NO_KNOWLEDGE_EVIDENCE","NO_候補","NO_CANDIDATE","MINIDORA_OUTPUT_ABSENT","NO_GUESS","証拠_INSUFFICIENT","EVIDENCE_INSUFFICIENT","MINIDORA_模型_模型核_NO_参照_CONTRIBUTION","MINIDORA_MODEL_CORE_NO_REFERENCE_CONTRIBUTION")): out.add(残差_観測不足)
    if any(x in joined for x in ("AMBIGUOUS_証拠","AMBIGUOUS_EVIDENCE","EXCEPTION_NOT_RESOLVED","参照_DIFFERENCE_NOT_UNIQUE","REFERENCE_DIFFERENCE_NOT_UNIQUE")): out.add(残差_候補競合)
    if (("HDS_作用_DELTA_ATTACHED" in joined or "HDS_ACTION_DELTA_ATTACHED" in joined) and not ("HDS_作用_DELTA_CONSUMED" in joined or "HDS_ACTION_DELTA_CONSUMED" in joined)): out.add(残差_状態差未消費)
    if not tuple(参照群): out.add(残差_観測不足)
    if 結果.状態 == "FAIL": out.add(残差_未解)
    if not out: out.add(残差_候補識別不足)
    return frozenset(out)

def _標準追加採用証明(基準: HDS選択実行結果, 拡張: HDS選択実行結果, *, 初期参照署名: str, 現在参照署名: str) -> bool:
    if _承認済み(基準) or not _承認済み(拡張) or 初期参照署名 == 現在参照署名: return False
    return HDS既存能力結果証明済み(拡張)

@dataclass(frozen=True, slots=True)
class HDS選択継承設定:
    最大回復回数: int = 6
    def __post_init__(self) -> None:
        if type(self.最大回復回数) is not int or not 0 <= self.最大回復回数 <= 64:
            raise ValueError("最大回復回数は0..64の整数である必要がある")

class HDS選択継承供給:
    """Compiler Kernelを固定したまま再観測・再評価・非退行を行う通常循環。"""
    def __init__(self, カーネル束: HDSカーネル束, コンパイラ, 初期参照: Sequence[参照記録], *,
                 模型核: MINIDORA模型核 | None = None, 基礎能力核=None, 既存能力継承: bool = True,
                 参照供給器: 参照供給器 | None = None, 計算実行器_: 計算実行器 | None = None,
                 設定: HDS選択継承設定 | None = None,
                 拡張採用証明: Callable[[HDS選択実行結果,HDS選択実行結果],bool] | None = None,
                 入力残差非阻害対象: Sequence[str] = ()) -> None:
        if not isinstance(カーネル束, HDSカーネル束): raise TypeError("選択継承循環にはHDSカーネル束が必要")
        self.カーネル束 = カーネル束; self.質問IR = カーネル束.意味IR; self.参照観測要求 = tuple(カーネル束.参照観測要求)
        self.候補意味IR = カーネル束.候補意味IR辞書 or None
        self.コンパイラ = コンパイラ; self.初期参照 = tuple(初期参照); self.初期参照署名 = _参照署名(self.初期参照)
        self.模型核 = 模型核 or 標準能力模型核()
        if 基礎能力核 is None and 既存能力継承:
            from .K3機能 import K3相当能力核
            基礎能力核 = K3相当能力核()
        self.基礎能力核 = 基礎能力核 if 既存能力継承 else None; self.既存能力継承 = bool(既存能力継承)
        self.参照供給器 = 参照供給器; self.計算実行器 = 計算実行器_; self.設定 = 設定 or HDS選択継承設定()
        self.拡張採用証明 = 拡張採用証明; self.入力残差非阻害対象 = frozenset(str(x) for x in 入力残差非阻害対象)
        self.選択肢 = tuple(x.座標ID.split(":",1)[1] for x in self.質問IR.座標 if x.座標ID.startswith("選択肢:"))
        self._計算降下済み = None

    @staticmethod
    def _成果(状態: HDS実行状態) -> dict[str, object]: return 状態.成果辞書()
    def _参照(self, 状態: HDS実行状態) -> tuple[参照記録,...]:
        value = self._成果(状態).get(参照成果名, self.初期参照)
        if not isinstance(value, tuple) or any(not isinstance(x,参照記録) for x in value): raise TypeError("HDS選択の参照成果は参照記録tupleである必要がある")
        return value

    def _評価(self, 参照群: tuple[参照記録,...]) -> HDS選択実行結果:
        compile_fn = getattr(self.コンパイラ,"コンパイル",None)
        if not callable(compile_fn): raise TypeError("選択継承循環には外部資料をコンパイル可能なHDSコンパイラが必要")
        if not self.既存能力継承:
            return HDS選択推論実行(self.質問IR,参照群,コンパイル=compile_fn,基礎能力核=None,候補意味IR=self.候補意味IR,模型核=self.模型核,正式模型評価=True)
        return HDS既存能力選択評価(self.質問IR,参照群,コンパイル=compile_fn,模型核=self.模型核,基礎能力核=self.基礎能力核,候補意味IR=self.候補意味IR)

    def _評価作用(self, 状態: HDS実行状態):
        成果=self._成果(状態); 参照群=self._参照(状態); ref_sig=_参照署名(参照群)
        if 成果.get(評価参照署名成果名)==ref_sig: return None
        def 実行(s: HDS実行状態):
            refs=self._参照(s); current_sig=_参照署名(refs); 結果=self._評価(refs); values=self._成果(s); 主体値=s.主体辞書()
            基準=主体値.get(基準結果主体名); 初回=not isinstance(基準,HDS選択実行結果); 基準差分=()
            if 初回: 基準=結果; 基準差分=((基準結果主体名,基準),)
            選択解消=frozenset(set(s.残差).intersection(選択残差集合)); 承認時入力解消=frozenset(set(s.残差).intersection(self.入力残差非阻害対象))
            成果群=[(現行結果成果名,結果),(評価参照署名成果名,current_sig)]
            if _承認済み(基準):
                正式基準 = _正式模型承認(基準)
                if 初回 and 正式基準 and self.参照供給器 is not None and self.設定.最大回復回数 > 0:
                    return HDS作用結果(
                        HDS作用状態.成立,
                        解消残差=選択解消,
                        追加残差=frozenset({残差_基準反証検証}),
                        成果=tuple(成果群),
                        主体状態差分=基準差分,
                        理由=("HDS_BASELINE_APPROVAL_REVERIFY_PENDING",),
                    )

                if not 初回 and 正式基準 and int(values.get(参照世代成果名, 0)) > 0:
                    反証 = HDS既存能力直接反証評価(
                        self.質問IR,
                        refs,
                        コンパイル=getattr(self.コンパイラ, "コンパイル"),
                        基礎能力核=self.基礎能力核,
                        候補意味IR=self.候補意味IR,
                        基準ラベル=str(基準.回答ラベル),
                        最小独立証拠数=2,
                    )
                    if 反証 is not None:
                        判定 = HDS証拠優越包絡(
                            基準,
                            反証,
                            基準承認判定=_承認済み,
                            拡張承認判定=_承認済み,
                            証拠優越証明=lambda _前, _後: True,
                        )
                        成果群[0] = (現行結果成果名, 反証)
                        成果群.extend(((非退行判定成果名, 判定), (影結果成果名, 反証), (回答成果名, 反証.回答ラベル)))
                        if 承認時入力解消:
                            成果群.append((入力残差影成果名, tuple(sorted(承認時入力解消))))
                        return HDS作用結果(
                            HDS作用状態.成立,
                            追加状態=frozenset({選択閉包状態}),
                            解消残差=frozenset((*選択解消, *承認時入力解消)),
                            成果=tuple(成果群),
                            主体状態差分=基準差分,
                            理由=tuple(dict.fromkeys((*判定.理由, "HDS_DIRECT_COUNTEREVIDENCE_REVERIFIED"))),
                        )
                    if 結果 is not 基準:
                        成果群.append((影結果成果名, 結果))

                成果群.append((回答成果名,基準.回答ラベル))
                if 承認時入力解消: 成果群.append((入力残差影成果名,tuple(sorted(承認時入力解消))))
                継承理由="HDS_MINIDORA_EXISTING_CAPABILITIES_INHERITED" if "HDS_EXISTING_CAPABILITY_INHERITED" in 基準.理由 else "HDS_MINIDORA_CANONICAL_INHERITED"
                return HDS作用結果(HDS作用状態.成立,追加状態=frozenset({選択閉包状態}),解消残差=frozenset((*選択解消,*承認時入力解消)),成果=tuple(成果群),主体状態差分=基準差分,理由=("HDS_BASELINE_APPROVAL_REVERIFIED" if not 初回 and 正式基準 else "HDS_BASELINE_APPROVAL_LOCKED",継承理由))
            if not 初回 and _承認済み(結果):
                proof=bool(self.拡張採用証明(基準,結果)) if self.拡張採用証明 is not None else _標準追加採用証明(基準,結果,初期参照署名=self.初期参照署名,現在参照署名=current_sig)
                判定=HDS非退行包絡(基準,基準承認判定=_承認済み,拡張実行=lambda:結果,拡張承認判定=_承認済み,拡張採用証明=lambda _前,_後:proof)
                成果群.extend(((非退行判定成果名,判定),(影結果成果名,結果)))
                if 判定.拡張採用:
                    成果群.append((回答成果名,結果.回答ラベル))
                    if 承認時入力解消: 成果群.append((入力残差影成果名,tuple(sorted(承認時入力解消))))
                    return HDS作用結果(HDS作用状態.成立,追加状態=frozenset({選択閉包状態}),解消残差=frozenset((*選択解消,*承認時入力解消)),成果=tuple(成果群),主体状態差分=基準差分,理由=tuple(dict.fromkeys((*判定.理由,"HDS_MINIDORA_CANONICAL_INHERITED"))))
                return HDS作用結果(HDS作用状態.成立,解消残差=選択解消,追加残差=frozenset({残差_証明不足}),成果=tuple(成果群),主体状態差分=基準差分,理由=tuple(dict.fromkeys((*判定.理由,"HDS_EXTENSION_SHADOW_ONLY"))))
            residuals=_選択残差(結果,refs)
            if self._計算計画() is not None and not bool(values.get(計算済み成果名,False)): residuals=frozenset((*residuals,残差_計算要求))
            return HDS作用結果(HDS作用状態.成立,解消残差=frozenset(set(選択解消).difference(residuals)),追加残差=frozenset(set(residuals).difference(s.残差)),成果=tuple(成果群),主体状態差分=基準差分,理由=tuple(dict.fromkeys(("HDS_SELECTION_NOT_CLOSED",*tuple(結果.理由)))))
        return HDS関数作用("HDS継承/模型再評価",実行,解消対象=tuple(sorted(選択残差集合|self.入力残差非阻害対象)),資源負荷=2,優先度=10.0,読取成果=(参照成果名,),入力署名=lambda s:_参照署名(self._参照(s)),契約版=HDS選択継承循環版,作用定義ID="HDS継承/模型再評価")

    def _計算計画(self):
        if self.計算実行器 is None: return None
        if self._計算降下済み is not None: return self._計算降下済み
        lower=getattr(self.コンパイラ,"計算降下",None)
        if not callable(lower): return None
        try: plan=lower(self.カーネル束)
        except (ValueError,TypeError): return None
        compute_ir=getattr(plan,"計算IR",None)
        if bool(getattr(plan,"参照必須",True)) or not tuple(getattr(compute_ir,"命令列",())): return None
        self._計算降下済み=plan; return plan

    def _計算作用(self, 状態: HDS実行状態):
        if 残差_計算要求 not in 状態.残差 or self.計算実行器 is None or bool(self._成果(状態).get(計算済み成果名,False)): return None
        plan=self._計算計画()
        if plan is None: return None
        def 実行(s: HDS実行状態):
            refs=self._参照(s)
            try: executed=self.計算実行器.計算実行(plan.計算IR,dict(plan.初期状態))
            except Exception as exc: return HDS作用結果(HDS作用状態.失敗,追加残差=frozenset({残差_未解}),理由=("HDS_INHERITED_COMPUTE_FAILED",type(exc).__name__))
            output=executed.出力
            if output is None: return HDS作用結果(HDS作用状態.保留,追加残差=frozenset({残差_未解}),理由=("HDS_INHERITED_COMPUTE_OUTPUT_ABSENT",))
            record=参照記録(識別子="compute:"+_署名((plan.計算IR.名称,plan.計算IR.版,plan.初期状態,output)),対象=self.質問IR.認知世界ID or "計算対象",内容=f"計算結果 {output}",由来="MINIDORA汎用計算実行",供給器="MINIDORA計算実行器",信頼=1.0,意味キー="計算結果",値=output,条件=(("hds_query_kind","compute"),),意味確定=True)
            merged=refs if any(x.識別子==record.識別子 for x in refs) else (*refs,record)
            return HDS作用結果(HDS作用状態.成立,解消残差=frozenset(set(s.残差).intersection({残差_計算要求,残差_観測不足,残差_候補識別不足})),成果=((参照成果名,tuple(merged)),(計算済み成果名,True)),理由=("HDS_INHERITED_COMPUTE_EXECUTED",))
        return HDS関数作用("HDS継承/計算",実行,解消対象=(残差_計算要求,残差_観測不足,残差_候補識別不足),資源負荷=1,優先度=8.0,読取成果=(参照成果名,計算済み成果名),入力署名=lambda s:_署名((_参照署名(self._参照(s)),bool(self._成果(s).get(計算済み成果名,False)))),契約版=HDS選択継承循環版,作用定義ID="HDS継承/計算")

    def _参照作用(self, 状態: HDS実行状態):
        if self.参照供給器 is None or not 回復可能残差.intersection(状態.残差): return None
        generation=int(self._成果(状態).get(参照世代成果名,0))
        if generation >= self.設定.最大回復回数: return None
        def 実行(s: HDS実行状態):
            values=self._成果(s); refs=self._参照(s); level=int(values.get(参照世代成果名,0))+1
            observed=HDS追加参照検索(
                self.参照供給器,self.質問IR,段階=level,
                観測要求=self.参照観測要求,残差群=s.残差,
            )
            統合上限=HDS追加参照統合上限(len(refs),len(observed))
            merged=HDS候補被覆優先統合(refs,observed,self.選択肢,統合上限)
            before=tuple((x.識別子,x.条件) for x in refs); after=tuple((x.識別子,x.条件) for x in merged); 解消=frozenset(set(s.残差).intersection(回復可能残差))
            if after==before:
                if 残差_基準反証検証 in s.残差:
                    基準=s.主体辞書().get(基準結果主体名)
                    if _承認済み(基準):
                        return HDS作用結果(
                            HDS作用状態.成立,
                            追加状態=frozenset({選択閉包状態}),
                            解消残差=解消,
                            成果=((参照世代成果名,level),(回答成果名,基準.回答ラベル)),
                            理由=("HDS_BASELINE_REVERIFY_NO_NEW_EVIDENCE",),
                        )
                次層 = (
                    HDS追加観測要求群(self.参照観測要求, 残差群=s.残差, 世代=level+1)
                    if level < self.設定.最大回復回数 else ()
                )
                if 次層:
                    return HDS作用結果(
                        HDS作用状態.成立,
                        成果=((参照世代成果名,level),),
                        理由=("HDS_INHERITED_REFERENCE_LAYER_NO_PROGRESS_CONTINUE",f"世代:{level}"),
                    )
                return HDS作用結果(HDS作用状態.成立,解消残差=解消,追加残差=frozenset({残差_観測無進展}),成果=((参照世代成果名,level),),理由=("HDS_INHERITED_REFERENCE_NO_PROGRESS",))
            return HDS作用結果(HDS作用状態.成立,解消残差=解消,成果=((参照成果名,tuple(merged)),(参照世代成果名,level)),理由=("HDS_INHERITED_REFERENCE_EXPANDED",f"世代:{level}",f"件数:{len(merged)}"))
        return HDS関数作用("HDS継承/追加参照",実行,解消対象=tuple(sorted(回復可能残差)),資源負荷=4,優先度=6.0,読取成果=(参照成果名,参照世代成果名),入力署名=lambda s:_署名((_参照署名(self._参照(s)),int(self._成果(s).get(参照世代成果名,0)))),契約版=HDS選択継承循環版,作用定義ID="HDS継承/追加参照")

    def 構成(self, 状態: HDS実行状態):
        評価=self._評価作用(状態)
        if 評価 is not None: return (評価,)
        計算=self._計算作用(状態); 参照=self._参照作用(状態)
        return tuple(x for x in (計算,参照) if x is not None)

__all__=["HDS選択継承循環版","HDS選択継承設定","HDS選択継承供給","参照成果名","参照世代成果名","計算済み成果名","基準結果主体名","現行結果成果名","評価参照署名成果名","非退行判定成果名","影結果成果名","回答成果名","入力残差影成果名","選択閉包状態","残差_未評価","残差_基準反証検証"]
