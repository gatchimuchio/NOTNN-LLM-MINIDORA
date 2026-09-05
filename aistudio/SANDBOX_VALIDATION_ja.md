# MINIDORA AI Studio Port — サンドボックス検証記録

## 実施内容

- AI Studio生成物の外殻を維持し、MINIDORA中核をTypeScriptで実装。
- Geminiは`/api/gemini`の独立比較経路だけに隔離。
- `/api/chat`はMINIDORA Coreだけを実行。

## 実装した中核

- HDS semantic frontend / HDS semantic IR
- 日本語命令形P / DataEnvelope分離
- 多段Operation Planner
- 非ニューラル厳密言語模型核（character n-gram / finite-state / exact rational）
- 言語模型状態serialize / restore / deterministic state hash
- 能力模型核（意味連続・関係整合・履歴近接・出力条件）
- Session working state
- Capability Registry
- Calculation / Summarization / Extraction / Transformation / Comparison / Conversation / Search / Knowledge Reference
- Provider由来追跡
- 実行経路Trace
- 実状態Health

## サンドボックス検証

### TypeScript Core strict compile

```text
tsc --target ES2022 --module NodeNext --moduleResolution NodeNext --lib ES2022,DOM --strict ...
Result: PASS
```

### Core self-test

18件を実行。

```text
PASS LM exact audit
PASS LM order-independent state
PASS LM serialize restore
PASS comparison capability
PASS calculation
PASS summarization compresses
PASS P/Data separation
PASS extraction + JSON chain
PASS session structured followup
PASS search disabled explicit
PASS search provider + provenance
PASS search -> summary chain
PASS knowledge no provider held
PASS conversation identity
PASS conversation recall
PASS trace nuclei
PASS health actual
PASS forbidden source audit

18 tests passed
```

### TypeScript syntax transpile

`src/**/*.ts`, `src/**/*.tsx`, `server.ts`, `tests/minidora.test.ts` をTypeScript transpileで構文検査。

```text
Result: PASS
```

### 禁止経路監査

`src` / `server.ts` に対して以下を検索。

- `new Function`
- `eval(`
- `MockSearchProvider`
- `example.com`
- `Gemini fallback`

```text
Result: 該当なし
```

`generateContent` / `GoogleGenAI` は `src/api/routes.ts` の `/api/gemini` 比較経路だけに存在。

## 実行できなかった検証

`npm install` はサンドボックスが外部npm registryへ接続できず、`@google/genai`がキャッシュされていないため実行不可。
そのため次は未実行。

- `npm test`
- `npm run lint`
- `npm run build`

失敗分類: environment / dependency retrieval limitation

AI Studioへ戻した後、依存取得可能な環境で上記3コマンドを実行すること。

## 現在の境界

- SearchProvider / ReferenceProviderは意図的に未接続。未設定時は明示保留し、架空Dataを生成しない。
- Gemini API keyはMINIDORA本体には不要。比較機能だけ任意。
- この実装はAI Studio向けTypeScript Portであり、Python正本の全ファイルを逐語移植したものではない。
- GPT-4級性能を達成したという主張は行わない。
