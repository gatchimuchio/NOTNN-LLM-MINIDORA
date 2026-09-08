# MINIDORA 現行正本

## 状態

```text
Canonical baseline: MINIDORA30
Date: 2026-09-09
Development state: ACTIVE
GPQA canonical benchmark: GPQA-E2E-LIVE only
GPQA fixed reference Data: FORBIDDEN
```

現行MINIDORAのGPQA Diamond汎用E2E性能セーブポイントは **MINIDORA30** とする。

| 指標 | 現行正本値 |
|---|---:|
| GPQA Diamond current | **30 / 198 (15.15%)** |
| 同run controlled baseline | 27 / 198 (13.64%) |
| current - baseline | **+3問 / +1.52pt** |
| 回答数 | 130 / 198 |
| SUSPEND | 68 / 198 |
| 改善 / 退行 | 3 / 0 |

正本表記:

```text
MINIDORA30 / GPQA-E2E-LIVE / 30/198 / 15.151515151515152%
```

## MINIDORA30 実測由来

- 局所解釈起点主要実装commit: `b70344677c3a761af3e3bfac57b1fe92980b6f0e`
- 実測対象実装親commit: `a3473fbdacc5e0e2ac1927faa08c60717ace0544`
- benchmark workflow commit: `63603f39d62bd77ae40732f6c51701aaab9fe468`
- GitHub Actions run: `34281226412`
- aggregate artifact: `10078256754`
- artifact SHA256: `0c7ef2b4a474bf5cd6ee55d5ca170480292186babbc7d559afb268c347ede83c`
- GPQA CSV SHA256: `41d1213cd7a4998605a26c2798500652572007161b3a92817ba46b35befcd305`

詳細:

- [MINIDORA30 GPQA E2E正本](評価/GPQA_Diamond_MINIDORA30_E2E_正本_2026-09-09.md)
- [機械可読正本manifest](評価/GPQA_Diamond_MINIDORA30_E2E_正本_2026-09-09.json)
- [MINIDORA30 Savepoint](docs/SAVEPOINT_2026-09-09_MINIDORA30.md)

## GPQA正本運用

2026-09-09のユーザー明示指示により、**以後GPQAでは固定参照Dataを禁止する。**

禁止対象:

```text
固定C2
保存済み検索結果
問題別Reference/Data bundle
Replay fixture
過去run参照の再投入
```

GPQA正本性能は、公式GPQA Diamond 198問へ実行時に参照を新規取得する汎用E2Eだけで測る。

正本入口:

```bash
python tools/benchmark_strict.py gpqa-e2e --out gpqa_e2e.json
```

正本条件:

```text
198 / 198 全数
choice seed = 0
OpenAlex = disabled
Wikipedia = en
reference = LIVE_ONLY
controlled A/B = required
fixed reference Data = forbidden
```

詳細契約は [Benchmark Contract v2](評価/BENCHMARK_CONTRACT_v2.md) を正本とする。

部分実行・任意条件・過去Replayは診断・履歴用途に限り、現行GPQA正本性能値として採用しない。

## 過去のCore37

2026-09-08に固定したCore37:

```text
Core = 32 / 198
Core+HDS = 37 / 198
reference = 固定C2 Replay
```

は**履歴として保存するが、現行GPQA正本ではない。**

固定C2 Replayを将来のGPQA正本性能比較へ再利用しない。Core37の監査文書・実測資産は当時の履歴証拠として残す。

2026-09-02の科学専門Capability Module replay `63/198` も同様に履歴・モジュール拡張成立実証として保持するが、現行GPQA性能へ混ぜない。

## 局所解釈起点

2026-09-09に再開した局所解釈起点は現行MINIDORAへ実装済みである。

```text
現在の局所解釈 S_t
+ 現在入力
→ 解釈 / 計画 / 判断 / 実行
→ 結果
→ S_t+1
```

これは同一Runtime寿命の局所意思決定連続性であり、永続人格・端末間同期・長期主体記憶をLLMへ追加するものではない。長期保持はAgent / AGI等の上位主体の責任として分離する。

- [局所解釈起点契約](設計/36_MINIDORA_局所解釈起点_v1.md)
- [2026-09-09 開発再開記録](docs/開発再開記録_2026-09-09.md)

## 正本置換条件

次にGPQA正本性能値を置換する場合は、Benchmark Contract v2の正本入口で198/198を完走し、LIVE_ONLY・固定参照Data禁止・dataset hash・seed・provider条件を機械確認する。

異なる日時のGPQA E2E得点差は、同一運用規則における性能スナップショットの時系列差として記録する。コード変更だけの純粋因果差を取るために固定GPQA参照Dataへ戻ることは禁止する。

コード単位の因果監査は、GPQAとは別の局所A/B・機能受入・退行試験で行う。
