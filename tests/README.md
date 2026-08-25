# tests

`tests/` はMINIDORA模型核・計算中間表現/実行境界・HDS境界・主体主幹・K/J経路の単体試験、negative control、回帰試験を保持する。

設計上の意味は `../設計/`、LLM成立上位契約は `../REFERENCES.md` を参照する。試験コードだけから仕様を逆定義しない。

## 現行追加試験

| Test | 主な対象 |
|---|---|
| `test_模型.py` | 文脈差→成立差、関係再利用、根拠なし停止、プログラム言語体系、Runtime模型核入口 |
| `test_計算IR_ABI.py` | P→計算中間表現降下、型付き状態参照、ABI決定論、旧P互換、HDS降下、未確定停止 |
| `test_layer0.py` | 旧Layer0名が計算実行器互換aliasであること、汎用命令作用の回帰 |

## 既存回帰

| Test | 主な対象 |
|---|---|
| `test_hds_ir_gate.py` | HDS-IR局所閉包、未確定入力・座標欠落negative control |
| `test_hds_adapter.py` | HDS Compiler接続、時間文脈、意味確定Data競合 |
| `test_hds_data_k.py` | Data HDS-IRからK構造Factへの接続 |
| `test_k3_hds_native.py` | HDS-IRネイティブK3経路、根拠なし・同率時の保留 |
| `test_k3_equivalence.py` | K3公開構造に対する機能相当評価 |
| `test_runtime.py` | R、採否、矛盾・境界違反、結果形成 |
| `test_subject_trunk.py` | 主体状態持続、理由なし反転、主体主幹迂回防止 |
| `test_multilingual_trinity.py` | 多言語HDS運用文脈、互換Compiler |
| `test_natural_language.py` | HDS Compiler未接続時のLegacy自然言語入口 |
| `test_reference.py` | 固定・複合参照供給器 |
| `test_cli.py` | module / JSON CLI、UTF-8標準入出力境界 |

## 計算中間表現の必須negative control

- `$`文字列がABIへ残らない。
- 状態値と状態住所を同一視しない。
- 交換以外へ状態住所を渡すと失敗する。
- 未確定HDS入力を計算中間表現へ昇格しない。
- 同一IR+初期状態で同一結果になる。
- 旧P入口も計算中間表現を迂回しない。

## 実行

```bash
python -m unittest discover -s tests -v
```

CIでは上記に加え、リポジトリ整合性監査、構文確認、module CLI、console scriptをLinux / Windows × Python 3.11–3.14で確認する。

## 状態の解釈

```text
局所test PASS
!= 大規模性の測定完了
!= HDS Compiler再設計完了
!= 製品・最終完成
```

v0.3プロトタイプ完成の固定判定は `../評価/PROTOTYPE_COMPLETION_2026-08-22.md` を参照する。現行模型核の大規模性は別評価として追加する。
