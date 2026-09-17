"""資料意味・内容構成・原文照合を、既存HDSが起動する作用として接続する。"""
from __future__ import annotations
from hashlib import sha256
import json
from ..能力合成 import 登録能力, _参照結合
from ..能力結果復元 import 能力結果を復元
from ..製品版.型 import 能力結果
from ..製品版.能力契約 import 能力文脈
from ..知識取得 import 知識取得版
from .値 import 正準
from .意味資料 import 資料意味を選ぶ
from .内容構成 import 内容仕様を構成, 資料文章を照合, 資料文章を再表現

一般接続版 = "HDS資料文章接続-v1"
_個数 = {"資料意味選択": None, "取得資料意味選択": 1, "資料内容構成": 1, "資料文章照合": 2, "資料文章再表現": 1}


def 取得資料を復元(成果):
    """取得記録と本文の対応を検査。第三者サイトの真実性を証明するものではない。"""
    記録 = 成果.データ
    if (not 成果.成立 or 記録.get("版") != 知識取得版 or 記録.get("状態") != "合格"
            or 記録.get("意味的事実検証") != "未実施"):
        raise ValueError("公開資料取得が未成立")
    原 = {鍵: 値 for 鍵, 値 in 記録.items() if 鍵 != "記録SHA256"}
    印 = sha256(json.dumps(原, ensure_ascii=False, sort_keys=True, allow_nan=False).encode()).hexdigest()
    if 印 != 記録.get("記録SHA256"):
        raise ValueError("取得記録の整合不一致")
    対応 = {行["参照ID"]: 行 for 行 in 記録["資料"]}
    if len(対応) != len(記録["資料"]) or set(対応) != {参照.識別子 for 参照 in 成果.参照}:
        raise ValueError("取得資料と参照の対応不一致")
    資料 = {}
    for 参照 in 成果.参照:
        行 = 対応[参照.識別子]
        if 行["本文SHA256"] != sha256(参照.本文.encode()).hexdigest() or 行["最終URL"] != 参照.URL:
            raise ValueError("取得本文の改変を検出")
        資料[参照.識別子] = 能力結果(True, 参照.本文, 参照=(参照,))
    return 資料


class 一般資料能力:
    版 = 一般接続版
    優先度 = 0

    def __init__(self, 名前):
        if 名前 not in _個数:
            raise ValueError("未対応の資料文章作用")
        self.名前 = 名前

    def _入力(self, 文脈):
        if not isinstance(文脈, 能力文脈) or type(文脈.補助) is not dict:
            raise ValueError("資料文章の構造化入力が必要")
        群, 設定 = 文脈.補助.get("合成入力"), 文脈.補助.get("合成設定", {})
        if type(群) not in (list, tuple) or not 1 <= len(群) <= 16 or type(設定) is not dict:
            raise ValueError("資料文章の入力数・設定が不正")
        if _個数[self.名前] is not None and len(群) != _個数[self.名前]:
            raise ValueError("資料文章の入力数不一致")
        if self.名前 not in ("資料意味選択", "取得資料意味選択", "資料文章再表現") and 設定:
            raise ValueError("資料文章作用に未知の設定")
        値 = tuple(能力結果を復元(行["結果"]) for 行 in 群)
        if any(not 項.成立 for 項 in 値):
            raise ValueError("資料文章の上流不成立")
        return 値, 設定

    def 判定(self, 文脈):
        try:
            self._入力(文脈)
            return 1.0
        except (ValueError, TypeError, KeyError):
            return 0.0

    def 実行(self, 文脈):
        try:
            値, 設定 = self._入力(文脈)
            参照 = _参照結合(参照 for 項 in 値 for 参照 in 項.参照)
            if self.名前 == "資料意味選択":
                if set(設定) != {"要求", "資料名"} or len(設定["資料名"]) != len(値) or len(set(設定["資料名"])) != len(値):
                    raise ValueError("資料の名前・入力対応不一致")
                成果 = 資料意味を選ぶ(dict(zip(設定["資料名"], 値)), 設定["要求"])
            elif self.名前 == "取得資料意味選択":
                成果 = 資料意味を選ぶ(取得資料を復元(値[0]), 設定, 取得記録=正準(値[0].データ))
            elif self.名前 == "資料内容構成":
                成果 = 内容仕様を構成(値[0].データ)
            elif self.名前 == "資料文章照合":
                return 資料文章を照合(値[0].データ, 値[1])
            else:
                if set(設定) != {"形式"}:
                    raise ValueError("再表現の欄不一致")
                return 資料文章を再表現(値[0], 設定["形式"])
            return 能力結果(True, self.名前 + "が成立しました。", 参照=参照, データ=成果)
        except (ValueError, TypeError, KeyError, AttributeError, RecursionError, OverflowError) as 例外:
            return 能力結果(False, "", 保留理由="資料文章不成立:" + str(例外))

    def 登録(self):
        return 登録能力(self)


def 一般資料能力群():
    return tuple(一般資料能力(名前).登録() for 名前 in _個数)
