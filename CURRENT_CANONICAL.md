# MINIDORA 現行正本

## 状態

```text
Canonical baseline: MINIDORA Core37
Date: 2026-09-09
Development state: ACTIVE_REOPENED
Previous audited implementation commit: 43360697098fe2a62df7ee077a14cefd851351db
```

2026-09-08に固定したCore37は、固定条件のGPQA Diamond正式198問で確認済みの比較基準として保持する。

| 指標 | Core37基準値 |
|---|---:|
| Core | 32 / 198 (16.16%) |
| Core+HDS | **37 / 198 (18.69%)** |

37/198はMINIDORA方式そのものの理論限界ではない。**現行のLLM構成定義・既存LLM構文化・MINIDORA Core射影・設計系列を凍結した時点の実測セーブポイント**として扱う。

2026-09-02の科学専門Capability Module controlled replayで得た63/198は別系列であり、Core正本性能へ混ぜない。

## 2026-09-09 開発再開

ユーザー明示指示により開発凍結を解除した。

再開対象は、同一MINIDORA Runtime内で現在解釈を局所保持し、各turnの意思決定をその更新前状態から開始し、結果を受けて次状態へ更新する `局所解釈起点` である。

これは永続人格・端末間同期・長期主体記憶をLLMへ追加する変更ではない。長期保持はAgent / AGI等の上位主体の責任として分離する。

- [局所解釈起点契約](設計/36_MINIDORA_局所解釈起点_v1.md)
- [2026-09-09 開発再開記録](docs/開発再開記録_2026-09-09.md)

新実装の検証が完了しても、GPQA等の再測定で新しい能力値が確定するまではCore37を性能比較基準として残す。

## Core37根拠

- [Core37 正本固定監査](評価/MINIDORA_Core37_正本固定監査_2026-09-08.md)
- [2026-09-08 開発終了記録](docs/開発終了記録_2026-09-08.md)

## 正本置換条件

Core37性能基準そのものを置換する場合は、原則として次から再開する。

```text
残差・未表現領域の観測
→ 既存LLM再観測
→ 能力成立作用の再構文化
→ LLM構成定義の再監査・必要なら更新
→ MINIDORA Coreへ再射影
→ 再測定・監査
→ 新正本へ置換
```
