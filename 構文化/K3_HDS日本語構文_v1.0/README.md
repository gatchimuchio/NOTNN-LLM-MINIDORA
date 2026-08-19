# K3 HDS 日本語構文化 v1.0

## 位置づけ

これはMVPではない。

Source Lockで固定したK3公式公開情報を教師データとしてHDSで分別し、LLM Layer-0系へ全件写像し、意味系を日本語構文へ再記述した現行成果である。

```text
K3公開教師データ
→ HDS意味分別
→ Layer-0 / P / Adapter / P形成 / 実装効率 / 評価証拠
→ 日本語構文化
```

## 被覆

- 教師意味項目: 197
- 写像済み: 197
- HDS意味分別済み: 197
- 出典付き: 197
- 未写像: 0
- P本体へのK3固有語漏出: 0

## 正本

- [`教師固定/00_source_lock.json`](教師固定/00_source_lock.json)
- [`教師固定/README.md`](教師固定/README.md)
- `教師固定/教師_0001_0025.jsonl` 〜 `教師固定/教師_0176_0197.jsonl`
- [`HDS/00_HDS全量分別報告.md`](HDS/00_HDS全量分別報告.md)
- [`Layer0/Layer0写像正本.json`](Layer0/Layer0写像正本.json)
- [`P/日本語構文P_v1.k3p`](P/日本語構文P_v1.k3p)
- [`P形成/P形成構文_v1.k3p`](P形成/P形成構文_v1.k3p)
- [`Adapter/外部表現Adapter構文_v1.k3p`](Adapter/外部表現Adapter構文_v1.k3p)
- [`監査/coverage.json`](監査/coverage.json)

## 主張境界

ここでいう全件・100%は、Source Lockで固定した公式公開資料から抽出した**意味保持教師項目の変換被覆**を指す。

K3 Native内部、非公開training data、非公開内部状態、全重み内部意味を完全観測したという意味ではない。

また、この構文化完了だけでK3同等能力を宣言しない。次段はこのPをLayer-0へ実装し、K3の外部挙動教師証拠と照合する段階である。
