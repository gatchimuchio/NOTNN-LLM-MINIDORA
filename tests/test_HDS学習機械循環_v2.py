from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from minidora.HDS構文化器_v1 import 公開HDSコンパイラ
from minidora.HDS実行主体 import HDS関数作用, HDS作用結果, HDS作用状態, HDS終端, HDS実行状態, HDS実行結果
from minidora.統合駆動_v2.認識 import HDS認識項目, 認識区分
from minidora.HDS選択継承循環 import HDS選択継承供給, 初回評価参照成果名
from minidora.HDS駆動コア import HDS駆動コア
from minidora.参照 import 参照記録, 参照取得診断
from minidora.統合駆動_v2.記憶 import HDS資料
from minidora.駆動系.契約 import 関係項, 関係節, 関係変換契約
from minidora.駆動系.学習 import 関係形成, 関係学習状態, 変換を合成
from minidora.HDS選択継承循環 import (
    関係学習提案成果名, 回答成果名, 現行結果成果名, 参照成果名, 参照取得診断成果名,
)
from minidora.HDS観測計画 import HDS参照観測要求
from minidora.統合駆動_v2.適応記憶 import HDS適応記憶
from minidora.選択観測学習 import HDS観測経路鍵を構成, HDS観測経路鍵を文字列


class _空参照供給器:
    名称 = "学習機械空参照"
    並列安全 = False

    def __init__(self) -> None:
        self.問合せ: list[str] = []

    def 検索(self, 問合せ, 上限=8):
        self.問合せ.append(" ".join(str(問合せ).split()))
        return ()


def _観測要求(経路, *, label="A", ID="観測:A"):
    if 経路=="主観測":
        段階="primary"; provenance=("Compiler外部文脈",)
    elif 経路=="局所検証":
        段階="fallback"; provenance=("局所検証",)
    else:
        段階="fallback"; provenance=("縮退",)
    return HDS参照観測要求(
        ID=ID, 関係ID="r-current", 関係種別="作用", 未知位置="始点",
        既知端点=("target",), 条件範囲=(), 候補ラベル=label, 候補表層="candidate",
        外部言語="en", 外部検索表層=f"{label} route {経路}", 必須被覆=True,
        段階=段階, 優先度=10 if 段階=="primary" else 20, provenance=provenance,
    )


def _学習状態():
    x=関係項("x",変数=True,束縛域="test")
    a=関係変換契約("r1",(関係節("p",(("対象",x),)),),関係節("q",(("対象",x),)),("test:r1",))
    b=関係変換契約("r2",(関係節("q",(("対象",x),)),),関係節("r",(("対象",x),)),("test:r2",))
    formed=変換を合成(a,b,0)
    assert formed is not None
    return 関係学習状態((関係形成(formed.ID,formed,a,b,0,("proof",),("exp",)),))


class HDS観測経路学習試験(unittest.TestCase):
    def test_候補ラベルを観測学習キーへ入れない(self) -> None:
        a=_観測要求("局所検証",label="A",ID="観測:A")
        b=_観測要求("局所検証",label="B",ID="観測:B")
        self.assertEqual(HDS観測経路鍵を構成(a),HDS観測経路鍵を構成(b))

    def test_二回成功した局所検証を同型次問の主観測へ昇格する(self) -> None:
        記憶=HDS適応記憶()
        primary=_観測要求("主観測")
        local=_観測要求("局所検証")
        for _ in range(2):
            記憶.観測経路を記録((primary,local),(local,))
        次primary=_観測要求("主観測",label="B",ID="観測:B")
        次local=_観測要求("局所検証",label="B",ID="観測:B")
        adapted=記憶.観測要求を適応((次primary,次local))
        local_after=next(x for x in adapted if "局所検証" in x.provenance)
        primary_after=next(x for x in adapted if "Compiler外部文脈" in x.provenance)
        self.assertEqual(local_after.段階,"primary")
        self.assertEqual(primary_after.段階,"fallback")

    def test_一回成功だけでは観測経路を昇格しない(self) -> None:
        記憶=HDS適応記憶()
        primary=_観測要求("主観測");local=_観測要求("局所検証")
        記憶.観測経路を記録((primary,local),(local,))
        adapted=記憶.観測要求を適応((primary,local))
        self.assertEqual(next(x for x in adapted if "局所検証" in x.provenance).段階,"fallback")

    def test_観測経路経験を保存復元し初期化できる(self) -> None:
        記憶=HDS適応記憶();primary=_観測要求("主観測");local=_観測要求("局所検証")
        記憶.観測経路を記録((primary,local),(local,))
        復元=HDS適応記憶();復元.復元(記憶.スナップショット())
        self.assertEqual(復元.観測経路経験,記憶.観測経路経験)
        復元.初期化();self.assertEqual(復元.観測経路経験数,0)


