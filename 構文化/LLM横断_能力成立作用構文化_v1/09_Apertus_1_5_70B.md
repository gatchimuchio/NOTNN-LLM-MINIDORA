# 09 Apertus 1.5 70B — 能力成立作用構文化

- 観測深度: D3
- 区分: dense multimodal natural experiment
- ライセンス: CC-BY-4.0

## B0 観測境界

公開config/checkpoint/repository構成と公式説明を観測。1.0から1.5へのcontinued pretraining、同系decoder architectureの維持、vision/audio tokenizer weightの分離を確認。全weight意味解析と前段→decoder接続の全詳細は未観測。

## 観測事実

- 中央decoderは1.0系のdecoder-only Dense Transformer系譜を維持。
- 1.5はcontinued pretrainingを受ける。
- multimodal mixを形成過程へ追加。
- vision tokenizer / audio tokenizer weightを中央coreと別artifactで持つ。
- posttrainingでinstruction / thinking / tool capabilityを改善。

## B1 状態保持

中央decoderではstandard residual + dense global-attention系として、前状態を後段へ累積する。

## B2/B3 参照・再照合

中央text decoderはglobal attention系。局所専用周期の追加を本観測からは確定しない。

### 直接作用

新modalityの追加が、中央decoderの系列作用子を全面置換しなくても成立している。

## B4 深さ輸送

standard residual系。1.0→1.5で中央geometryを維持するという公開説明から、能力追加をdepth architecture刷新だけへ帰属できない。

## B5 幅選択

Dense FFN系。MoEを能力拡張の必須要因としない。

## B6 未確定差の共存

中央decoderの連続hidden/residual状態へ、異なる入力前段から得た表象を接続できる。具体的にmodal間競合をどう内部表現するかは未観測。

## B7 未来補助 / thinking mode

thinking modeはposttraining / serving modeとして中央decoder geometryと分離して扱う。内部反復機構は未観測。

## B8 形成作用

本モデルの最重要観測点。

```text
既存中央decoder
↓
continued pretraining
+ multimodal mix
+ posttraining
↓
同系geometryのまま能力範囲を拡張
```

### 直接作用

**architectureを維持したまま形成履歴と入力表象を変えることで能力を拡張できる。**

従って「能力が足りない → 中央architectureを増築する」だけが解ではない。

## B9 展開後制御

tool calling / thinking modeの利用条件はruntime modeとして中央模型性から分離する。

## MINIDORAへの作用射影候補

- 新modalityを追加するとき、模型核を書き換える前に**言語対応adapter**として共通内部状態へ接続できるかを検討する。
- 新しい能力・関係密度はformation処理によって獲得できる設計を持つ。
- `architecture変更` と `関係獲得` を別工程にする。
- thinking / tool modeはruntime制御として追跡する。

## 未観測

- 1.5全weight意味分布
- modality前段→decoder接続の全topology
- thinking内部機構

## 出典

- Apertus 1.5 official model/repository documentation
- 第一巡HDS固定観測
