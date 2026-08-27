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
- 版: `2026-08-28-成立規定-7`
- 参照commit: `debb83e091a705a5eac09ef4fb97a5b36305db6d`
- 正本: `規定/02_大規模言語模型成立.md`

MINIDORA内の現行参照定数は `src/minidora/規定参照.py` を正とする。v0.4以前のファイルに残る旧版記録を現行Authorityへ昇格しない。

## 2. 現行二核

v0.5では次を分離する。

```text
MINIDORA厳密言語模型
= 完全言語状態上の整合した確率法則

MINIDORA能力模型核
= 候補・証拠・関係評価 / 推論 / knowledge choice
```

旧 `MINIDORA模型核` / `模型核` は能力核互換名であり、厳密LM核を意味しない。

候補score、HDS寄与、GPQA得点をsoftmax等で確率へ変換し、厳密LM成立証拠へ読み替えない。

## 3. 厳密LM受入境界

最低限、次を満たす。

- 完全言語状態の標本空間を宣言する。
- 各prefix条件分布が厳密に1へ正規化される。
- 系列確率がchain ruleで一貫して計算できる。
- 可変長ではEOS/終端確率が正で、無限長へ確率質量が漏れない。
- 模型状態を保存・復元して同じ確率法則を再現できる。
- samplingを模型成立条件にしない。
- 非ニューラルであること、決定論的に確率値を算出することと、確率法則を持つことを矛盾扱いしない。

## 4. 能力・Large・呼称を分ける

```text
厳密LM成立
!= 推論能力
!= GPQA性能
!= Large
!= 現代LLM呼称適合
```

旧v0.4三面規模測定は履歴証拠として保存するが、v0.5のLarge成立証拠へ無言転用しない。

## 5. HDS境界

HDS Compiler / HDS判断主体 / 参照Rは厳密LM法則と分離する。

knowledge choice互換経路では能力模型核を利用する。後段HDSへ渡すのはMINIDORA能力出力だけとし、HOLD/REJECT後の差し戻しを追加しない。

HDS Dataや候補寄与を厳密LMの形成済み確率へ実行時に自動昇格しない。

## 6. 計算境界

旧Layer0は計算実行器互換名であり、厳密LM核ではない。

```text
日本語命令形P
→ 計算中間表現
→ 計算実行境界
→ 計算実行器
```

を維持する。

## 7. Legacy

過去の構文化、v0.3/v0.4評価、旧Layer-0、構成再現v3、GPQA実測は削除しない。履歴として残し、現行意味へ無言復帰させない。

## 8. 実装原則

- 日本語で書ける内部概念は日本語を優先する。
- 候補ID・正解ラベル・benchmark固有名を厳密LM法則へ埋め込まない。
- 世界知識を最小LMのbootstrapへ埋め込まない。
- 根拠差がない能力経路で勝手な一候補確定をしない。
- PへDataを埋め込まない。
- HDS型を厳密LM核へ逆流させない。
- 下流実装に合わせて外部成立規定を曲げない。

## 9. 正本ブランチと検証

`main` を唯一の現行正本とする。変更前はサンドボックスで検証し、完成差分だけmainへ還元する。

最低限:

```bash
python tools/repository_consistency_check.py
python -m compileall -q src tests tools
python -m unittest discover -s tests -v
python -m minidora "2+3"
```

CIはLinux / Windows × Python 3.11–3.14を確認する。
