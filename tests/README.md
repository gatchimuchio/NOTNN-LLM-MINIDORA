# tests

`tests/` はMINIDORA模型核・計算中間表現/実行境界・HDS境界・主体主幹・K/J経路の単体試験、negative control、回帰試験を保持する。

設計上の意味は `../設計/`、LLM成立上位契約は `../REFERENCES.md` を参照する。試験コードだけから仕様を逆定義しない。

## 現行追加試験

| Test | 主な対象 |
|---|---|
| `test_模型.py` | 文脈差→成立差、関係再利用、根拠なし停止、プログラム言語体系、Runtime模型核入口 |
| `test_計算IR_ABI.py` | P→計算中間表現降下、型付き状態参照、実行境界決定論、旧P互換、未確定停止 |
| `test_hds_compiler_pipeline_v1_3.py` | Architecture v1.2維持、Pipeline v1.3、意味IR/P分離、自然言語再解析なし計算降下、Legacy互換、独立Data意味入口 |
| `test_layer0.py` | 旧Layer0名が計算実行器互換aliasであること、汎用命令作用の回帰 |

## Pipeline v1.3必須negative control

- 意味IRへPを混入しない。
- 意味IRへ計算初期状態を混入しない。
- 計算降下時に自然言語を再解析しない。
- 独立Data/候補の意味IRへPを混入しない。
- 旧 `コンパイル()` の互換IRを意味正本として扱わない。

## 計算中間表現の必須negative control

- `$`文字列が計算実行境界へ残らない。
- 状態値と状態住所を同一視しない。
- 交換以外へ状態住所を渡すと失敗する。
- 未確定HDS入力を計算中間表現へ昇格しない。
- 同一IR+初期状態で同一結果になる。
- 旧P入口も計算中間表現を迂回しない。

## 既存回帰

HDS-IR Gate、外部参照、K/J、K3相当、主体主幹、多言語文脈、CLI等の既存試験を継続する。

## 実行

```bash
python -m unittest discover -s tests -v
```

CIでは上記に加え、リポジトリ整合性監査、構文確認、module CLI、console scriptをLinux / Windows × Python 3.11–3.14で確認する。

## 状態の解釈

```text
局所test PASS
!= 大規模性の測定完了
!= 製品・最終完成
```

HDS Compiler Pipeline v1.3の責任分離は受入済み。現行模型核の大規模性は別評価として測定する。