class HDS観測根拠帰還試験(unittest.TestCase):
    def _結果(self, req, *, 寄与=True):
        経路印=HDS観測経路鍵を文字列(HDS観測経路鍵を構成(req))
        ref=参照記録("doc:1","対象","candidate relation target evidence","試験","試験",1.0,
            条件=(("hds_query_学習経路",経路印),))
        roots=("最大局所対応:doc:1:1.000000000",) if 寄与 else ("最大局所対応:other:1.000000000",)
        模型=SimpleNamespace(候補差=(SimpleNamespace(
            候補ID="A",寄与=(SimpleNamespace(関係名="候補共同参照",根拠=roots),)),))
        current=SimpleNamespace(回答ラベル="A",MINIDORA模型結果=模型)
        diag=参照取得診断(req.外部検索表層,"試験","取得",1)
        状態=HDS実行状態(成果=(
            (回答成果名,"A"),(現行結果成果名,current),(参照成果名,(ref,)),
            (参照取得診断成果名,(diag,)),
        ))
        return HDS実行結果(HDS終端.採用,状態,())

    def test_採用候補へ実寄与した参照経路だけ成功経験へ帰還する(self) -> None:
        中核=HDS駆動コア();req=_観測要求("局所検証")
        self.assertTrue(中核._選択観測経験を帰還(self._結果(req), (req,)))
        self.assertEqual(中核.観測経路経験数,1)
        self.assertTrue(中核._適応記憶.観測経路経験[0].成功)

    def test_取得しただけの非寄与資料は観測成功へ昇格しない(self) -> None:
        中核=HDS駆動コア();req=_観測要求("局所検証")
        self.assertFalse(中核._選択観測経験を帰還(self._結果(req,寄与=False), (req,)))
        self.assertEqual(中核.観測経路経験数,0)


