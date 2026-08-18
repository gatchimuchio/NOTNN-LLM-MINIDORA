# MINIDORA K3教師データ写像 MVP v0.2

## 目的

本MVPの目的は一つ。

```text
K3公開情報を教師データとして固定
↓
HDSで意味・機構・成立関係を分別
↓
LLM Layer-0の機能責任へ写像
↓
意味系を日本語の実行可能構文Pとして再記述
↓
Layer-0がPを実行
↓
非ニューラルLLM計算主体の最小閉路を確認
```

K3固有architectureを非ニューラルに模倣しない。
2.8T scalarを一個ずつ概念へ対応付けない。
日本語は内部意味・命令構文の基底であり、外部入出力を日本語へ限定しない。

## 教師／方法／写像先／成果の分離

- **教師データ**: Kimi K3の公開情報、Kimi Linear、Attention Residuals等
- **方法**: HDS
- **写像先**: LLM Layer-0
- **再記述言語**: 日本語
- **成果**: Layer-0が実行可能な命令形保持体P
- **外部Data**: R。Pと分離し、必要時に参照する

## MVPで実装したLayer-0責任

K3固有語ではなく、次の実装非依存責任だけを実行する。

1. 内容依存の選択参照・状態更新
2. 条件付き命令変換
3. 有効直列深度
4. 結果形成

`KDA / MLA / AttnRes / MoE / 896 / Top-16 / 93 layers` は教師観測にのみ存在し、Layer-0の命令語彙には存在しない。

## 日本語命令P

`p/命令形P.json` が正本。

## 表層言語

内部Pは日本語基底だが、外部入力は別Adapter。

MVPでは同一意味要求へ次を写像する例を持つ。

```text
日本の首都は？
What is the capital of Japan?
日本的首都是哪里？
```

すべて内部では、

```text
要求種: 関係質問
対象: 日本
関係列: [首都]
```

へ落ちる。

これは「一般多言語理解完成」の主張ではなく、**外部言語と内部日本語基底が別責任であることの実証**。

## 実行

```bash
python -m unittest discover -s tests -v

PYTHONPATH=src python -m minidora.cli "日本の首都は？"
PYTHONPATH=src python -m minidora.cli "What is the capital of Japan?"
PYTHONPATH=src python -m minidora.cli "日本的首都是哪里？"
PYTHONPATH=src python -m minidora.cli "太郎の親の親は？"
PYTHONPATH=src python -m minidora.cli "(2+3)*4"
```

## 主張境界

このMVPが成立確認するのは、K3教師データ→HDS分別→Layer-0責任の追跡可能な写像、日本語命令P、Layer-0/P/R/表層Adapterの責任分離、多段関係処理、Data差替え、P差替え、未解／矛盾停止まで。

K3同等能力、一般多言語理解、open-domain知識、自由生成、frontier性能は未成立。
