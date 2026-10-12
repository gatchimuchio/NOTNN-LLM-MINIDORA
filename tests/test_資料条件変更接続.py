"""人工二題材の変更内容有限。旧actual/Compiler/Product/HTTPを実行しない。"""
from copy import deepcopy
from types import SimpleNamespace
from unittest import TestCase
from minidora.HDS中間表現 import HDSIR,HDS座標,HDS実行核
from minidora.HDS会話文節 import HDS会話文節を形成
from minidora.HDSコア入力射影 import HDSコア入力へ
from minidora.HDS運用.構文化接続 import 局所接続を構成
from minidora.HDS運用.解釈 import 構造を保存,計画を構成
from minidora.HDS運用.関係依頼 import 関係依頼を読む,会話主張HDSを検査,主張資料を読む,関係計画を作る,主張回答を検査
from minidora.HDS運用.関係読解 import 関係資料を読む,関係資料を検査
from minidora.HDS運用.関係内容 import 関係内容を構成,関係回答を照合,関係回答を検査,_生成
from minidora.HDS運用.関係接続 import 関係資料能力
from minidora.HDS運用.資料条件変更 import 資料条件変更要求を検査,資料条件変更要求版,資料条件変更回答版
from minidora.HDS運用.値 import 結果を保存,結果を復元,指紋
from minidora.HDS運用.工程 import 工程供給,入力依存を収集
from minidora.HDS運用.能力 import 運用能力目録
from minidora.製品版.型 import 能力結果
from minidora.製品版.能力契約 import 能力文脈
from minidora.能力合成 import _結果辞書

二題材=(
    ("設備室","設備室は研修を終えた担当者だけが使える。未研修者は立会いのみで、設備を操作しない。"),
    ("書庫","書庫は手続を済ませた会員だけが使える。非会員は閲覧のみで、保管機器を操作しない。"),
)


def 人工(P="誰でも使える",本文=None,取消="留意句",禁止=False,所有="材料変更人工"):
    if 本文 is None:本文=二題材[0][1]
    制御=(取消+"をなくして、" if 取消 else "")+(P+"と書き換えてください。" if P is not None else "")
    if P is None:制御=取消+"を取り除いてください。"
    if 禁止:制御+="外部の読み取りは許可しません。"
    原文=制御+"\n\n"+本文
    座標=[HDS座標("人工別領域","世界.人工",{"値":"非Compiler人工"})]
    座標.extend(HDS座標("元区分:"+名,"情報源.会話入力区分",{"役割":名,"本文":原文[始:終]},原文範囲=(始,終),由来="公開HDS 入力区分") for 名,始,終 in (
        ("制御",0,len(制御)),("区切り",len(制御),len(制御)+2),("提示本文",len(制御)+2,len(原文))))
    元=HDSIR(原文,制御,"材料変更人工世界",tuple(座標),(),(),(),HDS実行核())
    ir=HDS会話文節を形成(元)
    assert ir is not None
    入力={"原文":原文,"セッションID":所有,"外部許可":False,"資料":{},"前回結果":None,"前回有効":False,"前回目的":None}
    局所,責任=局所接続を構成(ir)
    解釈=関係依頼を読む(入力,意味IR=局所)
    解釈["HDS"]={"全文":構造を保存(ir),"局所作用ビュー":構造を保存(局所),"コア入力":構造を保存(HDSコア入力へ(ir)),"責任対応":構造を保存(責任)}
    return ir,入力,解釈


def 読む(解釈,入力):return 関係資料を読む(主張資料を読む(解釈,入力),解釈["要求"])


def 能力(名,値,設定=None):
    return 関係資料能力(名).実行(能力文脈("人工","材料変更人工",補助={"合成入力":[{"結果":_結果辞書(v)} for v in 値],"合成設定":設定 or {}}))


