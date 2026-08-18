from __future__ import annotations

import json
import math
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from collections import Counter
from pathlib import Path
from typing import Iterable, Sequence

from .型 import ReferenceRecord


def _tokens(text: str) -> tuple[str, ...]:
    normalized = text.casefold().replace("　", " ")
    words = []
    current = []
    for char in normalized:
        if char.isalnum() or "ぁ" <= char <= "龯" or char in {"ー", "々"}:
            current.append(char)
        else:
            if current:
                words.append("".join(current))
                current = []
    if current:
        words.append("".join(current))
    grams = list(words)
    for word in words:
        if len(word) >= 2:
            grams.extend(word[i : i + 2] for i in range(len(word) - 1))
    return tuple(grams)


class ReferenceProvider(ABC):
    provider_id: str

    @abstractmethod
    def search(self, query: str, *, limit: int = 8) -> tuple[ReferenceRecord, ...]:
        raise NotImplementedError


class StaticReferenceProvider(ReferenceProvider):
    def __init__(self, records: Sequence[ReferenceRecord], provider_id: str = "static") -> None:
        self.records = tuple(records)
        self.provider_id = provider_id
        self._terms = {row.record_id: Counter(_tokens(" ".join((row.title, row.body, *row.tags)))) for row in self.records}
        self._df = Counter(term for terms in self._terms.values() for term in terms)

    @classmethod
    def from_json_files(cls, paths: Iterable[Path], provider_id: str = "static") -> "StaticReferenceProvider":
        records: list[ReferenceRecord] = []
        for path in paths:
            value = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(value, dict):
                for category, items in value.items():
                    records.append(
                        ReferenceRecord(
                            record_id=f"ontology:{category}",
                            kind="ontology",
                            title=f"{category}の語彙分類",
                            body="、".join(items),
                            tags=(category, *tuple(items)),
                            source=path.name,
                            metadata={"category": category, "items": items},
                        )
                    )
            else:
                for row in value:
                    records.append(
                        ReferenceRecord(
                            record_id=row.get("記録番号", row.get("record_id")),
                            kind=row.get("種別", row.get("kind")),
                            title=row.get("題名", row.get("title")),
                            body=row.get("本文", row.get("body")),
                            tags=tuple(row.get("標識群", row.get("標識", row.get("tags", [])))),
                            source=row.get("出典", row.get("source", path.name)),
                            authority=row.get("権限", row.get("authority", "参照")),
                            metadata=row.get("付記", row.get("metadata", {})),
                        )
                    )
        return cls(records, provider_id)

    def search(self, query: str, *, limit: int = 8) -> tuple[ReferenceRecord, ...]:
        q = Counter(_tokens(query))
        total = max(1, len(self.records))
        scored: list[tuple[float, ReferenceRecord]] = []
        for row in self.records:
            score = 0.0
            terms = self._terms[row.record_id]
            length = max(1, sum(terms.values()))
            for term, qf in q.items():
                tf = terms.get(term, 0)
                if not tf:
                    continue
                idf = math.log1p((total + 0.5) / (self._df[term] + 0.5))
                score += qf * idf * (tf / length) ** 0.5
            if score > 0:
                scored.append((score, row))
        return tuple(row for _, row in sorted(scored, key=lambda item: (-item[0], item[1].record_id))[:limit])


class CompositeProvider(ReferenceProvider):
    def __init__(self, providers: Sequence[ReferenceProvider], provider_id: str = "composite") -> None:
        self.providers = tuple(providers)
        self.provider_id = provider_id

    def search(self, query: str, *, limit: int = 8) -> tuple[ReferenceRecord, ...]:
        seen: set[str] = set()
        rows: list[ReferenceRecord] = []
        for provider in self.providers:
            for row in provider.search(query, limit=limit):
                if row.record_id not in seen:
                    seen.add(row.record_id)
                    rows.append(row)
        return tuple(rows[:limit])


class JSONHTTPProvider(ReferenceProvider):
    """検索API等をReferenceRecordへ変換する最小adapter。LLM固定ではない。"""

    def __init__(self, endpoint_template: str, provider_id: str, timeout_seconds: float = 10.0) -> None:
        self.endpoint_template = endpoint_template
        self.provider_id = provider_id
        self.timeout_seconds = timeout_seconds

    def search(self, query: str, *, limit: int = 8) -> tuple[ReferenceRecord, ...]:
        from urllib.parse import quote

        url = self.endpoint_template.format(query=quote(query), limit=limit)
        request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "ミニドラK3命令化版/0.1"})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.load(response)
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            return (
                ReferenceRecord(
                    record_id=f"provider-error:{self.provider_id}",
                    kind="provider_error",
                    title="参照Provider取得失敗",
                    body=str(exc),
                    tags=("error", self.provider_id),
                    source=self.provider_id,
                    authority="誤り",
                ),
            )
        items = payload.get("results", payload if isinstance(payload, list) else [])
        rows: list[ReferenceRecord] = []
        for index, item in enumerate(items[:limit]):
            if not isinstance(item, dict):
                continue
            title = str(item.get("title", item.get("name", f"result-{index}")))
            body = str(item.get("body", item.get("snippet", item.get("text", ""))))
            rows.append(
                ReferenceRecord(
                    record_id=str(item.get("id", f"{self.provider_id}:{index}:{hash((title, body))}")),
                    kind=str(item.get("kind", "external_reference")),
                    title=title,
                    body=body,
                    tags=tuple(item.get("tags", [])),
                    source=str(item.get("url", self.provider_id)),
                    metadata=item,
                )
            )
        return tuple(rows)


参照供給器 = ReferenceProvider
固定参照供給器 = StaticReferenceProvider
複合参照供給器 = CompositeProvider
JSON_HTTP参照供給器 = JSONHTTPProvider
