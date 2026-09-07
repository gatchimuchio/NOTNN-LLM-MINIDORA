# MINIDORA 現行正本

## 状態

```text
Canonical: MINIDORA Core37
Date: 2026-09-08
Development state: FROZEN
Audited implementation commit: 43360697098fe2a62df7ee077a14cefd851351db
```

現時点の正本は、固定条件のGPQA Diamond正式198問で次を確認した現行Core系列である。

| 指標 | 正本値 |
|---|---:|
| Core | 32 / 198 (16.16%) |
| Core+HDS | **37 / 198 (18.69%)** |

37/198はMINIDORA方式そのものの理論限界ではない。**現行のLLM構成定義・既存LLM構文化・MINIDORA Core射影・設計系列を凍結するための実測セーブポイント**として扱う。

2026-09-02の科学専門Capability Module controlled replayで得た63/198は別系列であり、Core正本性能へ混ぜない。

## 正本根拠

- [Core37 正本固定監査](評価/MINIDORA_Core37_正本固定監査_2026-09-08.md)
- [2026-09-08 開発終了記録](docs/開発終了記録_2026-09-08.md)

## 更新条件

現行正本を置換する場合は、原則として次から再開する。

```text
残差・未表現領域の観測
→ 既存LLM再観測
→ 能力成立作用の再構文化
→ LLM構成定義の再監査・必要なら更新
→ MINIDORA Coreへ再射影
→ 再測定・監査
→ 新正本へ置換
```

新正本が成立するまではCore37を基準とする。
