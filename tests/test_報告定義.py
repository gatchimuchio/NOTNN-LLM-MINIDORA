"""原位置付きの報告名詞定義。実検索で観測した題材を正解表へ入れない。"""
from copy import deepcopy
import unittest
from minidora.HDS運用.資料回答 import _定義文を読む, 記載関係を読む
from minidora.HDS運用.意味資料 import 資料意味を選ぶ
from minidora.HDS運用.内容構成 import 資料文章を検査
from test_基本チャット内容 import 要求, 実行
from minidora.製品版.型 import 能力結果


class 報告定義試験(unittest.TestCase):
    def test_前置範囲と報告と選言修飾を原文のまま保持する(self):
        for 対象, 主部 in (("保管箱", "保管用の容器"), ("供給網", "供給用の設備")):
            文 = f'資料分類の中で{対象}は、「保存又は供給」を目的とする{主部}であるとされ、用途を説明しています。'
            読み = _定義文を読む(文)
            self.assertEqual(読み["主語"], 対象)
            self.assertIsNone(読み["報告定義"]["報告主体"])
            証明 = 読み["報告定義"]
            for 名 in ("前置", "対象", "接続", "名詞述部", "報告標識", "後続"):
                項 = 証明[名]
                self.assertEqual(文[項["開始"]:項["終了"]], 項["原文"])
            成果 = 実行(文, 要求(主題=(対象,), 関係焦点=("定義",)))
            self.assertIn(文, 成果.本文)
            self.assertIn("又は", 成果.本文)
            self.assertTrue(資料文章を検査(成果))

    def test_下位対象の定義を上位対象へ転用しない(self):
        with self.assertRaises(ValueError):
            実行("小型保管箱は保管用の容器であるとされ、用途を説明しています。",
                 要求(主題=("保管箱",), 関係焦点=("定義",)))

    def test_撤回と非名詞と条件付き主体を定義へ昇格しない(self):
        for 文 in ("保管箱は安全であるとされ、用途を説明しています。",
                   "保管箱は保管用の容器であるとされ、後に撤回された。",
                   "条件を満たす場合の保管箱は保管用の容器であるとされ、用途を説明しています。"):
            self.assertIsNone(_定義文を読む(文))

    def test_原本文改変を再封印した内容だけで受け入れない(self):
        成果 = 実行("保管箱は保管用の容器であるとされ、用途を説明しています。",
                    要求(主題=("保管箱",), 関係焦点=("定義",)))
        改変 = deepcopy(成果)
        改変.データ["意味成果"]["意味"]["命題"][0]["本文"] = "保管箱は安全です。"
        self.assertFalse(資料文章を検査(改変))

    def test_報告の後続理由を独立事実や作用へ転写しない(self):
        文 = "保管箱は保管用の容器であるとされ、温度が高いため、保管箱は変形する。"
        構造 = 資料意味を選ぶ({"開発資料": 能力結果(True, 文)}, 要求(主題=("保管箱",)))
        行 = 記載関係を読む(構造)[0]
        self.assertIsNone(行["関係"]["理由"])
        self.assertIsNone(行["関係"]["目的"])
        self.assertIsNone(行["命題"])
        self.assertIsNone(行["資料作用"]["作用"])
        self.assertEqual(行["資料作用"]["動作核候補"], [])
        with self.assertRaises(ValueError):
            実行(文, 要求(操作="理由", 主題=("保管箱",), 関係焦点=("変形する",)))


if __name__ == "__main__":
    unittest.main()
