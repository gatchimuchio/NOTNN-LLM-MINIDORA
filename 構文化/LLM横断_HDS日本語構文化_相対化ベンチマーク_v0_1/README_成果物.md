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

成果物ZIP:
`LLM横断_HDS日本語構文化_相対化ベンチマーク_v0_1.zip`

SHA-256:
`d732760cb3541c19a79f68e29b6af9c682b1d1446882779ce5a06bf2a784559b`

ZIP内には統合報告、各モデル個別構文化、HDS更新差分、HDS相対座標JSON、MANIFESTを格納しています。
