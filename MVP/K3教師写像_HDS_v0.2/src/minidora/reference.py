from __future__ import annotations
import json
from pathlib import Path

class 外部参照R:
    def __init__(self, 記録群):
        self.記録群 = tuple(dict(x) for x in 記録群)

    @classmethod
    def JSONL(cls, path: str | Path):
        rows = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rows.append(json.loads(line))
        return cls(rows)

    def 問う(self, 主語: str, 関係: str):
        return tuple(x for x in self.記録群 if x["主語"] == 主語 and x["関係"] == 関係)
