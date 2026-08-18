"""FastAPI製品API。OpenAI互換Chatと管理API。"""
from __future__ import annotations

import asyncio
import hashlib
import json
import threading
import time
import uuid
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from .runtime import DocumentInput, Effort, FactInput, MiniDoraEngine, RuleInput


class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1)


class ChatRequest(BaseModel):
    model: str = "minidora-notnn-1"
    messages: list[Message] = Field(min_length=1)
    stream: bool = False
    user: str | None = None
    reasoning_effort: Literal["low", "medium", "high", "max"] = "medium"


class DocumentCreate(BaseModel):
    title: str
    body: str
    source_uri: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class FactCreate(BaseModel):
    predicate: str
    args: list[str]
    polarity: bool = True
    source_id: str = "manual"
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class RuleCreate(BaseModel):
    name: str
    premises: list[list[str]]
    conclusion: list[str]
    priority: int = 100


class RateLimiter:
    def __init__(self, per_minute: int) -> None:
        self.per_minute = per_minute
        self.values: dict[str, deque[float]] = defaultdict(deque)
        self.lock = threading.RLock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self.lock:
            queue = self.values[key]
            while queue and now - queue[0] >= 60:
                queue.popleft()
            if len(queue) >= self.per_minute:
                return False
            queue.append(now)
            return True


def _bearer(value: str | None) -> str | None:
    if not value:
        return None
    return value.removeprefix("Bearer ").strip()


def _verify(token: str | None, keys: tuple[str, ...], *, required: bool) -> bool:
    if not required and not keys:
        return True
    if token is None:
        return False
    token_digest = hashlib.sha256(token.encode()).hexdigest()
    return any(token == key or key == f"sha256:{token_digest}" for key in keys)


