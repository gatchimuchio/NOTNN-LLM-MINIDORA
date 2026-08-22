# MINIDORA 性能改善 v0.5 作業ログ — 2026-08-22

## 状態

`IN PROGRESS / BENCHMARK NOT YET RERUN`

この文書は履歴ログであり、成果宣言ではない。性能価値は次の実測値だけで判定する。

## 参照記録

- 過去記録: 8 / 198 = 4.0404040%
- 直近開発実測: 17 / 198 = 8.5858586%

どちらも参照ログであり、保護対象の性能値ではない。

## v0.5 一般能力改修

### 技術表現・数式

- 1桁数値、符号付き数値、科学記数法、指数、分数を意味保持
- LaTeX分数、平方根を `math:` anchorとして保持
- 列挙記号・変数・ギリシャ文字を `atom:` / `sym:` として内部保持
- 内部anchorは外部検索へ通常表記で渡す

### 候補差分検索

- 長文choice全文ではなく、他候補との差分意味を候補別queryへ使用
- 数値・数式だけが異なる候補も識別
- 全候補へ同一規則を適用
- 主検索で一部候補しか被覆できない場合、未被覆候補だけ段階縮退
- `対象 + 候補差分` → `候補差分単独` の二段fallback

### 長文QA焦点

- query切詰め時に冒頭文脈と末尾焦点を同時保持
- 最後の実質問文を背景とは別のfocus queryとして検索
- 長い背景の末尾にある問いを検索面から消さない

### K3候補識別

- 候補全文の共通意味と、候補集合内の差分意味を分離
- 候補固有意味を証拠照合・graph探索で優先
- 共通語だけの一致は弱く残し、差分意味まで一致した証拠を強くする
- 同一sourceが複数候補へ当たる場合は候補間の相対差を主に使用

### 検索経路provenance

- どの候補queryで参照文書を取得したかを保持
- 同一文書が複数候補queryで取得された場合は全経路を保持し、候補固有証拠にしない
- 候補固有query由来でも、本文自身が候補固有意味に一致しなければ証拠化しない
- 弱い検索経路証拠は複数独立文書・一意優勢を要求し、confidenceを低く制限

### 例外・否定選択

- `except / incorrect / not true / 該当しない` 等を最終質問文だけから判定
- 背景文中の `not` や `false positive` は採否方向へ伝染させない
- 例外問題を単純な最低score選択へしない
- N択のうちN−1候補が独立出典かつ候補固有意味まで確認できた場合だけ残り1候補を消去
- 条件不足時は `SUSPEND / NO_GUESS`

### 科学参照R

標準一般知識Rを次へ拡張:

- Wikipedia: 百科事典
- Europe PMC: key不要の科学・生命科学・医学文献abstract
- Crossref: key不要の分野横断学術メタデータ・abstract
- OpenAlex: API keyが明示された場合だけ追加

検索順位や被引用数を真偽confidenceへ変換しない。
Europe PMC / Crossrefで同一DOIを得た場合はDOI共通識別子で1資料へ統合し、複数独立sourceとして水増ししない。同一sourceの複数Provider記録はconfidence・本文量の高い記録へ品質統合する。

### 既存能力の再利用

Layer-0には既に加算・減算・乗算・除算・比較があるため、v0.5ではベンチ用の別計算器を新設しない。

## 過学習防止境界

禁止:

- GPQA問題番号・設問固有文字列による分岐
- GPQA正答辞書
- goldをR / Compiler / K / Jへ渡すこと
- 特定設問だけに対応する物理・化学公式の直書き
- 検索hit数だけを真偽へ変換すること
- 同一論文をProvider違いで複数独立sourceへ数えること
- 点数目的のJ閾値緩和
- SUSPENDの無根拠回答化

採用する改修は、検索QA・技術文書・数式・一般選択問題へ同一規則で適用できるものに限定する。

## 一般fixture

GPQAとは無関係なfixtureとして以下を追加済み:

- ProteinXの候補被覆・段階検索
- 同一資料のA/B両候補query provenance保持
- 検索経路hitだけでは証拠化しない境界
- 長文の冒頭文脈＋末尾焦点保持
- 長文最終質問の独立focus query
- 数値・数式・ギリシャ記号の意味保持
- 候補共通意味と差分意味の分離
- N−1根拠付き例外消去
- 背景中の否定語による誤反転防止
- Europe PMC / Crossrefレスポンス変換
- DOI共通識別とProvider横断品質統合

## 実行基盤状況

2026-08-22時点:

- GitHub Actions: GPQA測定run #2も `measure` jobが `steps=null` のままrunner開始前failure
- 通常CIも同様にrunner開始前failure
- Hugging Face Jobs: `402 Payment Required`

外部基盤停止であり、v0.5の性能値として扱わない。

GPQA workflowは `src/minidora/**` の変更でも自動起動するよう更新済み。runner復旧時は現行PR headを自動再測定する。

## 次回測定

198 / 198を再実測し、少なくとも以下を残す。

- correct
- answered
- wrong
- SUSPEND
- NO_KNOWLEDGE_EVIDENCE
- AMBIGUOUS_EVIDENCE
- provider別取得数

新しい実測値が出るまで、v0.5をmainへマージしない。
