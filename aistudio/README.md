# MINIDORA — AI Studio / Web UI

日本語正本。

このディレクトリは、MINIDORAの製品UIと、**完全に独立したGemini比較窓**を提供する。

## 画面構成

### MINIDORA本窓

通常のチャットAI製品として使う主画面。

- MINIDORA Chat
- Capability Module表示
- Sources表示
- Governance Trace
- 新しい会話
- MINIDORA Backend接続状態
- Gemini比較ON/OFF

### Gemini比較窓

`/gemini` で別ウィンドウとして開く。

GeminiはMINIDORAの内部経路へ一切入らない。

```text
同じユーザー入力
      ├─ MINIDORA
      │    └─ Core / Capability Modules / Search API / Governance
      │
      └─ Gemini比較窓
           └─ Gemini API
```

## 絶対境界

- GeminiをMINIDORAのData sourceにしない。
- GeminiをMINIDORAの検索、推論、要約、fallbackに使わない。
- MINIDORAのSources、Trace、Module出力をGeminiへ渡さない。
- Geminiの回答をMINIDORAへ渡さない。
- 比較ON時に共有するのは**ユーザー入力文だけ**。
- MINIDORAが必要とする外部情報は、MINIDORA側のSearch / Reference Moduleから検索APIへ接続する。

この分離により、デモ時の説明は次の一文で閉じる。

> MINIDORAは検索APIからDataを取得して自身のCapability Moduleで処理し、Geminiは別ウィンドウで独立した比較対象として同じ質問に回答している。

## 設定

MINIDORA本窓:

```text
MINIDORA_BACKEND_URL=https://<minidora-backend>
```

Gemini比較窓をAPI接続する場合:

```text
GEMINI_API_KEY=...
GEMINI_MODEL=...
```

`GEMINI_API_KEY` 未設定時もMINIDORA本窓は使用できる。比較窓は未設定を明示し、モック回答は生成しない。

## 起動

Node.js 18以上。

```bash
npm start
```

既定:

```text
MINIDORA: http://localhost:3000/
Gemini比較窓: http://localhost:3000/gemini
```

## API

MINIDORA Backendへ透過:

- `POST /api/chat`
- `GET /api/trace/:trace_id`
- `GET /api/capabilities`
- `GET /health`

独立Gemini比較:

- `POST /api/gemini`

UI状態:

- `GET /bridge/status`

## 同期

`BroadcastChannel` が利用可能な場合、比較ON時にMINIDORA本窓からGemini比較窓へユーザー入力文だけを同期する。

未対応ブラウザではGemini比較窓へ手動入力できる。
