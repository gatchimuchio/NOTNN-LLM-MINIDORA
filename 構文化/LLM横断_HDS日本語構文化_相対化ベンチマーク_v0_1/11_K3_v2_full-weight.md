# K3 v2 full-weight — HDS日本語構文化 第一巡

- 日付: 2026-08-21
- 区分: highest-depth MoE anchor
- 観測深度: D4 — weight全payload実読＋tensor全数監査＋公開設定/構造を照合

## 観測境界
固定revision c5d1dd4c428bd1ce8b88c5044f3b6ccde9e3b721。96/96 shard、497,220/497,220 tensor、payload 1,560,860,324,864 byteを実読。

## 日本語構文化
- 系列方向: KDA/MLA等を名称だけで同一視せずlayer配置・作用で分離。
- 深さ方向: AttnResをattention内部へ潰さず、深さ方向の選択参照/輸送として独立。
- 幅方向: Stable LatentMoE等の専門経路制御を系列参照と分離。
- 未来方向/予測補助: MOPD等は独立制御として保持し、未確定機能を未来予測へ勝手に寄せない。
- 入力表象・モダリティ: 今回のfullweight対象範囲に従う。
- 形成過程: 旧v6.1意味構文を教師として使わずblind-primary-v2で再観測。
- 展開後制御: weight構造と外部runtimeを分離。

## 相対化上の意味
今回の最高解像度基準点。DeepSeek V4/Qwen/OLMo/Llama等を相対化した後に再配置すると、系列・深さ・幅の独立性がより明確になる。

## 未解残差
- shard1 zero位置の位置帰属は当時保持されず推測しない
- 非公開training/deployment情報

## 出典
