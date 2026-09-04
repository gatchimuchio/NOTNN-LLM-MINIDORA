from __future__ import annotations
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json, os, re, mimetypes
from pathlib import Path
from urllib.parse import urlparse
from .製品チャット import 製品ミニドラ

API版 = "MINIDORA-PRODUCT-API-v1"

def _json(handler: BaseHTTPRequestHandler, status: int, body: dict):
    raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type","application/json; charset=utf-8")
    handler.send_header("Content-Length",str(len(raw)))
    handler.send_header("Cache-Control","no-store")
    handler.send_header("Access-Control-Allow-Origin", os.getenv("MINIDORA_CORS_ORIGIN","*"))
    handler.end_headers(); handler.wfile.write(raw)

class APIHandler(BaseHTTPRequestHandler):
    server_version = "MINIDORA-Product/1"
    max_body = 256_000

    @property
    def app(self) -> 製品ミニドラ:
        return self.server.app  # type: ignore[attr-defined]

    def log_message(self, fmt, *args):
        if os.getenv("MINIDORA_HTTP_LOG","1") != "0": super().log_message(fmt,*args)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", os.getenv("MINIDORA_CORS_ORIGIN","*"))
        self.send_header("Access-Control-Allow-Headers","Content-Type")
        self.send_header("Access-Control-Allow-Methods","GET,POST,OPTIONS")
        self.end_headers()

    def _static(self, path: str):
        base = Path(__file__).resolve().parent / "web"
        rel = "index.html" if path == "/" else path.removeprefix("/static/")
        target = (base / rel).resolve()
        try:
            target.relative_to(base.resolve())
        except ValueError:
            return _json(self,403,{"error":"forbidden"})
        if not target.is_file():
            return _json(self,404,{"error":"not_found"})
        raw = target.read_bytes(); mime = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        self.send_response(200); self.send_header("Content-Type",mime); self.send_header("Content-Length",str(len(raw))); self.send_header("Cache-Control","no-cache"); self.end_headers(); self.wfile.write(raw)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/" or path.startswith("/static/"): return self._static(path)
        if path == "/health": return _json(self,200,{"ok":True,"service":"MINIDORA Product","api_version":API版})
        if path == "/api/capabilities": return _json(self,200,{"capabilities":list(self.app.能力一覧())})
        m = re.fullmatch(r"/api/trace/([a-f0-9]{32})", path)
        if m:
            r = self.app.監査台帳.取得(m.group(1))
            if not r: return _json(self,404,{"error":"trace_not_found"})
            return _json(self,200,{"trace":r.辞書化(),"valid":self.app.監査台帳.検証(m.group(1))})
        return _json(self,404,{"error":"not_found"})

    def do_POST(self):
        if urlparse(self.path).path != "/api/chat": return _json(self,404,{"error":"not_found"})
        try: length = int(self.headers.get("Content-Length","0"))
        except ValueError: return _json(self,400,{"error":"invalid_content_length"})
        if length <= 0 or length > self.max_body: return _json(self,413,{"error":"invalid_body_size"})
        try: payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception: return _json(self,400,{"error":"invalid_json"})
        message = str(payload.get("message","")).strip(); session = str(payload.get("session_id","default")).strip() or "default"
        if not message: return _json(self,400,{"error":"message_required"})
        response = self.app.応答(message, セッションID=session)
        return _json(self,200,response.辞書化())

def serve(app: 製品ミニドラ, host: str = "0.0.0.0", port: int | None = None):
    p = int(port or os.getenv("PORT","8080"))
    server = ThreadingHTTPServer((host,p), APIHandler); server.app = app  # type: ignore[attr-defined]
    server.serve_forever()
