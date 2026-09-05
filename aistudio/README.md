# AI Studio GitHub Import 用実装

このディレクトリはAI StudioがGitHub Import後にroot workspace経由で起動するMINIDORA実装です。
Python正本はRepositoryの`src/minidora/`。本実装はそのAI Studio向けTypeScript portです。

# MINIDORA — AI Studio Port

非ニューラル・非Transformer型言語処理系 MINIDORA の AI Studio / Node.js 向け実装。

この版は「GeminiをMINIDORAとして呼ぶUI」ではない。MINIDORA本体はGemini APIなしで起動・実行する。Geminiは任意の独立比較窓だけに隔離される。

## 実装核

```text
User Input
   ↓
HDS semantic frontend
   ├─ 対象 / 目的 / 手段
   ├─ P（作用）/ Data 分離
   ├─ 関係抽出 / 残差
   └─ HDS semantic IR
   ↓
Operation Planner
   ↓
Capability Registry
   ├─ Calculation
   ├─ Summarization
   ├─ Extraction
   ├─ Transformation
   ├─ Comparison
   ├─ Conversation
   ├─ Search
   └─ Knowledge Reference
   ↓
Capability Result (structured state)
   ↓
Capability Model Kernel
   ├─ 意味連続
   ├─ 関係整合
   ├─ 履歴近接
   └─ 出力条件整合
   ↓
Strict Language Model Kernel
   └─ deterministic finite-state character n-gram / exact rational probability
   ↓
Final Validation
   ↓
Response + Trace + Sources
```

厳密言語模型核と能力模型核を同一視しない。HDS semantic IRもLLM核そのものではなく、自然言語要求から運用入力へ射影する境界として扱う。

## Data / Knowledge 境界

世界知識はCoreへ埋め込まない。

- SearchProvider: 外部検索Data
- ReferenceProvider: 外部知識Data
- SessionState: 会話内の作業状態
- Capability: 処理作用

Search / Reference Provider が未設定でもCoreは `ready`。外部知識を要求された場合だけ明示的に保留する。架空SourceやGemini fallbackは生成しない。

## Gemini比較

`GEMINI_API_KEY` は任意。設定した場合のみUIに「Geminiで比較」が表示される。

```text
MINIDORA path: User → MINIDORA Core → Response
Gemini path:   User → /api/gemini → Gemini Response
```

MINIDORA Response / Trace / Sources をGeminiへ渡さない。Gemini ResponseもMINIDORAへ戻さない。

## 実行

前提: Node.js 20+ 推奨。

```bash
npm install
npm run dev
```

MINIDORA本体にAPI keyは不要。

任意でGemini比較を使う場合だけ:

```bash
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-2.5-flash
```

## API

- `GET /health`
- `GET /api/health`
- `GET /api/capabilities`
- `POST /api/chat`
- `GET /api/trace/:traceId`
- `POST /api/gemini` — comparator only

`POST /api/chat`:

```json
{
  "text": "日付を抜いてJSONにして: 会議は2026-09-05です。",
  "sessionId": "optional-session-id"
}
```

## 実装済みCapability

- 厳密有理数を使う数式Parser（四則演算、括弧、整数指数）
- 抽出要約（語頻度、関係密度、位置、冗長性抑制）
- Email / URL / 日付 / 金額 / 数値 / key-value / relation抽出
- JSON / 箇条書き / Markdown表 / 行番号 / 重複除去 / 空白整理 / 大小文字変換
- 数値比較 / 二Dataの意味差分比較
- セッション内会話状態
- SearchProvider / ReferenceProvider交換境界
- 多段Capability計画（例: Search → Summarization、Extraction → Transformation）
- 実行経路から生成されるTrace

## 検証

```bash
npm test
npm run lint
npm run build
```

テストでは、計算、要約、抽出、複数Module連鎖、会話状態、Provider未設定時の保留、Source由来、Trace一致、厳密言語模型監査、Gemini分離を確認する。

## 非目標

このAI Studio Portだけで「GPT-4級性能を達成した」とは主張しない。現在の目的は、MINIDORAの非ニューラル中核・責任分離・Capability成長経路を、実際に動くWeb製品境界へ持ち込むこと。