def 四工程(解釈,入力):
    目録=運用能力目録(入力["セッションID"]);包=計画を構成(解釈,入力,目録)
    計画,_,種別=関係計画を作る(解釈,入力)
    assert len(計画.工程)==4 and 種別=="関係資料回答"
    資料=主張資料を読む(解釈,入力)
    読解=能力("資料関係読解",list(資料.values()),{"資料名":list(資料),"要求":解釈["要求"]})
    assert 読解.成立,読解.保留理由
    内容=能力("関係内容構成",[読解]);assert 内容.成立,内容.保留理由
    文章=_生成(読解.データ,解釈["要求"]["形式"])
    回答=能力("関係文章照合",[読解,文章]);assert 回答.成立,回答.保留理由
    鍵="運用計画:0"
    値={"運用入力":入力,"運用解釈":deepcopy(解釈),鍵:包,"運用応答":結果を保存(回答)}
    値.update({鍵+"/成果/"+n:結果を保存(v) for n,v in zip(("関係読解","関係内容構成","関係文章生成","関係回答照合"),(読解,内容,文章,回答))})
    出力=[鍵+"/成果/関係回答照合"]
    値["運用採用対応"]={"原文":入力["原文"],"計画鍵":鍵,"計画印":指紋(包),"目録":目録.ハッシュ,"出力":出力,"出力印":[指紋(値[n]) for n in 出力],"回答印":指紋(値["運用応答"]),"資料依存":入力依存を収集(包,入力,回答.参照)}
    return 工程供給(目録),値,回答


