# HDS-IRネイティブK3接続経路

HDS Compilerが形成した一般HDS-IRを、表層言語へ戻さずK3相当能力核へ直接渡す既存運用接続の補助説明である。

この文書はv0.3由来の実装経路を説明し、v0.4のLLM模型中核や設計正本を置き換えない。

参照する現行契約:

- [`../設計/07_HDS_IR入力契約.md`](../設計/07_HDS_IR入力契約.md) — HDS-IRを意味Projection・運用外周として扱う境界。
- [`../設計/02_大規模言語模型成立契約.md`](../設計/02_大規模言語模型成立契約.md) — v0.4模型中核の局所写像。
- [`../REFERENCES.md`](../REFERENCES.md) — 上流LLM成立規定と外部参照階層。

## 経路の不変条件

- ベンチ名・設問固有語・正解情報に依存しない。
- `choice:*` 座標から候補集合を受け取る。
- Kの根拠事実が候補と問いの双方に接続するときだけ候補を形成する。
- 根拠なし・同率根拠はJ/HDSが `SUSPEND` し、推測で回答しない。
- HDS-IRをLLM模型中核またはCompute IRと同一視しない。

実装は `src/minidora/k3_hds_native.py`、関連試験は `tests/test_k3_hds_native.py` と `tests/test_k3_hds_structural.py` を参照する。