def create_app(
    database_path: Path | str = "data/minidora.sqlite3",
    *,
    auth_required: bool = False,
    admin_auth_required: bool = True,
    api_keys: tuple[str, ...] = (),
    admin_api_keys: tuple[str, ...] = (),
    max_request_bytes: int = 1_048_576,
    rate_limit_per_minute: int = 120,
) -> FastAPI:
    engine = MiniDoraEngine(database_path)
    limiter = RateLimiter(rate_limit_per_minute)
    app = FastAPI(title="MINIDORA", version=engine.VERSION, description="日本語優先・HDS統治型の非ニューラル言語Runtime")
    app.state.engine = engine

    @app.middleware("http")
    async def boundary(request: Request, call_next):  # type: ignore[no-untyped-def]
        request_id = request.headers.get("x-request-id") or "http_" + uuid.uuid4().hex
        request.state.request_id = request_id
        length = request.headers.get("content-length")
        if length:
            try:
                if int(length) < 0:
                    raise ValueError
            except ValueError:
                return JSONResponse(status_code=400, content={"error": "Content-Lengthが不正です"})
            if int(length) > max_request_bytes:
                return JSONResponse(status_code=413, content={"error": "requestが上限を超えています"})
        if request.method in {"POST", "PUT", "PATCH"}:
            body = await request.body()
            if len(body) > max_request_bytes:
                return JSONResponse(status_code=413, content={"error": "requestが上限を超えています"})
        token = _bearer(request.headers.get("authorization"))
        key = hashlib.sha256(token.encode()).hexdigest() if token else (request.client.host if request.client else "unknown")
        if not limiter.allow(key):
            return JSONResponse(status_code=429, content={"error": "rate limitを超えました"})
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        response.headers["x-content-type-options"] = "nosniff"
        response.headers["x-frame-options"] = "DENY"
        response.headers["cache-control"] = "no-store"
        return response

    def user_auth(authorization: str | None = Header(default=None)) -> None:
        if not _verify(_bearer(authorization), api_keys, required=auth_required):
            raise HTTPException(status_code=401, detail="API keyが不正です")

    def admin_auth(authorization: str | None = Header(default=None)) -> None:
        keys = admin_api_keys or api_keys
        required = admin_auth_required or bool(keys) or auth_required
        if not _verify(_bearer(authorization), keys, required=required):
            raise HTTPException(status_code=403, detail="管理API権限がありません")

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {"status": "ok", "model": "minidora-notnn-1", "version": engine.VERSION}

    @app.get("/ready")
    def ready() -> dict[str, Any]:
        return {"status": "ready", "integrity": engine.store.integrity(), "doctor": engine.doctor()}

    @app.get("/v1/models", dependencies=[Depends(user_auth)])
    def models() -> dict[str, Any]:
        return {"object": "list", "data": [{"id": "minidora-notnn-1", "object": "model", "owned_by": "gatchimuchio"}]}

    @app.post("/v1/chat/completions", dependencies=[Depends(user_auth)], response_model=None)
    async def chat(payload: ChatRequest) -> dict[str, Any] | StreamingResponse:
        if payload.model != "minidora-notnn-1":
            raise HTTPException(status_code=404, detail="modelが存在しません")
        users = [message.content for message in payload.messages if message.role == "user"]
        if not users:
            raise HTTPException(status_code=422, detail="user messageが必要です")
        result = await asyncio.to_thread(engine.query, users[-1], session_id=payload.user, effort=Effort(payload.reasoning_effort))
        created = int(result.created_at.timestamp())
        body = {
            "id": result.request_id,
            "object": "chat.completion",
            "created": created,
            "model": payload.model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": result.text}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": len(users[-1]), "completion_tokens": len(result.text), "total_tokens": len(users[-1]) + len(result.text)},
            "minidora": {"status": result.status.value, "audit_id": result.audit_id, "session_id": result.session_id, "reason_codes": list(result.reason_codes)},
        }
        if not payload.stream:
            return body

        async def events():  # type: ignore[no-untyped-def]
            for index in range(0, len(result.text), 36):
                chunk = {"id": result.request_id, "object": "chat.completion.chunk", "created": created, "model": payload.model, "choices": [{"index": 0, "delta": {"content": result.text[index:index+36]}, "finish_reason": None}]}
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(events(), media_type="text/event-stream")

    @app.post("/api/v1/documents", dependencies=[Depends(admin_auth)])
    def add_document(payload: DocumentCreate) -> dict[str, Any]:
        document_id = engine.add_document(DocumentInput(payload.title, payload.body, payload.source_uri, payload.metadata))
        return {"status": "PASS", "document_id": document_id}

    @app.post("/api/v1/facts", dependencies=[Depends(admin_auth)])
    def add_fact(payload: FactCreate) -> dict[str, Any]:
        fact_id = engine.add_fact(FactInput(payload.predicate, tuple(payload.args), payload.polarity, payload.source_id, payload.confidence))
        return {"status": "PASS", "fact_id": fact_id}

    @app.post("/api/v1/rules", dependencies=[Depends(admin_auth)])
    def add_rule(payload: RuleCreate) -> dict[str, Any]:
        rule_id = engine.add_rule(RuleInput(payload.name, tuple(tuple(row) for row in payload.premises), tuple(payload.conclusion), payload.priority))
        return {"status": "PASS", "rule_id": rule_id}

    @app.get("/api/v1/audits/{audit_id}", dependencies=[Depends(user_auth)])
    def audit(audit_id: str) -> dict[str, Any]:
        value = engine.audit(audit_id)
        if not value["events"]:
            raise HTTPException(status_code=404, detail="監査記録が存在しません")
        return value

    @app.post("/api/v1/admin/doctor", dependencies=[Depends(admin_auth)])
    def doctor() -> dict[str, Any]:
        return engine.doctor()

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def index() -> str:
        return """<!doctype html><html lang='ja'><meta charset='utf-8'><title>MINIDORA</title>
        <style>body{font-family:sans-serif;max-width:900px;margin:40px auto;padding:0 16px}textarea{width:100%;height:100px}pre{white-space:pre-wrap;background:#f4f4f4;padding:16px}</style>
        <h1>MINIDORA</h1><p>日本語優先・HDS統治型の非ニューラル言語Runtime</p>
        <textarea id='q'>MINIDORAについて教えてください</textarea><button onclick='go()'>質問</button><pre id='o'></pre>
        <script>async function go(){const q=document.getElementById('q').value;const r=await fetch('/v1/chat/completions',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({model:'minidora-notnn-1',messages:[{role:'user',content:q}]})});document.getElementById('o').textContent=JSON.stringify(await r.json(),null,2)}</script>"""

    return app
