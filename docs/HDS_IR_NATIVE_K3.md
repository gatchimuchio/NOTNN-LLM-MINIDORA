# HDS-IRネイティブK3接続経路

HDS Compilerが形成した一般HDS-IRを、表層自然言語へ戻さずK3相当能力核へ直接渡す接続層の補助説明である。

この文書は実装経路の要約であり、設計正本を置き換えない。

参照する現行契約:

- [`../設計/07_HDS_IR入力契約.md`](../設計/07_HDS_IR入力契約.md) — HDS-IR受入・実行境界
- [`../設計/02_Layer0責任契約.md`](../設計/02_Layer0責任契約.md) — Layer-0上位契約のMINIDORA局所写像
- [`../REFERENCES.md`](../REFERENCES.md) — Layer-0正本と外部参照階層

## 経路の不変条件

- ベンチ名・設問固有語・正解情報に依存しない。
- `choice:*` 座標から候補集合を受け取る。
- Kの根拠事実が候補と問いの双方に接続するときだけ候補を形成する。
- 根拠なし・同率根拠はJ/HDSが `SUSPEND` し、推測で回答しない。
- HDS Compiler内部は本公開リポジトリへ含めない。

実装は `src/minidora/k3_hds_native.py`、関連試験は `tests/test_k3_hds_native.py` と `tests/test_k3_hds_structural.py` を参照する。
