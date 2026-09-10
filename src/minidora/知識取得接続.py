"""知識取得を既存Capability契約へ接続する。検索の実値は合成設定Dataから受け取る。"""
from __future__ import annotations

from .知識取得 import 知識取得器, 知識取得要求, 知識取得版
from .能力合成 import 登録能力
from .製品版.能力契約 import 能力文脈
from .製品版.型 import 能力結果


class 知識取得Module:
    名前 = "知識取得"
    版 = 知識取得版
    優先度 = 0

    def __init__(self, 取得器: 知識取得器, *, 外部読取許可: bool = False):
        if type(外部読取許可) is not bool:
            raise ValueError("外部読取許可はbool")
        self.取得器, self.外部読取許可 = 取得器, 外部読取許可

    @staticmethod
    def _要求(文脈: 能力文脈) -> 知識取得要求:
        if not isinstance(文脈, 能力文脈):
            raise ValueError("能力文脈型不正")
        settings = (文脈.補助 or {}).get("合成設定", {})
        allowed = set(知識取得要求.__dataclass_fields__)
        if type(settings) is not dict or set(settings) - allowed or not {"検索語", "必要語"} <= set(settings):
            raise ValueError("取得設定が未確定または未対応")
        values = dict(settings)
        for field in ("必要語", "優先ホスト"):
            if field in values and type(values[field]) is list:
                values[field] = tuple(values[field])
        request = 知識取得要求(**values)
        request.検証()
        return request

    def 判定(self, 文脈: 能力文脈) -> float:
        try:
            self._要求(文脈)
            return 1.0
        except (TypeError, ValueError, AttributeError):
            return 0.0

    def 実行(self, 文脈: 能力文脈) -> 能力結果:
        try:
            request = self._要求(文脈)
        except (TypeError, ValueError, AttributeError):
            return 能力結果(False, "", 保留理由="知識取得設定不正")
        return self.取得器.実行(request, 外部読取許可=self.外部読取許可)

    def 登録(self) -> 登録能力:
        return 登録能力(self, 外部読取=True)