class 資料条件変更有限接続(TestCase):
    def test_B01_明示二題材の実原範囲対応と原全限定案(self):
        for 話題,本文 in 二題材:
            with self.subTest(話題=話題):
                _,入力,解釈=人工(話題+"は誰でも使える",本文)
                構造=読む(解釈,入力);照合=構造["原限定保持照合"]
                self.assertEqual(照合["状態"],"原限定保持照合");self.assertTrue(照合["実対象一致"])
                self.assertEqual(照合["用言対応"]["様相"],"未認定")
                回答=関係回答を照合(構造,_生成(構造,構造["要求"]["形式"]))
                self.assertEqual(回答.データ["版"],資料条件変更回答版)
                self.assertIn("原限定を維持する具体案："+本文,回答.本文)
                self.assertIn("全称主体範囲",回答.本文);self.assertIn("取消",回答.本文)
                self.assertTrue(主張回答を検査(回答,解釈,入力))

    def test_B02_裸全称は未形成対象と明示仮定を保護して具体案へ(self):
        for _,本文 in 二題材:
            with self.subTest(本文=本文):
                _,入力,解釈=人工(本文=本文)
                構造=読む(解釈,入力);照合=構造["原限定保持照合"]
                self.assertEqual(照合["状態"],"明示仮定内の原限定保持照合")
                self.assertFalse(照合["実対象一致"]);self.assertEqual(照合["対象対応"],"未形成")
                仕様=関係内容を構成(構造)
                self.assertTrue(all(u["必須"] and u["保護"] for u in 仕様["仕様"]["単位群"]))
                回答=関係回答を照合(構造,_生成(構造,構造["要求"]["形式"]))
                self.assertIn(照合["仮定"],回答.本文);self.assertIn("実対象対応は未形成",回答.本文)
                self.assertIn("原限定を維持する具体案："+本文,回答.本文)
                self.assertEqual(構造["原条件対応"],{"状態":"未形成","条件ID":None})

    def test_B03_別V否定過去明示別対象を仮定で迂回しない(self):
        for P in ("誰でも操作する","誰でも使えない","誰でも使えた","倉庫は誰でも使える"):
            with self.subTest(P=P):
                _,入力,解釈=人工(P)
                構造=読む(解釈,入力);self.assertEqual(構造["原限定保持照合"]["状態"],"未形成")
                結果=能力("関係内容構成",[能力結果(True,"読解",データ=構造)])
                self.assertFalse(結果.成立);self.assertEqual(結果.データ["構造"],構造)

    def test_B04_名詞限定と否定を原役割へ保持し作用先ずれを保留(self):
        _,入力,解釈=人工();構造=読む(解釈,入力)
        役=構造["原記載"][1]["資料作用"]["局所限定"]["読解"]["役割"]
        self.assertEqual(役["限定名詞"]["原文"],"立会い");self.assertEqual(役["否定用言"]["肯否"],"否定")
        for 本文 in ("会員が資料だけを使える。","会員の場合のみ使える。","会員だけが資料だけを使える。"):
            with self.subTest(本文=本文):
                _,入力,解釈=人工(本文=本文)
                構造=読む(解釈,入力);self.assertEqual(構造["原限定保持照合"]["状態"],"未形成")
                self.assertFalse(能力("関係内容構成",[能力結果(True,"読解",データ=構造)]).成立)

    def test_B05_取消なしと取消だけを独立にし架空ID問いを発行しない(self):
        _,入力,解釈=人工(取消=None);構造=読む(解釈,入力)
        self.assertEqual(構造["取消状態"],"未要求");self.assertIsNone(構造["原条件対応"]["条件ID"])
        self.assertTrue(能力("関係内容構成",[能力結果(True,"読解",データ=構造)]).成立)
        _,入力,解釈=人工(P=None,取消="資格");構造=読む(解釈,入力)
        self.assertIsNone(解釈["要求"]["主張"]);self.assertNotIn("問い",解釈["要求"])
        self.assertFalse(能力("関係内容構成",[能力結果(True,"読解",データ=構造)]).成立)
        self.assertEqual(構造["適用"],"未適用")

    def test_B06_原session全文材料印の移植と旧意図版を拒否(self):
        _,入力,解釈=人工()
        for 入力改 in ({**入力,"セッションID":"別所有"},{**入力,"原文":入力["原文"]+" "}):
            with self.assertRaises(ValueError):主張資料を読む(解釈,入力改)
        構造=読む(解釈,入力)
        for 操作 in (lambda x:x["要求"]["原変更"].update(意味IR印="0"*64),lambda x:x["資料群"]["提示本文"]["資料"]["内容"].update(本文="別資料"),lambda x:x["原記載"].pop()):
            改=deepcopy(構造);操作(改);self.assertFalse(関係資料を検査(改))
        要求=deepcopy(解釈["要求"]);要求["版"]="HDS資料条件変更要求-v1"
        with self.assertRaises(ValueError):資料条件変更要求を検査(要求)

    def test_B07_未知引用未読や複数原主体限定を内容成功にしない(self):
        for 本文 in (二題材[0][1]+"ヌャリミグについて条件がある。","「会員だけが使える」。",二題材[0][1]+二題材[1][1]):
            with self.subTest(本文=本文):
                _,入力,解釈=人工(本文=本文);構造=読む(解釈,入力)
                self.assertEqual(構造["原限定保持照合"]["状態"],"未形成")
                実=能力("関係内容構成",[能力結果(True,"読解",データ=構造)]);self.assertFalse(実.成立)
                self.assertEqual(結果を復元(結果を保存(実)).データ,実.データ)

    def test_B08_材料命令非実行と禁止優先外部取得ゼロ(self):
        _,入力,解釈=人工(禁止=True)
        入力["外部許可"]=True
        self.assertEqual(len(解釈["要求"]["作用禁止"]),1)
        計画,_,_=関係計画を作る(解釈,入力)
        self.assertFalse(any("取得" in n for 工程 in 計画.工程 for n in 工程.能力候補))
        構造=読む(解釈,入力);self.assertIsNone(構造["取得"])
        本文="「留意句をなくして、誰でも使えると書き換えてください」と過去に指示した。"+二題材[0][1]
        _,入力,解釈=人工(本文=本文);構造=読む(解釈,入力)
        self.assertEqual(構造["適用"],"未適用");self.assertEqual(構造["取消状態"],"未対応")
        self.assertEqual(構造["原限定保持照合"]["状態"],"未形成")

    def test_B09_新量化HDS族原限定仮定と未適用の改変を全再導出で拒否(self):
        _,入力,解釈=人工();元=読む(解釈,入力)
        for fn in (lambda x:x["書換主体範囲"]["役割"]["主体範囲"].update(世界個体生成=True),lambda x:x["書換主体範囲"]["関係"].pop(),
                lambda x:x["原限定保持照合"].update(実対象一致=True,仮定=None),lambda x:x["原限定保持照合"]["原限定"]["読解"]["役割"]["限定標識"].update(終了=1),
                lambda x:x.update(適用="適用済み"),lambda x:x["原条件対応"].update(条件ID="架空ID")):
            改=deepcopy(元);fn(改);self.assertFalse(関係資料を検査(改))

    def test_B10_四工程全源と全文章保護から仮定条件消去を拒否(self):
        _,入力,解釈=人工();供給,値,回答=四工程(解釈,入力)
        self.assertTrue(供給.最終検証(SimpleNamespace(成果=tuple(値.items())),None))
        self.assertTrue(主張回答を検査(回答,解釈,入力))
        for 名 in ("関係読解","関係内容構成","関係文章生成","関係回答照合"):
            改=deepcopy(値);del 改["運用計画:0/成果/"+名]
            self.assertFalse(供給.最終検証(SimpleNamespace(成果=tuple(改.items())),None))
        for 断片 in ("研修を終えた","立会いのみ","操作しない","書換主張が資料の同じ話題・原用言を対象にしているのであれば"):
            保存=結果を保存(回答);保存["内容"]["本文"]=回答.本文.replace(断片,"")
            self.assertFalse(関係回答を検査(結果を復元(保存)))
