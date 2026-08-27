# src

`src/` はMINIDORA Runtimeの実装ソースを保持する。

現行パッケージは `src/minidora/`。意味正本は `../設計/`、外部LLM成立正本は `../REFERENCES.md`、実測は `../評価/` を参照する。実装コードだけから上位仕様を逆定義しない。

## 現行主要境界

| Module | 主な責任 |
|---|---|
| `模型.py` | 言語対応、状態保持、一般/形成済み関係、参照寄与、候補共同再照合、終端成立差。正式knowledge choiceでは計算主体C |
| `hds判断主体.py` | Cが形成した候補差を証拠・矛盾・候補横断・Commit・総暫定性で裁定するHDS判断主体J |
| `hds判断参照境界.py` | 成功Data IRと実参照識別子・信頼を同一添字でJへ保持 |
| `hds_model_projection.py` | HDS構文化済みQuestion/Candidate/DataをC→Jへ接続し、Data残差の局所証拠境界を保持 |
| `言語構造.py` | 意味順序、有向関係、肯否、条件結合のHDS非依存構造化 |
| `規模測定.py` | 状態域・関係域・共有適用規模の三面測定 |
| `計算中間表現.py` | Compute IRに相当する計算専用型 |
| `計算実行境界.py` | ABI v1に相当する決定論的計算実行契約 |
| `命令計算降下.py` | 日本語命令形Pから計算中間表現への降下 |
| `計算実行器.py` | P互換入口を計算中間表現へ降下して実行 |
| `hds_compiler_v1.py` | Meaning/Audit Architecture v1.2 + Pipeline v1.3の公開HDS Compiler入口 |
| `hds_compiler_pipeline_v1_3.py` | 意味IR・計算計画・計算降下の責任分離 |
| `hds_ir.py` | 公開HDS意味IR RecordとGate |
| `hds_adapter.py` | HDS CompilerとのProtocol境界 |
| `layer0.py` | 旧Layer0 API互換窓口。現行LLM模型中核ではない |
| `runtime.py` | v0.4模型核と運用経路の統合入口 |
| `runtime_v03.py` | v0.3 Runtimeの履歴互換実装 |
| `旧_layer0_v03.py` | v0.3 Layer0命令器の履歴実装 |
| `命令.py` | 日本語命令形Pの実行前表現 |
| `参照.py` | 外部参照R |
| `主体.py` | 運用主体性 |
| `採否.py` | 採否 |
| `言語.py` | Legacy互換の決定論的計算意図形成・表面化 |
| `semantic_tokens.py` | 意味語内部住所 |
| `k3_functional.py` | K3構文化由来の能力補助 |
| `__main__.py` | CLI入口 |

## 上位LLM成立規定

- [gatchimuchio/LLM-Constitutive-Specification](https://github.com/gatchimuchio/LLM-Constitutive-Specification)
- 版 `2026-08-27-成立規定-3`
- 参照commit `306ff834e5ac7e7e958b513db723a24619c8895a`

## 模型核の関係域

```text
意味連続
順序連続
有向関係整合
肯否整合
履歴近接
条件結合
```

これらは世界知識ではなく、異なる言語状態・端点・文脈へ再利用する一般模型関係である。v3ではこれに状態保持・参照寄与・候補共同再照合・形成済み関係分離を接続する。`模型.py` / `言語構造.py` はHDSへ依存しない。

## 正式knowledge choice

```text
R
↓ 実識別子・信頼
HDS構文化済みData
↓
MINIDORA模型核 C
↓ 候補差
HDS判断主体 J
↓
APPROVE / SUSPEND
```

Cは候補差を形成するだけで最終採否権を持たない。Jは同一source共通支持、完全支持、弱支持、反証、競合、未閉包を分別し、Commit/HOLDを裁定する。Dataの`semantic_loss`はsource全体を確定証拠へ上げず、残差の影響座標が関係端点へ掛かる場合はその関係だけを局所留保する。

## HDS Compiler現行経路

```text
自然言語
↓
意味コンパイル
↓
意味HDS-IR
├─ R / K / J / 監査
└─ 計算計画
   ↓
 計算降下
   ↓
 計算中間表現
```

`意味コンパイル()` の結果へP・計算初期状態を混入しない。`コンパイル()` は旧Runtime向け互換窓口に限定する。

## 規模測定

`規模測定.py` は模型核単体を対象にし、外部参照R・HDS Compiler・HDS判断主体J・主体主幹・K3補助・計算実行器を加算しない。

現行v2測定は **局所成立候補**。詳細は `../評価/MINIDORA_v0_4_規模測定_v2_2026-08-26.md` を参照する。