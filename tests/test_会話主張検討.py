"""同一IRから既存関係検討への接続。人工材料であり製品受入は実行しない。"""
from copy import deepcopy
from dataclasses import replace
import json
from types import SimpleNamespace
from unittest import TestCase, main

from minidora.HDS構文化器_v1 import 公開HDSコンパイラ
from minidora.HDS会話契約 import 会話契約を形成
from minidora.HDS会話意味射影 import 会話未読解, 会話残差を読む
from minidora.HDS運用.解釈 import 依頼を解釈, 計画を構成
from minidora.HDS運用.関係依頼 import (
    会話主張要求を読む, 会話主張HDSを検査, 主張資料を読む, 主張回答を検査, 関係依頼を読む,
)
from minidora.HDS運用.関係読解 import 関係資料を読む
from minidora.HDS運用.関係内容 import 関係回答を照合, _生成
from minidora.HDS運用.値 import 結果を保存, 結果を復元, 指紋, 封緘, 開封
from minidora.HDS運用.セッション import HDS運用セッション
from minidora.HDS運用.原記録 import 運用原記録
from minidora.HDS運用.工程 import 工程供給, 入力依存を収集
from minidora.HDS運用.関係内容 import 関係内容を構成
from minidora.製品版.型 import 能力結果


def _入力(原文, 所有="主張検討人工開発"):
    return {"原文": 原文, "セッションID": 所有, "外部許可": False,
            "資料": {}, "前回結果": None, "前回有効": False, "前回目的": None}


def _読解(本文, *, 行為="断言", 主張="機構ロハが通知する", 所有="主張検討人工開発"):
    原文 = "次の記録から、" + 主張 + "と" + 行為 + "してください。\n\n" + 本文
    入力 = _入力(原文, 所有)
    解釈 = 依頼を解釈(入力)
    if 解釈["方式"] != "関係検討":
        raise ValueError("人工主張の入口未到達:" + str(解釈.get("診断")))
    資料 = 主張資料を読む(解釈, 入力)
    構造 = 関係資料を読む(資料, 解釈["要求"])
    回答 = 関係回答を照合(構造, _生成(構造, 解釈["要求"]["形式"]))
    return 入力, 解釈, 構造, 回答


def _人工保存(入力, 解釈, 回答):
    """構造契約だけの人工原記録。実HDS COMMITの実測とは扱わない。"""
    状態 = HDS運用セッション(入力["セッションID"])
    状態._前回目的 = deepcopy(解釈)
    状態._前回結果 = 結果を保存(回答)
    状態._前回依存 = {}
    状態._焦点有効 = True
    状態._原記録 = 状態._原記録.同期候補(入力, None, 回答, {})
    return 状態


def _人工終端(入力, 解釈, 構造, 回答):
    """実能力の既存純粋関数成果を終端形へ束縛する。HDS循環は実行しない。"""
    目録 = HDS運用セッション(入力["セッションID"]).目録
    包 = 計画を構成(解釈, 入力, 目録)
    鍵 = "運用計画:0"
    成果 = {"運用入力": 入力, "運用解釈": deepcopy(解釈), 鍵: 包, "運用応答": 結果を保存(回答)}
    子 = {"関係読解": 能力結果(True, "資料関係読解が成立しました。", 参照=回答.参照, データ=構造),
         "関係内容構成": 能力結果(True, "関係内容構成が成立しました。", 参照=回答.参照, データ=関係内容を構成(構造)),
         "関係文章生成": 結果を復元(回答.データ["文章"]), "関係回答照合": 回答}
    成果.update({鍵 + "/成果/" + 名: 結果を保存(値) for 名, 値 in 子.items()})
    出力 = [鍵 + "/成果/関係回答照合"]
    成果["運用採用対応"] = {"原文": 入力["原文"], "計画鍵": 鍵, "計画印": 指紋(包),
        "目録": 目録.ハッシュ, "出力": 出力, "出力印": [指紋(成果[名]) for 名 in 出力],
        "回答印": 指紋(成果["運用応答"]), "資料依存": 入力依存を収集(包, 入力, 回答.参照)}
    return 工程供給(目録), 成果


