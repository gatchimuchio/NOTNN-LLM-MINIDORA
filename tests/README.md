# tests

`tests/` は、MINIDORA Runtime・Layer-0局所実装・HDS境界・主体主幹・K/J経路の単体試験、negative control、回帰試験を保持する。

設計上の意味は `../設計/`、Layer-0の論理上位契約は `../REFERENCES.md` を参照する。試験コードだけから仕様を逆定義しない。

## 試験マップ

| Test | 主な対象 |
|---|---|
| `test_layer0.py` | Layer-0命令実行器の基本作用 |
| `test_hds_ir_gate.py` | HDS-IR局所閉包、未確定入力・座標欠落negative control |
| `test_hds_adapter.py` | 外部HDS Compiler接続、時間文脈、意味確定Data競合 |
| `test_hds_data_k.py` | Data HDS-IRからK構造Factへの接続 |
| `test_k3_hds_native.py` | HDS-IRネイティブK3経路、根拠なし・同率時の保留 |
| `test_k3_hds_structural.py` | 問題・候補・DataのHDS構造照合、関係経路 |
| `test_k3_equivalence.py` | K3公開構造に対する機能相当評価 |
| `test_runtime.py` | R、採否、矛盾・境界違反、結果形成 |
| `test_subject_trunk.py` | 主体状態持続、理由なし反転、主体主幹迂回防止 |
| `test_multilingual_trinity.py` | 多言語HDS実行核、Trinity J/C/M文脈、互換Compiler |
| `test_natural_language.py` | HDS Compiler未接続時のLegacy自然言語入口 |
| `test_reference.py` | 固定・複合参照供給器 |
| `test_cli.py` | module / JSON CLI、UTF-8標準入出力境界 |

## 実行

```bash
python -m unittest discover -s tests -v
```

CIでは上記に加え、リポジトリ整合性監査、構文確認、module CLI、console scriptをLinux / Windows × Python 3.11–3.14で確認する。

## 状態の解釈

単体試験PASSは、その試験が定義する局所条件の成立を示す。

```text
局所test PASS
!= Layer-0上位契約全体の普遍性証明
!= 製品・最終完成
```

プロトタイプ完成の固定判定は `../評価/PROTOTYPE_COMPLETION_2026-08-22.md` を参照する。
