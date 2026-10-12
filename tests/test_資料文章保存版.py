"""意味作用の版変更で、旧保存を再生成・再表現へ無言昇格しない対照。"""
from copy import deepcopy
import unittest
from unittest.mock import patch

from minidora.HDS運用.意味資料 import 資料意味を選ぶ
from minidora.HDS運用.内容構成 import (
    _文章, 資料文章を照合, 資料文章を検査, 資料文章を再表現, 資料文章の版を検査,
)
from minidora.HDS運用.値 import 結果を保存
from minidora.製品版.型 import 能力結果


def _現行成果():
    本文 = "測定器丙は表示装置である。"
    要求 = {"版": "HDS一般会話要求-v2", "対象": [], "主題": ["測定器丙"],
            "操作": ["要約"], "形式": "文章", "範囲": "自動", "最大文字数": 24000,
            "問い": "測定器丙の説明", "比較対象": [], "観点": [], "詳細": "標準",
            "提示本文": 本文, "関係焦点": [], "肯否": "未指定"}
    構造 = 資料意味を選ぶ({"版対照": 能力結果(True, 本文)}, 要求)
    return 資料文章を照合(構造, _文章(構造))


class 資料文章保存版試験(unittest.TestCase):
    def test_現行意味成果は再表現後も原構造を保つ(self):
        成果 = _現行成果()
        self.assertTrue(資料文章を検査(成果))
        再 = 資料文章を再表現(成果, "箇条書き")
        self.assertTrue(資料文章を検査(再))
        self.assertEqual(再.データ["構造"], 成果.データ["構造"])
        self.assertEqual(再.データ["意味成果"], 成果.データ["意味成果"])

    def test_旧外側版は原保存を変更せず再生成前に失効(self):
        成果 = _現行成果()
        成果.データ["版"] = "HDS資料文章-v1"
        原保存 = deepcopy(結果を保存(成果))
        with patch("minidora.HDS運用.内容構成.資料文章を照合", side_effect=AssertionError("旧成果の再生成")):
            self.assertFalse(資料文章を検査(成果))
        with self.assertRaisesRegex(ValueError, "保存版.*失効.*明示移行"):
            資料文章を再表現(成果, "文章")
        self.assertEqual(結果を保存(成果), 原保存)

    def test_外側だけ現行に書き換えた旧意味版も再生成前に失効(self):
        成果 = _現行成果()
        成果.データ["意味成果"]["版"] = "HDS資料回答内容-v2"
        原保存 = deepcopy(結果を保存(成果))
        with patch("minidora.HDS運用.内容構成.資料文章を照合", side_effect=AssertionError("旧意味の再生成")):
            self.assertFalse(資料文章を検査(成果))
        with self.assertRaisesRegex(ValueError, "意味保存版.*失効.*再計算"):
            資料文章を再表現(成果, "文章")
        self.assertEqual(結果を保存(成果), 原保存)

    def test_現行版でも意味内容の改変は拒否する(self):
        成果 = _現行成果()
        成果.データ["意味成果"]["使用記載"] = []
        self.assertFalse(資料文章を検査(成果))

    def test_意味版欠落は旧成果と同様に明示失効(self):
        成果 = _現行成果()
        del 成果.データ["意味成果"]
        with self.assertRaisesRegex(ValueError, "意味保存版.*失効"):
            資料文章の版を検査(成果)

    def test_今回提示した本文は継承候補の旧本文で上書きされない(self):
        from minidora.HDS運用.一般依頼 import _一般会話計画を作る
        前回 = _現行成果()
        要求 = deepcopy(前回.データ["構造"]["要求"])
        要求["問い"] = "新しい本文の要約"
        要求["主題"] = []
        要求["提示本文"] = "測定器丁は停止している。"
        入力 = {"原文": "新しい本文の要約", "前回有効": True,
                "前回結果": 結果を保存(前回), "外部許可": False, "資料": {}}
        _, 素材, _ = _一般会話計画を作る(要求, 入力, 根拠継承=True)
        self.assertEqual(素材["一般:資料:0"].本文, 要求["提示本文"])
        self.assertEqual(素材["一般:束縛"].データ["実範囲"], "提示本文")
        self.assertNotIn("取得記録", 素材["一般:要求"].データ)


if __name__ == "__main__":
    unittest.main()
