# 02 Claude Fable 5 / Mythos 5 — 能力成立作用構文化

- 観測深度: D2
- 区分: frontier closed / deployment natural experiment
- ライセンス: CC-BY-4.0

## B0 観測境界

underlying modelのweight/config/内部architectureは非公開。Fable 5とMythos 5が同一underlying modelを共有するという公開情報と、外部classifier / safeguard / fallbackの差を観測対象とする。

## 観測事実

- Fable 5 / Mythos 5は同一underlying modelを共有する。
- Fable系では外部classifier / safeguardがqueryを判定し、条件に応じて別modelへfallback / rerouteする。
- Mythos系では同じunderlying modelを使いつつ一部の外部制御が異なる。

## B1〜B7 core内部作用

**未観測。**

同一coreという事実から内部の状態保持方式、attention、depth transport、latent hypothesis保持等を逆推定しない。

## B8 形成作用

内部recipeの全量は未観測。少なくとも、Fable/Mythos間の可観測差を形成差だけへ帰属できない。deployment差だけで挙動差が成立するからである。

## B9 展開後制御

```text
入力
↓
外部分類・安全判定
├─ coreへ通す
└─ fallback / reroute
     ↓
   別model / 別経路
```

### 直接作用

- queryの一部はunderlying modelへ到達する前に別経路へ送られる。
- 同一coreでも外部Gateの条件が違えば可観測出力分布・拒否・fallback率が変わる。
- したがって、製品挙動からcore能力を直接測ると外部制御が混入する。

## 比較推定

Fable / Mythosは、**model coreとdeployment policyを分けなければ能力差の因果を誤認する**ことを示す強い自然実験である。

MINIDORAでも、未知停止・安全停止・外部参照不足・model側関係不足を同じSUSPEND理由へ潰すと、能力監査が壊れる。

## MINIDORAへの作用射影候補

- model coreの成立差と外部Gateの採否を別ログへ残す。
- fallback / routingで得た結果をmodel core自身の知識として加算しない。
- 「答えなかった」を「知らなかった」へ自動変換しない。
- 安全・policy・authority controlをK/Jの意味能力と分離する。

## 未観測

- underlying architecture
- state retention mechanism
- internal hypothesis competition
- classifier全構造
- fallback条件全量

## 出典

- Anthropic公開Fable/Mythos説明
- Anthropic model / transparency report
- 第一巡HDS固定観測
