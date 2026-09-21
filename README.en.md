# NOTNN-LLM-MINIDORA — MINIDORA

> **A Japanese-first non-neural LLM research and implementation project that separates LLM constitutive requirements and capability effects from today's dominant implementation architecture, then reimplements them without neural networks or Transformers as the core.**

[日本語正本](README.md) / [Product](製品版/README.en.md) / [Design](設計/README.md) / [Evaluation](評価/README.md)

The Japanese documents are the normative source of meaning. The public repository does not publish complete internal-theory definitions or full theory-to-implementation mappings.

## Current status

| Evaluation line | Canon | GPQA Diamond |
|---|---|---:|
| Model core | **MINIDORA30** | **30 / 198 (15.15%)** |
| Core + scientific capability modules | **MINIDORA80** | **80 / 198 (40.40%)** |
| Integrated execution system | separate line | separate acceptance evidence |

Since 2026-09-09, canonical GPQA runs use newly retrieved `LIVE_ONLY` references and forbid frozen reference bundles.

MINIDORA80 same-run controlled A/B:

```text
modules OFF = 29 / 198 (14.65%)
modules ON  = 80 / 198 (40.40%)
net correct gain = +51
module activations = 55
correct activations = 55 / 55
regressions = 0
```

On the limited GPQA-score axis, this is in the same roughly-40% band as the 39% GPT-4 baseline reported by the original GPQA paper. The evaluation conditions are not identical, so this is not a claim of overall GPT-4 capability equivalence.

Canonical references:
- [Current canon](CURRENT_CANONICAL.md)
- [MINIDORA30](評価/GPQA_Diamond_MINIDORA30_E2E_正本_2026-09-09.md)
- [MINIDORA80](評価/GPQA_Diamond_MINIDORA80_Module_E2E_正本_2026-09-09.md)
- [Evaluation contract](評価/評価契約_v2.md)

## Architecture boundary

MINIDORA separates a compact model core from exchangeable capabilities.

```text
model core
├─ non-neural language model
├─ general capabilities
├─ deterministic computation
├─ external references
└─ execution / audit

capability modules
├─ conversation
├─ summarization
├─ extraction
├─ calculation
├─ knowledge reference
└─ additional general or specialist capabilities
```

Adding a capability module is not the same as retraining, fine-tuning, enlarging, or replacing the model core.

## Run

```bash
python -m pip install -e .
python -m minidora.製品版 --HDS --serve
```

Product-only entry:

```bash
python -m minidora.製品版 --serve
```

HTTP:

```text
POST /api/chat
GET  /api/trace/{trace_id}
GET  /api/capabilities
GET  /health
```

## Evaluation boundaries

MINIDORA keeps these separate:

```text
strict language-model conformance
!= reasoning mechanism
!= model-core performance
!= system performance with capability modules
!= product maturity
!= Large classification
```

Historical work logs and obsolete evaluation payloads are not duplicated in the default tree. Canonical development milestones and restore commits are recorded in [開発正本履歴.md](開発正本履歴.md). The `構文化/` corpus is retained as construction input, not treated as disposable work logs.

## Repository

| Path | Responsibility |
|---|---|
| [`src/minidora/`](src/minidora/) | current implementation |
| [`tests/`](tests/) | unit, regression and acceptance tests |
| [`設計/`](設計/) | public local design / compatibility boundaries |
| [`評価/`](評価/) | current canonical and acceptance evidence |
| [`docs/`](docs/) | current supporting documents |
| [`構文化/`](構文化/) | observation / reconstruction history |
| [`製品版/`](製品版/) | product documentation |
| [`artifacts/`](artifacts/) | small fixed artifacts only |

Large benchmark result JSON and frozen reference bundles are kept out of the default tree.

## Japanese-first policy

Japanese is the normative language and internal semantic source of truth. English is an external/publication surface.

## Verification

```bash
python tools/リポジトリ整合性監査.py
python tools/日本語基底監査.py
python tools/日本語基底詳細監査.py
python tools/公開境界監査.py
python -m compileall -q src tests tools
python -m unittest discover -s tests -q
```

## License

- Source code and implementation: **Apache License 2.0** — [LICENSE-APACHE-2.0](LICENSE-APACHE-2.0)
- Specifications, design, evaluation and documentation: **CC-BY-4.0** — [LICENSE-CC-BY-4.0](LICENSE-CC-BY-4.0)
- Scope: [LICENSE](LICENSE)
- Attribution: [NOTICE](NOTICE)

## Author

**がっちむち♂**
