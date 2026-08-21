# Claude Fable 5 / Mythos 5 — HDS日本語構文化 第一巡

- 日付: 2026-08-21
- 区分: frontier closed / natural experiment
- 観測深度: D2 — 開発元の公式model/system card・engineering文書・公開挙動まで。内部weight/configは未観測

## 観測境界
AnthropicがFable 5とMythos 5を同じunderlying modelと明示。

## 日本語構文化
- 系列方向: 未確定
- 深さ方向: 未確定
- 幅方向: 未確定
- 未来方向/予測補助: 未確定
- 入力表象・モダリティ: 公開サービス能力としてvision等あり。内部統合方式は未確定。
- 形成過程: 内部詳細は限定公開。
- 展開後制御: Fableは外部classifier/safeguardを伴い、flagged queryをOpusへfallback/reroute。Mythosは同じunderlying modelで一部safeguardを外す。

## 相対化上の意味
同一core modelでも展開後制御だけで「別名サービス」「別の可観測挙動」が成立する自然実験。A1/A8を強く確定。

## 未解残差
- underlying architecture
- weight geometry
- classifier内部詳細の全量

## 出典
- https://www.anthropic.com/news/claude-fable-5-mythos-5
- https://www.anthropic.com/transparency/model-report
- https://www.anthropic.com/news/redeploying-fable-5
