# 04 DeepSeek V4 — 能力成立作用構文化

- 観測深度: D3相当
- 区分: frontier architecture-public / MoE
- ライセンス: CC-BY-4.0

## B0 観測境界

公開paper、Transformers実装、configから中央構造を観測。weight全量の意味分布、各expertの意味役割、production harness全量は未観測。

## 観測事実

- 系列方向にlocal sliding branchとlong-range branchを併置する。
- long-range側はCSA / HCAという異なる圧縮・選択方式を持つ。
- CSAは圧縮表象とindexer top-k選択を組み合わせる。
- HCAはより高く圧縮した長距離表象を広く参照する。
- 深さ方向はstandard residualではなくmHCを用い、複数parallel residual streamを混合する。
- 幅方向はMoEを持つ。

## B1 状態保持

local branchは近傍の細部を、compressed branchはより長距離の情報を別表象として後段へ渡せる。

mHCは深さ方向に単一路ではなく複数streamを持ち、後段で混合可能な状態を維持する。

### 直接作用

**細部状態・圧縮長距離状態・深さ方向複数streamを早期に一つへ潰さず後段へ運べる。**

## B2 局所更新・参照

sliding-window branchが近傍情報を明示参照する。局所的な語順・関係・最近の状態差を高圧縮long-range表象だけへ依存させない。

## B3 大域再照合

CSA / HCAが局所window外の情報を再接続する。

- CSA: long-range候補を選択して参照する作用。
- HCA: より圧縮された広域表象を密に再参照する作用。

圧縮率と選択方式を別軸として持つため、長距離情報を「保持する/しない」の二値だけでなく、**どの精度・密度で残していつ呼び戻すか**を変えられる。

## B4 深さ輸送

mHCはattentionとは別に、層間で複数残差streamを制約付きで混合する。

### 直接作用

同じ系列参照結果でも、深さ方向へ残す経路を複数持てる。従って「何を参照するか」と「参照後の差をどう保持・混合するか」は独立である。

## B5 幅選択

MoEは入力状態に応じて一部expertを選ぶ。shared/common pathと専門pathを分けられる構成を持つ。

expert固有意味は未読のため、「科学expert」「数学expert」のような意味ラベルは付けない。

## B6 未確定差の共存

複数branch、複数residual stream、MoE出力は連続状態として後段へ統合される。途中で一つの離散回答へ確定する構造ではない。

ただし、具体的な仮説A/Bがどのstreamに保持されるかは未観測。

## B7 未来補助

公開V4系列で確認できる補助機構は主自己回帰経路と分離する。未確認部分を補わない。

## B8 形成作用

大規模pretrainingとposttrainingにより、architectureが提供する多数の保持/参照経路へ具体的な関係が形成される。architectureだけではその中身は決まらない。

## B9 展開後制御

Transformers実装は観測済み。production routing、cache、service orchestrationは模型外として分離する。

## MINIDORAへの作用射影候補

- 近傍の高解像度状態と、長距離の圧縮状態を別に保持する。
- 圧縮した情報を捨てず、必要時に元Dataまたは高解像度関係へ戻れる索引を持つ。
- 一つの中間状態だけでなく、競合する作業stateを複数保持できるようにする。
- 共通作用と条件付き専門作用を分離する。
- 上記をattention/MoE/mHCそのものとしてコピーしない。

## 未観測

- weight全量意味分布
- expert固有意味
- residual streamの意味分業
- production harness

## 出典

- DeepSeek V4 paper / public Transformers implementation
- 第一巡HDS固定観測
