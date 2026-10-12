"""人工値で外送前停止と別版監査を検査する。実Google通信・一般意味品質の採点ではない。"""
from dataclasses import replace
import json
import unittest
from unittest.mock import patch

from minidora.公開送信条件 import 公開送信条件, 公開送信停止, 公開語を検査
from minidora.取得実行制御 import 公開取得上限, 共有取得制御
from minidora.知識取得 import 知識取得器, 知識取得要求
from minidora.製品版.Google検索 import GoogleCloud検索供給器
from minidora.製品版.監査 import 監査台帳, 監査仕様版, 安全監査仕様版
from minidora.製品版.型 import 能力結果, 参照資料
from minidora.HDS運用.製品 import HDS製品ミニドラ
from minidora.HDS運用.セッション import 運用応答
from Google検索予算fixture import 局所送信予算
from test_知識取得 import 試験検索, 試験本文, 候補, document, BASE


class _認証:
    def __init__(self):
        self.calls = []

    def 認証する(self, url, *, 取得制御):
        self.calls.append(url)
        raise AssertionError("停止前に認証してはいけない")


class 公開送信条件試験(unittest.TestCase):
    def test_既知形式と全角表記は原値を返さず停止する(self):
        for 値 in ("user@example.test", "０９０－１２３４－５６７８", "Bearer LOCAL_TEST_TOKEN",
                   "eyJhbGciOiJIUzI1NiJ9.cHVibGlj.signature", "パスワード：LOCAL_TEST_SECRET",
                   "住所は人工県人工町一番地", "https://example.test/?token=LOCAL_TEST_TOKEN"):
            with self.subTest(値=値), self.assertRaises(公開送信停止) as 停止:
                公開語を検査(値)
            self.assertNotIn(値, json.dumps(停止.exception.記録(), ensure_ascii=False))
            self.assertEqual(str(停止.exception), "公開送信条件不成立")

    def test_秘密の一般語だけで公開主題を停止しない(self):
        for 値 in ("メール 暗号化", "電話 仕組み", "APIキー 定義", "パスワード 管理", "家計調査 定義"):
            公開語を検査(値)

    def test_前会話の秘密値と必要語への分割を当回だけ照合する(self):
        条件 = 公開送信条件(("APIキーは「LOCAL TEST SECRET」です。",), 人名=False)
        for 語, 必要 in (("LOCAL TEST SECRET", ()), ("LOCALTESTSECRET", ()),
                        ("公開主題", ("LOCAL", "TEST", "SECRET"))):
            with self.subTest(語=語), self.assertRaises(公開送信停止):
                公開語を検査(語, 必要, 条件)
        公開語を検査("公開主題", ("定義",), 条件)
        公開語を検査("LOCAL TEST SECRET", (), 公開送信条件())

    def test_観測済みの語尾付き値と分割監査も同じ境界で除外する(self):
        条件 = 公開送信条件(("APIキーはLOCAL_TEST_SECRETです。", "APIキーは「LOCAL TEST SECOND」です。"), 人名=False)
        for 語 in ("LOCAL_TEST_SECRET", "LOCALTESTSECOND"):
            with self.subTest(語=語), self.assertRaises(公開送信停止):
                公開語を検査(語, 条件=条件)
            self.assertEqual(条件.安全表現(語), "[非公開値を含む文字列]")
        表示 = 条件.安全表現({"必要語": ["LOCAL", "TEST", "SECOND"]})
        self.assertNotIn("SECOND", json.dumps(表示))
        for 構造 in ({"a": "LOCAL", "b": "TEST", "c": "SECOND"},
                     {"a": {"値": "LOCAL"}, "b": ["TEST", "SECOND"]}):
            表示 = 条件.安全表現(構造)
            self.assertNotIn("SECOND", json.dumps(表示))

    def test_公開主題の説明から新しい秘密値を推測しない(self):
        条件 = 公開送信条件(("パスワードとは何か。",), 人名=False)
        説明 = "パスワードは本人確認に使う文字列である。"
        self.assertEqual(条件.安全表現(説明), 説明)

    def test_固定字句の人名候補は公開人物と推測しない(self):
        with self.assertRaises(公開送信停止) as 停止:
            公開語を検査("山田太郎 経歴")
        self.assertIn("人名候補", 停止.exception.分類)
        公開語を検査("統計局 調査概要")

    def test_取得要求の必要語も検索計数と追跡の前に停止する(self):
        検索 = 試験検索((候補(),))
        本文 = 試験本文({BASE + "a": document()})
        制御 = 共有取得制御(公開取得上限(最小通信間隔秒=0))
        器 = 知識取得器(検索, 本文).制御を束縛(制御)
        for 要求 in (知識取得要求("user@example.test", ("電圧",)),
                     知識取得要求("公開主題", ("user@example.test",))):
            結果 = 器.実行(要求, 外部読取許可=True)
            self.assertFalse(結果.成立)
            self.assertEqual(結果.保留理由, "公開送信条件不成立")
            self.assertNotIn("user@example.test", json.dumps(結果.データ, ensure_ascii=False))
            self.assertNotIn("要求", 結果.データ)
        self.assertEqual(検索.calls, [])
        self.assertEqual(本文.calls, [])
        self.assertTrue(all(v == 0 for v in 制御.記録()["使用"].values()))

    def test_候補継続も当回の保護値を外送しない(self):
        検索 = 試験検索((候補(),))
        本文 = 試験本文({BASE + "a": document()})
        器 = 知識取得器(検索, 本文)
        前 = 器.実行(知識取得要求("公開主題", ("電圧",)), 外部読取許可=True)
        制御 = 共有取得制御(公開取得上限(), 公開条件=公開送信条件(("APIキーは公開主題。",), 人名=False))
        結果 = 器.制御を束縛(制御).継続(知識取得要求("公開主題", ("電圧",)), 前, 外部読取許可=True)
        self.assertEqual(結果.保留理由, "公開送信条件不成立")
        self.assertEqual(len(検索.calls), 1)
        self.assertEqual(len(本文.calls), 1)
        self.assertNotIn("公開主題", json.dumps(結果.データ, ensure_ascii=False))

    def test_直接Googleも認証と予約と通信の前に止める(self):
        認証 = _認証()
        予算 = 局所送信予算(認証)
        器 = GoogleCloud検索供給器("minidora-507702", "minidora-public-web", 認証,
                                    送信予算=予算, 許可ホスト=("example.test",))
        with patch.object(予算, "予約する") as 予約, patch("minidora.公開本文取得.socket.create_connection") as 接続:
            with self.assertRaises(公開送信停止):
                器.検索("user@example.test")
        self.assertEqual(認証.calls, [])
        予約.assert_not_called()
        接続.assert_not_called()

    def test_本番候補は文脈なしの直接呼出しと裸制御を拒否する(self):
        認証 = _認証()
        器 = GoogleCloud検索供給器("minidora-507702", "minidora-public-web", 認証,
             送信予算=局所送信予算(認証), 許可ホスト=("example.test",), 公開条件必須=True)
        for 対象 in (器, 器.制御を束縛(共有取得制御(公開取得上限()))):
            with self.assertRaises(公開送信停止) as 停止:
                対象.検索("公開主題")
            self.assertEqual(停止.exception.分類, ("文脈未束縛",))
        self.assertEqual(認証.calls, [])

    def test_安全監査は別版で検証し原文は書き換えない(self):
        原文 = "メールはuser@example.test、APIキーはLOCAL_TEST_SECRET。"
        条件 = 公開送信条件((原文,), 人名=False)
        台帳 = 監査台帳()
        会話 = 台帳.開始(原文, "user@example.test", 安全表現=条件.安全表現)
        会話.記録("入力", "人工", "v1", {"原文": 原文}, {"値": "LOCAL_TEST_SECRET"})
        記録 = 会話.確定("user@example.test", "SUSPEND")
        self.assertEqual(記録.仕様版, 安全監査仕様版)
        self.assertTrue(台帳.検証(記録.追跡ID))
        表示 = json.dumps(記録.辞書化(), ensure_ascii=False)
        for 秘匿 in ("user@example.test", "LOCAL_TEST_SECRET"):
            self.assertNotIn(秘匿, 表示)
        self.assertIn("user@example.test", 原文)
        台帳._records[記録.追跡ID] = replace(記録, 最終応答="改変")
        self.assertFalse(台帳.検証(記録.追跡ID))
        旧 = 台帳.開始("公開主題", "old").確定("公開応答", "APPROVE")
        self.assertEqual(旧.仕様版, 監査仕様版)
        self.assertTrue(台帳.検証(旧.追跡ID))

    def test_安全監査の数値秘匿と鍵衝突と未知型を黙って変換しない(self):
        条件 = 公開送信条件(("暗証番号は1234。",), 人名=False)
        台帳 = 監査台帳()
        会話 = 台帳.開始("公開主題", "safe", 安全表現=条件.安全表現)
        会話.記録("値", "人工", "v1", {}, {"値": 1234})
        記録 = 会話.確定("保留", "SUSPEND")
        self.assertNotIn("1234", json.dumps(記録.辞書化()))
        self.assertTrue(台帳.検証(記録.追跡ID))
        for 値 in ({1: "人工A", "1": "人工B"}, object()):
            with self.assertRaises(TypeError):
                会話.記録("型", "人工", "v1", 値, {})

    def test_実HDS製品で秘密主題を外送せず原入力と公開監査を分ける(self):
        検索 = 試験検索((候補(),))
        本文 = 試験本文({BASE + "a": document()})
        製品 = HDS製品ミニドラ(基本チャット=True, 手順形成=False,
                              取得器=知識取得器(検索, 本文))
        原文 = "user@example.testとは何ですか。"
        with patch("minidora.公開本文取得.socket.create_connection") as 通信:
            応答 = 製品.応答(原文, セッションID="公開境界検査")
        self.assertEqual(応答.状態, "SUSPEND")
        self.assertEqual(検索.calls, [])
        self.assertEqual(本文.calls, [])
        通信.assert_not_called()
        記録 = 製品.監査台帳.取得(応答.追跡ID)
        self.assertEqual(記録.仕様版, 安全監査仕様版)
        self.assertTrue(製品.監査台帳.検証(応答.追跡ID))
        self.assertNotIn("user@example.test", json.dumps(応答.辞書化(), ensure_ascii=False))
        self.assertNotIn("user@example.test", json.dumps(記録.辞書化(), ensure_ascii=False))
        self.assertEqual(製品.セッション("公開境界検査")._発話[-1]["入力"], 原文)

    def test_製品の本文参照全欄と会話識別子とメタデータも公開表現にする(self):
        秘密 = "user@example.test"
        製品 = HDS製品ミニドラ(手順形成=False)
        主体 = 製品.セッション(秘密)
        参照 = 参照資料(秘密, 秘密, 秘密, "https://example.test/?token=LOCAL_TEST_TOKEN", 本文=秘密)
        原結果 = 運用応答("SUSPEND", 秘密, 結果=能力結果(False, 秘密, 参照=(参照,)),
                           追跡={"原文": 秘密})
        with patch.object(主体, "応答", return_value=原結果) as 実行:
            応答 = 製品.応答("公開主題", セッションID=秘密)
        実行.assert_called_once_with("公開主題", 外部読取許可=False)
        表示 = json.dumps(応答.辞書化(), ensure_ascii=False)
        for 値 in (秘密, "LOCAL_TEST_TOKEN"):
            self.assertNotIn(値, 表示)
        self.assertEqual(主体.ID, 秘密)
        self.assertEqual(原結果.本文, 秘密)
        self.assertTrue(製品.監査台帳.検証(応答.追跡ID))


if __name__ == "__main__":
    unittest.main()
