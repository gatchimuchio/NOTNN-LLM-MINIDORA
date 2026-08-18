"""日本語CLI。"""
from __future__ import annotations

import argparse
import json
import tomllib
from pathlib import Path
from typing import Any

import uvicorn

from .api import create_app
from .documents import ingest
from .runtime import DocumentInput, Effort, FactInput, MiniDoraEngine, RuleInput


def _config(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    with path.open("rb") as stream:
        return tomllib.load(stream)


def _engine(config: dict[str, Any]) -> MiniDoraEngine:
    database = Path(config.get("storage", {}).get("database_path", "data/minidora.sqlite3"))
    return MiniDoraEngine(database)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="minidora", description="MINIDORA 非ニューラル言語Runtime")
    root.add_argument("--config", type=Path, default=Path("config/minidora.toml"))
    sub = root.add_subparsers(dest="command", required=True)

    serve = sub.add_parser("serve", help="APIと日本語Web UIを起動")
    serve.add_argument("--host")
    serve.add_argument("--port", type=int)
    serve.add_argument("--allow-public-without-auth", action="store_true")

    ask = sub.add_parser("ask", help="質問する")
    ask.add_argument("text")
    ask.add_argument("--session-id")
    ask.add_argument("--effort", choices=[value.value for value in Effort], default="medium")
    ask.add_argument("--json", action="store_true")

    ingest_file = sub.add_parser("ingest-file", help="ローカル文書を投入")
    ingest_file.add_argument("path", type=Path)
    ingest_file.add_argument("--recursive", action="store_true")

    ingest_jsonl = sub.add_parser("ingest", help="document/fact/rule JSONLを投入")
    ingest_jsonl.add_argument("path", type=Path)

    audit = sub.add_parser("audit", help="監査記録を表示")
    audit.add_argument("audit_id")

    backup = sub.add_parser("backup", help="SQLite online backup")
    backup.add_argument("destination", type=Path)

    sub.add_parser("doctor", help="製品自己診断")
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    config = _config(args.config)
    if args.command == "serve":
        server = config.get("server", {})
        security = config.get("security", {})
        host = args.host or server.get("host", "127.0.0.1")
        port = args.port or int(server.get("port", 8765))
        loopback = host in {"127.0.0.1", "localhost", "::1"}
        auth_required = bool(security.get("auth_required", False))
        allow_public = bool(security.get("allow_unauthenticated_public_bind", False)) or args.allow_public_without_auth
        if not loopback and not auth_required and not allow_public:
            raise SystemExit("非loopbackへ認証なしでbindする操作を拒否しました")
        app = create_app(
            config.get("storage", {}).get("database_path", "data/minidora.sqlite3"),
            auth_required=auth_required,
            admin_auth_required=bool(security.get("admin_auth_required", True)),
            api_keys=tuple(security.get("api_keys", [])),
            admin_api_keys=tuple(security.get("admin_api_keys", [])),
            max_request_bytes=int(security.get("max_request_bytes", 1_048_576)),
            rate_limit_per_minute=int(security.get("rate_limit_per_minute", 120)),
        )
        uvicorn.run(app, host=host, port=port)
        return 0

    engine = _engine(config)
    if args.command == "ask":
        result = engine.query(args.text, session_id=args.session_id, effort=Effort(args.effort), include_trace=args.json)
        if args.json:
            print(json.dumps({
                "status": result.status.value,
                "text": result.text,
                "answer": result.answer,
                "sources": [source.__dict__ for source in result.sources],
                "reason_codes": list(result.reason_codes),
                "audit_id": result.audit_id,
                "session_id": result.session_id,
                "elapsed_ms": result.elapsed_ms,
                "trace": list(result.trace),
            }, ensure_ascii=False, indent=2))
        else:
            print(result.text)
            print(f"\n状態: {result.status.value} / 監査ID: {result.audit_id}")
        return 0 if result.status.value == "PASS" else 2

    if args.command == "ingest-file":
        ids = ingest(engine, args.path, recursive=args.recursive)
        print(json.dumps({"status": "PASS", "document_ids": ids}, ensure_ascii=False, indent=2))
        return 0

    if args.command == "ingest":
        counts = {"document": 0, "fact": 0, "rule": 0}
        for line_number, line in enumerate(args.path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            row = json.loads(line)
            kind = row.get("type")
            if kind == "document":
                engine.add_document(DocumentInput(row["title"], row.get("body", row.get("content", "")), row["source_uri"], row.get("metadata", {}), row.get("id")))
            elif kind == "fact":
                engine.add_fact(FactInput(row["predicate"], tuple(row.get("args", row.get("arguments", []))), row.get("polarity", True), row.get("source_id", row.get("source_uri", "manual")), row.get("confidence", 1.0)))
            elif kind == "rule":
                engine.add_rule(RuleInput(row["name"], tuple(tuple(item) for item in row["premises"]), tuple(row["conclusion"]), row.get("priority", 100)))
            else:
                raise SystemExit(f"{line_number}行目のtypeが不明です")
            counts[kind] += 1
        print(json.dumps({"status": "PASS", "counts": counts}, ensure_ascii=False, indent=2))
        return 0

    if args.command == "audit":
        print(json.dumps(engine.audit(args.audit_id), ensure_ascii=False, indent=2, default=str))
        return 0

    if args.command == "backup":
        engine.backup(args.destination)
        print(json.dumps({"status": "PASS", "destination": str(args.destination)}, ensure_ascii=False))
        return 0

    if args.command == "doctor":
        value = engine.doctor(); print(json.dumps(value, ensure_ascii=False, indent=2)); return 0 if value["status"] == "PASS" else 1
    return 2
