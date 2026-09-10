"""明示した翻訳対象を既存Capabilityへ接続する。本文を命令に自動昇格しない。"""
from __future__ import annotations

from .多言語変換 import 多言語版, 対訳語, 対訳を変換
from .応答構成 import 能力結果を復元
from .能力合成 import 登録能力
from .製品版.型 import 能力結果
from .製品版.能力契約 import 能力文脈


class 多言語変換Module:
    名前 = "多言語変換"
    版 = 多言語版
    優先度 = 0

    @staticmethod
    def _入力(context):
        if not isinstance(context, 能力文脈) or type(context.補助) is not dict:
            raise ValueError("明示された翻訳入力が必要")
        rows = context.補助.get("合成入力", ())
        settings = context.補助.get("合成設定", {})
        required = {"入力言語", "出力言語", "種別"}
        if (type(rows) is not tuple or len(rows) != 1 or type(settings) is not dict
                or not required <= set(settings) or set(settings) - required - {"対訳", "最大出力バイト数"}):
            raise ValueError("翻訳入力・設定が不正")
        value = 能力結果を復元(rows[0]["結果"])
        if not value.成立:
            raise ValueError("上流不成立")
        options = dict(settings)
        words = options.get("対訳", ())
        if type(words) not in (list, tuple) or len(words) > 128:
            raise ValueError("対訳Data型・件数が不正")
        if any(type(w) is not dict or set(w) != set(対訳語.__dataclass_fields__) for w in words):
            raise ValueError("対訳Dataの項目不一致")
        options["対訳"] = tuple(対訳語(**w) for w in words)
        return value, options

    def 判定(self, context):
        try:
            self._入力(context)
            return 1.0
        except (TypeError, ValueError, KeyError, AttributeError, RecursionError):
            return 0.0

    def 実行(self, context):
        try:
            value, options = self._入力(context)
            return 対訳を変換(value.本文, **options)
        except (TypeError, ValueError, KeyError, AttributeError, RecursionError):
            return 能力結果(False, "", 保留理由="多言語変換入力不正")

    def 登録(self):
        return 登録能力(self)
