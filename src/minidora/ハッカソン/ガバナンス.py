from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
from threading import RLock
from typing import Any, Protocol
from uuid import uuid4

from .型 import 監査イベント, 監査記録, 監査値へ


監査仕様版 = "MINIDORA-ハッカソン監査-v0.2"


def _正規JSON(value: Any) -> str:
    return json.dumps(監査値へ(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _ハッシュ(value: Any) -> str:
    return sha256(_正規JSON(value).encode("utf-8")).hexdigest()


class 監査保存先(Protocol):
    def 保存(self, record: 監査記録) -> None: ...


class JSONL監査保存先:
    """1応答1行の追記専用JSONL保存先。単一プロセス内ではflush+fsyncまで行う。"""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._lock = RLock()

    def 保存(self, record: 監査記録) -> None:
        line = _正規JSON(record.監査辞書()) + "\n"
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8", newline="\n") as stream:
                stream.write(line)
                stream.flush()
                os.fsync(stream.fileno())


class 監査セッション:
    def __init__(self, 台帳: "監査台帳", 入力文: str, セッションID: str) -> None:
        self._台帳 = 台帳
        self.追跡ID = uuid4().hex
        self.セッションID = セッションID
        self.開始時刻 = datetime.now(timezone.utc)
        self.入力文 = 入力文
        self.経路 = "未確定"
        self._イベント: list[監査イベント] = []
        self._前段ハッシュ = "0" * 64

    def 経路設定(self, 経路: str) -> None:
        self.経路 = str(経路)

    def 記録(
        self,
        *,
        段階: str,
        モジュール: str,
        モジュール版: str,
        入力: Any,
        出力: Any,
        根拠識別子: tuple[str, ...] = (),
    ) -> 監査イベント:
        number = len(self._イベント) + 1
        material = {
            "監査仕様版": 監査仕様版,
            "追跡ID": self.追跡ID,
            "番号": number,
            "段階": 段階,
            "モジュール": モジュール,
            "モジュール版": モジュール版,
            "入力": 監査値へ(入力),
            "出力": 監査値へ(出力),
            "根拠識別子": 根拠識別子,
            "前段ハッシュ": self._前段ハッシュ,
        }
        stage_hash = _ハッシュ(material)
        event = 監査イベント(
            番号=number,
            段階=段階,
            モジュール=モジュール,
            モジュール版=モジュール版,
            入力=監査値へ(入力),
            出力=監査値へ(出力),
            根拠識別子=tuple(str(item) for item in 根拠識別子),
            前段ハッシュ=self._前段ハッシュ,
            段階ハッシュ=stage_hash,
        )
        self._イベント.append(event)
        self._前段ハッシュ = stage_hash
        return event

    def 確定(self, *, 最終応答: str, 最終状態: str = "合格") -> 監査記録:
        final_material = {
            "監査仕様版": 監査仕様版,
            "追跡ID": self.追跡ID,
            "セッションID": self.セッションID,
            "開始時刻": self.開始時刻,
            "入力文": self.入力文,
            "経路": self.経路,
            "最終応答": 最終応答,
            "最終状態": 最終状態,
            "最終段階ハッシュ": self._前段ハッシュ,
        }
        root_hash = _ハッシュ(final_material)
        record = 監査記録(
            追跡ID=self.追跡ID,
            セッションID=self.セッションID,
            開始時刻=self.開始時刻,
            入力文=self.入力文,
            経路=self.経路,
            イベント=tuple(self._イベント),
            最終応答=最終応答,
            最終状態=最終状態,
            ルートハッシュ=root_hash,
        )
        self._台帳._保存(record)
        return record


class 監査台帳:
    """応答生成経路を保持し、任意の追記専用保存先へ同時永続化できる監査台帳。"""

    def __init__(self, 保存先: 監査保存先 | None = None) -> None:
        self._記録: dict[str, 監査記録] = {}
        self._保存先 = 保存先
        self._lock = RLock()

    def 開始(self, 入力文: str, セッションID: str) -> 監査セッション:
        return 監査セッション(self, 入力文, セッションID)

    def _保存(self, record: 監査記録) -> None:
        with self._lock:
            if record.追跡ID in self._記録:
                raise RuntimeError("同一追跡IDへの上書きは禁止されている")
            self._記録[record.追跡ID] = record
            if self._保存先 is not None:
                self._保存先.保存(record)

    def 取得(self, 追跡ID: str) -> 監査記録 | None:
        with self._lock:
            return self._記録.get(追跡ID)

    def 検証(self, 追跡ID: str) -> bool:
        record = self.取得(追跡ID)
        if record is None:
            return False
        previous = "0" * 64
        for event in record.イベント:
            if event.前段ハッシュ != previous:
                return False
            material = {
                "監査仕様版": 監査仕様版,
                "追跡ID": record.追跡ID,
                "番号": event.番号,
                "段階": event.段階,
                "モジュール": event.モジュール,
                "モジュール版": event.モジュール版,
                "入力": event.入力,
                "出力": event.出力,
                "根拠識別子": event.根拠識別子,
                "前段ハッシュ": event.前段ハッシュ,
            }
            expected = _ハッシュ(material)
            if expected != event.段階ハッシュ:
                return False
            previous = expected
        final_material = {
            "監査仕様版": 監査仕様版,
            "追跡ID": record.追跡ID,
            "セッションID": record.セッションID,
            "開始時刻": record.開始時刻,
            "入力文": record.入力文,
            "経路": record.経路,
            "最終応答": record.最終応答,
            "最終状態": record.最終状態,
            "最終段階ハッシュ": previous,
        }
        return _ハッシュ(final_material) == record.ルートハッシュ

    def JSON取得(self, 追跡ID: str) -> str | None:
        record = self.取得(追跡ID)
        if record is None:
            return None
        return json.dumps(record.監査辞書(), ensure_ascii=False, sort_keys=True, indent=2)
