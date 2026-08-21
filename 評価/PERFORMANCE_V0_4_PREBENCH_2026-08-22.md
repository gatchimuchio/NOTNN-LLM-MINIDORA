# MINIDORA v0.4 性能改善候補 — 再ベンチ前監査 2026-08-22

**状態: IMPLEMENTED / REGRESSION PASS / EXTERNAL BENCHMARK NOT YET RERUN**

この文書は、MINIDORAプロトタイプ完成baseline `GPQA Diamond 8 / 198` の後に行った性能改善について、外部ベンチ再実行前の実装状態を固定する。

## 1. この記録が示すこと

現行性能候補では、K3機能相当47/47を維持したまま、実タスク経路で観測された次の損失源を修正した。

1. 問い・候補・graphで意味語正規化が一致していなかった。
2. HDS Compiler導出座標が `原文範囲` 不在だけで意味署名から落ちていた。
3. 同一HDS文書内に分散した意味がFact単位採点で接続できなかった。
4. 同一意味Factを複数sourceが支持してもcanonical Kでprovenanceが1件へ潰れていた。
5. graph探索深さが固定的で、問いの構造量と連動していなかった。
6. HDS Runtimeの外部参照が問題文1 queryに固定されていた。
7. 複合参照Rで先頭Providerが上限を埋めると後続Providerが使われなかった。

## 2. 実装した性能改善

### 意味接続

- 問い / 候補 / graphで共通 `意味語` 正規化を使用する。
- 単純な英語屈折差を吸収する。
- 確定・推定されたCompiler導出座標を意味署名へ含める。
- 未確定 / 未観測 / 矛盾 / 留保は確定署名へ昇格しない。

### K / 証拠保持

- Kのcanonical Fact重複排除は維持する。
- それとは別に、独立sourceごとのHDS証拠Fact台帳を保持する。
- 同一HDS文書内の分散意味は低重みdocument evidenceとして再統合する。
- 未確定関係がある文書を、単なる共起で確定関係へ迂回昇格させない。

### graph reasoning

- 意味語正規化を問い・候補と統一する。
- 未確定 / 未観測 / 矛盾 / 留保のHDS関係を確定graph経路から除外する。
- まず4段で探索し、未到達時だけK3型effort policyに従って追加探索する。

### P / effort

HDS構造量から `low / high / max` を決定論的に選び、K3の `DistilledEffortPolicyController` へ接続した。

| effort | 証拠採用上限 | graph追加探索上限 |
|---|---:|---:|
| low | 3 | 6 |
| high | 5 | 8 |
| max | 8 | 10 |

4択問題は最低 `high` とし、関係密度・残差・意味構造量が大きい場合は `max` へ上げる。ベンチ名・正解情報は使用しない。

### R / Data coverage

- HDS正規化文だけでなく、確定意味座標から主題queryを形成する。
- 各choiceを**全候補対称**に主題queryへ結合して検索する。
- query結果はround-robinで統合する。
- 複数Providerもround-robinで統合し、先頭Providerによる独占を防ぐ。

これは正解choiceを特別扱いしないためgold leakageではない。

## 3. 維持した境界

- J/HDSの `NO_GUESS` を緩めていない。
- `AMBIGUOUS_EVIDENCE` はSUSPENDのまま維持する。
- provenance proofを持たないknowledge candidateをAPPROVEしない。
- 未確定関係を確定根拠へ昇格させない。
- GPQA固有ルールを追加していない。
- HDS Compiler内部方式を変更していない。
- Layer-0上位契約を変更していない。

## 4. 内部検証

GitHub Actions run #164:

- Ubuntu Python 3.11 / 3.12 / 3.13 / 3.14: PASS
- Windows Python 3.11 / 3.12 / 3.13 / 3.14: PASS
- repository consistency audit: PASS
- full unittest: PASS
- module CLI / console CLI: PASS
- K3機能相当: **47 / 47 PASS**

Ubuntu Python 3.12の代表run:

- unit tests: **74 tests PASS**
- K3 equivalence elapsed: 約0.55秒
- peak tracemalloc: 約4.47 MiB
- K3 fit metrics: before NLL 2.9444 / after NLL 0.2247

これらは回帰・構造適合の確認であり、GPQA性能値ではない。

## 5. GPQA baselineとの関係

プロトタイプ完成baseline:

```text
GPQA Diamond
8 / 198 = 4.0404040%
answered 27
SUSPEND 171
retrieval empty 98 / 198
```

このbaselineは履歴固定値として上書きしない。

本性能候補について、**公開リポジトリ内には完成runで使用したGPQA入力・HDS Compiler実装・OpenAlex/Wikipedia取得Data/HDS-IR一式が保存されていないため、同条件の外部GPQA再実行はこのリポジトリ単体では再現できない。**

したがって、この文書から「GPQAスコアが8/198より上がった」とは主張しない。

## 6. 次回外部再ベンチの固定条件

新しいGPQA値を正式記録するには、少なくとも次を揃える。

1. 同一GPQA Diamond 198問。
2. 問題・4候補を全件HDS Compilerへ通す。
3. 外部取得Dataを全件HDS Compilerへ通す。
4. 生文字列DataをKへ直入れしない。
5. OpenAlex / Wikipedia等のProvider条件を記録する。
6. gold labelをCompiler / R / K / P / Jへ渡さない。
7. gold labelは採点時だけ使用する。
8. answered / SUSPEND / correct / retrieval empty / Data件数 / HDS座標 / HDS関係 / K Factを記録する。
9. 旧8/198 baselineは保持し、新しい日付baselineを追加する。

## 7. 現在の判断

今回の変更は、性能を上げるためにJを緩めたものではなく、**既にHDS/K内に存在する意味・証拠・探索資源を本番経路で取り零していた実装損失を削減する変更**である。

次の正式な性能判断は、同条件の外部ベンチ再実行後に行う。
