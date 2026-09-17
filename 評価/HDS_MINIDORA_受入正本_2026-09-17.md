# HDS-MINIDORA 受入正本 — 2026-09-17

## 結論

HDS-MINIDORA系は、MINIDORA30系とは別系統の正本として保持する。

この文書はHDS-MINIDORA系の**受入評価正本**であり、MINIDORA30系のGPQA性能正本 `30/198` を置換しない。

## 1. RMW修正後の同run LIVE_ONLY比較

評価条件:

```text
GPQA Diamond 198/198
choice seed = 0
OpenAlex = disabled
Wikipedia = en
reference = LIVE_ONLY
同一run controlled A/B
```

GitHub Actions:

- run: `35195104842`
- evaluation head: `caf44f7afbbc47cdde137a419bf1a2f00dd22412`
- aggregate artifact: `10486474821`
- aggregate artifact digest: `sha256:bd790a4320c9f071c29e959e89e9999848d6ac9e5bc1405b4fd65f0ac356cfe3`

結果:

| 系 | 正答 | 扱い |
|---|---:|---|
| MINIDORA30互換 | **25 / 198** | 同run基準 |
| 並列HDS-v3 | **24 / 198** | HDS固有処理の観測 |

差分:

```text
改善 = 1
退行 = 2
純差 = -1
```

この結果により、RMW自己失効修正だけでは「HDS-MINIDORAがMINIDORA30水準を常に下回らない」という受入条件を満たさないことを確認した。

## 2. 原因と修正

### 原子的read-modify-write

同一作用が読取成果を同時に更新する場合、旧入力から同時産出物へ自己依存を自動付与していたため、追加参照作用が自身の出力状態を失効させる経路があった。

修正後は、同一作用内で読取・産出が重なるノードを旧版自動依存元から除外し、後続作用からの通常依存だけを形成する。

### 性能下限

RMW修正後にも1問の純退行が残ったため、性能下限を暗黙期待ではなく `HDS非退行包絡` の契約へ昇格した。

## 3. 非退行包絡の受入再生

同runで得た基準出力とHDS拡張出力に、最終実装した非退行包絡を適用した。

結果:

```text
正答 = 25 / 198
回答 = 112 / 198
保留 = 86 / 198
MINIDORA30互換との差 = 0
```

基準APPROVEは保持し、基準未承認時のHDS拡張は追加採用証明が無い限りshadow結果へ留めるため、観測済みMINIDORA30互換出力を下回らないことを確認した。

## 4. この値の意味

`25/198` は、HDS-MINIDORA系の新しいGPQA性能正本値ではない。

これは次の受入条件を確認するための再生値である。

> **HDS-MINIDORA系は、同一入力で得た既知成立基準を無証明で破壊せず、追加成果を証明付きでのみ昇格する。**

MINIDORA30系の現行GPQA性能正本は引き続き:

```text
MINIDORA30 / GPQA-E2E-LIVE / 30/198 / 15.151515151515152%
```

HDS-MINIDORA固有のGPQA性能値を正本化する場合は、HDS-MINIDORA最終構成そのものをLIVE_ONLY 198/198で新規実行し、別成果物として保存する。

## 5. 実装受入

HDS-MINIDORA現行実装はPR #118でmainへ統合した。

- main commit: `3ba94bc583f3ceac49413ad350af970b2c28d068`
- ブラウザCI: PASS
- 再構築CI: Ubuntu / Windows × Python 3.11–3.14 PASS
- main push再構築CI run: `35203423151` PASS

## 6. 系統境界

```text
MINIDORA30系正本
!=
HDS-MINIDORA系正本
```

この受入評価を理由にMINIDORA30を旧版化しない。

同様に、MINIDORA30の30/198をHDS-MINIDORA固有スコアとして転記しない。
