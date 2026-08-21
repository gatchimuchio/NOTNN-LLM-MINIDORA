# LLM横断 HDS日本語構文化・相対化ベンチマーク v0.1

2026-08-21 実施の第一巡成果物です。

対象:
- OpenAI GPT-5.6 Sol
- Claude Fable 5 / Mythos 5
- Google Gemini 3.7 Flash / 3.1 Pro
- DeepSeek V4
- Qwen3.6-35B-A3B
- Grok 4.6
- Llama 3 70B (2024-04)
- OLMo 3
- Apertus 1.5 70B
- K2-V2 70B
- K3 v2 full-weight

目的は単一モデルの絶対評価ではなく、異質なLLMを同一の日本語HDS座標へ置き、差分によって基準自体を精密化することです。

GitHubでは転送監査性を優先し、成果物を展開済みテキスト正本として格納しています。
`MANIFEST.json` の bytes / SHA-256 を各ファイルの正本検証値とします。

ローカル生成ZIPの参考SHA-256:
`d732760cb3541c19a79f68e29b6af9c682b1d1446882779ce5a06bf2a784559b`

ZIPそのものはGitHubには置かず、同内容を展開済みで格納しています。
