from __future__ import annotations
import json
from pathlib import Path

class 命令形P:
    def __init__(self, document: dict):
        self.document = document
        self.規則 = {x["適用"]: x for x in document.get("規則", [])}

    @classmethod
    def JSON(cls, path: str | Path):
        return cls(json.loads(Path(path).read_text(encoding="utf-8")))

    def 選ぶ(self, 要求種: str):
        return self.規則.get(要求種)
