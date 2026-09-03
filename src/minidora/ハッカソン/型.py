from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime
from typing import Any, Mapping


def 監査値へ(value: Any) -> Any:
    """hash/JSON用に値を安定した基本型へ変換する。"""
    if is_dataclass(value):
        return 監査値へ(asdict(value))
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): 監査値へ(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (tuple, list)):
        return [監査値へ(item) for item in value]
    if isinstance(value, set):
        return sorted((監査値へ(item) for item in value), key=repr)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return repr(value)


@dataclass(frozen=True, slots=True)
class ニュース項目:
    識別子: str
    題名: str
    要約素材: str
    出典名: str
    URL: str
    公開時刻: datetime | None = None

    def 監査辞書(self) -> dict[str, Any]:
        return 監査値へ(self)


@dataclass(frozen=True, slots=True)
class 監査イベント:
    番号: int
    段階: str
    モジュール: str
    モジュール版: str
    入力: Any
    出力: Any
    根拠識別子: tuple[str, ...]
    前段ハッシュ: str
    段階ハッシュ: str


@dataclass(frozen=True, slots=True)
class 監査記録:
    追跡ID: str
    セッションID: str
    開始時刻: datetime
    入力文: str
    経路: str
    イベント: tuple[監査イベント, ...]
    最終応答: str
    最終状態: str
    ルートハッシュ: str

    def 監査辞書(self) -> dict[str, Any]:
        return 監査値へ(self)


@dataclass(frozen=True, slots=True)
class チャット応答:
    本文: str
    追跡ID: str
    監査ハッシュ: str
    経路: str
    状態: str = "合格"

    def API辞書(self) -> dict[str, str]:
        return {
            "response": self.本文,
            "trace_id": self.追跡ID,
            "trace_hash": self.監査ハッシュ,
            "route": self.経路,
            "status": self.状態,
        }