class HDS学習機械循環V2試験(unittest.TestCase):
    def test_選択COMMITの関係学習提案を中核へ帰還する(self) -> None:
        中核=HDS駆動コア()
        提案=_学習状態()
        状態=HDS実行状態(成果=((関係学習提案成果名,提案),))
        結果=HDS実行結果(HDS終端.採用,状態,())
        self.assertTrue(中核._選択学習提案を帰還(結果))
        self.assertEqual(中核.関係学習状態,提案)

    def test_選択SUSPENDの学習提案は中核へ帰還しない(self) -> None:
        中核=HDS駆動コア()
        提案=_学習状態()
        状態=HDS実行状態(成果=((関係学習提案成果名,提案),))
        結果=HDS実行結果(HDS終端.保留,状態,())
        self.assertFalse(中核._選択学習提案を帰還(結果))
        self.assertEqual(中核.関係学習状態,関係学習状態())

    def test_現在材料を評価してから不足時だけ候補関係観測が発火する(self) -> None:
        構文化器 = 公開HDSコンパイラ()
        中核 = HDS駆動コア(HDSコンパイラ=構文化器, 最大作用回数=40)
        供給器 = _空参照供給器()
        元評価 = HDS選択継承供給._評価
        評価時問合せ数: list[int] = []

        def 評価を監査(自己, 参照群):
            評価時問合せ数.append(len(供給器.問合せ))
            return 元評価(自己, 参照群)

        with patch.object(HDS選択継承供給, "_評価", new=評価を監査):
            中核.選択実行(
                "Which molecule inhibits Enzyme X?",
                ("Molecule A", "Molecule B"),
                初期参照=(),
                参照供給器=供給器,
                最大回復回数=2,
            )

        self.assertTrue(評価時問合せ数)
        self.assertEqual(評価時問合せ数[0], 0)
        self.assertGreater(len(供給器.問合せ), 0)

    def test_実観測参照は同一中核の次処理へ継承される(self) -> None:
        構文化器 = 公開HDSコンパイラ()
        中核 = HDS駆動コア(HDSコンパイラ=構文化器, 最大作用回数=40)
        問い = "Which molecule inhibits Enzyme X?"
        選択肢 = ("Molecule A", "Molecule B")
        観測 = 参照記録(
            識別子="memory-a",
            対象="Molecule A",
            内容="Molecule A inhibits Enzyme X.",
            由来="試験観測",
            供給器="試験",
            信頼=1.0,
        )

        中核.選択実行(問い, 選択肢, 初期参照=(観測,))
        self.assertGreaterEqual(中核.継続参照件数, 1)

        次 = 中核.選択実行(問い, 選択肢, 初期参照=())
        初回参照 = 次.状態.成果辞書().get(初回評価参照成果名, ())
        self.assertTrue(any(x.識別子 == "memory-a" for x in 初回参照))

    def test_全保持認識から現在問の作業集合だけを投入し未使用認識は保持する(self) -> None:
        中核=HDS駆動コア(最大作用回数=8)
        扉資料=HDS資料("door","1","扉は施錠","試験")
        天気資料=HDS資料("weather","1","晴天","試験")
        中核._継続記憶=中核._継続記憶.更新((扉資料,天気資料))
        扉=HDS認識項目("door-lock","扉","施錠",True,認識区分.確定,
            根拠=(扉資料.出典(),),検証契約="test/v1")
        天気=HDS認識項目("weather-clear","天気","晴天",True,認識区分.確定,
            根拠=(天気資料.出典(),),検証契約="test/v1")
        中核._継続認識=(扉,天気)
        観測=[]
        def 実行(状態):
            観測.append(tuple(x.ID for x in 状態.認識))
            return HDS作用結果(HDS作用状態.成立,追加状態=frozenset({"完了"}))
        結果=中核.実行("扉の施錠を確認",要求状態=("完了",),
            追加作用=(HDS関数作用("確認",実行,出力状態=("完了",)),))
        self.assertEqual(結果.終端,HDS終端.採用)
        self.assertEqual(観測,[("door-lock",)])
        self.assertEqual({x.ID for x in 中核._継続認識},{"door-lock","weather-clear"})

    def test_作業外認識も根拠資料改訂時は正本から失効する(self) -> None:
        中核=HDS駆動コア(最大作用回数=8)
        扉資料=HDS資料("door","1","扉は施錠","試験")
        天気旧=HDS資料("weather","1","晴天","試験")
        天気新=HDS資料("weather","2","雨天","試験")
        中核._継続記憶=中核._継続記憶.更新((扉資料,天気旧))
        扉=HDS認識項目("door-lock","扉","施錠",True,認識区分.確定,
            根拠=(扉資料.出典(),),検証契約="test/v1")
        天気=HDS認識項目("weather-clear","天気","晴天",True,認識区分.確定,
            根拠=(天気旧.出典(),),検証契約="test/v1")
        中核._継続認識=(扉,天気)
        def 更新(状態):
            return HDS作用結果(HDS作用状態.成立,追加状態=frozenset({"更新済み"}),
                記憶更新=状態.記憶.更新((天気新,)))
        中核.実行("扉の施錠を確認",要求状態=("更新済み",),
            追加作用=(HDS関数作用("資料更新",更新,出力状態=("更新済み",)),))
        self.assertEqual({x.ID for x in 中核._継続認識},{"door-lock"})

    def test_構造tuple内の関係語から過去認識を作業集合へ戻す(self) -> None:
        根拠資料=HDS資料("関係資料","1","Molecule A inhibits Enzyme X.","試験")
        関係認識=HDS認識項目(
            "関係認識1","参照記憶:関係資料","観測された記述関係",
            ("inhibits",(("始点","Molecule A"),("終点","Enzyme X"))),
            認識区分.確定,根拠=(根拠資料.出典(),),検証契約="試験検証/v1",
        )
        群=HDS駆動コア._認識作業集合("Which molecule inhibits Enzyme X?",(関係認識,))
        self.assertEqual(tuple(x.ID for x in 群),("関係認識1",))

    def test_作業認識の依存鎖を一緒に投入する(self) -> None:
        根=HDS認識項目("root","天気","晴天",True,認識区分.確定,
            依存=("seed",),検証契約="test/v1")
        seed=HDS認識項目("seed","観測","晴天",True,認識区分.確定,
            根拠=(HDS資料("seed-doc","1","晴天","試験").出典(),),検証契約="test/v1")
        群=HDS駆動コア._認識作業集合("天気を判断",(seed,根))
        self.assertEqual({x.ID for x in 群},{"root","seed"})

    def test_継続状態は別中核へ漏れない(self) -> None:
        構文化器 = 公開HDSコンパイラ()
        問い = "Which molecule inhibits Enzyme X?"
        選択肢 = ("Molecule A", "Molecule B")
        観測 = 参照記録(
            識別子="memory-a",
            対象="Molecule A",
            内容="Molecule A inhibits Enzyme X.",
            由来="試験観測",
            供給器="試験",
            信頼=1.0,
        )
        第一 = HDS駆動コア(HDSコンパイラ=構文化器, 最大作用回数=40)
        第一.選択実行(問い, 選択肢, 初期参照=(観測,))
        self.assertGreaterEqual(第一.継続参照件数, 1)

        第二 = HDS駆動コア(HDSコンパイラ=公開HDSコンパイラ(), 最大作用回数=40)
        結果 = 第二.選択実行(問い, 選択肢, 初期参照=())
        初回参照 = 結果.状態.成果辞書().get(初回評価参照成果名, ())
        self.assertEqual(初回参照, ())
        self.assertEqual(第二.継続参照件数, 0)

    def test_確定認識が次実行の推論前提へ継承される(self) -> None:
        中核 = HDS駆動コア(最大作用回数=16)
        資料 = HDS資料("扉観測", "1", "扉は施錠されている", "試験")
        導出 = HDS認識項目(
            "扉施錠",
            "扉",
            "施錠",
            True,
            認識区分.確定,
            根拠=(資料.出典(),),
            検証契約="試験検証/v1",
        )

        初回 = 中核.実行(
            "観測から施錠状態を導出する",
            要求状態=("導出済み",),
            追加作用=(HDS関数作用(
                "導出",
                lambda 状態: HDS作用結果(
                    HDS作用状態.成立,
                    追加状態=frozenset({"導出済み"}),
                    記憶更新=状態.記憶.更新((資料,)),
                    認識更新=(導出,),
                ),
                出力状態=("導出済み",),
            ),),
        )
        self.assertEqual(初回.終端, HDS終端.採用)
        self.assertEqual(中核.継続認識件数, 1)

        def 前提を使う(状態):
            項目 = 状態.認識辞書().get("扉施錠")
            if 項目 is None or 項目.値 is not True:
                return HDS作用結果(HDS作用状態.保留)
            return HDS作用結果(HDS作用状態.成立, 追加状態=frozenset({"事前確認必要"}))

        次回 = 中核.実行(
            "施錠経験から事前確認を行う",
            要求状態=("事前確認必要",),
            追加作用=(HDS関数作用("前提利用", 前提を使う, 出力状態=("事前確認必要",)),),
        )
        self.assertEqual(次回.終端, HDS終端.採用)

    def test_根拠更新で旧認識を次実行前提から再開放する(self) -> None:
        中核 = HDS駆動コア(最大作用回数=16)
        旧資料 = HDS資料("扉観測", "1", "扉は施錠されている", "試験")
        新資料 = HDS資料("扉観測", "2", "扉は解錠されている", "試験")
        導出 = HDS認識項目(
            "扉施錠",
            "扉",
            "施錠",
            True,
            認識区分.確定,
            根拠=(旧資料.出典(),),
            検証契約="試験検証/v1",
        )
        中核.実行(
            "施錠認識を形成する",
            要求状態=("形成済み",),
            追加作用=(HDS関数作用(
                "形成",
                lambda 状態: HDS作用結果(
                    HDS作用状態.成立,
                    追加状態=frozenset({"形成済み"}),
                    記憶更新=状態.記憶.更新((旧資料,)),
                    認識更新=(導出,),
                ),
                出力状態=("形成済み",),
            ),),
        )
        self.assertEqual(中核.継続認識件数, 1)

        更新 = 中核.実行(
            "反証資料へ更新する",
            要求状態=("更新済み",),
            追加作用=(HDS関数作用(
                "資料更新",
                lambda 状態: HDS作用結果(
                    HDS作用状態.成立,
                    追加状態=frozenset({"更新済み"}),
                    記憶更新=状態.記憶.更新((新資料,)),
                ),
                出力状態=("更新済み",),
            ),),
        )
        self.assertEqual(更新.終端, HDS終端.採用)
        self.assertEqual(中核.継続認識件数, 0)

    def test_HDS記憶は次実行の処理前提になる(self) -> None:
        中核 = HDS駆動コア(最大作用回数=16)
        資料 = HDS資料("経験資料", "1", "扉は施錠されていた", "試験")

        def 記憶する(状態):
            return HDS作用結果(
                HDS作用状態.成立,
                追加状態=frozenset({"記憶済み"}),
                記憶更新=状態.記憶.更新((資料,)),
            )

        初回 = 中核.実行(
            "経験を保持する",
            要求状態=("記憶済み",),
            追加作用=(HDS関数作用("経験保持", 記憶する, 出力状態=("記憶済み",)),),
        )
        self.assertEqual(初回.終端, HDS終端.採用)

        def 記憶を使う(状態):
            if "経験資料" not in 状態.記憶.正本辞書():
                return HDS作用結果(HDS作用状態.保留)
            return HDS作用結果(HDS作用状態.成立, 追加状態=frozenset({"経験利用済み"}))

        次回 = 中核.実行(
            "保持経験を後続処理で使う",
            要求状態=("経験利用済み",),
            追加作用=(HDS関数作用("経験利用", 記憶を使う, 出力状態=("経験利用済み",)),),
        )
        self.assertEqual(次回.終端, HDS終端.採用)

    def test_実行経験から形成した適応が同一中核の次実行へ継承される(self) -> None:
        中核 = HDS駆動コア(最大作用回数=24)
        作用群 = (
            HDS関数作用(
                "段1",
                lambda 状態: HDS作用結果(HDS作用状態.成立, 追加状態=frozenset({"途中"})),
                出力状態=("途中",),
                純粋作用=True,
            ),
            HDS関数作用(
                "段2",
                lambda 状態: HDS作用結果(HDS作用状態.成立, 追加状態=frozenset({"完了"})),
                入力状態=("途中",),
                出力状態=("完了",),
                純粋作用=True,
            ),
        )

        初回 = 中核.実行("手順経験", 要求状態=("完了",), 追加作用=作用群)
        self.assertEqual(初回.終端, HDS終端.採用)
        self.assertTrue(初回.状態.形成関係)

        次回 = 中核.実行("手順経験", 要求状態=("完了",), 追加作用=作用群)
        self.assertEqual(次回.終端, HDS終端.採用)
        self.assertGreater(次回.計装.形成再利用数, 0)

    def test_問固有の検索経路印は次経験へ持ち越さない(self) -> None:
        中核 = HDS駆動コア(HDSコンパイラ=公開HDSコンパイラ(), 最大作用回数=40)
        観測 = 参照記録(
            "r-route",
            "Molecule A",
            "Molecule A inhibits Enzyme X.",
            "試験",
            "試験",
            1.0,
            条件=(("hds_query_選択肢", "A"), ("hds_observation_id", "old"), ("領域条件", "保持")),
        )
        中核.選択実行(
            "Which molecule inhibits Enzyme X?",
            ("Molecule A", "Molecule B"),
            初期参照=(観測,),
        )
        記憶 = next(x for x in 中核.継続参照記憶 if x.識別子 == "r-route")
        self.assertNotIn(("hds_query_選択肢", "A"), 記憶.条件)
        self.assertNotIn(("hds_observation_id", "old"), 記憶.条件)
        self.assertIn(("領域条件", "保持"), 記憶.条件)

    def test_継続状態を明示初期化できる(self) -> None:
        中核 = HDS駆動コア(HDSコンパイラ=公開HDSコンパイラ(), 最大作用回数=40)
        観測 = 参照記録("r", "Molecule A", "Molecule A inhibits Enzyme X.", "試験", "試験", 1.0)
        中核.選択実行(
            "Which molecule inhibits Enzyme X?",
            ("Molecule A", "Molecule B"),
            初期参照=(観測,),
        )
        self.assertGreater(中核.継続参照件数, 0)
        中核.継続状態を初期化()
        self.assertEqual(中核.継続記憶資料件数, 0)
        self.assertEqual(中核.継続認識件数, 0)
        self.assertEqual(中核.継続形成関係件数, 0)
        self.assertEqual(中核.適応経験数, 0)
        self.assertEqual(中核.継続参照件数, 0)


if __name__ == "__main__":
    unittest.main()