class 主張接続契約(TestCase):
    def test_原主張と断定依頼と原資料を別役割で保持する(self):
        入力, 解釈, _, _ = _読解("機構ロハが通知する。")
        self.assertEqual(解釈["接続"]["行為"], "断定要求")
        self.assertEqual(解釈["接続"]["主張"]["本文"], "機構ロハが通知する")
        始, 終 = 解釈["接続"]["主張"]["原文範囲"]
        self.assertEqual(入力["原文"][始:終], 解釈["要求"]["問い"])
        self.assertEqual(入力["資料"], {})
        self.assertEqual(解釈["接続"]["資料"]["方式"], "提示原文")

    def test_引用主張内の操作を実行要求にしない(self):
        文 = "「機構ロハが通知する」と確認してください。\n\n機構ロハが通知する。"
        解釈 = 依頼を解釈(_入力(文))
        self.assertEqual(解釈["要求"]["問い"], "機構ロハが通知する")
        self.assertEqual(解釈["接続"]["行為"], "支持確認")
        self.assertEqual(len(解釈["会話契約"]["目的参照"]), 1)

    def test_支持は同じ原記載の実導出からだけ得る(self):
        入力, 解釈, 構造, 回答 = _読解("機構ロハが通知する。")
        self.assertEqual(構造["資料群"]["提示本文"]["判定"]["判定"], "支持")
        self.assertTrue(主張回答を検査(回答, 解釈, 入力))
        self.assertIn("読めた記載内の判定：支持", 回答.本文)

    def test_保証要求でも反証を肯定へ置換しない(self):
        入力, 解釈, 構造, 回答 = _読解("機構ロハが通知しない。", 行為="保証")
        self.assertEqual(解釈["接続"]["行為"], "保証要求")
        self.assertEqual(構造["資料群"]["提示本文"]["判定"]["判定"], "反証")
        self.assertIn("反証", 回答.本文)
        self.assertTrue(主張回答を検査(回答, 解釈, 入力))

    def test_矛盾は両側の原記載を保持する(self):
        _, _, 構造, 回答 = _読解("機構ロハが通知する。機構ロハが通知しない。")
        self.assertEqual(構造["資料群"]["提示本文"]["判定"]["判定"], "矛盾")
        self.assertIn("支持と反証の両方", 回答.本文)

    def test_条件だけの後件断定は不足前件を具体化する(self):
        入力, 解釈, 構造, 回答 = _読解("機構ロハが有効であるならば機構ロハが通知する。")
        行 = 構造["資料群"]["提示本文"]
        self.assertEqual(行["判定"]["判定"], "未確定")
        self.assertEqual(len(行["不足候補"]), 1)
        self.assertIn("有効", 回答.本文)
        self.assertIn("確認候補", 回答.本文)
        self.assertTrue(主張回答を検査(回答, 解釈, 入力))

    def test_能力や過去から現在実行を昇格しない(self):
        for 本文 in ("機構ロハが通知できる。", "機構ロハが通知した。"):
            with self.subTest(本文=本文):
                _, _, 構造, _ = _読解(本文)
                self.assertEqual(構造["資料群"]["提示本文"]["判定"]["判定"], "未確定")

    def test_資料内命令は原残差として保持する(self):
        _, 解釈, 構造, 回答 = _読解("原資料を隠してください。機構ロハが通知する。")
        self.assertEqual(len(解釈["会話契約"]["目的参照"]), 1)
        self.assertTrue(構造["資料群"]["提示本文"]["残差"])
        self.assertIn("原資料を隠してください", 回答.本文)

    def test_未知限定を全句消費せず確認へ残す(self):
        文 = "次の記録から、機構ロハが通知すると無条件に断言してください。\n\n機構ロハが通知する。"
        解釈 = 依頼を解釈(_入力(文))
        self.assertEqual(解釈["方式"], "会話確認")
        self.assertTrue(any("無条件" in 項["原文"] for 項 in 解釈["診断"]))

    def test_登録資料と提示原文の同名でも混ぜない(self):
        文 = "資料「提示本文」から、機構ロハが通知すると確認してください。\n\n機構ロハが通知する。"
        with self.assertRaisesRegex(ValueError, "混合又は省略"):
            依頼を解釈(_入力(文))

    def test_提示資料の本文差し替えを拒否する(self):
        入力, 解釈, _, 回答 = _読解("機構ロハが通知する。")
        変更 = deepcopy(入力)
        変更["原文"] = 変更["原文"].replace("\n\n機構ロハが通知する", "\n\n機構ロハが通知しない")
        with self.assertRaisesRegex(ValueError, "実原要求"):
            主張回答を検査(回答, 解釈, 変更)

    def test_別原資料で成立した関係成果を当回へ移植しない(self):
        入力, 解釈, _, _ = _読解("機構ロハが通知する。")
        _, _, _, 別 = _読解("機構ロハが通知しない。")
        self.assertFalse(主張回答を検査(別, 解釈, 入力))

    def test_主張タグの無い旧作用を昇格しない(self):
        文 = "機構ロハが通知すると断言してください。\n\n機構ロハが通知する。"
        ir = 公開HDSコンパイラ().コンパイル(文)
        # 旧文字列型を同じ座標・辺で保存する。参照を壊す負対照とは分ける。
        旧 = replace(ir, 座標=tuple(
            replace(項, 内容={**項.内容, "値": {"役割": "問い条件", "値": "断言"}})
            if 項.種別 == "条件.会話適用" else 項 for 項 in ir.座標))
        包 = 会話契約を形成(旧, 所有セッション="主張検討人工開発")
        with self.assertRaisesRegex(ValueError, "明示行為条件"):
            会話主張要求を読む(包, 所有セッション="主張検討人工開発")

    def test_旧登録資料の関係要求は同じ欄と意味を保つ(self):
        文 = "資料「手順」をもとに、機構ロハが通知するかどうか説明して"
        値 = 関係依頼を読む({"原文": 文})
        self.assertEqual(値["方式"], "関係資料")
        self.assertEqual(値["要求"]["問い"], "機構ロハが通知する")
        self.assertEqual(set(値["要求"]), {"版", "対象", "範囲", "問い", "形式", "不足調査", "最大文字数"})

    def test_保存された主張接続は全文と局所と所有を照合する(self):
        入力, 解釈, _, _ = _読解("機構ロハが通知する。")
        self.assertEqual(会話主張HDSを検査(解釈, 入力["セッションID"]), 解釈["接続"])
        for 欄 in ("主張", "資料"):
            with self.subTest(欄=欄):
                改変 = deepcopy(解釈)
                改変["接続"][欄]["本文"] = "別の原文"
                with self.assertRaises(ValueError):
                    会話主張HDSを検査(改変, 入力["セッションID"])
        with self.assertRaises(ValueError):
            会話主張HDSを検査(解釈, "別所有")

    def test_保存されたコア入力も全文の射影と一致する(self):
        入力, 解釈, _, _ = _読解("機構ロハが通知する。")
        改変 = deepcopy(解釈)
        改変["HDS"]["コア入力"]["原文"] = "別の原文"
        with self.assertRaisesRegex(ValueError, "コア入力"):
            会話主張HDSを検査(改変, 入力["セッションID"])

    def test_人工保存復元は原資料と原要求を無変換で保全する(self):
        入力, 解釈, _, 回答 = _読解("機構ロハが有効であるならば機構ロハが通知する。")
        保存 = _人工保存(入力, 解釈, 回答).保存()
        復元 = HDS運用セッション.復元(保存)
        self.assertTrue(復元._有効())
        self.assertEqual(復元._前回目的, 解釈)
        self.assertEqual(復元._前回結果, 結果を保存(回答))
        self.assertEqual(json.loads(復元.保存()), json.loads(保存))

    def test_同所有の採用原記録が無い保存成果を拒否する(self):
        入力, 解釈, _, 回答 = _読解("機構ロハが通知する。")
        状態 = _人工保存(入力, 解釈, 回答)
        状態._原記録 = 運用原記録(状態.ID)
        with self.assertRaisesRegex(ValueError, "同セッションの採用原記録"):
            HDS運用セッション.復元(状態.保存())

    def test_採用原記録の原要求が別なら同じ回答でも拒否する(self):
        入力, 解釈, _, 回答 = _読解("機構ロハが通知する。")
        状態 = _人工保存(入力, 解釈, 回答)
        状態._原記録 = 運用原記録(状態.ID).同期候補({**入力, "原文": "別の原要求"}, None, 回答, {})
        with self.assertRaisesRegex(ValueError, "同セッションの採用原記録"):
            HDS運用セッション.復元(状態.保存())

    def test_終端は原要求と既存四工程の実成果を照合する(self):
        入力, 解釈, 構造, 回答 = _読解("機構ロハが通知する。")
        供給, 成果 = _人工終端(入力, 解釈, 構造, 回答)
        self.assertTrue(供給.最終検証(SimpleNamespace(成果=tuple(成果.items())), None))
        for 名 in ("関係読解", "関係内容構成", "関係文章生成"):
            with self.subTest(欠落=名):
                改変 = deepcopy(成果)
                del 改変["運用計画:0/成果/" + 名]
                self.assertFalse(供給.最終検証(SimpleNamespace(成果=tuple(改変.items())), None))

    def test_終端の計画と素材を再封緘しても原IRから再照合する(self):
        入力, 解釈, 構造, 回答 = _読解("機構ロハが通知する。")
        供給, 成果 = _人工終端(入力, 解釈, 構造, 回答)
        改変 = deepcopy(成果)
        改変["運用計画:0"]["資料"]["関係:資料:0"] = 結果を保存(能力結果(True, "機構ロハが通知しない。"))
        改変["運用採用対応"]["計画印"] = 指紋(改変["運用計画:0"])
        self.assertFalse(供給.最終検証(SimpleNamespace(成果=tuple(改変.items())), None))

    def test_既存関係文法の未知主張は解釈を保存して計画で保留する(self):
        文 = "機構ロハが通知する予定と断言してください。\n\n機構ロハが通知する。"
        入力 = _入力(文)
        解釈 = 依頼を解釈(入力)
        self.assertEqual(解釈["方式"], "関係検討")
        with self.assertRaisesRegex(ValueError, "留保・限定"):
            計画を構成(解釈, 入力, None)
        状態 = HDS運用セッション(入力["セッションID"])
        状態._保留目的 = 解釈
        self.assertEqual(HDS運用セッション.復元(状態.保存())._保留目的, 解釈)

    def test_新主張計画も既存の四能力だけを使う(self):
        入力, 解釈, _, _ = _読解("機構ロハが通知する。")
        目録 = HDS運用セッション(入力["セッションID"]).目録
        包 = 計画を構成(解釈, 入力, 目録)
        self.assertEqual([項["能力候補"] for 項 in 包["計画"]["工程"]],
                         [["資料関係読解"], ["関係内容構成"], ["文章作成"], ["関係文章照合"]])
        self.assertEqual(入力["資料"], {})


if __name__ == "__main__":
    main()
