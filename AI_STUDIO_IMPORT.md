# Google AI Studio Import

このRepositoryをGoogle AI StudioへGitHub Importした場合、root `package.json` は
`aistudio/` workspaceへ実行を委譲する。

- `npm run dev` -> `aistudio` MINIDORA Web app
- `npm run build`
- `npm run test`
- `npm run lint`

Python正本 `src/minidora/` は変更しない。
AI Studio版の実装責任範囲は `aistudio/`。

Geminiは独立Comparatorのみ。MINIDORA `/api/chat` からGeminiを呼ばない。
