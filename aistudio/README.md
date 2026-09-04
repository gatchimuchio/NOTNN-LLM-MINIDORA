# MINIDORA — Google AI Studio 接続版

このWebアプリはMINIDORA本体をNode.jsで再実装しない。
Google AI Studio Build ModeのWebランタイムはNode.jsであるため、実MINIDORA（Python）は別のCloud Run serviceとして起動し、このアプリはHTTPで接続する。

## 構成

```text
Google AI Studio / Browser
        ↓
Node.js Bridge（本ディレクトリ）
        ↓ MINIDORA_BACKEND_URL
MINIDORA Product Backend（Python / Cloud Run）
        ↓
MINIDORA Core + Capability Modules + Governance
```

## 必須設定

AI StudioのSecrets / Environmentで次を設定する。

```text
MINIDORA_BACKEND_URL=https://<real-minidora-backend>/
```

未設定時はモック応答を返さず、HTTP 503 `minidora_backend_not_configured` を返す。

## ローカル確認

Node.js 18以上。

```bash
MINIDORA_BACKEND_URL=http://127.0.0.1:8080 npm start
```

フロント側は通常 `http://127.0.0.1:3000`。

## API

以下を実MINIDORA backendへ透過する。

- `POST /api/chat`
- `GET /api/trace/:trace_id`
- `GET /api/capabilities`
- `GET /health`

## 禁止

- `server.js` 内に固定応答・疑似Traceを追加しない。
- Gemini等の外部LLMをMINIDORA本体の代替として呼ばない。
- MINIDORA CoreやCapability ModuleのロジックをNode側へ複製しない。
