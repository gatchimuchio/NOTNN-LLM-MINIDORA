# HDS Compiler Pipeline v1.3 受入記録

日付: 2026-08-26

## 対象

- MINIDORA v0.4
- Meaning/Audit Architecture: `v1.2`
- Compiler Pipeline: `v1.3`
- validated head: `29fe0bbca28310a23c23ef22c5533814d9fd06c3`
- workflow run id: `32890261690`

## 変更目的

旧Compilerでは意味座標・関係を形成した後、計算計画を同じHDSIRへ `実行核 / 初期状態 / 種別 / 手順` として再結合していた。

Pipeline v1.3では、意味HDS-IRと計算計画を分離し、計算実行が必要な場合だけ別バックエンドで計算中間表現へ降下する。

## 受入した境界

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
 計算中間表現 v1
```

確認事項:

- `意味コンパイル()` のHDSIRは `手順=None`。
- 意味HDS-IRは計算初期状態を内包しない。
- `コンパイル束()` は意味IRと計算計画を別フィールドで保持する。
- 計算降下は形成済み束だけを使い、自然言語を再解析しない。
- `コンパイル()` はLegacy互換窓口でのみPを再付与する。
- 独立Data/候補コンパイルは意味入口を優先しPを混入しない。
- Meaning/Audit Architecture v1.2の既存能力を維持する。

## 実測

GitHub Actions `MINIDORA 再構築CI` run `32890261690`:

- Ubuntu / Windows × Python 3.11–3.14: **全8 job PASS**
- 代表job: **345 tests / OK**
- Pipeline v1.3追加試験: **9 / 9 PASS**
- Compute IR / ABI試験: 維持PASS
- K3相当構造: **47 / 47 PASS**
- module CLI: `5です。`
- console CLI: `5です。`

途中run `32890017426` は345試験中1件のみ失敗したが、原因は新規試験が `HDS関係.種別` を `HDS関係.関係種別` と誤記した試験コード側の観測名誤りであり、製品実装回帰ではなかった。修正後のrun `32890261690`で全PASSを確認した。

## 判定

```text
HDS Compiler Pipeline v1.3 責任分離
= PASS
```

ただし、これはMINIDORA v0.4の大規模性測定完了や製品完成を意味しない。

次関門は上流 `大規模言語模型成立規定` の規模記述に従う、状態域規模・関係域規模・共有適用規模の再測定である。
