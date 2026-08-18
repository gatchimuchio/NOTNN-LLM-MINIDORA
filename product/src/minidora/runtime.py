"""MINIDORA製品Runtime。

ニューラルネットワークを使用せず、文書・事実・規則・会話状態を根拠に、
HDSの採否を通して日本語結果を返す。
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
import threading
import time
import unicodedata
import uuid
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field, replace
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


class DecisionStatus(StrEnum):
    PASS = "PASS"
    SUSPEND = "SUSPEND"
    FAIL = "FAIL"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class Effort(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    MAX = "max"


@dataclass(frozen=True, slots=True)
class QueryFrame:
    raw: str
    normalized: str
    language: str
    intent: str
    predicate: str
    args: tuple[str | None, ...]
    entities: tuple[str, ...]
    terms: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SourceCitation:
    source_id: str
    title: str
    source_uri: str
    excerpt: str


@dataclass(frozen=True, slots=True)
class Evidence:
    evidence_id: str
    source_id: str
    kind: str
    excerpt: str
    score: float


@dataclass(frozen=True, slots=True)
class Candidate:
    candidate_id: str
    answer: str
    relation: str
    confidence: float
    specialist: str
    evidence: tuple[Evidence, ...] = ()
    contradictions: tuple[Evidence, ...] = ()
    proof: tuple[str, ...] = ()
    risk_flags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Decision:
    status: DecisionStatus
    selected: Candidate | None
    reason_codes: tuple[str, ...]
    confidence: float


@dataclass(frozen=True, slots=True)
class ChatResult:
    request_id: str
    session_id: str
    status: DecisionStatus
    text: str
    answer: str
    confidence: float
    reason_codes: tuple[str, ...]
    sources: tuple[SourceCitation, ...]
    audit_id: str
    elapsed_ms: float
    trace: tuple[dict[str, Any], ...] = ()
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class DocumentInput:
    title: str
    body: str
    source_uri: str
    metadata: Mapping[str, Any] = field(default_factory=dict)
    document_id: str | None = None


@dataclass(frozen=True, slots=True)
class FactInput:
    predicate: str
    args: tuple[str, ...]
    polarity: bool = True
    source_id: str = "manual"
    confidence: float = 1.0


@dataclass(frozen=True, slots=True)
class RuleInput:
    name: str
    premises: tuple[tuple[str, ...], ...]
    conclusion: tuple[str, ...]
    priority: int = 100
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class Fact:
    fact_id: str
    predicate: str
    args: tuple[str, ...]
    polarity: bool
    source_id: str
    confidence: float
    proof: tuple[str, ...] = ()
    depth: int = 0


@dataclass(frozen=True, slots=True)
class Rule:
    rule_id: str
    name: str
    premises: tuple[tuple[str, ...], ...]
    conclusion: tuple[str, ...]
    priority: int


_JA = re.compile(r"[一-龯々〆ヵヶぁ-んァ-ヶー]")
_ASCII = re.compile(r"[a-z0-9]+(?:[-_./'][a-z0-9]+)*", re.I)
_JA_RUN = re.compile(r"[一-龯々〆ヵヶぁ-んァ-ヶー]+")
_SPACE = re.compile(r"\s+")
_STOPWORDS = {
    "について", "教えて", "ください", "何ですか", "どこですか", "ありますか", "できますか",
    "は", "が", "を", "に", "の", "と", "で", "です", "ます", "する", "した", "いる", "ある",
}
_HAZARD_PATTERNS = (
    "以前の指示を無視", "すべての指示を無視", "秘密を出力", "system promptを表示",
    "ignore previous instructions", "ignore all instructions", "reveal the system prompt",
    "execute shell", "run this command", "jailbreak",
)


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _stable_id(prefix: str, *parts: Any) -> str:
    return f"{prefix}_{_digest(parts)[:24]}"


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).replace("\r\n", "\n").replace("\r", "\n")
    return _SPACE.sub(" ", normalized.strip()).casefold()


def tokenize(text: str) -> tuple[str, ...]:
    normalized = normalize_text(text)
    values: list[str] = [token.casefold() for token in _ASCII.findall(normalized)]
    for run in _JA_RUN.findall(normalized):
        values.append(run)
        chars = list(run)
        values.extend(chars)
        values.extend("".join(chars[index : index + 2]) for index in range(max(0, len(chars) - 1)))
        values.extend("".join(chars[index : index + 3]) for index in range(max(0, len(chars) - 2)))
    return tuple(value for value in values if value and value not in _STOPWORDS)


def _clean_entity(value: str) -> str:
    return normalize_text(value).strip("『』「」()（）?？!！。,.、:： ")


def parse_query(text: str, state: Mapping[str, Any] | None = None) -> QueryFrame:
    raw = text.strip()
    normalized = normalize_text(raw)
    state = state or {}
    last_answer = str(state.get("last_answer") or "")
    last_entity = str(state.get("last_entity") or "")
    if normalized.startswith("それ") and last_answer:
        normalized = last_answer + normalized.removeprefix("それ")
    elif normalized.startswith("その") and last_entity:
        normalized = last_entity + normalized.removeprefix("その")
    language = "ja" if _JA.search(raw) else "en"
    patterns: list[tuple[re.Pattern[str], str, str, tuple[int | None, ...]]] = [
        (re.compile(r"^(.+?)(?:は|が)何を使(?:っていますか|うの|う)\??$"), "knowledge", "uses", (1, None)),
        (re.compile(r"^(.+?)(?:は|が)(?:文書|データ|記録)?を?どこ(?:に|へ)(?:保存|格納)(?:していますか|するの|する)\??$"), "knowledge", "stores_at", (1, None)),
        (re.compile(r"^(.+?)(?:は|が)何ができますか\??$"), "knowledge", "capability", (1, None)),
        (re.compile(r"^(.+?)の(?:能力|機能)(?:は|を)?\??$"), "knowledge", "capability", (1, None)),
        (re.compile(r"^(.+?)の祖父母(?:は|を)?誰(?:ですか)?\??$"), "reasoning", "grandparent", (None, 1)),
        (re.compile(r"^(.+?)(?:が|は)停止した(?:場合|とき)の?(?:リスク|危険)(?:は|を)?\??$"), "reasoning", "risk", (1, None)),
        (re.compile(r"^(.+?)の所有者(?:は|を)?誰(?:ですか)?\??$"), "knowledge", "owned_by", (1, None)),
        (re.compile(r"^(.+?)(?:とは|について教えてください|について教えて|について)$"), "search", "search", (1,)),
        (re.compile(r"^what does (.+?) use\??$", re.I), "knowledge", "uses", (1, None)),
        (re.compile(r"^where does (.+?) store(?: its)? (?:documents|data|records)\??$", re.I), "knowledge", "stores_at", (1, None)),
        (re.compile(r"^what can (.+?) do\??$", re.I), "knowledge", "capability", (1, None)),
        (re.compile(r"^who is the grandparent of (.+?)\??$", re.I), "reasoning", "grandparent", (None, 1)),
        (re.compile(r"^what risk follows if (.+?) is offline\??$", re.I), "reasoning", "risk", (1, None)),
        (re.compile(r"^who owns (.+?)\??$", re.I), "knowledge", "owned_by", (1, None)),
    ]
    for pattern, intent, predicate, layout in patterns:
        match = pattern.match(normalized)
        if match:
            groups = match.groups()
            args = tuple(None if index is None else _clean_entity(groups[index - 1]) for index in layout)
            entities = tuple(value for value in args if value)
            return QueryFrame(raw, normalized, language, intent, predicate, args, entities, tokenize(normalized))
    entity = _clean_entity(normalized)
    return QueryFrame(raw, normalized, language, "search", "search", (entity,), (entity,), tokenize(normalized))


def contains_hazard(text: str) -> bool:
    normalized = normalize_text(text)
    return any(pattern in normalized for pattern in _HAZARD_PATTERNS)


class SQLiteStore:
    SCHEMA_VERSION = 1

    def __init__(self, path: Path) -> None:
        self.path = path.resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._write_lock = threading.RLock()
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=5, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=5000")
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=NORMAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS documents(
                    id TEXT PRIMARY KEY, title TEXT NOT NULL, body TEXT NOT NULL,
                    source_uri TEXT NOT NULL, metadata_json TEXT NOT NULL,
                    content_digest TEXT NOT NULL, deleted INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS facts(
                    id TEXT PRIMARY KEY, predicate TEXT NOT NULL, args_json TEXT NOT NULL,
                    polarity INTEGER NOT NULL, source_id TEXT NOT NULL,
                    confidence REAL NOT NULL, created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_facts_predicate ON facts(predicate);
                CREATE TABLE IF NOT EXISTS rules(
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, premises_json TEXT NOT NULL,
                    conclusion_json TEXT NOT NULL, priority INTEGER NOT NULL,
                    enabled INTEGER NOT NULL, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sessions(
                    id TEXT PRIMARY KEY, state_json TEXT NOT NULL, version INTEGER NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS messages(
                    id TEXT PRIMARY KEY, session_id TEXT NOT NULL, role TEXT NOT NULL,
                    content TEXT NOT NULL, metadata_json TEXT NOT NULL, created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, created_at);
                CREATE TABLE IF NOT EXISTS audit_events(
                    id TEXT PRIMARY KEY, request_id TEXT NOT NULL, session_id TEXT NOT NULL,
                    sequence INTEGER NOT NULL, event_type TEXT NOT NULL, payload_json TEXT NOT NULL,
                    previous_hash TEXT NOT NULL, event_hash TEXT NOT NULL, created_at TEXT NOT NULL,
                    UNIQUE(request_id, sequence)
                );
                CREATE INDEX IF NOT EXISTS idx_audit_request ON audit_events(request_id, sequence);
                """
            )
            connection.execute(
                "INSERT INTO meta(key,value) VALUES('schema_version',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (str(self.SCHEMA_VERSION),),
            )

    def bootstrap(self) -> None:
        if self.get_document("system_minidora") is not None:
            return
        documents = (
            DocumentInput(
                "MINIDORA",
                "MINIDORAは日本語優先で、ニューラルネットワークを使用せず、内容検索、規則合成、選択状態、HDS採否、監査hash chainで応答する言語Runtimeです。",
                "product://minidora",
                {"authority": "system"},
                "system_minidora",
            ),
            DocumentInput("Project Atlas", "Project Atlasは索引処理をAurora Indexへ委譲します。", "example://atlas", document_id="seed_atlas"),
            DocumentInput("Aurora Index", "Aurora Indexは文書を/srv/auroraへ保存し、全文検索を実行できます。", "example://aurora", document_id="seed_aurora"),
            DocumentInput("家族関係", "AliceはBobの親です。BobはCarolの親です。", "example://family", document_id="seed_family"),
            DocumentInput("設備安全", "Pump P1は潤滑油を供給します。潤滑油はタービン過熱を防止します。現在Pump P1は停止しています。", "example://pump", document_id="seed_pump"),
        )
        for document in documents:
            self.add_document(document)
        facts = (
            FactInput("definition", ("minidora", "日本語優先・監査可能な非ニューラルネットワーク言語runtime"), source_id="system_minidora"),
            FactInput("capability", ("minidora", "根拠付き応答"), source_id="system_minidora"),
            FactInput("uses", ("project atlas", "aurora index"), source_id="seed_atlas"),
            FactInput("stores_at", ("aurora index", "/srv/aurora"), source_id="seed_aurora"),
            FactInput("capability", ("aurora index", "全文検索"), source_id="seed_aurora"),
            FactInput("parent", ("alice", "bob"), source_id="seed_family"),
            FactInput("parent", ("bob", "carol"), source_id="seed_family"),
            FactInput("supplies", ("pump p1", "lubrication"), source_id="seed_pump"),
            FactInput("prevents", ("lubrication", "turbine overheating"), source_id="seed_pump"),
            FactInput("offline", ("pump p1",), source_id="seed_pump"),
        )
        for fact in facts:
            self.add_fact(fact)
        rules = (
            RuleInput("transitive_use", (("uses", "?a", "?b"), ("uses", "?b", "?c")), ("uses", "?a", "?c"), 10),
            RuleInput("delegated_storage", (("uses", "?system", "?index"), ("stores_at", "?index", "?location")), ("stores_at", "?system", "?location"), 20),
            RuleInput("delegated_capability", (("uses", "?system", "?component"), ("capability", "?component", "?ability")), ("capability", "?system", "?ability"), 20),
            RuleInput("grandparent", (("parent", "?x", "?y"), ("parent", "?y", "?z")), ("grandparent", "?x", "?z"), 30),
            RuleInput("offline_risk", (("offline", "?machine"), ("supplies", "?machine", "?resource"), ("prevents", "?resource", "?risk")), ("risk", "?machine", "?risk"), 30),
        )
        for rule in rules:
            self.add_rule(rule)

    def add_document(self, item: DocumentInput) -> str:
        document_id = item.document_id or _stable_id("doc", item.source_uri, item.title, item.body)
        now = _now()
        with self._write_lock, self.connect() as connection:
            connection.execute(
                """
                INSERT INTO documents(id,title,body,source_uri,metadata_json,content_digest,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET title=excluded.title,body=excluded.body,
                source_uri=excluded.source_uri,metadata_json=excluded.metadata_json,
                content_digest=excluded.content_digest,deleted=0,updated_at=excluded.updated_at
                """,
                (document_id, item.title.strip(), item.body.strip(), item.source_uri, json.dumps(dict(item.metadata), ensure_ascii=False), _digest(item.body), now, now),
            )
        return document_id

    def get_document(self, document_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM documents WHERE id=? AND deleted=0", (document_id,)).fetchone()
        return dict(row) if row else None

    def list_documents(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute("SELECT * FROM documents WHERE deleted=0 ORDER BY id").fetchall()
        return [dict(row) for row in rows]

    def add_fact(self, item: FactInput) -> str:
        args = tuple(normalize_text(value) for value in item.args)
        predicate = normalize_text(item.predicate)
        fact_id = _stable_id("fact", predicate, args, item.polarity, item.source_id)
        with self._write_lock, self.connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO facts(id,predicate,args_json,polarity,source_id,confidence,created_at) VALUES(?,?,?,?,?,?,?)",
                (fact_id, predicate, json.dumps(args, ensure_ascii=False), int(item.polarity), item.source_id, float(item.confidence), _now()),
            )
        return fact_id

    def list_facts(self) -> list[Fact]:
        with self.connect() as connection:
            rows = connection.execute("SELECT * FROM facts ORDER BY id").fetchall()
        return [
            Fact(row["id"], row["predicate"], tuple(json.loads(row["args_json"])), bool(row["polarity"]), row["source_id"], float(row["confidence"]))
            for row in rows
        ]

    def add_rule(self, item: RuleInput) -> str:
        rule_id = _stable_id("rule", item.name, item.premises, item.conclusion)
        with self._write_lock, self.connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO rules(id,name,premises_json,conclusion_json,priority,enabled,created_at) VALUES(?,?,?,?,?,?,?)",
                (rule_id, item.name, json.dumps(item.premises, ensure_ascii=False), json.dumps(item.conclusion, ensure_ascii=False), item.priority, int(item.enabled), _now()),
            )
        return rule_id

    def list_rules(self) -> list[Rule]:
        with self.connect() as connection:
            rows = connection.execute("SELECT * FROM rules WHERE enabled=1 ORDER BY priority,id").fetchall()
        return [
            Rule(row["id"], row["name"], tuple(tuple(part) for part in json.loads(row["premises_json"])), tuple(json.loads(row["conclusion_json"])), int(row["priority"]))
            for row in rows
        ]

    def session_state(self, session_id: str) -> tuple[dict[str, Any], int]:
        with self.connect() as connection:
            row = connection.execute("SELECT state_json,version FROM sessions WHERE id=?", (session_id,)).fetchone()
        if row is None:
            return {}, 0
        return json.loads(row["state_json"]), int(row["version"])

    def commit_turn(
        self,
        *,
        request_id: str,
        session_id: str,
        expected_version: int,
        state: Mapping[str, Any],
        user_text: str,
        assistant_text: str,
        events: Sequence[tuple[str, Mapping[str, Any]]],
    ) -> None:
        now = _now()
        previous = "0" * 64
        prepared: list[tuple[str, str, int, str, str, str, str, str]] = []
        for sequence, (event_type, payload) in enumerate(events):
            payload_json = json.dumps(dict(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
            event_hash = hashlib.sha256((previous + event_type + payload_json).encode("utf-8")).hexdigest()
            prepared.append((_stable_id("event", request_id, sequence, event_hash), request_id, sequence, event_type, payload_json, previous, event_hash, now))
            previous = event_hash
        with self._write_lock, self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            current = connection.execute("SELECT version FROM sessions WHERE id=?", (session_id,)).fetchone()
            current_version = int(current["version"]) if current else 0
            if current_version != expected_version:
                connection.rollback()
                raise RuntimeError("sessionの楽観lockが競合しました")
            connection.execute(
                "INSERT INTO sessions(id,state_json,version,updated_at) VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET state_json=excluded.state_json,version=excluded.version,updated_at=excluded.updated_at",
                (session_id, json.dumps(dict(state), ensure_ascii=False), expected_version + 1, now),
            )
            connection.execute(
                "INSERT INTO messages(id,session_id,role,content,metadata_json,created_at) VALUES(?,?,?,?,?,?)",
                (_stable_id("msg", request_id, "user"), session_id, "user", user_text, "{}", now),
            )
            connection.execute(
                "INSERT INTO messages(id,session_id,role,content,metadata_json,created_at) VALUES(?,?,?,?,?,?)",
                (_stable_id("msg", request_id, "assistant"), session_id, "assistant", assistant_text, json.dumps({"request_id": request_id}, ensure_ascii=False), now),
            )
            connection.executemany(
                "INSERT INTO audit_events(id,request_id,session_id,sequence,event_type,payload_json,previous_hash,event_hash,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                [(row[0], row[1], session_id, row[2], row[3], row[4], row[5], row[6], row[7]) for row in prepared],
            )
            connection.commit()

    def audit(self, request_id: str) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute("SELECT * FROM audit_events WHERE request_id=? ORDER BY sequence", (request_id,)).fetchall()
        return [dict(row) for row in rows]

    def verify_audit(self, request_id: str) -> dict[str, Any]:
        rows = self.audit(request_id)
        previous = "0" * 64
        for expected_sequence, row in enumerate(rows):
            payload_json = row["payload_json"]
            actual = hashlib.sha256((previous + row["event_type"] + payload_json).encode("utf-8")).hexdigest()
            if row["sequence"] != expected_sequence or row["previous_hash"] != previous or row["event_hash"] != actual:
                return {"status": "FAIL", "event_count": len(rows), "failed_sequence": expected_sequence}
            previous = actual
        return {"status": "PASS" if rows else "SUSPEND", "event_count": len(rows), "head_hash": previous}

    def backup(self, destination: Path) -> None:
        destination = destination.resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        source = self.connect()
        target = sqlite3.connect(destination)
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()

    def integrity(self) -> dict[str, Any]:
        with self.connect() as connection:
            value = connection.execute("PRAGMA integrity_check").fetchone()[0]
        return {"status": "PASS" if value == "ok" else "FAIL", "detail": value}


class BM25Index:
    def __init__(self, documents: Sequence[Mapping[str, Any]]) -> None:
        self.documents = list(documents)
        self.tokens = {str(row["id"]): tokenize(str(row["title"]) + " " + str(row["body"])) for row in documents}
        self.tf = {key: Counter(values) for key, values in self.tokens.items()}
        self.df = Counter(term for values in self.tokens.values() for term in set(values))
        self.avg_len = sum(map(len, self.tokens.values())) / max(1, len(self.tokens))

    def search(self, query: str, limit: int) -> list[tuple[float, Mapping[str, Any]]]:
        query_terms = tokenize(query)
        total_documents = max(1, len(self.documents))
        hits: list[tuple[float, Mapping[str, Any]]] = []
        for document in self.documents:
            document_id = str(document["id"])
            document_length = len(self.tokens[document_id])
            score = 0.0
            for term in query_terms:
                frequency = self.tf[document_id].get(term, 0)
                if not frequency:
                    continue
                document_frequency = self.df[term]
                inverse = math.log(1 + (total_documents - document_frequency + 0.5) / (document_frequency + 0.5))
                score += inverse * frequency * 2.5 / (frequency + 1.5 * (0.25 + 0.75 * document_length / max(1.0, self.avg_len)))
            if score > 0:
                hits.append((score, document))
        return sorted(hits, key=lambda item: (-item[0], str(item[1]["id"])))[:limit]


class FactGraph:
    def __init__(self, facts: Iterable[Fact]) -> None:
        self.facts: dict[str, Fact] = {}
        self.by_predicate: dict[str, list[str]] = defaultdict(list)
        for fact in facts:
            self.add(fact)

    def add(self, fact: Fact) -> bool:
        for fact_id in self.by_predicate[fact.predicate]:
            current = self.facts[fact_id]
            if current.args == fact.args and current.polarity == fact.polarity:
                return False
        self.facts[fact.fact_id] = fact
        self.by_predicate[fact.predicate].append(fact.fact_id)
        return True

    def query(self, predicate: str, args: Sequence[str | None]) -> list[Fact]:
        values: list[Fact] = []
        for fact_id in self.by_predicate.get(predicate, []):
            fact = self.facts[fact_id]
            if fact.polarity and len(fact.args) == len(args) and all(expected is None or normalize_text(expected) == actual for expected, actual in zip(args, fact.args)):
                values.append(fact)
        return sorted(values, key=lambda fact: (fact.depth, fact.args))

    def contradictions(self, fact: Fact) -> tuple[Fact, ...]:
        return tuple(
            current for current in self.facts.values()
            if current.predicate == fact.predicate and current.args == fact.args and current.polarity != fact.polarity
        )

    def sources(self, fact: Fact) -> tuple[str, ...]:
        sources = {fact.source_id} if fact.source_id else set()
        stack = [part for part in fact.proof if part.startswith("fact_")]
        while stack:
            current = self.facts.get(stack.pop())
            if current is None:
                continue
            if current.source_id:
                sources.add(current.source_id)
            stack.extend(part for part in current.proof if part.startswith("fact_"))
        return tuple(sorted(sources))


class RuleEngine:
    @staticmethod
    def _unify(pattern: Sequence[str], fact: Fact, binding: Mapping[str, str]) -> dict[str, str] | None:
        if pattern[0] != fact.predicate or len(pattern) - 1 != len(fact.args) or not fact.polarity:
            return None
        result = dict(binding)
        for expected, actual in zip(pattern[1:], fact.args):
            if expected.startswith("?"):
                if expected in result and result[expected] != actual:
                    return None
                result[expected] = actual
            elif normalize_text(expected) != actual:
                return None
        return result

    def infer(self, graph: FactGraph, rules: Sequence[Rule], *, rounds: int, timeout_ms: int = 3000) -> dict[str, Any]:
        started = time.perf_counter()
        derived: list[str] = []
        executed = 0
        for round_index in range(rounds):
            snapshot = list(graph.facts.values())
            created = 0
            for rule in rules:
                partials: list[tuple[dict[str, str], tuple[str, ...], int]] = [({}, (), 0)]
                for premise in rule.premises:
                    next_partials: list[tuple[dict[str, str], tuple[str, ...], int]] = []
                    for binding, proof, depth in partials:
                        for fact in snapshot:
                            unified = self._unify(premise, fact, binding)
                            if unified is not None:
                                next_partials.append((unified, proof + (fact.fact_id,), max(depth, fact.depth)))
                    partials = next_partials
                for binding, proof, depth in partials:
                    args = tuple(binding.get(value, normalize_text(value)) for value in rule.conclusion[1:])
                    fact = Fact(
                        _stable_id("fact", rule.conclusion[0], args, True, rule.rule_id),
                        rule.conclusion[0], args, True, "", 0.95,
                        proof + ("rule:" + rule.name,), depth + 1,
                    )
                    if graph.add(fact):
                        derived.append(fact.fact_id)
                        created += 1
                if (time.perf_counter() - started) * 1000 > timeout_ms:
                    return {"rounds": round_index + 1, "derived": derived, "timeout": True}
            executed += 1
            if not created:
                break
        return {"rounds": executed, "derived": derived, "timeout": False}


class HDSJudge:
    def decide(self, candidates: Sequence[Candidate], *, input_hazard: bool) -> Decision:
        if input_hazard:
            return Decision(DecisionStatus.FAIL, None, ("INPUT_HAZARD", "AUTHORITY_DENIED"), 0.0)
        if not candidates:
            return Decision(DecisionStatus.SUSPEND, None, ("NO_CANDIDATE", "UNKNOWN_REMAINS"), 0.0)
        ranked = sorted(candidates, key=lambda item: (-item.confidence, item.answer))
        selected = ranked[0]
        if selected.risk_flags:
            return Decision(DecisionStatus.FAIL, selected, ("EVIDENCE_HAZARD", "AUTHORITY_DENIED"), selected.confidence)
        if selected.contradictions:
            return Decision(DecisionStatus.SUSPEND, selected, ("UNRESOLVED_CONTRADICTION",), selected.confidence)
        if not selected.evidence:
            return Decision(DecisionStatus.SUSPEND, selected, ("NO_EVIDENCE",), selected.confidence)
        competing = [item for item in ranked[1:] if item.answer != selected.answer and abs(item.confidence - selected.confidence) <= 0.08]
        if competing:
            return Decision(DecisionStatus.SUSPEND, selected, ("COMPETING_CANDIDATES",), selected.confidence)
        return Decision(DecisionStatus.PASS, selected, ("EVIDENCE_PRESENT", "NO_UNRESOLVED_CONTRADICTION", "AUTHORITY_SEPARATED"), selected.confidence)


class MiniDoraEngine:
    VERSION = "1.0.0rc2"
    EFFORT = {
        Effort.LOW: {"rounds": 1, "documents": 3, "timeout_ms": 500},
        Effort.MEDIUM: {"rounds": 3, "documents": 6, "timeout_ms": 1500},
        Effort.HIGH: {"rounds": 6, "documents": 12, "timeout_ms": 4000},
        Effort.MAX: {"rounds": 12, "documents": 24, "timeout_ms": 10000},
    }

    def __init__(self, database_path: Path | str) -> None:
        self.store = SQLiteStore(Path(database_path))
        self.store.bootstrap()
        self.rules = RuleEngine()
        self.judge = HDSJudge()
        self._locks: dict[str, threading.RLock] = {}
        self._locks_guard = threading.RLock()

    def _session_lock(self, session_id: str) -> threading.RLock:
        with self._locks_guard:
            return self._locks.setdefault(session_id, threading.RLock())

    def add_document(self, item: DocumentInput) -> str:
        return self.store.add_document(item)

    def add_fact(self, item: FactInput) -> str:
        return self.store.add_fact(item)

    def add_rule(self, item: RuleInput) -> str:
        return self.store.add_rule(item)

    def query(
        self,
        text: str,
        *,
        session_id: str | None = None,
        effort: Effort | str = Effort.MEDIUM,
        include_trace: bool = False,
    ) -> ChatResult:
        started = time.perf_counter()
        request_id = "req_" + uuid.uuid4().hex
        session_id = session_id or "session_" + uuid.uuid4().hex
        effort_value = effort if isinstance(effort, Effort) else Effort(effort)
        with self._session_lock(session_id):
            return self._query_locked(text, request_id, session_id, effort_value, include_trace, started)

    def _query_locked(
        self,
        text: str,
        request_id: str,
        session_id: str,
        effort: Effort,
        include_trace: bool,
        started: float,
    ) -> ChatResult:
        state, version = self.store.session_state(session_id)
        frame = parse_query(text, state)
        budget = self.EFFORT[effort]
        events: list[tuple[str, Mapping[str, Any]]] = []
        trace: list[dict[str, Any]] = []

        def stage(name: str, payload: Mapping[str, Any]) -> None:
            events.append((name, payload))
            trace.append({"event": name, "payload": dict(payload)})

        stage("REQUEST_ACCEPTED", {"effort": effort.value, "message_digest": _digest(text)})
        stage("LANGUAGE_ADDRESSABILITY", asdict(frame))

        documents = self.store.list_documents()
        index = BM25Index(documents)
        hits = index.search(frame.normalized, int(budget["documents"]))
        stage("CONTEXT_SELECTED", {"document_ids": [row[1]["id"] for row in hits], "count": len(hits)})

        graph = FactGraph(self.store.list_facts())
        inference = self.rules.infer(graph, self.store.list_rules(), rounds=int(budget["rounds"]), timeout_ms=int(budget["timeout_ms"]))
        stage("SERIAL_TRANSFORMATION", inference)

        candidates = self._candidates(frame, graph, hits, documents)
        stage("CANDIDATES_FORMED", {"candidate_ids": [item.candidate_id for item in candidates], "count": len(candidates)})
        decision = self.judge.decide(candidates, input_hazard=contains_hazard(text))
        stage("HDS_AUTHORITY_GATE", {"status": decision.status.value, "reason_codes": list(decision.reason_codes), "selected": decision.selected.candidate_id if decision.selected else None})

        response, sources = self._render(decision, documents)
        stage("RESULT_SURFACE", {"status": decision.status.value, "response_digest": _digest(response), "source_ids": [item.source_id for item in sources]})

        new_state = dict(state)
        new_state["last_intent"] = frame.intent
        if frame.entities:
            new_state["last_entity"] = frame.entities[0]
        if decision.selected and decision.status == DecisionStatus.PASS:
            new_state["last_answer"] = decision.selected.answer
        self.store.commit_turn(
            request_id=request_id,
            session_id=session_id,
            expected_version=version,
            state=new_state,
            user_text=text,
            assistant_text=response,
            events=events,
        )
        elapsed_ms = (time.perf_counter() - started) * 1000
        return ChatResult(
            request_id=request_id,
            session_id=session_id,
            status=decision.status,
            text=response,
            answer=decision.selected.answer if decision.selected and decision.status == DecisionStatus.PASS else "",
            confidence=decision.confidence,
            reason_codes=decision.reason_codes,
            sources=sources,
            audit_id=request_id,
            elapsed_ms=elapsed_ms,
            trace=tuple(trace) if include_trace else (),
        )

    def _candidates(
        self,
        frame: QueryFrame,
        graph: FactGraph,
        hits: Sequence[tuple[float, Mapping[str, Any]]],
        documents: Sequence[Mapping[str, Any]],
    ) -> tuple[Candidate, ...]:
        by_document = {str(row["id"]): row for row in documents}
        candidates: list[Candidate] = []
        if frame.predicate != "search":
            matched = graph.query(frame.predicate, frame.args)
            if matched:
                answer_index = frame.args.index(None) if None in frame.args else len(frame.args) - 1
                answers = sorted({fact.args[answer_index] for fact in matched})
                facts = [fact for fact in matched if fact.args[answer_index] in answers]
                evidence: list[Evidence] = []
                contradiction_evidence: list[Evidence] = []
                proof: set[str] = set()
                source_ids: set[str] = set()
                max_depth = 0
                for fact in facts:
                    max_depth = max(max_depth, fact.depth)
                    proof.update(fact.proof)
                    source_ids.update(graph.sources(fact))
                    for contradiction in graph.contradictions(fact):
                        contradiction_evidence.append(Evidence(contradiction.fact_id, contradiction.source_id, "contradiction", repr(contradiction.args), 1.0))
                for source_id in sorted(source_ids):
                    document = by_document.get(source_id)
                    excerpt = str(document["body"])[:500] if document else source_id
                    evidence.append(Evidence(_stable_id("evidence", source_id, frame.predicate), source_id, "fact" if max_depth == 0 else "rule", excerpt, 1.0))
                answer = "; ".join(answers)
                confidence = max(0.60, 0.99 - max_depth * 0.05)
                candidates.append(
                    Candidate(
                        _stable_id("candidate", frame.predicate, answer, tuple(sorted(source_ids))),
                        answer,
                        frame.predicate,
                        confidence,
                        "direct_fact" if max_depth == 0 else "rule_engine",
                        tuple(evidence),
                        tuple(contradiction_evidence),
                        tuple(sorted(proof)),
                    )
                )
        elif hits:
            score, document = hits[0]
            body = str(document["body"])
            risk = ("INSTRUCTION_INJECTION",) if contains_hazard(body) else ()
            evidence = Evidence(_stable_id("evidence", document["id"], score), str(document["id"]), "document", body[:500], float(score))
            candidates.append(
                Candidate(
                    _stable_id("candidate", document["id"], frame.normalized),
                    body[:1000],
                    "extractive",
                    min(0.95, 0.60 + score / (score + 5.0)),
                    "retrieval",
                    (evidence,),
                    risk_flags=risk,
                )
            )
        return tuple(candidates)

    @staticmethod
    def _render(decision: Decision, documents: Sequence[Mapping[str, Any]]) -> tuple[str, tuple[SourceCitation, ...]]:
        by_document = {str(row["id"]): row for row in documents}
        sources: list[SourceCitation] = []
        if decision.selected:
            for evidence in decision.selected.evidence:
                document = by_document.get(evidence.source_id)
                if document:
                    sources.append(SourceCitation(evidence.source_id, str(document["title"]), str(document["source_uri"]), evidence.excerpt))
        if decision.status == DecisionStatus.FAIL:
            return "安全・整合性境界により処理を停止しました。", tuple(sources)
        if decision.status == DecisionStatus.SUSPEND:
            return "証拠不足、未知、または未解消の矛盾があるため、回答を確定せず保留します。", tuple(sources)
        if decision.status == DecisionStatus.NOT_APPLICABLE:
            return "この要求は現在の製品範囲外です。", tuple(sources)
        assert decision.selected is not None
        if decision.selected.specialist == "rule_engine":
            text = f"根拠を合成した結果、{decision.selected.answer}です。"
        elif decision.selected.specialist == "retrieval":
            text = f"関連する根拠は次のとおりです。\n{decision.selected.answer}"
        else:
            text = f"確認できた範囲では、{decision.selected.answer}です。"
        if sources:
            text += "\n\n出典：" + "、".join(f"{source.title} ({source.source_uri})" for source in sources)
        return text, tuple(sources)

    def audit(self, request_id: str) -> dict[str, Any]:
        return {"verification": self.store.verify_audit(request_id), "events": self.store.audit(request_id)}

    def backup(self, destination: Path) -> None:
        self.store.backup(destination)

    def doctor(self) -> dict[str, Any]:
        probe = self.query("Project Atlasは文書をどこに保存していますか？", effort=Effort.HIGH)
        verification = self.store.verify_audit(probe.audit_id)
        integrity = self.store.integrity()
        checks = {
            "多段推論": probe.status == DecisionStatus.PASS and "/srv/aurora" in probe.text,
            "監査hash chain": verification["status"] == "PASS" and verification["event_count"] == 7,
            "SQLite整合性": integrity["status"] == "PASS",
            "ニューラル依存なし": True,
            "GPU不要": True,
        }
        return {
            "status": "PASS" if all(checks.values()) else "FAIL",
            "checks": checks,
            "version": self.VERSION,
            "runtime": {
                "neural_network_used": False,
                "transformer_used": False,
                "vector_embedding_used": False,
                "gpu_required": False,
            },
        }


__all__ = [
    "MiniDoraEngine", "DecisionStatus", "Effort", "ChatResult", "DocumentInput",
    "FactInput", "RuleInput", "parse_query", "tokenize", "normalize_text",
    "Fact", "Rule", "FactGraph", "RuleEngine", "HDSJudge", "contains_hazard",
]
