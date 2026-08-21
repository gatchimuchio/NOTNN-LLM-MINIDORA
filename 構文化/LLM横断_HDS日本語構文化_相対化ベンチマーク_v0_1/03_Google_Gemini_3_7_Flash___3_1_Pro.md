# Google Gemini 3.7 Flash / 3.1 Pro — HDS日本語構文化 第一巡

- 日付: 2026-08-21
- 区分: frontier closed multimodal
- 観測深度: D2 — 開発元の公式model/system card・engineering文書・公開挙動まで。内部weight/configは未観測

## 観測境界
3.7 Flashは3.6 Flash依存、3.1 Proは3 Pro依存と公式cardに明示。詳細weight geometryは非公開。

## 日本語構文化
- 系列方向: 未確定
- 深さ方向: 未確定
- 幅方向: 未確定
- 未来方向/予測補助: customizable thinking configurationを持つが内部実装へは遡及しない。
- 入力表象・モダリティ: text/image/audio/video、1M context。tool useはfunction calling/search/computer use等のproduct/API境界として観測。
- 形成過程: 版依存関係は明示されるが内部recipeの確定範囲は限定。
- 展開後制御: Gemini App/API/Vertex等複数channel。tool capabilityをcore weight属性と同一視しない。

## 相対化上の意味
「natively multimodal」という機能表現と、内部のモダリティ接続方式は別。非公開系では能力名から部品を逆推定しない基準点。

## 未解残差
- internal architecture details
- modality integration topology
- thinking internal mechanism

## 出典
