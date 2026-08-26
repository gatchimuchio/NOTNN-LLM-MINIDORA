# AGENTS.md — MINIDORA 実装・監査規約

## 1. Authority

作業時は次の順を優先する。

1. ユーザーの明示指示
2. 外部正本 **大規模言語模型成立規定**
3. `設計/` の現行MINIDORA局所契約
4. `src/minidora/` の現行実装
5. `tests/` / `評価/` の実測・回帰結果
6. `構文化/` の観測・再構成履歴
7. `artifacts/` の固定取得物・由来記録
8. 推測・一般論

外部正本:

- Repository: https://github.com/gatchimuchio/LLM-Constitutive-Specification
- 版: `2026-08-27-成立規定-3`
- 参照commit: `306ff834e5ac7e7e958b513db723a24619c8895a`
- 現行正本: `規定/02_大規模言語模型成立.md`

旧 `Layer-0` は歴史上の暫定名称であり、現行MINIDORAの構造名として新規使用しない。

## 2. 正本ブランチ

`main` を唯一の現行正本とする。ユーザーが明示的に別方針を指定しない限り、長期作業ブランチやPR前提の運用へ戻さない。

変更前に現物・近傍仕様・試験を確認し、変更後はCIまで確認する。

## 3. 規定言語

日本語をMINIDORAリポジトリの基底・規定言語とする。

他言語は、外部API、標準規格、プログラム構文、固有名、原文引用、検索再現等の**実務上やむを得ない境界**だけに限定する。

英語識別子や外部用語から日本語正本の意味を逆定義しない。

## 4. LLM成立と構成再現を分ける

LLM成立は `独立対象 / 文脈依存関係 / 関係再利用 / 言語対応 / 局所対応` の5条件で監査する。

既存LLMの作用をMINIDORAへ忠実に再構成する場合は、別に次の7条件を監査する。

```text
状態分離・保持・更新
意味・関係同一性追跡
未確定差の共存
寄与調整と確定分離
構成連鎖・再作用・再結合
再作用閉包・終端成立差
形成済み関係の保持と作用機構との分離
```

標準6模型関係は維持するが、6関係だけを構成再現全体とは扱わない。外部Dataが意味対応済み参照状態へ入った後、そのDataが候補差へどう寄与するかは模型核の監査対象である。

HDS型、検索器、計算実行器、主体主幹、表面化、製品harnessは模型核そのものへ混入させない。

## 5. 大規模性

言語模型性と大規模性を混同しない。

大規模性は外部正本に従い、少なくとも次を別に記録する。

- 状態域規模
- 関係域規模
- 共有適用規模

v0.3の性能値・プロトタイプ完成記録を、v0.4模型核の大規模性証拠へ無言転用しない。必要な再測定は新しい評価記録として追加する。

## 6. HDS公開境界

HDSはMINIDORAの観測・意味Projection・外部運用に利用できるが、HDSであること自体をLLM模型性の成立条件にしない。

公開HDS Compilerは現行リポジトリ内の公開実装として保持する。ただし今回のv0.4模型核再構成ではCompiler本体を新模型核へ合わせて先回り改変しない。

順序は次とする。

```text
LLM成立規定
→ MINIDORA模型核
→ 計算情報構造 / Compute IR
→ HDS Compiler lowering
```

HDS本体の上流理論・非公開解析正本を公開Compilerへ無断転記しない。

## 7. Legacyと履歴

過去の成果・評価・構文化を整理目的だけで削除しない。

- v0.2 / v0.3構文化
- PROTOTYPE COMPLETE記録
- GPQA等の固定実測
- 旧Layer-0責任契約

は履歴として残す。ただし現行設計へ無言復帰させない。

旧仕様を退役させる場合は、`設計/旧/` またはGit履歴へ位置を明示する。

## 8. 実装原則

- 日本語で書ける内部概念は日本語を優先する。
- 候補ID・正解ラベル・benchmark固有名を模型関係へ埋め込まない。
- 根拠差がない場合に勝手な一候補確定をしない。
- 確率・samplingを使う場合でも、それをLLM成立の普遍形式へ昇格させない。
- PへDataを埋め込まない。
- 共有言語基底へ百科事典的世界知識を混入しない。
- 取得・検索と模型側関係を同一視しない。
- 実行系の故障を模型側関係の消失へ自動帰属しない。
- 下流実装へ合わせて外部成立規定を曲げない。

## 9. 検証

最低限次を通す。

```bash
python tools/repository_consistency_check.py
python -m compileall -q src tests tools
python -m unittest discover -s tests -v
python -m minidora "2+3"
```

CIはLinux / Windows × Python 3.11–3.14で確認する。

失敗時は product regression / environment failure / dependency or upstream failure / documentation mismatch / test flakiness / audit inconclusive 等を切り分ける。