# MINIDORA v0.2 公開再構成成果 — Legacy

**状態: LEGACY / 履歴固定**

このディレクトリは、MINIDORA v0.2時点で公開可能だった再構成成果を履歴として保持する。

現行MINIDORAはv0.3であり、現在の設計正本・Runtime・Layer-0責任を本ディレクトリから復元しない。

- `Layer0/` — v0.2時点のLayer-0入出力・責任再構成
- `P/` — v0.2時点の日本語命令形P
- `R/` — v0.2時点の外部参照R分離境界
- `Adapter/` — v0.2時点の外部表現と内部実行系の接続境界

特に、v0.2内の旧Layer-0責任を現行v4の責任数・意味へ昇格させない。

現行のLayer-0論理上位正本は [gatchimuchio/LLM-Layer-0-Functional-Compliance-Specification](https://github.com/gatchimuchio/LLM-Layer-0-Functional-Compliance-Specification) `v4.0-provisional`、MINIDORA局所写像は [`../../設計/02_Layer0責任契約.md`](../../設計/02_Layer0責任契約.md) を参照する。

現行再構成成果は [`../MINIDORA_v0.3/`](../MINIDORA_v0.3/) を参照する。

上流の解析手順・内部台帳・意味分別資料は含めない。
