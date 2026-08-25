# 03 Google Gemini 3.7 Flash / 3.1 Pro — 能力成立作用構文化

- 観測深度: D2
- 区分: frontier closed multimodal
- ライセンス: CC-BY-4.0

## B0 観測境界

内部weight/config、系列作用子、深さ輸送、幅選択、モダリティ統合topologyは非公開。公開model card/API上の長文脈、multimodal、thinking control、tool capabilityを観測する。

## 観測事実

- text / image / audio / video等の複数入力を扱う。
- 長contextを公開する。
- thinking level / thinking configurationとして推論時の計算努力を外部から調節できる。
- function calling、search、computer use等のtool capabilityをAPI/product層で提供する。
- 同名family内でも版依存関係を持つ。

## B1〜B6 core内部作用

**未観測。**

multimodal能力から「共通embedding方式」「単一encoder」「特定cross-attention」を推定しない。thinking設定から内部CoT構造や特定latent loopを推定しない。

## B7 未来補助・test-time effort

外部から観測できるのは、同一model familyに対し推論努力量を変えられること。

### 直接作用

- 入力が同じでも、runtime設定により使用する計算予算・経路が変わりうる。
- 能力評価ではmodel identityとtest-time compute conditionを同時に固定する必要がある。

内部で何回再帰するか、どのstateを再利用するかは未観測。

## B8 形成作用

版依存・posttrainingの存在は観測できるが、内部recipe全量は未観測。能力差を中央architecture変更だけへ帰属しない。

## B9 展開後制御

App / API / Vertex等のchannel、tool integration、検索、computer useは外部運用層として扱う。

### 作用上の意味

```text
複数入力
↓
modelへ渡せる表象へ接続
↓
model処理
↓
tool / channel / runtime control
↓
可観測結果
```

このどの境界に能力が宿るかを非公開内部へ勝手に遡及しない。

## MINIDORAへの作用射影候補

- modalityは別adapterから共通の明示言語状態へ接続できる設計にする。
- reasoning effortは模型関係そのものではなく、同じ関係へ何回・どこまで再作用するかを決めるruntime制御として分離可能。
- tool resultをmodel内部知識と混同しない。
- 長context能力を単なる最大文字数ではなく、保持状態へ再アクセスできるかで評価する。

## 未観測

- modality integration topology
- internal thinking mechanism
- latent-state recurrence
- sequence/depth/width mechanisms

## 出典

- Google Gemini model cards / API documentation
- 第一巡HDS固定観測
