# tests

`tests/` はMINIDORA模型核・計算中間表現/実行境界・HDS境界・主体主幹・K/J経路の単体試験、negative control、回帰試験を保持する。

設計上の意味は `../設計/`、LLM成立上位契約は `../REFERENCES.md` を参照する。試験コードだけから仕様を逆定義しない。

## 現行追加試験

| Test | 主な対象 |
|---|---|
| `test_模型.py` | 文脈差→成立差、関係再利用、根拠なし停止、プログラム言語体系、Runtime模型核入口 |
| `test_模型関係域.py` | 有向関係、肯否、履歴順序、条件結合、17一般関係族、HDS非依存 |
| `test_規模測定.py` | 状態域・関係域・共有適用規模の三面、544関係構造、256共有適用、一点閾値禁止 |
| `test_計算IR_ABI.py` | P→計算中間表現、型付き状態参照、実行境界決定論、旧P互換、未確定停止 |
| `test_hds_compiler_pipeline_v1_3.py` | Architecture v1.2維持、Pipeline v1.3、意味IR/P分離、再解析なし計算降下 |
| `test_layer0.py` | 旧Layer0名が計算実行器互換aliasであること |

## 模型関係域の必須negative control

- `A causes B` と `B causes A` を同一視しない。
- `A causes B` と `A does not cause B` を同一視しない。
- 履歴を集合和へ潰して順序差を捨てない。
- 条件付き関係を無条件関係へ潰さない。
- 模型核へHDS依存を逆流させない。
- 負の成立差だけで候補を確定しない。

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

## 実行

```bash
python -m unittest discover -s tests -v
python tools/規模測定.py
```

CIではリポジトリ整合性監査、構文確認、単体試験、規模測定、module CLI、console scriptをLinux / Windows × Python 3.11–3.14で確認する。

## 状態の解釈

```text
局所test PASS
!= 製品・最終完成
!= 現代ニューラルLLMとの物理規模同等
```

現行v0.4規模測定v2は **局所成立候補**。詳細は `../評価/MINIDORA_v0_4_規模測定_v2_2026-08-26.md` を参照する。
