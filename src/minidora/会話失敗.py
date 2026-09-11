"""失敗を資料の本文ではなく、登録済みModuleの診断として上位へ戻す。"""
from dataclasses import asdict, dataclass
import json
from .製品版.型 import 能力結果

接頭 = '会話失敗:'
分類 = frozenset(('資料不足', '入力不正', '適用範囲不一致', '未解釈', '矛盾', '能力不足'))

@dataclass(frozen=True, slots=True)
class 失敗署名:
    種類: str
    対象: str
    詳細: str

    def 符号(self):
        if self.種類 not in 分類 or any(type(x) is not str or len(x) > 1024 for x in (self.対象, self.詳細)):
            raise ValueError('失敗署名の契約違反')
        return 接頭 + json.dumps(asdict(self), ensure_ascii=False, sort_keys=True)

    @classmethod
    def 復元(cls, text):
        if type(text) is not str or not text.startswith(接頭) or len(text) > 8192:
            return None
        try:
            raw = json.loads(text[len(接頭):])
            if type(raw) is not dict or set(raw) != {'種類', '対象', '詳細'}: return None
            result = cls(**raw); result.符号()
            return result
        except (ValueError, TypeError, RecursionError):
            return None


def 不成立(kind, target, detail):
    return 能力結果(False, '', 保留理由=失敗署名(kind, target, detail).符号())
